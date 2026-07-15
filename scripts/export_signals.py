#!/usr/bin/env python3
"""export_signals.py — Export signals/follow-ups to human-readable markdown."""
import argparse, os, sqlite3, sys
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

def export_signals(conn, root):
    """Export all active signals to signals/exports/YYYY-MM-DD-signals.md."""
    cur = conn.execute("SELECT * FROM signals WHERE status NOT IN ('expired','archived') ORDER BY score_total DESC, id")
    signals = cur.fetchall()
    if not signals:
        print("No active signals to export.")
        return
    today = date.today().isoformat()
    outdir = os.path.join(root, "signals", "exports")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{today}-signals.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Signal Dashboard — {today}\n\n")
        f.write(f"**Active signals:** {len(signals)}\n\n")
        f.write("| ID | Title | Type | Status | Score | Event Date |\n")
        f.write("|----|-------|------|--------|-------|------------|\n")
        for sig in signals:
            f.write(f"| {sig['id']} | {sig['title'][:60]} | {sig['trigger_type'][:25]} | {sig['status']} | {sig['score_total'] or '?'} | {sig['event_date'] or '?'} |\n")
        f.write("\n---\n\n")
        for sig in signals:
            f.write(f"## {sig['id']}: {sig['title']}\n\n")
            f.write(f"- **Trigger type:** {sig['trigger_type']}\n")
            f.write(f"- **Status:** {sig['status']}\n")
            f.write(f"- **Score:** {sig['score_total'] or 'unscored'}\n")
            f.write(f"- **Priority:** {sig['priority'] or 'unset'}\n")
            f.write(f"- **Event date:** {sig['event_date'] or 'unknown'}\n")
            f.write(f"- **Discovered:** {sig['discovered_at']}\n")
            if sig["summary"]:
                f.write(f"\n{sig['summary']}\n\n")
            # Sources
            cur2 = conn.execute("SELECT * FROM signal_sources WHERE signal_id=?", (sig["id"],))
            sources = cur2.fetchall()
            if sources:
                f.write("### Sources\n\n")
                for s in sources:
                    trust = {"high": "🟢", "medium": "🟡", "low": "🟠", "unverified": "⚪"}.get(s["trust_level"], "⚪")
                    f.write(f"- {trust} **{s['title'] or s['url'][:50]}** — {s['source_type']} ({s['trust_level']})\n")
                    if s["url"]:
                        f.write(f"  [{s['url'][:100]}]({s['url']})\n")
                    if s["extracted_summary"]:
                        f.write(f"  > {s['extracted_summary'][:200]}\n")
                f.write("\n")
            # Topics
            cur2 = conn.execute("SELECT topic, confidence FROM signal_topics WHERE signal_id=?", (sig["id"],))
            topics = cur2.fetchall()
            if topics:
                f.write(f"**Topics:** {', '.join(t['topic'] for t in topics)}\n\n")
            # Tickers
            cur2 = conn.execute("SELECT ticker, company_name, confidence FROM signal_tickers WHERE signal_id=? ORDER BY confidence", (sig["id"],))
            tickers = cur2.fetchall()
            if tickers:
                f.write("### Candidate Tickers\n\n")
                f.write("| Ticker | Company | Confidence |\n")
                f.write("|--------|---------|------------|\n")
                for t in tickers:
                    f.write(f"| {t['ticker']} | {t['company_name'] or '?'} | {t['confidence']} |\n")
                f.write("\n")
            f.write("---\n\n")
    print(f"Exported {len(signals)} signals to {path}")
    return path

def export_followups(conn, root):
    """Export open follow-ups to signals/exports/YYYY-MM-DD-followups.md."""
    cur = conn.execute("""SELECT f.*, s.title as signal_title FROM followups f
                          LEFT JOIN signals s ON f.signal_id = s.id
                          WHERE f.status IN ('open','in_progress')
                          ORDER BY f.due_date ASC""")
    items = cur.fetchall()
    if not items:
        print("No open follow-ups to export.")
        return
    today = date.today().isoformat()
    outdir = os.path.join(root, "signals", "exports")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{today}-followups.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Follow-up Queue — {today}\n\n")
        f.write(f"**Open items:** {len(items)}\n\n")
        f.write("| ID | Type | Status | Due | Signal |\n")
        f.write("|----|------|--------|-----|--------|\n")
        for fu in items:
            sig_name = fu["signal_title"][:40] if fu["signal_title"] else "?"
            f.write(f"| {fu['id']} | {fu['followup_type']} | {fu['status']} | {fu['due_date'] or '?'} | {sig_name} |\n")
        f.write("\n---\n\n")
        for fu in items:
            f.write(f"## {fu['id']}: {fu['title']}\n\n")
            f.write(f"- **Type:** {fu['followup_type']}\n")
            f.write(f"- **Status:** {fu['status']}\n")
            f.write(f"- **Priority:** {fu['priority'] or 'unset'}\n")
            f.write(f"- **Due:** {fu['due_date'] or 'none'}\n")
            f.write(f"- **Question:** {fu['question']}\n")
            f.write(f"- **Signal:** {fu['signal_title'] or fu['signal_id']}\n")
            if fu["result_summary"]:
                f.write(f"- **Result:** {fu['result_summary']}\n")
            if fu["decision"]:
                f.write(f"- **Decision:** {fu['decision']}\n")
            f.write("\n---\n\n")
    print(f"Exported {len(items)} follow-ups to {path}")
    return path

def export_watchlist(conn, root):
    """Generate signals/watchlist.md — thesis_candidate signals."""
    cur = conn.execute("SELECT * FROM signals WHERE status='thesis_candidate' ORDER BY score_total DESC")
    items = cur.fetchall()
    path = os.path.join(root, "signals", "watchlist.md")
    today = date.today().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Watchlist — {today}\n\n")
        if not items:
            f.write("*No thesis candidates currently.*\n")
            print("No thesis candidates — watchlist is empty.")
            return path
        f.write(f"**{len(items)} signals** flagged for deep research\n\n")
        for sig in items:
            f.write(f"### {sig['id']}: {sig['title']}\n\n")
            f.write(f"- **Score:** {sig['score_total']}\n")
            f.write(f"- **Trigger:** {sig['trigger_type']}\n")
            f.write(f"- **Discovered:** {sig['discovered_at']}\n")
            if sig["summary"]:
                f.write(f"\n{sig['summary']}\n\n")
            cur2 = conn.execute("SELECT ticker, company_name FROM signal_tickers WHERE signal_id=?", (sig["id"],))
            tickers = cur2.fetchall()
            if tickers:
                f.write("**Tickers:** " + ", ".join(f"{t['ticker']}({t['company_name'] or '?'})" for t in tickers) + "\n\n")
        print(f"Exported {len(items)} watchlist items to {path}")
    return path

def export_digest(conn, root):
    """Generate signals/weekly_digest/YYYY-Www.md."""
    today = date.today()
    iso_cal = today.isocalendar()
    week_dir = os.path.join(root, "signals", "weekly_digest")
    os.makedirs(week_dir, exist_ok=True)
    path = os.path.join(week_dir, f"{iso_cal[0]}-W{iso_cal[1]:02d}.md")
    cur = conn.execute("SELECT COUNT(*) as c FROM signals")
    total = cur.fetchone()["c"]
    cur = conn.execute("SELECT status, COUNT(*) as c FROM signals GROUP BY status")
    by_status = {r["status"]: r["c"] for r in cur.fetchall()}
    cur = conn.execute("SELECT COUNT(*) as c FROM followups WHERE status IN ('open','in_progress') AND due_date < ?", (today.isoformat(),))
    overdue = cur.fetchone()["c"]
    cur = conn.execute("SELECT * FROM signals WHERE status NOT IN ('expired','archived') ORDER BY score_total DESC LIMIT 5")
    top5 = cur.fetchall()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Signal Weekly Digest — {today.isoformat()}\n\n")
        f.write(f"## Overview\n\n")
        f.write(f"- **Total signals:** {total}\n")
        f.write(f"- **By status:** {', '.join(f'{k}={v}' for k, v in sorted(by_status.items()))}\n")
        f.write(f"- **Overdue follow-ups:** {overdue}\n\n")
        f.write(f"## Top Signals by Score\n\n")
        for sig in top5:
            f.write(f"- **{sig['id']}** ({sig['score_total']}): {sig['title'][:60]}\n")
        f.write("\n---\n*Auto-generated by export_signals.py*\n")
    print(f"Digest exported to {path}")
    return path

def main():
    ap = argparse.ArgumentParser(description="Export signals/follow-ups to markdown")
    ap.add_argument("--signals", action="store_true", help="Export signals dashboard")
    ap.add_argument("--followups", action="store_true", help="Export follow-up queue")
    ap.add_argument("--watchlist", action="store_true", help="Export watchlist")
    ap.add_argument("--digest", action="store_true", help="Export weekly digest")
    ap.add_argument("--all", action="store_true", help="Export everything")
    ap.add_argument("--db-path")
    args = ap.parse_args()
    root = get_project_root()
    db_path = args.db_path or os.environ.get("TW_SIGNALS_DB") or os.path.join(root, "data", "signals.sqlite")
    conn = get_db(db_path)
    if args.all or args.signals:
        export_signals(conn, root)
    if args.all or args.followups:
        export_followups(conn, root)
    if args.all or args.watchlist:
        export_watchlist(conn, root)
    if args.all or args.digest:
        export_digest(conn, root)
    if not any([args.signals, args.followups, args.watchlist, args.digest, args.all]):
        export_signals(conn, root)
        export_followups(conn, root)
    conn.close()

if __name__ == "__main__":
    main()