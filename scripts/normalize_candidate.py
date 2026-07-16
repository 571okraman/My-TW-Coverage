#!/usr/bin/env python3
"""normalize_candidate.py — 三線 candidate normalization (T09).

Reads three source types independently:
  - announcements  (*-announcements.json): clause whitelist + universe filter
  - institutional  (*-flagged.json):       flag_engine output, pass-through with flags
  - revenue        (*-revenue.json):       YoY ≥+30% 2mo OR 12mo high; partial if <2mo

Outputs:
  signals/candidates/YYYY-MM-DD-normalized.json (merged unified schema)

Enriched fields (v1 contract — 變更需重裁):
  - title:    [TOKEN] {ticker} {short} {event_date} {body}
  - trigger_type: source_type 映射 (announcement→policy_regulation, revenue→financial_inflection)
  - priority: "medium"
  - expires_at: None

Token 契約 (v1):
  token = md5(f"{ticker}|{source_type}|{event_date}|{summary}").hexdigest()[:6]
  欄位順序固定；source_type 用 normalize 枚舉值 (announcement|revenue)
  event_date 先 roc_to_iso 再進 token/title
  庫內 280 筆舊 token 為 Bridge v5 遺產，不回填、不重算，新舊並存

Usage:
  python3 normalize_candidate.py [--date YYYY-MM-DD] [--dry-run]
"""

import argparse
import hashlib
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

# trigger_type 映射 (v1 — 照 C0 golden 復刻；語意勘誤列 Phase 2)
TRIGGER_MAP = {
    "announcement": "policy_regulation",
    "revenue": "financial_inflection",
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


def roc_to_iso(s: str) -> str:
    """民國日期 → ISO: 1150715 → 2026-07-15；已是 ISO 則原樣返回。"""
    s = (s or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    if re.fullmatch(r"\d{7}", s):  # YYYMMDD 民國
        y = int(s[:3]) + 1911
        return f"{y:04d}-{s[3:5]}-{s[5:7]}"
    raise ValueError(f"bad event_date: {s!r}")


def make_token(ticker: str, source_type: str, event_date: str, summary: str) -> str:
    """Token 契約 v1: md5(ticker|source_type|event_date|summary)[:6]"""
    canonical = f"{ticker}|{source_type}|{event_date}|{summary}"
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()[:6]


def enrich(c: dict) -> dict:
    """補齊 ingest 契約欄位。未知 source_type → 報錯拒出。"""
    st = c.get("source_type")
    if st not in TRIGGER_MAP:
        raise ValueError(f"unknown source_type: {st!r}")

    # event_date 先轉 ISO
    ed = roc_to_iso(c["event_date"])
    c["event_date"] = ed

    summary = c["summary"]
    ticker = c["ticker"]
    tok = make_token(ticker, st, ed, summary)
    short = "ann" if st == "announcement" else "rev"

    # title 模板 (照 C0 golden 復刻)
    if st == "announcement":
        # golden: [tok] {ticker} ann {date} {主旨不含 ticker 前綴}
        body = summary
        if body.startswith(ticker):
            body = body[len(ticker):].lstrip()
        c["title"] = f"[{tok}] {ticker} {short} {ed} {body}"
    else:
        # golden: [tok] {ticker} rev {date} YoY+X.X% r={revenue}
        raw = c.get("raw_data") or {}
        yoy = raw.get("yoy_pct")
        rev = raw.get("revenue")
        yoy_s = f"YoY+{yoy:.1f}%" if isinstance(yoy, (int, float)) else "YoY+?"
        r_s = f"r={int(rev)}" if isinstance(rev, (int, float)) else "r=?"
        c["title"] = f"[{tok}] {ticker} {short} {ed} {yoy_s} {r_s}"

    c["trigger_type"] = TRIGGER_MAP[st]
    c["priority"] = "medium"
    c["expires_at"] = None
    return c


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
            c = {
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
            }
            c = enrich(c)
            candidates.append(c)
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
        start = str(entry.get("start_date", ""))[:10]
        if start != date_str:
            continue
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

    from collections import defaultdict
    by_ticker = defaultdict(list)
    for r in records:
        by_ticker[r["ticker"]].append(r)

    for ticker, recs in by_ticker.items():
        recs.sort(key=lambda x: x["month"])
        for r in recs:
            if r["yoy_pct"] is not None and r["yoy_pct"] >= 30:
                c = {
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
                }
                c = enrich(c)
                candidates.append(c)
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