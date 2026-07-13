#!/usr/bin/env python3
"""report_scaffold.py — Generate a report scaffold from signals/followups.

Usage:
  python scripts/report_scaffold.py --output signals/exports/report-2026-07-13.md
  python scripts/report_scaffold.py --output /dev/stdout --dry-run
"""
import argparse
import os
import sys
from datetime import date

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
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    ap = argparse.ArgumentParser(description="Generate a report scaffold from followups")
    ap.add_argument("--output", required=True, help="Output file path")
    ap.add_argument("--dry-run", action="store_true", help="Print to stdout only")
    ap.add_argument("--db-path", help="DB path (default: ./data/signals.sqlite)")
    args = ap.parse_args()

    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")

    if not os.path.exists(db_path):
        print(f"FATAL: DB not found at {db_path} (run init_signal_db.py first)", file=sys.stderr)
        sys.exit(1)

    conn = get_db(db_path)

    # Query followups grouped by status
    rows = conn.execute("""
        SELECT status, priority, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM followups
        GROUP BY status, priority
        ORDER BY
            CASE status WHEN 'open' THEN 0 WHEN 'pending' THEN 1 WHEN 'resolved' THEN 2 ELSE 3 END,
            CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END
    """).fetchall()

    today = date.today().isoformat()
    header = f"# Report {today}"

    lines = [header, ""]

    for row in rows:
        status = row["status"]
        priority = row["priority"]
        cnt = row["cnt"]
        ids = row["ids"]
        lines.append(f"## {status.upper()} ({priority.upper()}) — {cnt} items")
        lines.append("")
        lines.append(f"- IDs: {ids}")
        lines.append("")

    conn.close()

    if args.dry_run:
        print("\n".join(lines))
        return

    # Ensure output directory exists
    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[REPORT] {args.output} created ({today})")

if __name__ == "__main__":
    main()
