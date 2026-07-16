#!/usr/bin/env bash
# l1_chain.sh — L1 daily pipeline
# Usage: bash scripts/l1_chain.sh [--dry-run]
#
# Chain: flock → baseline → fetch → normalize → ingest → map → score → fu → export → commit → publish → 三件套
# Revenue: monthly idempotent via data/.last_revenue_{YYYY-MM} marker (gitignored)
# C1 sealed: institutional + flag_engine = SKIP
# Relay: Debian commits only; push is Mac-side

set -euo pipefail

# ── Flags ──────────────────────────────────────────────────────────────────
DRY_RUN=0
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=1
done

# ── Environment ───────────────────────────────────────────────────────────
ROOT="${TW_COVERAGE_ROOT:-$HOME/My-TW-Coverage}"
cd "$ROOT"
D=$(date +%Y-%m-%d)
YM=$(date +%Y-%m)
MARKER="data/.last_revenue_${YM}"
LOG_DIR="${HOME}/logs/l1-chain"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/${D}.log"
LOCKFILE="${ROOT}/.l1-chain.lock"

# ── flock ──────────────────────────────────────────────────────────────────
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "FATAL: another chain run is active (lock $LOCKFILE)" >&2
  exit 2
fi

# ── Helpers ────────────────────────────────────────────────────────────────
log() {
  local ts; ts=$(date '+%H:%M:%S')
  echo "[${ts}] $*" | tee -a "$LOG"
}

run_step() {
  local name="$1"; shift
  log "STEP=${name} START"
  local start_ts tmpout
  start_ts=$(date +%s)
  tmpout=$(mktemp)
  set +e
  eval "$@" >"$tmpout" 2>&1
  local exit_code=$?
  set -e
  local end_ts wall
  end_ts=$(date +%s)
  wall=$((end_ts - start_ts))
  tail -100 "$tmpout" | while IFS= read -r line; do
    log "  $line"
  done
  rm -f "$tmpout"
  if [[ $exit_code -eq 0 ]]; then
    log "STEP=${name} EXIT=0 WALL=${wall}s"
  else
    log "STEP=${name} EXIT=${exit_code} WALL=${wall}s"
  fi
  return $exit_code
}

check_soft_output() {
  local name="$1" exit_code="$2"; shift 2
  for f in "$@"; do
    if [[ -f "$f" ]] && [[ -s "$f" ]]; then
      if python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
        log "SOFT: ${name} EXIT=${exit_code} but ${f} valid — continuing"
        return 0
      fi
    fi
  done
  log "HARD: ${name} EXIT=${exit_code} with no valid output — STOPPING"
  return 1
}

get_db_count() {
  python3 -c "
import sqlite3
conn = sqlite3.connect('data/signals.sqlite')
conn.row_factory = sqlite3.Row
print(conn.execute('SELECT COUNT(*) FROM $1').fetchone()[0])
"
}

# ── Clear log ──────────────────────────────────────────────────────────────
: > "$LOG"
log "================================================================"
log "L1 CHAIN ${D} $(date '+%H:%M:%S %Z') DRY_RUN=${DRY_RUN}"
log "================================================================"

# ── Baseline ───────────────────────────────────────────────────────────────
log "=== BASELINE ==="
BASELINE_HEAD=$(git rev-parse HEAD)
log "HEAD=${BASELINE_HEAD}"
BASELINE_MD5=$(md5sum data/signals.sqlite | cut -d' ' -f1)
log "DB md5=${BASELINE_MD5}"
BASELINE_SIGNALS=$(get_db_count signals)
BASELINE_FUS=$(get_db_count followups)
log "signals=${BASELINE_SIGNALS} followups=${BASELINE_FUS}"
log "=== BASELINE DONE ==="

# ── Revenue tracking ──────────────────────────────────────────────────────
REV_FETCHED=0

# ── 2a: Fetch Announcements ───────────────────────────────────────────────
ANN_JSON="signals/candidates/${D}-announcements.json"
set +e
run_step fetch_announcements "python3 scripts/fetch_announcements.py --date '$D'"
ann_exit=$?
set -e
if [[ $ann_exit -ne 0 ]]; then
  check_soft_output fetch_announcements $ann_exit "$ANN_JSON" || {
    log "FATAL: fetch_announcements hard fail"; exit 1
  }
fi

# ── 2b: Fetch Revenue (marker gate) ────────────────────────────────────────
if [[ -f "$MARKER" ]]; then
  log "SKIP fetch_revenue: marker exists $MARKER"
else
  REV_JSON="signals/candidates/${D}-revenue.json"
  REV_JSON_ALT="signals/candidates/${YM}-revenue.json"
  set +e
  run_step fetch_revenue "python3 scripts/fetch_revenue.py --year-month '$YM'"
  rev_exit=$?
  set -e
  if [[ $rev_exit -eq 0 ]] || check_soft_output fetch_revenue $rev_exit "$REV_JSON" "$REV_JSON_ALT"; then
    REV_FETCHED=1
  else
    log "WARN: fetch_revenue failed (non-fatal)"
  fi
fi

# ── 2c/2d: C1 sealed ──────────────────────────────────────────────────────
log "SKIP institutional+flag: C1 sealed"

# ── 2e: Normalize ─────────────────────────────────────────────────────────
NORM="signals/candidates/${D}-normalized.json"
if ! run_step normalize "python3 scripts/normalize_candidate.py --date '$D'"; then
  log "FATAL: normalize failed"; exit 1
fi
[[ -f "$NORM" ]] || { log "FATAL: no $NORM"; exit 1; }
log "normalize: $(wc -c < "$NORM") bytes"

# ── 2f: Ingest (dry-run → real) ────────────────────────────────────────────
INGEST_CREATED=0

if ! run_step ingest_dryrun "python3 scripts/ingest_signals.py --dry-run '$NORM'"; then
  log "FATAL: ingest dry-run failed"; exit 1
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  set +e
  INGEST_OUTPUT=$(run_step ingest_real "python3 scripts/ingest_signals.py '$NORM'" 2>&1)
  ingest_exit=$?
  set -e
  [[ $ingest_exit -eq 0 ]] || { log "FATAL: ingest failed"; exit 1; }
  
  INGEST_CREATED=$(echo "$INGEST_OUTPUT" | grep -oP 'created=\K[0-9]+' || echo "0")
  log "ingest created=${INGEST_CREATED}"
  
  # Write revenue marker if revenue was fetched and ingest succeeded
  if [[ "$REV_FETCHED" -eq 1 ]]; then
    touch "$MARKER"
    log "MARKER: $MARKER"
  fi

  # ── Post-ingest (real run only) ────────────────────────────────────────
  if ! run_step map_all "python3 scripts/map_signal.py --all"; then
    log "WARN: map failed (non-fatal)"
  fi
  if ! run_step score_all "python3 scripts/score_signal.py --all"; then
    log "WARN: score failed (non-fatal)"
  fi
  if ! run_step fu_create "python3 scripts/list_followups.py --create"; then
    log "WARN: fu create failed (non-fatal)"
  fi
  if ! run_step fu_overdue "python3 scripts/list_followups.py --overdue"; then
    log "WARN: fu overdue failed (non-fatal)"
  fi
  if ! run_step export_all "python3 scripts/export_signals.py --all"; then
    log "FATAL: export failed"; exit 1
  fi

  # ── Porcelain: clean empty candidates ─────────────────────────────────
  for f in signals/candidates/${D}-*.json; do
    [[ -f "$f" ]] || continue
    if [[ ! -s "$f" ]]; then
      log "REMOVE 0-byte: $f"; rm -f "$f"; continue
    fi
    if python3 -c "
import json,sys; d=json.load(open('$f')); sys.exit(0 if isinstance(d,list) and not d else 1)
" 2>/dev/null; then
      case "$f" in
        *-announcements.json|*-revenue.json) log "KEEP (no-hit): $f" ;;
        *-normalized.json) log "SKIP: $f" ;;
        *) log "REMOVE empty: $f"; rm -f "$f" ;;
      esac
    fi
  done

  # ── Git commit ─────────────────────────────────────────────────────────
  log "=== GIT COMMIT ==="
  git add signals/exports/ signals/weekly_digest/ signals/watchlist.md signals/candidates/
  
  # git diff --cached --quiet: 0=has changes, 1=no changes
  if git diff --cached --quiet 2>/dev/null; then
    log "NO-OP: no changes"
  else
    git commit -m "l1-chain: ${D} (ingest created=${INGEST_CREATED})"
    log "COMMIT: $(git rev-parse HEAD)"
  fi

  # ── Publish DB ─────────────────────────────────────────────────────────
  log "=== PUBLISH_DB ==="
  bash scripts/publish_db.sh || bash scripts/publish_db.sh --force
  log "PUBLISH_DB: done"

  # ── Post-run state ─────────────────────────────────────────────────────
  log "=== POST-RUN ==="
  POST_MD5=$(md5sum data/signals.sqlite | cut -d' ' -f1)
  log "DB md5=${POST_MD5}"
  POST_SIGNALS=$(get_db_count signals)
  POST_FUS=$(get_db_count followups)
  log "signals=${POST_SIGNALS} followups=${POST_FUS}"
  POST_HEAD=$(git rev-parse HEAD)
  log "HEAD=${POST_HEAD}"

  # ── 三件套 ──────────────────────────────────────────────────────────────
  log "=== 三件套 ==="
  log "commit SHA: ${POST_HEAD}"
  NEW_EXPORTS=$(git show --name-only --pretty='' HEAD 2>/dev/null | grep -E '^(signals/exports|signals/weekly_digest)' || true)
  [[ -n "$NEW_EXPORTS" ]] && log "new exports: $NEW_EXPORTS" || log "new exports: (none)"
  log "md5: ${POST_MD5} (was ${BASELINE_MD5})"
  log "=== 三件套 DONE ==="
  log "delta: signals ${BASELINE_SIGNALS}→${POST_SIGNALS} (=$((POST_SIGNALS-BASELINE_SIGNALS))))"
else
  log "DRY-RUN: stopping after ingest dry-run"
fi

log "=== CHAIN DONE ==="
exit 0
