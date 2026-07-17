#!/usr/bin/env python3
from ssl_util import make_session
_SESSION = make_session()
"""fetch_revenue.py — 每月營收 (T187AP05)

Sources:
  上市: https://openapi.twse.com.tw/v1/opendata/t187ap05_L
  上櫃: https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O

Both return: list[dict] directly (not wrapped in {"data": ...}).
Each dict has fields like:
  出表日期, 資料年月, 公司代號, 公司名稱, 產業別,
  營業收入-當月營收, 營業收入-上月營收, 營業收入-去年當月營收,
  營業收入-上月比較增減(%), 營業收入-去年同月增減(%),
  累計營業收入-當月累計營收, 累計營業收入-去年累計營收,
  累計營業收入-前期比較增減(%), 備註

Outputs:
  signals/candidates/YYYY-MM-DD-revenue.json  (獨立檔名，避免三支 fetcher 互相覆蓋)
  signals/candidates/YYYY-MM-DD-revenue.md

Note: Revenue data is typically released around the 10th-12th of each month.
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

import requests

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

T187AP05_L = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
T187AP05_O = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O"

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def twse_year(year: int) -> str:
    """Convert Gregorian year to TWSE fiscal year string (e.g. 2026 -> 115)."""
    return str(year - 1911)


def tpex_year_month(year: int, month: int) -> str:
    """Convert to TPEx ym format (e.g. 2026-07 -> 11507)."""
    return f"{twse_year(year)}{month:02d}"


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_twse_revenue(year: int, month: int) -> list[dict]:
    """Fetch 上市營收 from TWSE.

    API returns list[dict] directly.
    """
    year_str = twse_year(year)
    url = f"{T187AP05_L}?year={year_str}&month={month:02d}"
    resp = _SESSION.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError("Expected list response")
    results = []
    for r in data:
        if not isinstance(r, dict):
            continue
        ticker = r.get("公司代號", "").strip()
        name = r.get("公司名稱", "").strip()
        if not ticker or ticker == "-":
            continue
        results.append({
            "ticker": ticker,
            "name": name,
            "revenue_current": r.get("營業收入-當月營收", ""),
            "revenue_last_month": r.get("營業收入-上月營收", ""),
            "revenue_last_year": r.get("營業收入-去年當月營收", ""),
            "mom_pct": r.get("營業收入-上月比較增減(%)", ""),
            "yoy_pct": r.get("營業收入-去年同月增減(%)", ""),
            "cumulative_current": r.get("累計營業收入-當月累計營收", ""),
            "cumulative_last_year": r.get("累計營業收入-去年累計營收", ""),
            "cumulative_pct": r.get("累計營業收入-前期比較增減(%)", ""),
            "industry": r.get("產業別", ""),
            "month": f"{year}-{month:02d}",
            "raw": r,
        })
    return results


def fetch_tpex_revenue(year: int, month: int) -> list[dict]:
    """Fetch 上櫃營收 from TPEx.

    API returns list[dict] directly.
    """
    ym = tpex_year_month(year, month)
    url = f"{T187AP05_O}?ym={ym}"
    resp = _SESSION.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError("Expected list response")
    results = []
    for r in data:
        if not isinstance(r, dict):
            continue
        ticker = r.get("SecuritiesCompanyCode", "").strip()
        name = r.get("CompanyName", "").strip()
        if not ticker or ticker == "-":
            continue
        results.append({
            "ticker": ticker,
            "name": name,
            "revenue_current": r.get("當月營收", ""),
            "revenue_last_month": r.get("上月營收", ""),
            "revenue_last_year": r.get("去年當月營收", ""),
            "mom_pct": r.get("上月比較增減(%)", ""),
            "yoy_pct": r.get("去年同月增減(%)", ""),
            "cumulative_current": r.get("當月累計營收", ""),
            "cumulative_last_year": r.get("去年累計營收", ""),
            "cumulative_pct": r.get("前期比較增減(%)", ""),
            "industry": r.get("產業別", ""),
            "month": f"{year}-{month:02d}",
            "raw": r,
        })
    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def build_candidate(data: list[dict], market: str, source: str,
                    partial: bool, date_str: str) -> dict:
    return {
        "source": source,
        "market": market,
        "date": date_str,
        "partial_failure": partial,
        "count": len(data),
        "data": data,
    }


def write_json(candidates: list[dict], date_str: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{date_str}-revenue.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    total = sum(c["count"] for c in candidates)
    print(f"[JSON] {path}  ({len(candidates)} sources, {total} items)")


def write_markdown(candidates: list[dict], date_str: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{date_str}-revenue.md")
    lines = [f"# 每月營收 Candidates — {date_str}", ""]
    for c in candidates:
        flag = " ⚠️ PARTIAL" if c.get("partial_failure") else ""
        lines.append(f"## {c['market']} — {c['source']}{flag}")
        lines.append("")
        if c["data"]:
            lines.append(f"_{c['count']} 筆紀錄_")
            lines.append("")
            lines.append("| 代號 | 名稱 | 當月營收 | 去年同月 | YoY% | 產業 |")
            lines.append("|------|------|---------|---------|------|------|")
            for rec in c["data"]:
                ticker = rec.get("ticker", "")
                name = rec.get("name", "")
                rev = rec.get("revenue_current", "-")
                rev_ly = rec.get("revenue_last_year", "-")
                yoy = rec.get("yoy_pct", "-")
                industry = rec.get("industry", "")
                lines.append(f"| {ticker} | {name} | {rev} | {rev_ly} | {yoy} | {industry} |")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[MD]   {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Fetch monthly 營收 revenue data")
    ap.add_argument("--year-month", help="YYYY-MM (default: previous month)")
    ap.add_argument("--output-dir", default="signals/candidates",
                    help="Output directory")
    args = ap.parse_args()

    if args.year_month:
        parts = args.year_month.split("-")
        year = int(parts[0])
        month = int(parts[1])
    else:
        # Default to previous month
        today = date.today()
        first_of_month = today.replace(day=1)
        prev_month = first_of_month - timedelta(days=1)
        year = prev_month.year
        month = prev_month.month

    date_str = f"{year}-{month:02d}"
    print(f"Fetching revenue for {year}-{month:02d}...")

    candidates = []
    errors = []

    # --- 上市 ---
    print("[1/2] Fetching TWSE (上市) ...")
    try:
        data = fetch_twse_revenue(year, month)
        candidates.append(build_candidate(data, "上市", "TWSE T187AP05", False, date_str))
        print(f"  → {len(data)} items")
    except Exception as e:
        errors.append(f"TWSE error: {e}")
        candidates.append(build_candidate([], "上市", "TWSE T187AP05", True, date_str))
        print(f"  → FAILED: {e}")

    # --- 上櫃 ---
    print("[2/2] Fetching TPEx (上櫃) ...")
    try:
        data = fetch_tpex_revenue(year, month)
        candidates.append(build_candidate(data, "上櫃", "TPEx T187AP05", False, date_str))
        print(f"  → {len(data)} items")
    except Exception as e:
        errors.append(f"TPEx error: {e}")
        candidates.append(build_candidate([], "上櫃", "TPEx T187AP05", True, date_str))
        print(f"  → FAILED: {e}")

    # Write outputs
    write_json(candidates, date_str, args.output_dir)
    write_markdown(candidates, date_str, args.output_dir)

    if errors:
        print(f"\n⚠️  {len(errors)} source(s) failed (partial results written):")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)
    else:
        total = sum(c["count"] for c in candidates)
        print(f"\n✅ Done — {total} total items across {len(candidates)} sources")


if __name__ == "__main__":
    main()