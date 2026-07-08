#!/usr/bin/env python3
"""resolve_followup.py — Update follow-up status (resolve / reject / expire / promote).

Closes the followup lifecycle per migrations/001 schema:
  open → in_progress → resolved / promoted / rejected / expired
Writes result_summary / decision / resolved_at. Can also postpone due_date.

Usage:
  # 驗證完成，销單
  python scripts/resolve_followup.py FU-20260702-003 --status resolved \
      --result "MOPS 6月營收 YoY +42%，支持 thesis" --decision keep

  # 延後到期日（例：等官源公布）
  python scripts/resolve_followup.py FU-20260702-005 --status open --due 2026-07-15

Acceptance (dry-run):
  python scripts/resolve_followup.py <existing FU> --status resolved \
      --result "test" --dry-run   # prints [DRY-RUN] … old → new, writes nothing
"""
import argparse
import os
import sqlite3
import sys
from datetime import date

STATUSES = ["open", "in_progress", "resolved", "promoted", "rejected", "expired"]
TERMINAL = {"resolved", "promoted", "rejected", "expired"}


def get_project_root():
    env = os.environ.get("TW_COVERAGE_ROOT")
    if env:
        return env
    d = os.path.dirname(os.path.abspath(__file__))
    c = os.path.dirname(d)
    if os.path.isdir(os.path.join(c, "migrations")):
        return c
    print("FATAL: cannot find TW_COVERAGE_ROOT", file=sys.stderr)
    sys.exit(1)


def get_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    ap = argparse.ArgumentParser(description="Update follow-up status")
    ap.add_argument("id", help="Follow-up ID (FU-...)")
    ap.add_argument("--status", required=True, choices=STATUSES)
    ap.add_argument("--result", help="result_summary text (required for terminal statuses)")
    ap.add_argument("--decision", help="decision text, e.g. keep / drop / promote")
    ap.add_argument("--due", help="New due date YYYY-MM-DD (postpone an open item)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    args = ap.parse_args()

    if args.due:
        try:
            date.fromisoformat(args.due)
        except ValueError:
            print(f"FATAL: --due must be YYYY-MM-DD, got {args.due}", file=sys.stderr)
            sys.exit(1)

    if args.status in TERMINAL and not args.result:
        print("FATAL: terminal status requires --result (result_summary)", file=sys.stderr)
        sys.exit(1)

    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")
    if not os.path.exists(db_path):
        print(f"FATAL: DB not found at {db_path} (run init_signal_db.py first)", file=sys.stderr)
        sys.exit(1)

    conn = get_db(db_path)
    row = conn.execute("SELECT * FROM followups WHERE id=?", (args.id,)).fetchone()
    if not row:
        print(f"FATAL: followup {args.id} not found", file=sys.stderr)
        conn.close()
        sys.exit(1)

    today = date.today().isoformat()
    resolved_at = today if args.status in TERMINAL else None

    tag = "[DRY-RUN]" if args.dry_run else "[UPDATE]"
    if not args.dry_run:
        conn.execute(
            """UPDATE followups SET status=?, result_summary=COALESCE(?, result_summary), decision=COALESCE(?, decision), due_date=COALESCE(?, due_date), resolved_at=?, updated_at=? WHERE id=?""",
            (args.status, args.result, args.decision, args.due,
             resolved_at, today, args.id),
        )
        conn.commit()
    print(f"{tag} {args.id}: {row['status']} → {args.status}")
    if args.result:
        print(f"{'':10s}result: {args.result[:70]}")
    if args.due:
        print(f"{'':10s}due: {row['due_date']} → {args.due}")
    conn.close()


if __name__ == "__main__":
    main()
