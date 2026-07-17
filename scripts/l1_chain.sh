#!/usr/bin/env bash
set -euo pipefail

# l1_chain.sh — L1 chain script
# Name mapping: fetch_announcements.sh->fetch_announcements.py, fetch_revenue.sh->fetch_revenue.py, map_signals.py->map_signal.py, score_signals.py->score_signal.py (fetch → normalize → ingest → map → score → followup → export → publish)
# v1.2: 正名修正 + 裁①硬失敗 + 裁②candidates commit
#
# Usage: bash l1_chain.sh [--dry-run]

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$HOME/logs/l1-chain"
LOG="$LOG_DIR/$(date +%Y-%m-%d).log"
LOCK="$ROOT/.l1-chain.lock"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  echo "DRY RUN MODE"
fi

# ── Setup ─────────────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

echo "=== L1 Chain Start $(date) ==="

# P4: flock (repo lock fd 9)
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "LOCK held by another process"; exit 1
fi

# ── Date Logic ────────────────────────────────────────────────────────────────
TODAY=$(date +%Y-%m-%d)
DAY=$(date +%-d)
YM=$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m)

echo "TODAY=$TODAY DAY=$DAY YM=$YM"

# P1: Marker gating — exists → skip rev pipeline
MARKER="$ROOT/data/.last_revenue_${YM}"
SKIP_REV=0
if [[ -f "$MARKER" ]]; then
  echo "WARN: marker $MARKER exists → skip rev pipeline"
  SKIP_REV=1
fi

# ── Fetch Announcements ──────────────────────────────────────────────────────
echo "── Fetch Announcements ──"
ANN_SCRIPT="$ROOT/scripts/fetch_announcements.py"
if [[ ! -f "$ANN_SCRIPT" ]]; then
  echo "HARD FAIL: missing $ANN_SCRIPT"; exit 1
fi
python3 "$ANN_SCRIPT" --date "$TODAY"
ANN_EXIT=$?
if [[ $ANN_EXIT -ne 0 ]]; then
  ANN_FILE="$ROOT/signals/candidates/${TODAY}-announcements.json"
  if [[ ! -f "$ANN_FILE" ]]; then
    echo "HARD FAIL: fetch_announcements exit $ANN_EXIT with no output"; exit 1
  else
    echo "WARN: fetch_announcements soft fail (exit $ANN_EXIT) but output exists"
  fi
fi

# ── Fetch Revenue ────────────────────────────────────────────────────────────
echo "── Fetch Revenue ──"
REV_EXIT=0
REV_SCRIPT="$ROOT/scripts/fetch_revenue.py"
if [[ ! -f "$REV_SCRIPT" ]]; then
  echo "HARD FAIL: missing $REV_SCRIPT"; exit 1
fi
REV_FILE="$ROOT/signals/candidates/${YM}-revenue.json"
if [[ $SKIP_REV -eq 1 ]]; then
  echo "SKIP: revenue fetch (marker exists)"
elif [[ $DAY -ge 11 ]]; then
  python3 "$REV_SCRIPT" --year-month "$YM"
  REV_EXIT=$?
  if [[ $REV_EXIT -ne 0 && ! -f "$REV_FILE" ]]; then
    echo "HARD FAIL: fetch_revenue exit $REV_EXIT with no output"; exit 1
  elif [[ $REV_EXIT -ne 0 ]]; then
    echo "WARN: fetch_revenue soft fail (exit $REV_EXIT) but output exists"
  fi
else
  echo "WARN: DAY<11 → fetch_revenue for backup only (no ingest)"
  python3 "$REV_SCRIPT" --year-month "$YM" || true
  REV_EXIT=$?
  if [[ $REV_EXIT -ne 0 && ! -f "$REV_FILE" ]]; then
    echo "WARN: fetch_revenue failed (backup)"
  fi
fi

# ── Normalize ──────────────────────────────────────────────────────────────────
echo "── Normalize ──"
NORM_SCRIPT="$ROOT/scripts/normalize_candidate.py"
if [[ ! -f "$NORM_SCRIPT" ]]; then
  echo "HARD FAIL: missing $NORM_SCRIPT"; exit 1
fi
python3 "$NORM_SCRIPT" --date "$TODAY"
NORM_EXIT=$?
if [[ $NORM_EXIT -ne 0 ]]; then
  echo "HARD FAIL: normalize failed"; exit 1
fi

NORM_FILE="$ROOT/signals/candidates/${TODAY}-normalized.json"
if [[ ! -f "$NORM_FILE" ]]; then
  echo "HARD FAIL: normalize produced no output"; exit 1
fi

# Count revenue candidates
REV_COUNT=$(python3 -c "import json; d=json.load(open('$NORM_FILE')); print(len([c for c in d if c.get('source_type')=='revenue']))")
echo "Normalized rev count: $REV_COUNT"

# ── Ingest ─────────────────────────────────────────────────────────────────────
if [[ $DRY_RUN -eq 1 ]]; then
  echo "SKIP: ingest (dry-run)"
  INGEST_CREATED=0
  INGEST_SKIPPED=0
else
  echo "── Ingest ──"
  INGEST_SCRIPT="$ROOT/scripts/ingest_signals.py"
  if [[ ! -f "$INGEST_SCRIPT" ]]; then
    echo "HARD FAIL: missing $INGEST_SCRIPT"; exit 1
  fi
  INGEST_OUTPUT=$(python3 "$INGEST_SCRIPT" "$NORM_FILE" 2>&1) || true
  echo "$INGEST_OUTPUT"
  INGEST_CREATED=$(echo "$INGEST_OUTPUT" | grep -oP 'created=\K\d+' || echo "0")
  INGEST_SKIPPED=$(echo "$INGEST_OUTPUT" | grep -oP 'skipped=\K\d+' || echo "0")
  echo "Ingest: created=$INGEST_CREATED skipped=$INGEST_SKIPPED"
fi

# ── Map / Score ────────────────────────────────────────────────────────────────
echo "── Map ──"
MAP_SCRIPT="$ROOT/scripts/map_signal.py"
if [[ ! -f "$MAP_SCRIPT" ]]; then
  echo "HARD FAIL: missing $MAP_SCRIPT"; exit 1
fi
python3 "$MAP_SCRIPT" --all || true

echo "── Score ──"
SCORE_SCRIPT="$ROOT/scripts/score_signal.py"
if [[ ! -f "$SCORE_SCRIPT" ]]; then
  echo "HARD FAIL: missing $SCORE_SCRIPT"; exit 1
fi
python3 "$SCORE_SCRIPT" --all || true

# ── Followup / Export ──────────────────────────────────────────────────────────
echo "── Followup Create ──"
python3 "$ROOT/scripts/list_followups.py" --create || true

echo "── Followup Overdue ──"
python3 "$ROOT/scripts/list_followups.py" --overdue || true

echo "── Export ──"
python3 "$ROOT/scripts/export_signals.py" --all || true

# ── Git Commit (裁②: candidates 實料入帳) ─────────────────────────────────────
if [[ $DRY_RUN -eq 0 ]]; then
  echo "── Git Commit ──"
  cd "$ROOT"
  
  # 空殼刪除（0-byte 或 [] JSON）
  for f in signals/candidates/*.json; do
    [[ -f "$f" ]] || continue
    if [[ ! -s "$f" ]] || python3 -c "import json; d=json.load(open('$f')); exit(0 if d else 1)" 2>/dev/null; then
      : # 有內容
    else
      rm -f "$f"
    fi
  done
  
  git add signals/exports/ signals/weekly_digest/ signals/watchlist.md 2>/dev/null || true
  git add signals/candidates/*.json signals/candidates/*.md 2>/dev/null || true
  if ! git diff --cached --quiet; then
    git commit -m "export: L1 chain $TODAY" || true
  else
    echo "No diff to commit"
  fi
fi

# ── Publish DB ────────────────────────────────────────────────────────────────
if [[ $DRY_RUN -eq 0 ]]; then
  echo "── Publish DB ──"
  bash "$ROOT/scripts/publish_db.sh" || true
fi

# ── Marker (P1/P3) ────────────────────────────────────────────────────────────
# P3: dual-market integrity check
if [[ $DRY_RUN -eq 0 && $SKIP_REV -eq 0 && $DAY -ge 11 ]]; then
  if [[ $REV_COUNT -eq 0 ]]; then
    echo "WARN: day>=$DAY but rev_count=0 — dual-market incomplete, skipping marker"
  else
  echo "── Touch Marker ──"
  touch "$MARKER"
  echo "Marker $MARKER touched"
  fi
fi

echo "=== L1 Chain End $(date) ==="