#!/usr/bin/env python3
"""fetch_institutional.py — 三大法人每日買賣超

Sources:
  上市: https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALLBUT0999&response=json
  上櫃: https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading (ymd=YYYMMDD)

TWSE T86 returns: {"stat": "...", "date": "...", "title": "...", "fields": [...], "data": [...], ...}
TPEx returns: list[dict]

Outputs:
  signals/candidates/YYYY-MM-DD-institutional.json
  signals/candidates/YYYY-MM-DD-institutional.md

Backfill mode:
  --backfill N fetches the last N trading days (TWSE only; TPEx historical TBD).
  Each request spaced 2-3s apart with retry on failure.
"""
import argparse
import json
import os
import sys
import time
from datetime import date, timedelta

import requests

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
T86_L = "https://www.twse.com.tw/rwd/zh/fund/T86"
T86_O = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"

# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_twse_institutional(api_date: str) -> list[dict]:
    """Fetch 上市三大法人買賣超 from TWSE.

    Columns (by index):
      0: 證券代號, 1: 證券名稱,
      2-4: 外陸資買進/賣出/買賣超,
      5-7: 外資自營商買進/賣出/買賣超,
      8-10: 投信買進/賣出/買賣超,
      11: 自營商買賣超,
      12-14: 自營商(自行)買進/賣出/買賣超,
      15-17: 自營商(避險)買進/賣出/買賣超,
      18: 三大法人買賣超
    """
    params = {
        "date": api_date,
        "selectType": "ALLBUT0999",
        "response": "json",
    }
    resp = requests.get(T86_L, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data", [])
    results = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        ticker = str(row[0]).strip()
        name = str(row[1]).strip()
        if not ticker or ticker == "-":
            continue
        summary = {
            "ticker": ticker,
            "name": name,
            "date": api_date,
        }
        summary["foreign_buy"] = str(row[2]).strip() if len(row) > 2 else ""
        summary["foreign_sell"] = str(row[3]).strip() if len(row) > 3 else ""
        summary["foreign_diff"] = str(row[4]).strip() if len(row) > 4 else ""
        summary["dealer_foreign_buy"] = str(row[5]).strip() if len(row) > 5 else ""
        summary["dealer_foreign_sell"] = str(row[6]).strip() if len(row) > 6 else ""
        summary["dealer_foreign_diff"] = str(row[7]).strip() if len(row) > 7 else ""
        summary["broker_buy"] = str(row[8]).strip() if len(row) > 8 else ""
        summary["broker_sell"] = str(row[9]).strip() if len(row) > 9 else ""
        summary["broker_diff"] = str(row[10]).strip() if len(row) > 10 else ""
        summary["dealer_total_diff"] = str(row[11]).strip() if len(row) > 11 else ""
        summary["dealer_self_buy"] = str(row[12]).strip() if len(row) > 12 else ""
        summary["dealer_self_sell"] = str(row[13]).strip() if len(row) > 13 else ""
        summary["dealer_self_diff"] = str(row[14]).strip() if len(row) > 14 else ""
        summary["dealer_hedge_buy"] = str(row[15]).strip() if len(row) > 15 else ""
        summary["dealer_hedge_sell"] = str(row[16]).strip() if len(row) > 16 else ""
        summary["dealer_hedge_diff"] = str(row[17]).strip() if len(row) > 17 else ""
        summary["three_institutions_diff"] = str(row[18]).strip() if len(row) > 18 else ""
        summary["raw"] = row
        results.append(summary)
    return results


def fetch_tpex_institutional(api_date: str) -> list[dict]:
    """Fetch 上櫃三大法人買賣超 from TPEx.

    API returns list[dict] directly with keys like:
      Date, SecuritiesCompanyCode, CompanyName,
      Foreign Investors...-Total Buy/Sell/Difference, etc.
    """
    year = int(api_date[:4])
    taiwan_year = year - 1911
    month = api_date[4:6]
    day = api_date[6:8]
    params = {"ymd": f"{taiwan_year}{month}{day}"}
    resp = requests.get(T86_O, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()  # list[dict] directly
    results = []
    for r in rows:
        ticker = str(r.get("SecuritiesCompanyCode", "")).strip()
        name = str(r.get("CompanyName", "")).strip()
        if not ticker or ticker == "-":
            continue
        summary = {
            "ticker": ticker,
            "name": name,
            "date": r.get("Date", api_date),
        }
        for key in r:
            if "Foreign Investors include Mainland" in key and "Total Buy" in key:
                summary["foreign_buy"] = r[key]
            elif "Foreign Investors include Mainland" in key and "Total Sell" in key:
                summary["foreign_sell"] = r[key]
            elif "Foreign Investors include Mainland" in key and "Difference" in key:
                summary["foreign_diff"] = r[key]
            elif "Foreign Dealers" in key and "Total Buy" in key:
                summary["dealer_buy"] = r[key]
            elif "Foreign Dealers" in key and "Total Sell" in key:
                summary["dealer_sell"] = r[key]
            elif "Foreign Dealers" in key and "Difference" in key:
                summary["dealer_diff"] = r[key]
            elif "ForeignInvestorsIncludeMainlandAreaInvestors" in key and "TotalBuy" in key:
                summary["foreign_investor_buy"] = r[key]
            elif "ForeignInvestorsIncludeMainlandAreaInvestors" in key and "TotalSell" in key:
                summary["foreign_investor_sell"] = r[key]
            elif "ForeignInvestorsIncludeMainlandAreaInvestors" in key and "Difference" in key:
                summary["foreign_investor_diff"] = r[key]
            elif "DomesticBrokers" in key and "TotalBuy" in key:
                summary["broker_buy"] = r[key]
            elif "DomesticBrokers" in key and "TotalSell" in key:
                summary["broker_sell"] = r[key]
            elif "DomesticBrokers" in key and "Difference" in key:
                summary["broker_diff"] = r[key]
        summary["raw"] = r
        results.append(summary)
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
        "records": data,
    }


def write_json(candidates: list[dict], date_str: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{date_str}-institutional.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    total = sum(c["count"] for c in candidates)
    print(f"[JSON] {path}  ({len(candidates)} sources, {total} items)")


def write_markdown(candidates: list[dict], date_str: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{date_str}-institutional.md")
    lines = [f"# 三大法人買賣超 Candidates — {date_str}", ""]
    for c in candidates:
        flag = " ⚠️ PARTIAL" if c.get("partial_failure") else ""
        lines.append(f"## {c['market']} — {c['source']}{flag}")
        lines.append("")
        if c["records"]:
            lines.append(f"_{c['count']} 筆紀錄_")
            lines.append("")
            lines.append("| 代號 | 名稱 | 外資買賣超 | 投信買賣超 | 自營商買賣超 | 三大法人合計 |")
            lines.append("|------|------|-----------|-----------|-------------|-------------|")
            for rec in c["records"]:
                ticker = rec.get("ticker", "")
                name = rec.get("name", "")
                foreign = rec.get("foreign_diff", "-")
                broker = rec.get("broker_diff", "-")
                dealer = rec.get("dealer_total_diff", "-")
                total = rec.get("three_institutions_diff", "-")
                lines.append(f"| {ticker} | {name} | {foreign} | {broker} | {dealer} | {total} |")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[MD]   {path}")


def fetch_with_retry(fn, api_date, max_retries=3):
    """Call fn with retry on any exception."""
    for attempt in range(max_retries):
        try:
            return fn(api_date)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  → retry {attempt+1}/{max_retries} after {wait}s (error: {e})")
                time.sleep(wait)
            else:
                raise
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Fetch daily 三大法人 institutional trading data")
    ap.add_argument("--date", help="Date YYYYMMDD (default: today)")
    ap.add_argument("--backfill", type=int, default=0,
                    help="Backfill N trading days (includes today)")
    ap.add_argument("--output-dir", default="signals/candidates",
                    help="Output directory")
    ap.add_argument("--interval", type=float, default=2.5,
                    help="Seconds between backfill requests (default: 2.5)")
    args = ap.parse_args()

    if args.date:
        today = args.date
        # Accept both YYYYMMDD and YYYY-MM-DD
        api_date = today.replace("-", "")
    else:
        today = date.today().isoformat()
        api_date = today.replace("-", "")

    # --- Single day mode ---
    if args.backfill == 0:
        candidates = []
        errors = []

        print("[1/2] Fetching TWSE (上市) ...")
        try:
            data = fetch_with_retry(fetch_twse_institutional, api_date)
            candidates.append(build_candidate(data, "上市", "TWSE T86", False, today))
            print(f"  → {len(data)} items")
        except Exception as e:
            errors.append(f"TWSE error: {e}")
            candidates.append(build_candidate([], "上市", "TWSE T86", True, today))
            print(f"  → FAILED: {e}")

        print("[2/2] Fetching TPEx (上櫃) ...")
        try:
            data = fetch_with_retry(fetch_tpex_institutional, api_date)
            candidates.append(build_candidate(data, "上櫃", "TPEx T86", False, today))
            print(f"  → {len(data)} items")
        except Exception as e:
            errors.append(f"TPEx error: {e}")
            candidates.append(build_candidate([], "上櫃", "TPEx T86", True, today))
            print(f"  → FAILED: {e}")

        write_json(candidates, today, args.output_dir)
        write_markdown(candidates, today, args.output_dir)

        if errors:
            print(f"\n⚠️  {len(errors)} source(s) failed (partial results written):")
            for err in errors:
                print(f"   - {err}")
            sys.exit(1)
        else:
            total = sum(c["count"] for c in candidates)
            print(f"\n✅ Done — {total} total items across {len(candidates)} sources")

    # --- Backfill mode ---
    else:
        print(f"🔁 Backfill mode: fetching {args.backfill} trading days of TWSE T86 data")
        print(f"   Interval: {args.interval}s between requests")
        print("   ⚠️  TPEx historical support not verified — will flag for later check\n")

        # Generate date list (calendar days, will get empty responses for non-trading days)
        base = date.today()
        date_list = []
        for i in range(args.backfill):
            d = base - timedelta(days=i)
            date_list.append(d)

        twse_results = {}
        tpex_historical_support = True  # assume yes, flip flag if first attempt fails

        for i, d in enumerate(date_list):
            yyyymmdd = d.strftime("%Y%m%d")
            date_iso = d.isoformat()

            print(f"[{i+1}/{len(date_list)}] {date_iso} ... ", end="", flush=True)

            # TWSE
            try:
                data = fetch_with_retry(fetch_twse_institutional, yyyymmdd)
                twse_results[date_iso] = data
                print(f"TWSE: {len(data)} items", end="", flush=True)
            except Exception as e:
                twse_results[date_iso] = []
                print(f"TWSE: FAILED ({e})", end="", flush=True)

            # TPEx (only if historical support confirmed)
            if tpex_historical_support:
                try:
                    data = fetch_with_retry(fetch_tpex_institutional, yyyymmdd)
                    if i == 0 and len(data) == 0:
                        # First request returned empty — TPEx historical may not work
                        tpex_historical_support = False
                        print(" | TPEx: empty — will skip historical", end="", flush=True)
                    else:
                        print(f" | TPEx: {len(data)} items", end="", flush=True)
                except Exception as e:
                    if i == 0:
                        tpex_historical_support = False
                        print(f" | TPEx: FAILED ({e}) — disabling historical", end="", flush=True)
                    else:
                        print(f" | TPEx: FAILED ({e})", end="", flush=True)

            print()

            # Sleep between requests
            if i < len(date_list) - 1:
                time.sleep(args.interval)

        # Write results — one file per day with TWSE data only (TPEx as probe)
        written = 0
        for date_iso, twse_data in sorted(twse_results.items()):
            candidates = []
            candidates.append(build_candidate(twse_data, "上市", "TWSE T86", False, date_iso))
            write_json(candidates, date_iso, args.output_dir)
            written += 1

        print(f"\n✅ Backfill complete — {written} daily files written to {args.output_dir}/")
        print(f"   (TWSE T86 only; TPEx historical {'NOT supported' if not tpex_historical_support else 'supported'} — see notes)")


if __name__ == "__main__":
    main()