#!/usr/bin/env python3
"""fetch_announcements.py — 每日重訊公告 (T187AP04)

Sources:
  上市: https://openapi.twse.com.tw/v1/opendata/t187ap04_L
  上櫃: https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O

Both return: list[dict] directly (not wrapped in {"data": ...}).

Outputs:
  signals/candidates/YYYY-MM-DD-announcements.json  (獨立檔名，避免三支 fetcher 互相覆蓋)
  signals/candidates/YYYY-MM-DD-announcements.md
"""
import argparse
import json
import os
import sys
from datetime import date

import requests

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

T187AP04_L = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
T187AP04_O = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O"

# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_twse_announcements(api_date: str) -> list[dict]:
    """Fetch 上市重訊公告 from TWSE.

    API returns list[dict] directly. Each item has:
      公司代號, 公司名稱, 主旨, 事實發生日, 說明, 符合條款, ...
    """
    resp = requests.get(T187AP04_L, params={"date": api_date}, timeout=30)
    resp.raise_for_status()
    rows = resp.json()  # list[dict] directly
    results = []
    for r in rows:
        title = r.get("主旨", "").strip()
        if not title or title == "-":
            continue
        results.append({
            "ticker": r.get("公司代號", ""),
            "name": r.get("公司名稱", ""),
            "title": title,
            "event_date": r.get("事實發生日", api_date),
            "clause": r.get("符合條款", ""),
            "explanation": r.get("說明", ""),
            "raw": r,
        })
    return results


def fetch_tpex_announcements(api_date: str) -> list[dict]:
    """Fetch 上櫃重訊公告 from TPEx.

    API returns list[dict] directly. Each item has:
      SecuritiesCompanyCode, CompanyName, 主旨, 事實發生日, 說明, 符合條款, ...
    """
    resp = requests.get(T187AP04_O, params={"date": api_date}, timeout=30)
    resp.raise_for_status()
    rows = resp.json()  # list[dict] directly
    results = []
    for r in rows:
        title = r.get("主旨", "").strip()
        if not title or title == "-":
            continue
        results.append({
            "ticker": r.get("SecuritiesCompanyCode", ""),
            "name": r.get("CompanyName", ""),
            "title": title,
            "event_date": r.get("事實發生日", api_date),
            "clause": r.get("符合條款", ""),
            "explanation": r.get("說明", ""),
            "raw": r,
        })
    return results


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def build_candidate(announcements: list[dict], market: str, source: str,
                    partial: bool, date_str: str) -> dict:
    return {
        "source": source,
        "market": market,
        "date": date_str,
        "partial_failure": partial,
        "count": len(announcements),
        "announcements": announcements,
    }


def write_json(candidates: list[dict], date_str: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{date_str}-announcements.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    total = sum(c["count"] for c in candidates)
    print(f"[JSON] {path}  ({len(candidates)} sources, {total} items)")


def write_markdown(candidates: list[dict], date_str: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{date_str}-announcements.md")
    lines = [f"# 重訊公告 Candidates — {date_str}", ""]
    for c in candidates:
        flag = " ⚠️ PARTIAL" if c.get("partial_failure") else ""
        lines.append(f"## {c['market']} — {c['source']}{flag}")
        lines.append("")
        if c["announcements"]:
            lines.append(f"_{c['count']} 筆公告_")
            lines.append("")
            for ann in c["announcements"]:
                ticker = ann.get("ticker", "")
                name = ann.get("name", "")
                title = ann.get("title", "")
                clause = ann.get("clause", "")
                event_date = ann.get("event_date", "")
                line = f"- **{ticker} {name}**: {title}"
                if clause:
                    line += f" (條款: {clause})"
                if event_date:
                    line += f" — {event_date}"
                lines.append(line)
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[MD]   {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Fetch daily 重訊 announcements")
    ap.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    ap.add_argument("--output-dir", default="signals/candidates",
                    help="Output directory")
    args = ap.parse_args()

    today = args.date or date.today().isoformat()
    date_str = today
    api_date = date_str.replace("-", "")

    candidates = []
    errors = []

    # --- 上市 ---
    print("[1/2] Fetching TWSE (上市) ...")
    try:
        data = fetch_twse_announcements(api_date)
        candidates.append(build_candidate(data, "上市", "TWSE T187AP04", False, date_str))
        print(f"  → {len(data)} items")
    except Exception as e:
        errors.append(f"TWSE error: {e}")
        candidates.append(build_candidate([], "上市", "TWSE T187AP04", True, date_str))
        print(f"  → FAILED: {e}")

    # --- 上櫃 ---
    print("[2/2] Fetching TPEx (上櫃) ...")
    try:
        data = fetch_tpex_announcements(api_date)
        candidates.append(build_candidate(data, "上櫃", "TPEx T187AP04", False, date_str))
        print(f"  → {len(data)} items")
    except Exception as e:
        errors.append(f"TPEx error: {e}")
        candidates.append(build_candidate([], "上櫃", "TPEx T187AP04", True, date_str))
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