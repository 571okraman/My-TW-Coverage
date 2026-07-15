#!/usr/bin/env bash
# publish_db.sh — Publish read-only copy of canonical signals.sqlite to ~/db-dist
# Usage: bash scripts/publish_db.sh [--force]
#
# Gate: aborts if My-TW-Coverage working tree is dirty (has uncommitted changes)
# unless --force is passed.

set -eu

TW_COVERAGE_ROOT="${TW_COVERAGE_ROOT:-$HOME/My-TW-Coverage}"
CANONICAL="$TW_COVERAGE_ROOT/data/signals.sqlite"
DIST_DIR="$HOME/db-dist"
DIST_DB="$DIST_DIR/signals.sqlite"
LOG="$DIST_DIR/PUBLISH_LOG"
FORCE="${1:-}"

# Gate: canonical must exist
if [ ! -f "$CANONICAL" ]; then
  echo "FATAL: canonical DB not found at $CANONICAL"
  exit 1
fi

# Gate: clean working tree (unless --force)
if [ "$FORCE" != "--force" ]; then
  DIRTY=$(git -C "$TW_COVERAGE_ROOT" status --porcelain 2>/dev/null || true)
  if [ -n "$DIRTY" ]; then
    echo "ABORT: working tree dirty — refuse to publish."
    echo "Use --force to override."
    exit 1
  fi
fi

# Ensure dist dir
mkdir -p "$DIST_DIR"

# If target exists with 444, temporarily unlock for overwrite
if [ -f "$DIST_DB" ]; then
  chmod u+w "$DIST_DB" 2>/dev/null || true
fi

# Copy
cp "$CANONICAL" "$DIST_DB"
chmod 444 "$DIST_DB"

# Log
MASTER_SHA=$(git -C "$TW_COVERAGE_ROOT" rev-parse --short HEAD)
MD5=$(md5sum "$DIST_DB" | awk '{print $1}')
NOW=$(date '+%Y-%m-%d %H:%M:%S')
echo "$NOW | md5=$MD5 | master=$MASTER_SHA" >> "$LOG"

echo "PUBLISHED: md5=$MD5 master=$MASTER_SHA"
echo "  log: $LOG"
