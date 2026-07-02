#!/usr/bin/env python3
"""normalize_candidate.py — Normalize raw fetcher output into unified candidate schema.

Reads:
  signals/candidates/YYYY-MM-DD-candidates.json (from fetchers)

Outputs:
  signals/candidates/YYYY-MM-DD-normalized.json (unified schema)

Schema:
  - ticker: 股票代號（4 碼）
  - event_date: 事實發生日（YYYY-MM-DD）
  - source_url: 來源 URL
  - source_type: 來源類型（announcement/institutional/revenue）
  - clause_number: 條款號/flag 名（如 "第 20 款"、"法說會"）
  - summary: 原始摘要
  - raw_data: 原始 JSON（保留供 debug）
  - market: "twse" 或 "tpex"
  - filtered_out: bool（未通過白名單或 universe 過濾）

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

# scripts/ is inside the repo root, so go up one level
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGNALS_DIR = PROJECT_ROOT / "signals"
CANDIDATES_DIR = SIGNALS_DIR / "candidates"
PILOT_REPORTS_DIR = PROJECT_ROOT / "Pilot_Reports"

# Clause whitelist: 第 XX 款 or specific clause names
# Based on T09 spec: 第 20 款（取得處分資產/capex）、第 12 款（法說會）
# 合併收購、私募增資、長約/訂單相關條款
CLAUSE_WHITELIST = {
    # 條款號
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
    # 關鍵字（模糊匹配）
    "合併",
    "收購",
    "私募",
    "增資",
    "長約",
    "訂單",
    "capex",
    "資本支出",
    "處分資產",
    "法說會",
    "法人說明會",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_universe() -> set[str]:
    """Read all ticker codes from Pilot_Reports/**/*.md filenames (recursive)."""
    tickers = set()
    if not PILOT_REPORTS_DIR.exists():
        print(f"⚠️  Pilot_Reports not found at {PILOT_REPORTS_DIR}", file=sys.stderr)
        return tickers
    # Recursively find all .md files in subdirectories
    for f in PILOT_REPORTS_DIR.rglob("*.md"):
        if f.is_file():
            # Filename is like "2330_台積電.md"
            name = f.stem
            # Extract 4-digit ticker from beginning
            m = re.match(r"^(\d{4})", name)
            if m:
                tickers.add(m.group(1))
    return tickers


def load_clause_whitelist() -> set[str]:
    """Return the set of clause keywords to match."""
    return CLAUSE_WHITELIST.copy()


def normalize_announcement(ann: dict, source_type: str, date_str: str, market: str) -> dict:
    """Normalize a single announcement record into unified schema."""
    ticker = str(ann.get("ticker", "")).strip()
    title = str(ann.get("title", "")).strip()
    url = str(ann.get("url", "")).strip()

    # Try to extract clause number from title
    clause_match = re.search(r"第\s*(\d+)\s*款", title)
    clause_number = clause_match.group(0) if clause_match else ""

    # Build summary
    summary = f"{ticker} {title}" if ticker else title

    return {
        "ticker": ticker,
        "event_date": date_str,
        "source_url": url,
        "source_type": source_type,
        "clause_number": clause_number,
        "summary": summary,
        "raw_data": ann.get("raw", ann),
        "market": market,
        "filtered_out": False,  # Will be set by whitelist/universe filter
    }


def normalize_institutional(rec: dict, source_type: str, date_str: str, market: str) -> dict:
    """Normalize a single institutional trading record."""
    ticker = str(rec.get("ticker", "")).strip()
    name = str(rec.get("name", "")).strip()

    # Build summary from key fields
    summary_parts = [f"{ticker} {name}"]
    for key in ["foreign_buy", "foreign_sell", "foreign_diff", "dealer_self_diff", "three_institutions_diff"]:
        if key in rec and rec[key] not in ("-", "", None):
            summary_parts.append(f"{key}: {rec[key]}")
    summary = " | ".join(summary_parts)

    return {
        "ticker": ticker,
        "event_date": date_str,
        "source_url": "",  # Institutional data doesn't have individual URLs
        "source_type": source_type,
        "clause_number": "",  # No clause number for institutional data
        "summary": summary,
        "raw_data": rec.get("raw", rec),
        "market": market,
        "filtered_out": False,
    }


def normalize_revenue(rec: dict, source_type: str, date_str: str, market: str) -> dict:
    """Normalize a single revenue record."""
    ticker = str(rec.get("ticker", "")).strip()
    name = str(rec.get("name", "")).strip()
    revenue = str(rec.get("revenue", "")).strip()
    month = str(rec.get("month", "")).strip()

    summary = f"{ticker} {name} {month} 營收 {revenue}"

    return {
        "ticker": ticker,
        "event_date": date_str,
        "source_url": "",
        "source_type": source_type,
        "clause_number": "",
        "summary": summary,
        "raw_data": rec.get("raw", rec),
        "market": market,
        "filtered_out": False,
    }


def check_clause_whitelist(candidate: dict, whitelist: set[str]) -> bool:
    """Check if candidate matches clause whitelist. Returns True if matched.
    
    For institutional/revenue source: always pass (these don't have clauses).
    For announcements: must match clause whitelist.
    """
    source_type = candidate.get("source_type", "")
    
    # Institutional and revenue data don't have clause concepts — always pass
    # source_type could be "institutional", "revenue", or raw source like "TWSE T86"
    if source_type in ("institutional", "revenue") or "T86" in source_type or "tpex_3insti" in source_type:
        return True
    
    # For announcements: check clause whitelist
    summary = candidate.get("summary", "")
    clause = candidate.get("clause_number", "")

    # Check clause number first
    if clause:
        # Extract the number from "第 XX 款"
        m = re.search(r"第\s*(\d+)\s*款", clause)
        if m:
            num = m.group(1)
            # Check if this number is in whitelist
            for kw in whitelist:
                if kw.startswith("第 ") and kw.endswith(" 款"):
                    if kw == clause:
                        return True

    # Check keyword matching
    for kw in whitelist:
        if kw in summary:
            return True

    return False


def check_universe(candidate: dict, universe: set[str]) -> bool:
    """Check if candidate's ticker is in universe. Returns True if in universe."""
    ticker = candidate.get("ticker", "")
    return ticker in universe


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Normalize fetcher output to unified schema")
    parser.add_argument("--date", type=str, help="Date string (YYYY-MM-DD), default: today")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--input-dir", type=str, default=str(CANDIDATES_DIR), help="Input directory")
    parser.add_argument("--output-dir", type=str, default=str(CANDIDATES_DIR), help="Output directory")
    args = parser.parse_args()

    # Set date
    if args.date:
        date_str = args.date
    else:
        date_str = date.today().isoformat()

    # Load universe
    universe = load_universe()
    print(f"📚 Universe: {len(universe)} tickers loaded from Pilot_Reports/")

    # Load whitelist
    whitelist = load_clause_whitelist()
    print(f"📋 Clause whitelist: {len(whitelist)} entries")

    # Find input files
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    # Find candidate JSON files matching the date
    candidate_files = sorted(input_dir.glob(f"*{date_str}*-candidates.json"))

    if not candidate_files:
        print(f"⚠️  No candidate files found for {date_str} in {input_dir}", file=sys.stderr)
        # Create empty output for downstream compatibility
        os.makedirs(args.output_dir, exist_ok=True)
        output_path = os.path.join(args.output_dir, f"{date_str}-normalized.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"📝 Empty output written to {output_path}")
        return

    print(f"📂 Found {len(candidate_files)} candidate file(s)")

    # Process each file
    all_candidates = []
    stats = {
        "total_raw": 0,
        "normalized": 0,
        "clause_filtered": 0,
        "universe_filtered": 0,
        "passed": 0,
    }

    for cf in candidate_files:
        print(f"\n📖 Reading {cf.name}...")
        with open(cf, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        for item in data:
            source = item.get("source", "announcement")
            market_raw = item.get("market", "twse")
            date_raw = item.get("date", date_str)

            # Map market to "twse" or "tpex"
            if "TWSE" in source or "上市" in market_raw:
                market = "twse"
            elif "TPEx" in source or "上櫃" in market_raw:
                market = "tpex"
            else:
                market = "unknown"

            # Normalize based on source type
            if "announcements" in item:
                # Announcement source
                for ann in item.get("announcements", []):
                    stats["total_raw"] += 1
                    cand = normalize_announcement(ann, source, date_raw, market)
                    all_candidates.append(cand)
                    stats["normalized"] += 1

            elif "records" in item:
                # Institutional source
                for rec in item.get("records", []):
                    stats["total_raw"] += 1
                    cand = normalize_institutional(rec, source, date_raw, market)
                    all_candidates.append(cand)
                    stats["normalized"] += 1

            elif "data" in item:
                # Revenue source
                for rec in item.get("data", []):
                    stats["total_raw"] += 1
                    cand = normalize_revenue(rec, source, date_raw, market)
                    all_candidates.append(cand)
                    stats["normalized"] += 1

    print(f"\n📊 Raw candidates: {stats['total_raw']}")
    print(f"📊 Normalized: {stats['normalized']}")

    # Apply filters
    for cand in all_candidates:
        # Clause whitelist filter
        if not check_clause_whitelist(cand, whitelist):
            cand["filtered_out"] = True
            stats["clause_filtered"] += 1
            continue

        # Universe filter
        if not check_universe(cand, universe):
            cand["filtered_out"] = True
            stats["universe_filtered"] += 1
            continue

        stats["passed"] += 1

    # Print filter results
    print(f"📊 Clause filtered out: {stats['clause_filtered']}")
    print(f"📊 Universe filtered out: {stats['universe_filtered']}")
    print(f"📊 Passed filters: {stats['passed']}")

    if args.dry_run:
        print(f"\n🔍 DRY RUN — would write to {args.output_dir}/{date_str}-normalized.json")
        # Print first 5 candidates
        for i, cand in enumerate(all_candidates[:5]):
            status = "✅" if not cand["filtered_out"] else "❌"
            print(f"  {status} {cand['ticker']} | {cand['summary'][:60]}")
        if len(all_candidates) > 5:
            print(f"  ... and {len(all_candidates) - 5} more")
        return

    # Write output
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, f"{date_str}-normalized.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Normalized candidates written to {output_path}")
    print(f"   Total: {len(all_candidates)} | Passed: {stats['passed']} | Filtered: {stats['clause_filtered'] + stats['universe_filtered']}")


if __name__ == "__main__":
    main()