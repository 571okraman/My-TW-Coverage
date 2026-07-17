#!/usr/bin/env python3
from ssl_util import make_session
_SESSION = make_session()
"""fetch_announcements.py — 每日重訊公告 (T187AP04)

Sources:
  上市: https://openapi.twse.com.tw/v1/opendata/t187ap04_L
  上櫃: https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O

Both return: list[dict] directly (not wrapped in {"data": ...}).

Outputs:
  signals/candidates/YYYY-MM-DD-announcements.json  (獨立檔名，避免三支 fetcher 互相覆蓋)
  signals/candidates/YYYY-MM-DD-announcements.md
  signals/candidates/YYYY-MM-DD-announcements-summary.json  (per-source count summary)
    Format: {"date": str, "type": "announcements", "sources": [{"source","market","count","retries","timestamp"}]}

Summary file naming convention (commit message + header comment):
  announce:  signals/candidates/YYYY-MM-DD-announcements-summary.json
  revenue:   signals/candidates/YYYY-MM-DD-revenue-summary.json
  Both follow: {date}-{type}-summary.json
"""

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

T187AP04_L = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
T187AP04_O = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O"

# ---------------------------------------------------------------------------
# Retry config (env-overridable)
# ---------------------------------------------------------------------------

TPEX_RETRIES = int(os.environ.get("TPEX_ANN_RETRIES", "3"))
TPEX_RETRY_INTERVAL = int(os.environ.get("TPEX_ANN_RETRY_INTERVAL", "30"))

# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


def fetch_twse_announcements(api_date: str) -> list[dict]:
    """Fetch 上市重訊公告 from TWSE.

    API returns list[dict] directly. Each item has:
      公司代號, 公司名稱, 主旨, 事實發生日, 說明, 符合條款, ...
    """
    resp = _SESSION.get(T187AP04_L, params={"date": api_date}, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    if not isinstance(rows, list):
        raise ValueError("Expected list response")
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


def fetch_tpex_announcements_with_retry(api_date: str) -> tuple[list[dict], int]:
    """Fetch 上櫃重訊公告 from TPEx, with transport-layer retry on empty response.

    HTTP 200 + empty list → retry up to TPEX_RETRIES times (default 3),
    each spaced by TPEX_RETRY_INTERVAL seconds (default 30).
    If all retries return empty, returns empty list with retries=TPEX_RETRIES
    (legitimate empty — EXIT 0).

    Returns (data, retries_used).
    """
    retries_used = 0
    for attempt in range(TPEX_RETRIES + 1):  # 1 initial + up to N retries
        if attempt > 0:
            retries_used += 1
            print(f"  TPEx empty, retry {retries_used}/{TPEX_RETRIES} after {TPEX_RETRY_INTERVAL}s ...")
            time.sleep(TPEX_RETRY_INTERVAL)

        resp = _SESSION.get(T187AP04_O, params={"date": api_date}, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        if not isinstance(rows, list):
            raise ValueError("Expected list response")

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

        if results:
            return results, retries_used
        # Empty list → retry (unless last attempt)
        if attempt < TPEX_RETRIES:
            continue
        # All retries exhausted — legitimate empty
        print(f"  TPEx empty after {TPEX_RETRIES} retries — legitimate empty")
        return [], retries_used

    return [], retries_used  # unreachable


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def build_summary(date_str: str, fetch_type: str, sources: list[dict]) -> dict:
    """Build per-source count summary JSON."""
    return {
        "date": date_str,
        "type": fetch_type,
        "sources": sources,
    }


def write_summary(summary: dict, date_str: str, output_dir: str):
    """Write summary file alongside JSON/MD outputs."""
    os.makedirs(output_dir, exist_ok=True)
    # Summary file naming: {date}-{type}-summary.json
    # See commit message and header comment for naming convention.
    path = os.path.join(output_dir, f"{date_str}-announcements-summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[SUMMARY] {path}  ({len(summary['sources'])} sources)")


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
    summary_sources = []

    now_iso = datetime.utcnow().isoformat()

    # --- 上市 ---
    print("[1/2] Fetching TWSE (上市) ...")
    try:
        data = fetch_twse_announcements(api_date)
        candidates.append(build_candidate(data, "上市", "TWSE T187AP04", False, date_str))
        print(f"  → {len(data)} items")
        summary_sources.append({
            "source": "TWSE T187AP04",
            "market": "上市",
            "count": len(data),
            "retries": 0,
            "timestamp": now_iso,
        })
    except Exception as e:
        errors.append(f"TWSE error: {e}")
        candidates.append(build_candidate([], "上市", "TWSE T187AP04", True, date_str))
        print(f"  → FAILED: {e}")
        summary_sources.append({
            "source": "TWSE T187AP04",
            "market": "上市",
            "count": 0,
            "retries": 0,
            "timestamp": now_iso,
        })

    # --- 上櫃 (with retry) ---
    print("[2/2] Fetching TPEx (上櫃) ...")
    try:
        data, retries_used = fetch_tpex_announcements_with_retry(api_date)
        partial = retries_used > 0 and len(data) == 0
        candidates.append(build_candidate(data, "上櫃", "TPEx T187AP04", partial, date_str))
        print(f"  → {len(data)} items (retries={retries_used})")
        summary_sources.append({
            "source": "TPEx T187AP04",
            "market": "上櫃",
            "count": len(data),
            "retries": retries_used,
            "timestamp": now_iso,
        })
    except Exception as e:
        errors.append(f"TPEx error: {e}")
        candidates.append(build_candidate([], "上櫃", "TPEx T187AP04", True, date_str))
        print(f"  → FAILED: {e}")
        summary_sources.append({
            "source": "TPEx T187AP04",
            "market": "上櫃",
            "count": 0,
            "retries": 0,
            "timestamp": now_iso,
        })

    # Write outputs
    write_json(candidates, date_str, args.output_dir)
    write_markdown(candidates, date_str, args.output_dir)

    # Write per-source count summary
    summary = build_summary(date_str, "announcements", summary_sources)
    write_summary(summary, date_str, args.output_dir)

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
