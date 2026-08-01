#!/usr/bin/env bash
# publish_db.sh — Publish read-only copy of canonical signals.sqlite to ~/db-dist
# Usage: bash scripts/publish_db.sh [--force]
#
# Gate: aborts if My-TW-Coverage working tree is dirty (has uncommitted changes)
# unless --force is passed.
#
# PUBLISHED 判定（PS-20260701-002-T21 D3 防再發）：
#   只有當 GitHub origin master（fork remote，read-only fetch）與 local HEAD 一致時，
#   才回報 PUBLISHED。否則：
#     - remote 可讀且 != local  → PUBLISHED_LOCAL_ONLY（Debian 領先 = 待 Mac relay 接走，常態）
#     - remote 讀不到           → PUBLISHED_UNVERIFIED（無法對帳，視為異常）
#   後兩者皆 human_action_required=true。

set -eu

TW_COVERAGE_ROOT="${TW_COVERAGE_ROOT:-$HOME/My-TW-Coverage}"
CANONICAL="$TW_COVERAGE_ROOT/data/signals.sqlite"
DIST_DIR="/home/jyw-debian/db-dist"
DIST_DB="$DIST_DIR/signals.sqlite"
LOG="$DIST_DIR/PUBLISH_LOG"
FORCE="${1:-}"
# GitHub read-only remote（方案B：Debian 只有 fetch 能力，push 是 DISABLED）
REMOTE_NAME="${REMOTE_NAME:-fork}"

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
[[ "$DIST_DIR" != /home/jyw-debian/db-dist ]] && { echo "FATAL: DIST_DIR not /home/jyw-debian/db-dist"; exit 1; }
mkdir -p "$DIST_DIR"

# If target exists with 444, temporarily unlock for overwrite
if [ -f "$DIST_DB" ]; then
  chmod u+w "$DIST_DB" 2>/dev/null || true
fi

# Copy
cp "$CANONICAL" "$DIST_DB"
chmod 444 "$DIST_DB"

# Log
MASTER_SHA=$(git -C "$TW_COVERAGE_ROOT" rev-parse HEAD)
MASTER_SHORT=$(git -C "$TW_COVERAGE_ROOT" rev-parse --short HEAD)
MD5=$(md5sum "$DIST_DB" | awk '{print $1}')
NOW=$(date '+%Y-%m-%d %H:%M:%S')

# ── PUBLISHED 判定（D3 防再發）— 對帳 GitHub origin master ──────────────
# 只有 remote == local HEAD 才叫 PUBLISHED；否則誠實標 LOCAL_ONLY / UNVERIFIED。
HUMAN_ACTION_REQUIRED=false
REMOTE_SHA=""
if REMOTE_SHA=$(timeout 20 git -C "$TW_COVERAGE_ROOT" ls-remote "$REMOTE_NAME" refs/heads/master 2>/dev/null | awk '{print $1}'); then
  if [ -n "$REMOTE_SHA" ] && [ "$REMOTE_SHA" = "$MASTER_SHA" ]; then
    STATUS="PUBLISHED"
  else
    STATUS="PUBLISHED_LOCAL_ONLY"
    HUMAN_ACTION_REQUIRED=true
  fi
else
  STATUS="PUBLISHED_UNVERIFIED"
  HUMAN_ACTION_REQUIRED=true
fi

REMOTE_LABEL="${REMOTE_SHA:-unreachable}"
echo "$NOW | $STATUS | md5=$MD5 | master=$MASTER_SHORT | remote=$REMOTE_LABEL" >> "$LOG"

echo "$STATUS: md5=$MD5 master=$MASTER_SHORT remote=$REMOTE_LABEL"
if [ "$HUMAN_ACTION_REQUIRED" = "true" ]; then
  echo "  human_action_required=true"
  echo "  → Mac relay: cd ~/tmp/My-TW-Coverage && git fetch debian && git merge --ff-only debian/master && git push origin master && git ls-remote origin master"
fi
echo "  log: $LOG"

# UNVERIFIED = 連對帳都做不到，視為異常（chain 端有 || true，不會硬性中斷）
[ "$STATUS" = "PUBLISHED_UNVERIFIED" ] && exit 1
exit 0
