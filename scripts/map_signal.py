#!/usr/bin/env python3
"""map_signal.py — Signal topic → themes/WIKILINKS → candidate tickers."""
import argparse, json, os, re, sqlite3, sys

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

def load_wikilinks(root):
    """Parse WIKILINKS.md → {topic: [ticker, ...]}."""
    path = os.path.join(root, "WIKILINKS.md")
    if not os.path.exists(path):
        print("WARN: WIKILINKS.md not found", file=sys.stderr)
        return {}
    # Parse format: - [[topic]] (count)
    topic_map = {}
    with open(path) as f:
        for line in f:
            m = re.match(r'-\s+\[\[(.+?)\]\]\s+\((\d+)\)', line)
            if m:
                topic_map[m.group(1).lower()] = int(m.group(2))
    return topic_map

def load_themes(root):
    """Parse themes/*.md → {theme_name: [(ticker, company_name), ...]}."""
    themes_dir = os.path.join(root, "themes")
    if not os.path.isdir(themes_dir):
        print("WARN: themes/ not found", file=sys.stderr)
        return {}
    themes = {}
    for fn in os.listdir(themes_dir):
        if not fn.endswith(".md") or fn == "README.md":
            continue
        fp = os.path.join(themes_dir, fn)
        name = fn[:-3]
        tickers = []
        with open(fp) as f:
            for line in f:
                m = re.match(r'-\s+\*\*(\d+)\s+(.+?)\*\*', line)
                if m:
                    tickers.append((m.group(1), m.group(2).strip()))
        if tickers:
            themes[name.lower()] = tickers
    return themes

def match_topics(signal_topics, wikilinks, themes):
    """For each signal topic, find matching themes and tickers."""
    results = {}  # topic -> matched themes
    for topic in signal_topics:
        tl = topic.lower()
        matched = []
        # Direct match in themes
        if tl in themes:
            matched.append({"theme": tl, "source": "themes_direct", "tickers": themes[tl]})
        # Substring match in themes
        for tname, tickers in themes.items():
            if tl in tname or tname in tl:
                if tl != tname:
                    matched.append({"theme": tname, "source": "themes_fuzzy", "tickers": tickers})
        # Check if it's a known wikilink
        if tl in wikilinks:
            if not matched:
                matched.append({"source": "wikilink_only", "count": wikilinks[tl]})
        results[topic] = matched
    return results

def main():
    ap = argparse.ArgumentParser(description="Map signal topics to themes/tickers")
    ap.add_argument("signal_id", nargs="?", help="Signal ID to map")
    ap.add_argument("--all", action="store_true", help="Map all unmapped signals")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()
    root = get_project_root()
    db_path = args.db_path or os.path.join(root, "data", "signals.sqlite")
    wikilinks = load_wikilinks(root)
    themes = load_themes(root)
    conn = get_db(db_path)
    if args.all:
        cur = conn.execute("SELECT DISTINCT s.id, s.title FROM signals s WHERE s.id NOT IN (SELECT DISTINCT signal_id FROM signal_tickers) ORDER BY s.id")
        signals = cur.fetchall()
    elif args.signal_id:
        cur = conn.execute("SELECT id, title FROM signals WHERE id=?", (args.signal_id,))
        signals = cur.fetchall()
    else:
        cur = conn.execute("SELECT id, title FROM signals ORDER BY id LIMIT 10")
        signals = cur.fetchall()
    if not signals:
        print("No signals to map.")
        return
    output = []
    for sig in signals:
        cur = conn.execute("SELECT topic FROM signal_topics WHERE signal_id=?", (sig["id"],))
        topics = [r["topic"] for r in cur.fetchall()]
        matches = match_topics(topics, wikilinks, themes)
        # Count mapped tickers
        mapped_tickers = {}
        for topic, match_list in matches.items():
            for m in match_list:
                for tkr_info in m.get("tickers", []):
                    mapped_tickers[tkr_info[0]] = tkr_info[1]
        if not args.dry_run and mapped_tickers:
            for tkr, co_name in mapped_tickers.items():
                conn.execute("""INSERT OR IGNORE INTO signal_tickers(signal_id,ticker,company_name,exposure_reason,confidence) VALUES(?,?,?,?,?)""",
                             (sig["id"], tkr, co_name, "auto-mapped", "candidate"))
        result = {
            "signal_id": sig["id"],
            "title": sig["title"],
            "topics_matched": len(matches),
            "tickers_found": list(mapped_tickers.keys()) if not args.dry_run else list(mapped_tickers.keys()),
            "details": {t: [{"theme": m.get("theme","?"), "source": m["source"]} for m in ml] for t, ml in matches.items()}
        }
        output.append(result)
        print(f"[{'MAPPED' if mapped_tickers else 'NO-MATCH'}] {sig['id']}: {sig['title'][:50]}")
        print(f"  topics: {topics}")
        print(f"  matched: {len(matches)} themes, {len(mapped_tickers)} tickers")
    if not args.dry_run:
        conn.commit()
    conn.close()
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()