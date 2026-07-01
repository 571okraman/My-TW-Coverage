#!/usr/bin/env python3
"""score_signal.py — Rule-based signal scoring across 6 dimensions."""
import argparse, json, os, sqlite3, sys
from datetime import date, datetime

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

TRUST_SCORE = {
    "high": 3, "medium": 2, "low": 1, "unverified": 0, None: 1
}
TRIGGER_FINANCIAL_IMPACT = {
    "policy_regulation": 2,
    "tech_shift": 2,
    "supply_demand_imbalance": 3,
    "supply_chain_reshuffling": 2,
    "anchor_customer_roadmap": 3,
    "financial_inflection": 3,
    "market_behavior_anomaly": 1,
}
SOURCE_TYPE_VERIFIABILITY = {
    "government": 3, "company_disclosure": 3, "exchange": 3,
    "report": 2, "news": 2, "patent": 2, "paper": 2,
    "social": 0, "unknown": 1,
}

def score_rigidity(conn, signal_id):
    """Based on trust_level of sources."""
    cur = conn.execute("SELECT trust_level FROM signal_sources WHERE signal_id=?", (signal_id,))
    scores = [TRUST_SCORE.get(r["trust_level"], 1) for r in cur.fetchall()]
    if not scores:
        return 0
    return min(3, sum(scores) // len(scores) + (1 if len(scores) > 1 else 0))

def score_mappability(conn, signal_id):
    """Based on how many topics/tickers are mapped."""
    cur = conn.execute("SELECT COUNT(*) as c FROM signal_topics WHERE signal_id=?", (signal_id,))
    topics = cur.fetchone()["c"]
    cur = conn.execute("SELECT COUNT(*) as c FROM signal_tickers WHERE signal_id=?", (signal_id,))
    tickers = cur.fetchone()["c"]
    if tickers >= 3:
        return 3
    if tickers >= 1 and topics >= 2:
        return 2
    if topics >= 1:
        return 1
    return 0

def score_financial_impact(conn, signal_id):
    """Based on trigger_type."""
    cur = conn.execute("SELECT trigger_type FROM signals WHERE id=?", (signal_id,))
    row = cur.fetchone()
    if not row:
        return 0
    return TRIGGER_FINANCIAL_IMPACT.get(row["trigger_type"], 1)

def score_time_sensitivity(conn, signal_id):
    """Based on event_date proximity."""
    cur = conn.execute("SELECT event_date FROM signals WHERE id=?", (signal_id,))
    row = cur.fetchone()
    if not row or not row["event_date"]:
        return 1
    try:
        ed = datetime.strptime(row["event_date"][:10], "%Y-%m-%d").date()
    except ValueError:
        return 1
    delta = (date.today() - ed).days
    if delta <= 7:
        return 3
    if delta <= 30:
        return 2
    if delta <= 90:
        return 1
    return 0

def score_priced_in(conn, signal_id):
    """Default medium — requires manual review."""
    cur = conn.execute("SELECT trigger_type FROM signals WHERE id=?", (signal_id,))
    row = cur.fetchone()
    tt = row["trigger_type"] if row else ""
    if tt in ("financial_inflection", "market_behavior_anomaly"):
        return 1  # more likely already priced
    return 2  # default: not yet priced in

def score_verifiability(conn, signal_id):
    """Based on source_type."""
    cur = conn.execute("SELECT source_type FROM signal_sources WHERE signal_id=?", (signal_id,))
    scores = [SOURCE_TYPE_VERIFIABILITY.get(r["source_type"], 1) for r in cur.fetchall()]
    if not scores:
        return 0
    return min(3, sum(scores) // len(scores))

def score_signal(conn, signal_id):
    s = {}
    s["rigidity"] = score_rigidity(conn, signal_id)
    s["mappability"] = score_mappability(conn, signal_id)
    s["financial_impact"] = score_financial_impact(conn, signal_id)
    s["time_sensitivity"] = score_time_sensitivity(conn, signal_id)
    s["market_not_priced_in"] = score_priced_in(conn, signal_id)
    s["verifiability"] = score_verifiability(conn, signal_id)
    s["total"] = sum(s.values())
    if s["total"] >= 16:
        s["status"] = "thesis_candidate"
    elif s["total"] >= 12:
        s["status"] = "follow"
    elif s["total"] >= 7:
        s["status"] = "radar"
    else:
        s["status"] = "expired"
    return s

def main():
    ap = argparse.ArgumentParser(description="Score signals across 6 dimensions")
    ap.add_argument("signal_id", nargs="?", help="Signal ID to score")
    ap.add_argument("--all", action="store_true", help="Score all non-expired signals")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()
    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")
    conn = get_db(db_path)
    if args.all:
        cur = conn.execute("SELECT id, title, status, score_total FROM signals WHERE status NOT IN ('expired','archived') ORDER BY id")
    elif args.signal_id:
        cur = conn.execute("SELECT id, title, status, score_total FROM signals WHERE id=?", (args.signal_id,))
    else:
        cur = conn.execute("SELECT id, title, status, score_total FROM signals ORDER BY id LIMIT 10")
    signals = cur.fetchall()
    if not signals:
        print("No signals to score.")
        return
    results = []
    for sig in signals:
        s = score_signal(conn, sig["id"])
        old_status = sig["status"]
        new_status = s["status"]
        if not args.dry_run:
            if new_status != old_status or s["total"] != sig["score_total"]:
                conn.execute("UPDATE signals SET status=?, score_total=?, updated_at=? WHERE id=?",
                             (new_status, s["total"], date.today().isoformat(), sig["id"]))
        result = {"signal_id": sig["id"], "title": sig["title"], "old_status": old_status,
                  "new_status": new_status if not args.dry_run else f"{old_status}->{new_status}",
                  "scores": s}
        results.append(result)
        print(f"[{new_status.upper():16s}] {sig['id']}: {sig['title'][:50]}")
        print(f"  rigidity={s['rigidity']} mappability={s['mappability']} fin_impact={s['financial_impact']} time={s['time_sensitivity']} priced_in={s['market_not_priced_in']} verify={s['verifiability']}  TOTAL={s['total']}")
    if not args.dry_run:
        conn.commit()
    conn.close()
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()