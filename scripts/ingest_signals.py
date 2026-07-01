#!/usr/bin/env python3
"""ingest_signals.py — JSON input → dedup → insert into Signal/Follow-up DB."""
import argparse, difflib, json, os, sqlite3, sys, uuid
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
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def next_signal_id(conn, event_date):
    prefix = "SIG-" + event_date.replace("-", "")
    cur = conn.execute("SELECT id FROM signals WHERE id LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",))
    row = cur.fetchone()
    seq = (int(row["id"].split("-")[-1]) + 1) if row else 1
    return f"{prefix}-{seq:03d}"

def title_similar(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def check_dup(conn, event):
    eid = event.get("id")
    if eid:
        if conn.execute("SELECT 1 FROM signals WHERE id=?", (eid,)).fetchone():
            return "duplicate_id"
    for src in event.get("sources", []):
        url = src.get("url", "").strip()
        if url and conn.execute("SELECT 1 FROM signal_sources WHERE url=?", (url,)).fetchone():
            return "duplicate_url"
    title = event.get("title", "").strip()
    if title:
        for row in conn.execute("SELECT title FROM signals"):
            if title_similar(title, row["title"]) > 0.85:
                return "duplicate_title"
    return None

def insert_signal(conn, ev, sid):
    now = date.today().isoformat()
    conn.execute("""INSERT INTO signals(id,title,summary,trigger_type,status,priority,event_date,discovered_at,expires_at,score_total,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,0,?,?)""",
                 (sid, ev.get("title"), ev.get("summary"), ev.get("trigger_type"), "radar",
                  ev.get("priority"), ev.get("event_date"), now, ev.get("expires_at"), now, now))
    for src in ev.get("sources", []):
        conn.execute("""INSERT INTO signal_sources(id,signal_id,url,title,publisher,source_type,trust_level,published_at,extracted_summary) VALUES(?,?,?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), sid, src.get("url"), src.get("title"), src.get("publisher"),
                      src.get("source_type"), src.get("trust_level"), src.get("published_at"), src.get("extracted_summary")))
    for topic in ev.get("topics", []):
        conn.execute("""INSERT OR IGNORE INTO signal_topics(signal_id,topic,theme_path,confidence) VALUES(?,?,?,?)""",
                     (sid, topic, None, "candidate"))
    for tkr in ev.get("tickers", []):
        conn.execute("""INSERT OR IGNORE INTO signal_tickers(signal_id,ticker,company_name,report_path,exposure_reason,confidence) VALUES(?,?,?,?,?,?)""",
                     (sid, tkr.get("ticker"), tkr.get("company_name"), tkr.get("report_path"), tkr.get("exposure_reason"), tkr.get("confidence", "candidate")))

def main():
    ap = argparse.ArgumentParser(description="Ingest signals from JSON")
    ap.add_argument("input", nargs="?", help="JSON file (default: stdin)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    args = ap.parse_args()
    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            events = json.load(f)
    else:
        events = json.load(sys.stdin)
    if not isinstance(events, list):
        events = [events]
    conn = get_db(db_path) if not args.dry_run else None
    created, skipped = 0, 0
    for ev in events:
        if conn:
            reason = check_dup(conn, ev)
        else:
            reason = None
        if reason:
            skipped += 1
            if args.dry_run:
                print(f"[DRY-RUN] SKIP [{ev.get('title','?')}]: {reason}")
            continue
        if conn:
            sid = next_signal_id(conn, ev.get("event_date", date.today().isoformat()))
            insert_signal(conn, ev, sid)
        else:
            sid = f"SIG-{uuid.uuid4().hex[:8]}"
        created += 1
        print(f"{'[DRY-RUN]' if args.dry_run else '[INSERT]'} {sid}: {ev.get('title','?')}")
    if conn:
        conn.commit()
        conn.close()
    print(f"created={created}, skipped={skipped}")

if __name__ == "__main__":
    main()
