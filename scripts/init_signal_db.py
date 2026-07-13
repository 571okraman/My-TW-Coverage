#!/usr/bin/env python3
import argparse, os, sqlite3, sys

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

def read_migration(mdir):
    mf = os.path.join(mdir, "001_signal_followup_schema.sql")
    if not os.path.exists(mf):
        print(f"FATAL: migration not found: {mf}", file=sys.stderr)
        sys.exit(1)
    with open(mf) as f:
        return f.read()

def init_db(dbpath, sql):
    os.makedirs(os.path.dirname(dbpath), exist_ok=True)
    conn = sqlite3.connect(dbpath)
    try:
        conn.executescript(sql)
        conn.commit()
        print(f"OK: {dbpath}")
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        print(f"tables: {', '.join(tables)}")
    except sqlite3.Error as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db-path")
    ap.add_argument("--force", action="store_true", help="Overwrite existing DB")
    args = ap.parse_args()
    root = get_project_root()
    sql = read_migration(os.path.join(root, "migrations"))
    if args.dry_run:
        print(sql)
        return
    db = args.db_path or os.path.join(root, "data", "signals.sqlite")
    if not args.force and os.path.exists(db):
        print(f"FATAL: DB exists at {db}, use --force to overwrite", file=sys.stderr)
        sys.exit(1)
    init_db(db, sql)

if __name__ == "__main__":
    main()
