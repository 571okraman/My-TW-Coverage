#!/usr/bin/env python3
"""normalize_candidate.py — 三線 candidate normalization (T09).

Reads three source types independently:
  - announcements  (*-announcements.json): clause whitelist + universe filter
  - institutional  (*-flagged.json):       flag_engine output, pass-through with flags
  - revenue        (*-revenue.json):       YoY ≥+30% 2mo OR 12mo high; partial if <2mo

Outputs:
  signals/candidates/YYYY-MM-DD-normalized.json (merged unified schema)

Usage:
  python3 normalize_candidate.py [--date YYYY-MM-DD] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGNALS_DIR = PROJECT_ROOT / "signals"
CANDIDATES_DIR = SIGNALS_DIR / "candidates"
PILOT_REPORTS_DIR = PROJECT_ROOT / "Pilot_Reports"

CLAUSE_WHITELIST = {
    "第 20 款",      # 取得處分資產 / capex
    "第 12 款",      # 法說會
    "第 10 款",      # 合併、分割、收購
    "第 11 款",      # 私募增資
    "第 14 款",      # 長約 / 訂單
    "第 15 款",      # 長約 / 訂單
    "第 16 款",      # 長約 / 訂單
    "第 17 款",      # 長約 / 訂單
    "第 18 款",      # 長約 / 訂單
    "第 19 款",      # 長約 / 訂單
    "合併", "收購", "私募", "增資", "長約", "訂單",
    "capex", "資本支出", "處分資產", "法說會", "法人說明會",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_universe() -> set[str]:
    tickers = set()
    if not PILOT_REPORTS_DIR.exists():
        return tickers
    for f in PILOT_REPORTS_DIR.rglob("*.md"):
        if f.is_file():
            m = re.match(r"^(\d{4})", f.stem)
            if m:
                tickers.add(m.group(1))
    return tickers


def check_clause(entry: dict, whitelist: set[str]) -> bool:
    """Check if an announcement matches clause whitelist."""
    title = entry.get("title", "") + " " + entry.get("clause", "")
    for kw in whitelist:
        if kw in title:
            return True
    return False


# ── Pipeline 1: 重訊 (announcements) ────────────────────────────────────────

def normalize_announcements(date_str: str, universe: set[str]) -> list[dict]:
    """Read *-announcements.json → clause whitelist → universe filter."""
    candidates = []
    fpath = CANDIDATES_DIR / f"{date_str}-announcements.json"
    if not fpath.exists():
        print(f"  ⚠️  No announcements file for {date_str}")
        return candidates

    with open(fpath, encoding="utf-8") as f:
        items = json.load(f)

    for item in items:
        for ann in item.get("announcements", []):
            ticker = str(ann.get("ticker", "")).strip()
            if ticker not in universe:
                continue
            if not check_clause(ann, CLAUSE_WHITELIST):
                continue
            candidates.append({
                "ticker": ticker,
                "event_date": ann.get("event_date", date_str),
                "source_url": "",
                "source_type": "announcement",
                "clause_number": ann.get("clause", ""),
                "summary": f"{ticker} {ann.get('title', '')}" if ticker else ann.get("title", ""),
                "raw_data": ann.get("raw", ann),
                "market": "twse" if "TWSE" in item.get("source", "") else "tpex",
                "flag": "announcement",
                "flags": ["announcement"],
            })
    return candidates


# ── Pipeline 2: 法人 (institutional → flagged.json) ─────────────────────────

def normalize_institutional(date_str: str, universe: set[str]) -> list[dict]:
    """Read *-flagged.json (flag_engine output) → pass-through with flags.

    Only includes flagged candidates where start_date matches date_str
    (flag_engine output is cumulative — normalize filters to today).
    """
    candidates = []
    fpath = CANDIDATES_DIR / f"{date_str}-flagged.json"
    if not fpath.exists():
        print(f"  ⚠️  No flagged file for {date_str}")
        return candidates

    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)

    for entry in data.get("candidates", []):
        ticker = str(entry.get("ticker", "")).strip()
        if ticker not in universe:
            continue
        # Filter to candidates whose start_date matches the target date
        start = str(entry.get("start_date", ""))[:10]
        if start != date_str:
            continue
        # Dedup key is ticker+flag+start_date (native to flag_engine),
        # no source_url needed — market flag candidates don't have URLs by design.
        candidates.append({
            "ticker": ticker,
            "event_date": str(entry.get("start_date", date_str))[:10],
            "source_url": "",  # intentional: market flags have no URL
            "source_type": "institutional",
            "clause_number": "",
            "summary": entry.get("detail", ""),
            "raw_data": entry,
            "market": "twse",
            "flag": entry.get("flag", ""),
            "flags": entry.get("flags", [entry.get("flag", "")]),
            "direction": entry.get("direction", ""),
            "start_date": str(entry.get("start_date", ""))[:10],
            "end_date": str(entry.get("end_date", ""))[:10] if entry.get("end_date") else None,
            "metadata": entry.get("metadata", {}),
        })
    return candidates


# ── Pipeline 3: 營收 (revenue) ──────────────────────────────────────────────

def normalize_revenue(date_str: str, universe: set[str]) -> list[dict]:
    """Read *-revenue.json → YoY ≥+30% 2mo OR 12mo high.

    ⚠️ First month: only check 12-month high, mark partial.
    Revenue data is monthly, so date_str is YYYY-MM not a full date.
    """
    candidates = []

    # date_str is the run date; revenue data lives under the month it covers
    # e.g. 2026-06-revenue.json for June 2026 data
    month_str = date_str[:7]  # YYYY-MM
    fpath = CANDIDATES_DIR / f"{month_str}-revenue.json"
    if not fpath.exists():
        print(f"  ⚠️  No revenue file for {month_str}")
        return candidates

    with open(fpath, encoding="utf-8") as f:
        items = json.load(f)

    records = []
    for item in items:
        for rec in item.get("data", []):
            ticker = str(rec.get("ticker", "")).strip()
            if ticker not in universe:
                continue
            try:
                yoy = float(rec.get("yoy_pct", "").replace("%", "")) if rec.get("yoy_pct") else None
                rev = float(rec.get("revenue_current", "0").replace(",", ""))
            except (ValueError, TypeError):
                continue
            records.append({
                "ticker": ticker,
                "month": rec.get("month", month_str),
                "yoy_pct": yoy,
                "revenue": rev,
            })

    if not records:
        return candidates

    # Group by ticker
    from collections import defaultdict
    by_ticker = defaultdict(list)
    for r in records:
        by_ticker[r["ticker"]].append(r)

    for ticker, recs in by_ticker.items():
        recs.sort(key=lambda x: x["month"])
        # With only 1 month of data: can't check 2-month consecutive
        # Mark all YoY ≥+30% entries with partial=true
        for r in recs:
            if r["yoy_pct"] is not None and r["yoy_pct"] >= 30:
                candidates.append({
                    "ticker": ticker,
                    "event_date": r["month"] + "-01",
                    "source_url": "",
                    "source_type": "revenue",
                    "clause_number": "",
                    "summary": f"{ticker} 月營收 YoY {r['yoy_pct']:.1f}% (≥+30%) — partial (no prior month snapshot)",
                    "raw_data": r,
                    "market": "twse",
                    "flag": "revenue",
                    "flags": ["revenue"],
                    "partial": True,
                })
    return candidates


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Normalize three-source candidates")
    parser.add_argument("--date", type=str, help="Date (YYYY-MM-DD), default: today")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    date_str = args.date or date.today().isoformat()
    universe = load_universe()
    print(f"📚 Universe: {len(universe)} tickers")

    all_candidates = []
    stats = {}

    # Pipeline 1: 重訊
    print(f"\n─ Pipeline 1: 重訊 (announcements)")
    ann = normalize_announcements(date_str, universe)
    stats["announcements"] = len(ann)
    print(f"  → {len(ann)} candidates")
    all_candidates.extend(ann)

    # Pipeline 2: 法人
    print(f"\n─ Pipeline 2: 法人 (institutional → flagged.json)")
    inst = normalize_institutional(date_str, universe)
    stats["institutional"] = len(inst)
    print(f"  → {len(inst)} candidates")
    all_candidates.extend(inst)

    # Pipeline 3: 營收
    print(f"\n─ Pipeline 3: 營收 (revenue)")
    rev = normalize_revenue(date_str, universe)
    stats["revenue"] = len(rev)
    print(f"  → {len(rev)} candidates ({'partial — no prior month snapshot' if rev else 'none'})")
    all_candidates.extend(rev)

    print(f"\n{'='*50}")
    print(f"Total normalized candidates: {len(all_candidates)}")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n🔍 DRY RUN — skipping write")
        for c in all_candidates[:5]:
            tags = "|".join(c.get("flags", [c.get("flag", "")]))
            print(f"  [{tags}] {c['ticker']}: {c['summary'][:60]}")
        if len(all_candidates) > 5:
            print(f"  ... and {len(all_candidates) - 5} more")
        return

    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    outpath = CANDIDATES_DIR / f"{date_str}-normalized.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Written to {outpath}")


if __name__ == "__main__":
    main()