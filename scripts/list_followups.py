#!/usr/bin/env python3
"""list_followups.py — List, create, and manage follow-up items."""
import argparse, json, os, sqlite3, sys, uuid
from datetime import date, datetime, timedelta

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
    cur = conn.execute("SELECT id FROM followups WHERE id LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",))
    row = cur.fetchone()
    seq = (int(row["id"].split("-")[-1]) + 1) if row else 1
    return f"{prefix}-{seq:03d}"

def create_followups(conn, signal_id, dry_run):
    """Auto-create followups for a signal based on its status and trigger_type."""
    cur = conn.execute("SELECT id, title, trigger_type, status, priority, event_date FROM signals WHERE id=?", (signal_id,))
    sig = cur.fetchone()
    if not sig:
        print(f"  SKIP {signal_id}: not found")
        return 0
    if sig["status"] not in ("follow", "thesis_candidate"):
        return 0
    # Check if followups already exist
    cur = conn.execute("SELECT COUNT(*) as c FROM followups WHERE signal_id=?", (signal_id,))
    if cur.fetchone()["c"] > 0:
        return 0
    today = date.today().isoformat()
    created = 0
    # Determine followup types based on trigger_type
    tt = sig["trigger_type"]
    types_to_create = ["fact_check"]
    if tt in ("policy_regulation", "tech_shift"):
        types_to_create.append("mapping_check")
        types_to_create.append("exposure_check")
    elif tt in ("supply_demand_imbalance", "supply_chain_reshuffling"):
        types_to_create.append("exposure_check")
        types_to_create.append("financial_check")
    elif tt in ("financial_inflection", "market_behavior_anomaly"):
        types_to_create.append("financial_check")
        types_to_create.append("market_check")
    if sig["status"] == "thesis_candidate":
        types_to_create.append("repo_update_check")
    for ftype in types_to_create:
        fuid = next_fuid(conn, today)
        question = QUESTIONS.get(ftype, f"Verify {ftype} for {sig['title']}")
        due = (date.today() + timedelta(days=7)).isoformat()
        if not dry_run:
            conn.execute("""INSERT INTO followups(id, signal_id, title, question, followup_type, status, priority, due_date, created_at, updated_at) VALUES(?,?,?,?,?,'open',?,?,?,?)""",
                         (fuid, signal_id, f"{sig['title'][:50]} - {ftype}", question, ftype,
                          sig["priority"] or "medium", due, today, today))
        print(f"  {'[CREATE]' if not dry_run else '[DRY-RUN]'} {fuid}: {ftype}")
        created += 1
    return created

QUESTIONS = {
    "fact_check": "Does the source material support the claim?",
    "mapping_check": "Which themes/companies are affected?",
    "exposure_check": "Is the company exposure significant enough?",
    "financial_check": "Do monthly revenue / margin / backlog reflect this?",
    "market_check": "Has the market already priced this in?",
    "repo_update_check": "Do reports/themes need updating?",
}

def list_followups(conn, args):
    query = "SELECT f.*, s.title as signal_title, s.trigger_type FROM followups f LEFT JOIN signals s ON f.signal_id = s.id"
    conditions = []
    params = []
    if args.open:
        conditions.append("f.status IN ('open','in_progress')")
    if args.overdue:
        conditions.append("f.status IN ('open','in_progress') AND f.due_date < ?")
        params.append(date.today().isoformat())
    if args.signal_id:
        conditions.append("f.signal_id = ?")
        params.append(args.signal_id)
    if args.status:
        conditions.append("f.status = ?")
        params.append(args.status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY f.due_date ASC, f.priority DESC"
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    if not rows:
        print("No follow-ups found.")
        return rows
    for r in rows:
        sig_name = r["signal_title"][:40] if r["signal_title"] else "?"
        overdue = ""
        if r["due_date"] and r["status"] in ("open", "in_progress"):
            try:
                dd = datetime.strptime(r["due_date"][:10], "%Y-%m-%d").date()
                if dd < date.today():
                    overdue = " [OVERDUE!]"
            except ValueError:
                pass
        print(f"  {r['id']:25s} {r['followup_type']:20s} {r['status']:12s} due={r['due_date']}{overdue}")
        print(f"  {'':25s} {r['title'][:70]}")
        print(f"  {'':25s} signal: {sig_name}")
        print()
    return rows

def main():
    ap = argparse.ArgumentParser(description="List/create follow-up items")
    ap.add_argument("--all", action="store_true", help="List all follow-ups")
    ap.add_argument("--open", action="store_true", help="List open/in_progress follow-ups")
    ap.add_argument("--overdue", action="store_true", help="List overdue follow-ups")
    ap.add_argument("--create", action="store_true", help="Auto-create follow-ups for follow/thesis signals")
    ap.add_argument("--signal-id", help="Filter by signal ID")
    ap.add_argument("--status", help="Filter by status")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")
    conn = get_db(db_path)
    if args.create:
        # Find signals that need follow-ups
        cur = conn.execute("SELECT id, title, status FROM signals WHERE status IN ('follow','thesis_candidate') ORDER BY id")
        signals = cur.fetchall()
        print(f"Checking {len(signals)} signal(s) for follow-up creation...")
        total = 0
        for sig in signals:
            c = create_followups(conn, sig["id"], args.dry_run)
            total += c
        if not args.dry_run:
            conn.commit()
        print(f"Created {total} follow-up(s)")
    else:
        rows = list_followups(conn, args)
        if args.json:
            output = []
            for r in rows:
                output.append(dict(r))
            print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    conn.close()

if __name__ == "__main__":
    main()