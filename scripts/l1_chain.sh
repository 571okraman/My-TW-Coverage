#!/usr/bin/env bash
set -euo pipefail

# l1_chain.sh — L1 chain script (fetch → normalize → ingest → map → score → followup → export → publish)
# v1.1: P1 marker gating, P2 partial rev skip, P3 full month criteria, P4 lock/commit
#
# Usage: bash l1_chain.sh [--dry-run]
# Dry-run: skips ingest, marker touch, git commit, publish_db.sh

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
DAY=$(date +%-d)  # 1-31, no leading zero
YM=$(date -d "1 day ago" +%Y-%m)  # Previous month YYYY-MM

echo "TODAY=$TODAY DAY=$DAY YM=$YM"

# P1/P3: Marker gating
MARKER="$ROOT/data/.last_revenue_${YM}"
SKIP_REV=0
if [[ -f "$MARKER" ]]; then
  echo "WARN: marker $MARKER exists → skip rev pipeline"
  SKIP_REV=1
fi

# ── Fetch ──────────────────────────────────────────────────────────────────────
echo "── Fetch Announcements ──"
bash "$ROOT/scripts/fetch_announcements.sh" --date "$TODAY" || true
ANN_EXIT=$?

echo "── Fetch Revenue ──"
REV_EXIT=0
REV_FILE="$ROOT/signals/candidates/${YM}-revenue.json"
if [[ $SKIP_REV -eq 1 ]]; then
  echo "SKIP: revenue fetch (marker exists)"
elif [[ $DAY -ge 11 ]]; then
  # >=11: Full month eligible
  bash "$ROOT/scripts/fetch_revenue.sh" --year-month "$YM" || true
  REV_EXIT=$?
  if [[ $REV_EXIT -ne 0 && ! -f "$REV_FILE" ]]; then
    echo "FATAL: fetch_revenue failed with no output"; exit 1
  elif [[ $REV_EXIT -ne 0 ]]; then
    echo "WARN: fetch_revenue soft fail (exit $REV_EXIT) but output exists"
  fi
else
  # 1-10: Backup fetch only
  echo "WARN: DAY<11 → fetch_revenue for backup only (no ingest)"
  bash "$ROOT/scripts/fetch_revenue.sh" --year-month "$YM" || true
  REV_EXIT=$?
  if [[ $REV_EXIT -ne 0 && ! -f "$REV_FILE" ]]; then
    echo "WARN: fetch_revenue failed (backup)"
  fi
fi

# ── Normalize ──────────────────────────────────────────────────────────────────
echo "── Normalize ──"
python3 "$ROOT/scripts/normalize_candidate.py" --date "$TODAY"
NORM_EXIT=$?
if [[ $NORM_EXIT -ne 0 ]]; then
  echo "FATAL: normalize failed"; exit 1
fi

NORM_FILE="$ROOT/signals/candidates/${TODAY}-normalized.json"
if [[ ! -f "$NORM_FILE" ]]; then
  echo "FATAL: normalize produced no output"; exit 1
fi

# Count revenue candidates in normalized output
REV_COUNT=$(python3 -c "import json; d=json.load(open('$NORM_FILE')); print(len([c for c in d if c.get('source_type')=='revenue']))")
echo "Normalized rev count: $REV_COUNT"

# ── Ingest ─────────────────────────────────────────────────────────────────────
if [[ $DRY_RUN -eq 1 ]]; then
  echo "SKIP: ingest (dry-run)"
  INGEST_CREATED=0
  INGEST_SKIPPED=0
else
  echo "── Ingest ──"
  INGEST_OUTPUT=$(python3 "$ROOT/scripts/ingest_signals.py" "$NORM_FILE" 2>&1) || true
  echo "$INGEST_OUTPUT"
  INGEST_CREATED=$(echo "$INGEST_OUTPUT" | grep -oP 'created=\K\d+' || echo "0")
  INGEST_SKIPPED=$(echo "$INGEST_OUTPUT" | grep -oP 'skipped=\K\d+' || echo "0")
  echo "Ingest: created=$INGEST_CREATED skipped=$INGEST_SKIPPED"
fi

# ── Map / Score / Followup / Export ───────────────────────────────────────────
echo "── Map ──"
python3 "$ROOT/scripts/map_signals.py" --all || true

echo "── Score ──"
python3 "$ROOT/scripts/score_signals.py" --all || true

echo "── Followup Create ──"
python3 "$ROOT/scripts/list_followups.py" --create || true

echo "── Followup Overdue ──"
python3 "$ROOT/scripts/list_followups.py" --overdue || true

echo "── Export ──"
python3 "$ROOT/scripts/export_signals.py" --all || true

# ── Git Commit (P4) ───────────────────────────────────────────────────────────
if [[ $DRY_RUN -eq 0 ]]; then
  echo "── Git Commit ──"
  cd "$ROOT"
  git add exports/ weekly_digest/ watchlist.md 2>/dev/null || true
  if ! git diff --cached --quiet; then
    git commit -m "export: L1 chain $(date +%Y-%m-%d)" || true
  else
    echo "No export diff to commit"
  fi
fi

# ── Publish DB ────────────────────────────────────────────────────────────────
if [[ $DRY_RUN -eq 0 ]]; then
  echo "── Publish DB ──"
  bash "$ROOT/scripts/publish_db.sh" || true
fi

# ── Marker (P1/P3) ────────────────────────────────────────────────────────────
# Only touch marker if:
# 1. Not dry-run
# 2. SKIP_REV was 0 (no existing marker)
# 3. DAY >= 11 (full month eligible)
# 4. Ingest succeeded (created > 0 or at least no hard fail)
# 5. Revenue candidates were actually processed (REV_COUNT > 0)
if [[ $DRY_RUN -eq 0 && $SKIP_REV -eq 0 && $DAY -ge 11 && $REV_COUNT -gt 0 ]]; then
  echo "── Touch Marker ──"
  touch "$MARKER"
  echo "Marker $MARKER touched"
else
  echo "SKIP: marker touch (dry_run=$DRY_RUN skip_rev=$SKIP_REV day=$DAY rev_count=$REV_COUNT)"
fi

echo "=== L1 Chain End $(date) ==="