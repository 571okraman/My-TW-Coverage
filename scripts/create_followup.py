#!/usr/bin/env python3
"""create_followup.py — Manually create a follow-up item bound to a signal.

Complements list_followups.py --create (auto-creation, only for follow /
thesis_candidate signals). Manual creation covers analyst-initiated followups,
e.g. radar signals carrying card-level questions.

Usage:
  python scripts/create_followup.py --signal-id SIG-20260331-001 \
      --type financial_check --priority high --due 2026-07-15 \
      --question "…驗證問題…"

Acceptance (dry-run):
  python scripts/create_followup.py --signal-id <existing SIG> --type fact_check \
      --question "test" --dry-run   # prints [DRY-RUN] FU-..., writes nothing
"""
import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta

FOLLOWUP_TYPES = [
    "fact_check", "mapping_check", "exposure_check",
    "financial_check", "market_check", "repo_update_check",
]
PRIORITIES = ["high", "medium", "low"]


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


def next_fuid(conn, prefix_date):
    prefix = "FU-" + prefix_date.replace("-", "")
    cur = conn.execute(
        "SELECT id FROM followups WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (prefix + "%",),
    )
    row = cur.fetchone()
    seq = (int(row["id"].split("-")[-1]) + 1) if row else 1
    return f"{prefix}-{seq:03d}"


def main():
    ap = argparse.ArgumentParser(description="Manually create a follow-up item")
    ap.add_argument("--signal-id", required=True, help="Existing signal ID (SIG-...)")
    ap.add_argument("--type", required=True, choices=FOLLOWUP_TYPES)
    ap.add_argument("--question", required=True)
    ap.add_argument("--title", help="Default: '<signal title[:50]> - <type>'")
    ap.add_argument("--priority", default="medium", choices=PRIORITIES)
    ap.add_argument("--due", help="Due date YYYY-MM-DD (default: today +7d)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    args = ap.parse_args()

    if args.due:
        try:
            date.fromisoformat(args.due)
        except ValueError:
            print(f"FATAL: --due must be YYYY-MM-DD, got {args.due}", file=sys.stderr)
            sys.exit(1)

    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")
    if not os.path.exists(db_path):
        print(f"FATAL: DB not found at {db_path} (run init_signal_db.py first)", file=sys.stderr)
        sys.exit(1)

    conn = get_db(db_path)
    sig = conn.execute(
        "SELECT id, title FROM signals WHERE id=?", (args.signal_id,)
    ).fetchone()
    if not sig:
        print(f"FATAL: signal {args.signal_id} not found", file=sys.stderr)
        conn.close()
        sys.exit(1)

    today = date.today().isoformat()
    fuid = next_fuid(conn, today)
    due = args.due or (date.today() + timedelta(days=7)).isoformat()
    title = args.title or f"{sig['title'][:50]} - {args.type}"

    tag = "[DRY-RUN]" if args.dry_run else "[CREATE]"
    if not args.dry_run:
        conn.execute(
            """INSERT INTO followups(id, signal_id, title, question, followup_type, status, priority, due_date, created_at, updated_at) VALUES(?,?,?,?,?,'open',?,?,?,?)""",
            (fuid, args.signal_id, title, args.question, args.type,
             args.priority, due, today, today),
        )
        conn.commit()
    print(f"{tag} {fuid}: {args.type} priority={args.priority} due={due}")
    print(f"{'':10s}signal: {sig['id']} {sig['title'][:60]}")
    conn.close()


if __name__ == "__main__":
    main()
