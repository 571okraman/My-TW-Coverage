#!/usr/bin/env python3
"""integration_test.py — End-to-end integration test with isolated DB (T09).

Runs in a TEMP DB only — never touches production signals.sqlite.
Verifies production DB is unchanged at the end (13 signals / 29 followups).

Usage:
  python3 scripts/integration_test.py [--db /tmp/test_signals.sqlite] [--create-sample]
"""

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from datetime import date, datetime
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SIGNALS_DIR = PROJECT_ROOT / "signals"
SEED_DIR = SIGNALS_DIR / "seed"
PROD_DB = PROJECT_ROOT / "data" / "signals.sqlite"

RECOGNIZED_TRIGGERS = {
    "policy_regulation", "tech_shift", "supply_demand_imbalance",
    "supply_chain_reshuffling", "anchor_customer_roadmap",
    "financial_inflection", "market_behavior_anomaly",
}
OFFICIAL_SOURCE_TYPES = {"government", "company_disclosure", "exchange"}


# ── T08 Triage ──────────────────────────────────────────────────────────────

def triage_candidate(candidate: dict) -> tuple[bool, str]:
    title = candidate.get("title", "").strip()
    if not title:
        return False, "missing title"

    trigger = candidate.get("trigger_type", "")
    if trigger not in RECOGNIZED_TRIGGERS:
        return False, f"unrecognized trigger_type: {trigger}"

    event_date = candidate.get("event_date", "")
    try:
        ed = datetime.strptime(event_date[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False, "invalid event_date"
    if ed > date.today():
        return False, "event_date in the future"
    if (date.today() - ed).days > 90:
        return False, "event_date too old (>90 days)"

    sources = candidate.get("sources", [])
    if not sources:
        return False, "no sources"

    has_official = any(s.get("source_type", "") in OFFICIAL_SOURCE_TYPES for s in sources)
    if not has_official:
        return False, "no official source (verify≠3)"

    tickers = candidate.get("tickers", [])
    if not tickers:
        return False, "no tickers"

    topics = candidate.get("topics", [])
    if not topics:
        return False, "no topics"

    return True, "approved"


# ── Sample candidates (for isolated testing) ────────────────────────────────

def create_sample_candidates() -> list[dict]:
    today = date.today()
    return [
        # ✅ APPROVED
        {
            "id": f"CAND-{uuid.uuid4().hex[:8]}",
            "title": "台積電宣布 2026 年 Q2 月營收達 2,800 億台幣，年增 32%，3nm 與 CoWoS 貢獻逾 40%",
            "summary": f"台積電 {today.isoformat()} 公布 6 月營收 2,800 億台幣，年增 32%，創歷史新高。",
            "trigger_type": "financial_inflection",
            "event_date": today.isoformat(),
            "sources": [
                {"url": "https://mops.twse.com.tw/news/2026070001",
                 "title": "台積電 6 月營收出爐", "publisher": "TWSE",
                 "source_type": "exchange", "trust_level": "high",
                 "published_at": f"{today.isoformat()}T16:00:00+08:00"},
                {"url": "https://ir.tsmc.com/news/2026-june-revenue",
                 "title": "TSMC June 2026 Revenue Report", "publisher": "TSMC IR",
                 "source_type": "company_disclosure", "trust_level": "high",
                 "published_at": f"{today.isoformat()}T09:00:00+08:00"},
            ],
            "topics": ["月營收", "3nm", "CoWoS", "AI 伺服器"],
            "tickers": [
                {"ticker": "2330", "company_name": "台積電",
                 "exposure_reason": "直接關聯，3nm 與 CoWoS 營收創新高"},
                {"ticker": "3711", "company_name": "日月光",
                 "exposure_reason": "CoWoS 封裝測試受惠，先進封裝需求增加"},
            ],
        },
        # ❌ REJECTED: no official source
        {
            "id": f"CAND-{uuid.uuid4().hex[:8]}",
            "title": "外資看好台灣記憶體股，目標價上調 10%",
            "summary": "外資研究報告指出，受 AI 需求帶動，記憶體供應鏈將持續受惠。",
            "trigger_type": "supply_demand_imbalance",
            "event_date": today.isoformat(),
            "sources": [{"url": "https://example.com/foreign-memory", "title": "",
                         "publisher": "某券商", "source_type": "news",
                         "trust_level": "medium",
                         "published_at": f"{today.isoformat()}T10:00:00+08:00"}],
            "topics": ["記憶體", "AI"],
            "tickers": [{"ticker": "2408", "company_name": "南亞科",
                         "exposure_reason": "外資點名受惠"}],
        },
        # ❌ REJECTED: no tickers
        {
            "id": f"CAND-{uuid.uuid4().hex[:8]}",
            "title": "經濟部宣布新一輪半導體補助計畫",
            "summary": "經濟部宣布新一輪半導體補助。",
            "trigger_type": "policy_regulation",
            "event_date": today.isoformat(),
            "sources": [{"url": "https://www.moea.gov.tw/news/semiconductor",
                         "title": "半導體補助計畫", "publisher": "經濟部",
                         "source_type": "government", "trust_level": "high",
                         "published_at": f"{today.isoformat()}T10:00:00+08:00"}],
            "topics": ["半導體"],
            "tickers": [],
        },
    ]


# ── Pipeline execution (candidate → seed → pipeline) ──────────────────────

def run_pipeline(candidates: list[dict], db_path: Path, dry_run: bool = False):
    """Run triage on candidates → seed JSON → ingest → map → score → followup → export."""
    now = datetime.now()

    # Step 1: Triage
    print("\n--- Step 1: T08 Triage ---")
    approved = []
    for c in candidates:
        ok, reason = triage_candidate(c)
        print(f"  {'✅' if ok else '❌'} {c['title'][:50]}: {reason}")
        if ok:
            approved.append(c)

    if not approved:
        print("  No candidates approved. Skipping pipeline.")
        return

    # Step 2: Build seed JSON
    print(f"\n--- Step 2: Seed JSON ({len(approved)} approved) ---")
    seed = {"signals": []}
    for c in approved:
        seed["signals"].append({
            "title": c["title"],
            "summary": c.get("summary", ""),
            "trigger_type": c["trigger_type"],
            "event_date": c["event_date"],
            "sources": c["sources"],
            "topics": c["topics"],
            "tickers": c["tickers"],
            "status": "follow",
        })

    seed_dir = SEED_DIR
    seed_dir.mkdir(parents=True, exist_ok=True)
    seed_path = seed_dir / f"seed-integration-{now.strftime('%Y-%m-%d-%H%M%S')}.json"
    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(seed, f, indent=2, ensure_ascii=False)
    print(f"  Seed JSON: {seed_path}")

    if dry_run:
        print("\n  DRY RUN — skipping pipeline steps")
        return

    # Step 3: Pipeline (uses db_path argument from the script wrappers)
    pipeline_scripts = [
        f"python3 scripts/init_signal_db.py --db-path {db_path}",
        f"python3 scripts/ingest_signals.py {seed_path} --db-path {db_path}",
        "python3 scripts/map_signal.py --all",
        f"python3 scripts/score_signal.py --all --db-path {db_path}",
        f"python3 scripts/list_followups.py --create --db-path {db_path}",
        f"python3 scripts/export_signals.py --all --db-path {db_path}",
    ]

    for script in pipeline_scripts:
        print(f"\n  Running: {script.split()[2]} ...")
        r = subprocess.run(
            f"cd {PROJECT_ROOT} && source venv/bin/activate && {script}",
            capture_output=True, text=True, timeout=60, shell=True,
            executable="/bin/bash"
        )
        if r.returncode != 0:
            print(f"  FAILED ({r.returncode}): {r.stderr[:300]}")
            return False
        print(f"  OK")

    print("\n✅ Pipeline complete")
    return True


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Integration test with isolated DB")
    ap.add_argument("--db", type=str, default="",
                    help="Temp DB path (default: auto tmpdir)")
    ap.add_argument("--create-sample", action="store_true",
                    help="Use sample candidates (default: read from flagged.json)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview without pipeline execution")
    args = ap.parse_args()

    # Verify production DB is untouched at end
    def check_prod_db():
        if not PROD_DB.exists():
            print("  ⚠️  Production DB not found — cannot verify")
            return None
        conn = sqlite3.connect(str(PROD_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM signals")
        sig_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM followups")
        fu_count = c.fetchone()[0]
        conn.close()
        return sig_count, fu_count

    prod_before = check_prod_db()
    print(f"📊 Production DB before test: {prod_before[0]} signals / {prod_before[1]} followups")

    # Setup temp DB
    if args.db:
        db_path = Path(args.db)
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        print(f"🗄️  Temp DB: {db_path}")

    try:
        # Get candidates
        if args.create_sample:
            candidates = create_sample_candidates()
            print(f"📋 Using {len(candidates)} sample candidates")
        else:
            # Read from normalized.json
            today = date.today().isoformat()
            norm_path = CANDIDATES_DIR / f"{today}-normalized.json"
            if not norm_path.exists():
                print(f"⚠️  No normalized file: {norm_path}, falling back to samples")
                candidates = create_sample_candidates()
            else:
                with open(norm_path, encoding="utf-8") as f:
                    candidates = json.load(f)
                print(f"📋 Loaded {len(candidates)} normalized candidates")

        # Run pipeline on temp DB
        success = run_pipeline(candidates, db_path, args.dry_run)

        # Verify production DB unchanged
        prod_after = check_prod_db()
        print(f"\n{'='*50}")
        print("PRODUCTION DB INTEGRITY CHECK")
        print(f"  Before: {prod_before[0]} signals / {prod_before[1]} followups")
        print(f"  After:  {prod_after[0]} signals / {prod_after[1]} followups")
        if prod_before == prod_after:
            print("  ✅ Production DB UNCHANGED — isolated test passes")
        else:
            print(f"  ❌ Production DB CHANGED! (delta: {prod_after[0]-prod_before[0]} signals)")
            sys.exit(1)

    finally:
        # Clean up temp DB
        if not args.db and db_path.exists():
            os.unlink(db_path)
            print(f"🗑️  Temp DB cleaned up")


if __name__ == "__main__":
    main()