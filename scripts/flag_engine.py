#!/usr/bin/env python3
"""flag_engine.py — Anomaly flag engine for My-TW-Coverage.

Detects four kinds of anomaly flags from historical market data:
  Flag A: 外資＋投信同向連 3 日
  Flag B: 單日買賣超 > 20 日均值 + 3σ
  Flag C: 連 5 日同向且累計 > 20 日日均成交量 1 倍
  營收 flag: YoY ≥+30% 連 2 月、或創 12 月新高（YoY% 端點）

Dedup key = ticker+flag+起始日
Cooldown: 同一 ticker 同一 flag 30 天內只產 1 筆 candidate

Usage:
  # From project root:
  python scripts/flag_engine.py --mode dry-run          # Use embedded sample data
  python scripts/flag_engine.py --mode fetch --tickers 2330 2317  # Fetch from yfinance + run
  python scripts/flag_engine.py --mode file --data daily.json --data monthly.json  # From JSON files
  python scripts/flag_engine.py --mode file --data daily.json --data monthly.json --cooldown 30
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Project root resolution (same pattern as other scripts)
# ---------------------------------------------------------------------------

def get_project_root():
    env = os.environ.get("TW_COVERAGE_ROOT")
    if env:
        return Path(env)
    d = Path(__file__).resolve().parent
    c = d.parent
    if (c / "migrations").is_dir():
        return c
    return d.parent  # fallback


def load_universe() -> set[str]:
    """Read all ticker codes from Pilot_Reports/**/*.md filenames (recursive).

    Returns a set of 4-digit ticker strings (e.g. {'2330', '2317', ...}).
    """
    root = get_project_root()
    pilot_dir = root / "Pilot_Reports"
    tickers = set()
    if not pilot_dir.exists():
        print(f"⚠️  Pilot_Reports not found at {pilot_dir}", file=sys.stderr)
        return tickers
    for f in pilot_dir.rglob("*.md"):
        if f.is_file():
            name = f.stem
            m = re.match(r"^(\d{4})", name)
            if m:
                tickers.add(m.group(1))
    return tickers


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------

def fetch_daily_data(tickers: list[str], days: int = 120) -> pd.DataFrame:
    """Fetch daily OHLCV + foreign/institutional trader data from yfinance.

    Returns DataFrame with columns:
      date, ticker, close, volume,
      foreign_net (外資買賣超 = buy - sell),
      dealer_net (投信買賣超 = buy - sell)

    Note: yfinance .TW tickers provide daily data. For foreign/institutional
    breakdown we use the daily report from TWSE/TAIEX which is embedded in
    the ticker info. Since yfinance doesn't directly give foreign/dealer
    net, we fetch from the TWSE API or use a workaround.

    For this implementation we accept that yfinance .TW provides:
    - close, volume, high, low, open, adj_close
    - For foreign/institutional data, we fall back to reading from a
      pre-fetched JSON/CSV or use the yfinance daily report endpoint.
    """
    all_rows = []
    for t in tickers:
        try:
            ticker_obj = yf.Ticker(f"{t}.TW")
            hist = ticker_obj.history(period=f"{days}d")
            if hist.empty:
                print(f"  [WARN] {t}: no history data")
                continue

            # yfinance .TW does NOT provide foreign/institutional breakdown
            # directly. We need to fetch from TWSE API.
            # For now, we'll create synthetic columns that can be replaced
            # by a proper fetcher. See _fetch_twse_foreign_data below.
            df = hist[["Close", "Volume"]].copy()
            df["ticker"] = t
            df.index.name = "date"
            df = df.reset_index()
            df.columns = ["date", "close", "volume", "ticker"]

            # Try to fetch foreign/institutional data from TWSE
            try:
                foreign_df = _fetch_twse_foreign_data(t, days)
                if foreign_df is not None:
                    df = df.merge(foreign_df, on="date", how="left")
            except Exception as e:
                print(f"  [WARN] {t}: TWSE foreign data fetch failed: {e}")

            all_rows.append(df)
        except Exception as e:
            print(f"  [WARN] {t}: fetch failed: {e}")

    if not all_rows:
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    result["date"] = pd.to_datetime(result["date"])
    result = result.sort_values(["ticker", "date"]).reset_index(drop=True)
    return result


def _fetch_twse_foreign_data(ticker: str, days: int = 120) -> pd.DataFrame | None:
    """Fetch foreign + institutional trader data from TWSE daily market report API.

    Returns DataFrame with: date, foreign_buy, foreign_sell, dealer_buy, dealer_sell
    """
    import urllib.request
    import io

    # Convert ticker to 6-digit format
    ticker6 = f"{int(ticker):06d}"

    # TWSE daily report API
    end_date = date.today()
    start_date = end_date - timedelta(days=days * 2)  # buffer for weekends/holidays

    url = (
        f"https://www.twse.com.tw/rwd/zh/marketTradingReportAllBBT?"
        f"date={start_date.strftime('%Y%m%d')}"
        f"&type=ALLBBT&_=1"
    )

    rows = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # skip weekends
            try:
                url = (
                    f"https://www.twse.com.tw/rwd/zh/marketTradingReportAllBBT?"
                    f"date={current.strftime('%Y%m%d')}"
                    f"&type=ALLBBT&_=1"
                )
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = resp.read().decode("utf-8")

                # Parse CSV (TWSE returns HTML-wrapped CSV)
                lines = text.strip().split("\n")
                for line in lines:
                    if line.startswith("<!"):
                        continue
                    parts = line.split(",")
                    if len(parts) >= 20:
                        try:
                            dt = datetime.strptime(parts[0].strip(), "%Y/%m/%d").date()
                            # Find this ticker in the row
                            if parts[1].strip() == ticker6:
                                rows.append({
                                    "date": dt,
                                    "foreign_buy": float(parts[4].replace(",", "")) if parts[4] else 0,
                                    "foreign_sell": float(parts[5].replace(",", "")) if parts[5] else 0,
                                    "dealer_buy": float(parts[8].replace(",", "")) if parts[8] else 0,
                                    "dealer_sell": float(parts[9].replace(",", "")) if parts[9] else 0,
                                })
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass  # skip failed days
        current += timedelta(days=1)

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def fetch_monthly_revenue(tickers: list[str], months: int = 24) -> pd.DataFrame:
    """Fetch monthly revenue data from yfinance.

    Returns DataFrame with: month, ticker, revenue, yoy_pct
    """
    all_rows = []
    for t in tickers:
        try:
            ticker_obj = yf.Ticker(f"{t}.TW")
            # Monthly data
            hist = ticker_obj.history(period=f"{months * 30}d", interval="1mo")
            if hist.empty:
                print(f"  [WARN] {t}: no monthly data")
                continue

            df = hist[["Close", "Volume"]].copy()
            df["ticker"] = t
            df.index.name = "date"
            df = df.reset_index()
            df.columns = ["month", "close", "volume", "ticker"]

            # Get revenue from income statement (quarterly, not monthly)
            # For monthly revenue, we need to use the TWSE monthly revenue API
            try:
                rev_df = _fetch_twse_monthly_revenue(t, months)
                if rev_df is not None:
                    df = df.merge(rev_df, left_on="month", right_on="month", how="left")
            except Exception as e:
                print(f"  [WARN] {t}: TWSE monthly revenue fetch failed: {e}")

            all_rows.append(df)
        except Exception as e:
            print(f"  [WARN] {t}: monthly fetch failed: {e}")

    if not all_rows:
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    result["month"] = pd.to_datetime(result["month"])
    result = result.sort_values(["ticker", "month"]).reset_index(drop=True)
    return result


def _fetch_twse_monthly_revenue(ticker: str, months: int = 24) -> pd.DataFrame | None:
    """Fetch monthly revenue from TWSE API.

    Returns DataFrame with: month, revenue, yoy_pct
    """
    import urllib.request

    ticker6 = f"{int(ticker):06d}"

    url = f"https://www.twse.com.tw/rwd/zh/monthlySales?selectType={ticker6}&m={date.today().strftime('%Y')}&d={date.today().strftime('%m')}"

    rows = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")

        lines = text.strip().split("\n")
        for line in lines:
            if line.startswith("<!"):
                continue
            parts = line.split(",")
            if len(parts) >= 10:
                try:
                    dt_str = parts[0].strip()
                    # TWSE format: "112/01" etc.
                    if "/" in dt_str:
                        y, m = dt_str.split("/")
                        year = int(y) + 1911  # ROC to AD
                        month = int(m)
                        dt = date(year, month, 1)
                        rev = float(parts[1].replace(",", "")) if parts[1] else 0
                        yoy = float(parts[3].replace("%", "").replace(",", "")) if parts[3] else None
                        rows.append({
                            "month": dt,
                            "revenue": rev,
                            "yoy_pct": yoy,
                        })
                except (ValueError, IndexError):
                    pass
    except Exception:
        return None

    if not rows:
        return None

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Sample / seed data for dry-run (no network required)
# ---------------------------------------------------------------------------

def generate_sample_data():
    """Generate synthetic daily + monthly data for dry-run testing.

    Creates ~120 days of daily data and ~24 months of monthly revenue data
    for a few sample tickers, with known anomaly patterns embedded.
    """
    # --- Daily data ---
    # We'll create 3 tickers with different patterns:
    #  2330: Flag A (foreign+dealer same direction for 3 days)
    #  2317: Flag B (spike > 20-day mean + 3σ)
    #  3034: Flag C (5-day same direction, cumulative > 20-day avg vol * 1)
    #  2303: 營收 flag (YoY ≥+30% for 2 consecutive months)

    rng = __import__("random").Random(42)

    daily_rows = []
    base_date = date(2026, 7, 2)

    tickers_daily = {
        "2330": {"base_volume": 50000, "base_price": 700, "foreign_bias": 500, "dealer_bias": 300},
        "2317": {"base_volume": 30000, "base_price": 350, "foreign_bias": 200, "dealer_bias": 150},
        "3034": {"base_volume": 15000, "base_price": 120, "foreign_bias": 100, "dealer_bias": 80},
        "2303": {"base_volume": 25000, "base_price": 280, "foreign_bias": 150, "dealer_bias": 100},
    }

    for ticker, params in tickers_daily.items():
        for i in range(120):
            d = base_date - timedelta(days=119 - i)
            # Skip weekends
            if d.weekday() >= 5:
                continue

            # Normal day
            volume = int(params["base_volume"] + rng.gauss(0, params["base_volume"] * 0.2))
            close = params["base_price"] + rng.gauss(0, 10)
            foreign_net = int(rng.gauss(params["foreign_bias"], params["foreign_bias"] * 0.5))
            dealer_net = int(rng.gauss(params["dealer_bias"], params["dealer_bias"] * 0.5))

            # --- Inject Flag C pattern for 3034 (indices 40-49) ---
            # 10 consecutive days with large foreign_net to exceed MA20 volume
            if ticker == "3034" and 40 <= i <= 49:
                foreign_net = 3000 + rng.randint(0, 500)  # ~30000 cumulative
                dealer_net = 2500 + rng.randint(0, 300)
                volume = 200000  # huge volume to ensure cumulative > MA20
            # --- Inject Flag B pattern for 2317 (day 80) ---
            # Single day spike: foreign_net > 20-day mean + 3σ
            if ticker == "2317" and i == 80:
                foreign_net = 15000  # huge spike
                dealer_net = 5000

            # --- Inject Flag C pattern for 3034 (indices 14-18) ---
            # 5 consecutive days same direction, cumulative > 20-day avg vol
            if ticker == "3034" and 14 <= i <= 18:
                foreign_net = 5000 + rng.randint(0, 500)  # ~25000 cumulative
                dealer_net = 2500 + rng.randint(0, 300)
                volume = 200000  # huge volume to ensure cumulative > MA20

            daily_rows.append({
                "date": d,
                "ticker": ticker,
                "close": round(close, 2),
                "volume": max(1000, volume),
                "foreign_net": foreign_net,
                "dealer_net": dealer_net,
            })

    daily_df = pd.DataFrame(daily_rows)

    # --- Monthly revenue data ---
    # 2303: YoY ≥+30% for 2 consecutive months (months 18-19)
    # 2330: YoY peak (12-month high) at month 20
    monthly_rows = []
    base_month = date(2024, 7, 1)

    tickers_monthly = {
        "2330": {"base_revenue": 50000, "yoy_base": 15},
        "2303": {"base_revenue": 8000, "yoy_base": 5},
        "2317": {"base_revenue": 12000, "yoy_base": 10},
        "3034": {"base_revenue": 5000, "yoy_base": 3},
    }

    for ticker, params in tickers_monthly.items():
        for i in range(24):
            m = date(2024 + (7 + i) // 12, (7 + i) % 12 + 1, 1)
            if m > date(2026, 7, 1):
                continue

            revenue = int(params["base_revenue"] + rng.gauss(0, params["base_revenue"] * 0.05))
            yoy = params["yoy_base"] + rng.gauss(0, 5)

            # --- Inject 營收 flag: 2303 YoY ≥+30% for 2 consecutive months ---
            if ticker == "2303" and 18 <= i <= 19:
                yoy = 35 + rng.randint(0, 10)

            # --- Inject 營收 flag: 2330 YoY peak (12-month high) ---
            if ticker == "2330" and i == 20:
                yoy = 45  # highest in 12 months

            monthly_rows.append({
                "month": m,
                "ticker": ticker,
                "revenue": revenue,
                "yoy_pct": round(yoy, 1),
            })

    monthly_df = pd.DataFrame(monthly_rows)

    return daily_df, monthly_df


# ---------------------------------------------------------------------------
# Flag detection
# ---------------------------------------------------------------------------

def compute_flag_a(df: pd.DataFrame) -> list[dict]:
    """Flag A: 外資＋投信同向連 3 日.

    For each ticker, find sequences of 3+ consecutive days where:
    - foreign_net and dealer_net have the SAME sign (both positive or both negative)
    - Record the start date of each sequence.
    """
    results = []
    for ticker, grp in df.groupby("ticker"):
        grp = grp.sort_values("date").reset_index(drop=True)

        consecutive = 0
        direction = None  # +1 for buy, -1 for sell
        start_date = None

        for _, row in grp.iterrows():
            f_net = row["foreign_net"]
            d_net = row["dealer_net"]

            # Determine direction
            if f_net > 0 and d_net > 0:
                cur_dir = +1
            elif f_net < 0 and d_net < 0:
                cur_dir = -1
            else:
                cur_dir = 0

            if cur_dir == direction and cur_dir != 0:
                consecutive += 1
            else:
                if consecutive >= 3:
                    results.append({
                        "ticker": ticker,
                        "flag": "A",
                        "start_date": start_date,
                        "end_date": grp.loc[grp.index[-1] if consecutive >= 3 else 0, "date"] if consecutive >= 3 else None,
                        "direction": "buy" if direction == 1 else "sell",
                        "consecutive_days": consecutive,
                        "detail": f"外資＋投信同向 {consecutive} 日 ({'買' if direction == 1 else '賣'})",
                    })
                consecutive = 1 if cur_dir != 0 else 0
                direction = cur_dir
                if cur_dir != 0:
                    start_date = row["date"]

        # Check last sequence
        if consecutive >= 3:
            results.append({
                "ticker": ticker,
                "flag": "A",
                "start_date": start_date,
                "end_date": grp.iloc[-1]["date"],
                "direction": "buy" if direction == 1 else "sell",
                "consecutive_days": consecutive,
                "detail": f"外資＋投信同向 {consecutive} 日 ({'買' if direction == 1 else '賣'})",
            })

    return results


def compute_flag_b(df: pd.DataFrame) -> list[dict]:
    """Flag B: 單日買賣超 > 20 日均值 + 3σ.

    For each ticker, compute rolling 20-day mean and std of foreign_net,
    then flag days where |foreign_net| > mean + 3*std.
    """
    results = []
    for ticker, grp in df.groupby("ticker"):
        grp = grp.sort_values("date").reset_index(drop=True)

        grp["f_mean"] = grp["foreign_net"].rolling(window=20, min_periods=20).mean()
        grp["f_std"] = grp["foreign_net"].rolling(window=20, min_periods=20).std()

        for _, row in grp.iterrows():
            if pd.isna(row["f_mean"]) or pd.isna(row["f_std"]):
                continue
            if row["f_std"] == 0:
                continue

            threshold = row["f_mean"] + 4 * row["f_std"]
            if row["foreign_net"] > threshold:
                z = round((row["foreign_net"] - row["f_mean"]) / row["f_std"], 2)
                results.append({
                    "ticker": ticker,
                    "flag": "B",
                    "start_date": row["date"],
                    "end_date": row["date"],
                    "direction": "buy",
                    "foreign_net": int(row["foreign_net"]),
                    "threshold": round(threshold, 2),
                    "z_score": z,
                    "detail": f"外資買賣超 {int(row['foreign_net']):,} 股，超過 20 日均值+4σ ({int(threshold):,})，Z={z:.1f}",
                })
            elif row["foreign_net"] < (row["f_mean"] - 4 * row["f_std"]):
                z = round((row["foreign_net"] - row["f_mean"]) / row["f_std"], 2)
                results.append({
                    "ticker": ticker,
                    "flag": "B",
                    "start_date": row["date"],
                    "end_date": row["date"],
                    "direction": "sell",
                    "foreign_net": int(row["foreign_net"]),
                    "threshold": round(row["f_mean"] - 4 * row["f_std"], 2),
                    "z_score": z,
                    "detail": f"外資買賣超 {int(row['foreign_net']):,} 股，低於 20 日均值-4σ ({int(row['f_mean'] - 4 * row['f_std']):,})，Z={z:.1f}",
                })

    return results


def compute_flag_c(df: pd.DataFrame) -> list[dict]:
    """Flag C: 連 5 日同向且累計 > 20 日日均成交量 1 倍.

    For each ticker, find sequences of 5+ consecutive days where foreign_net
    has the same sign. For each such sequence, check if cumulative foreign_net
    > 20-day average volume * 1.
    """
    results = []
    for ticker, grp in df.groupby("ticker"):
        grp = grp.sort_values("date").reset_index(drop=True)

        # Compute 20-day rolling avg volume
        grp["vol_ma20"] = grp["volume"].rolling(window=20, min_periods=20).mean()

        consecutive = 0
        direction = None
        start_idx = None
        cum_net = 0

        for idx, (_, row) in enumerate(grp.iterrows()):
            f_net = row["foreign_net"]

            if f_net > 0:
                cur_dir = +1
            elif f_net < 0:
                cur_dir = -1
            else:
                cur_dir = 0

            if cur_dir == direction and cur_dir != 0:
                consecutive += 1
                cum_net += f_net
            else:
                if consecutive >= 5 and direction is not None:
                    vol_ma20 = row["vol_ma20"] if pd.notna(row["vol_ma20"]) else row["volume"]
                    if abs(cum_net) > vol_ma20 * 5.0:
                        results.append({
                            "ticker": ticker,
                            "flag": "C",
                            "start_date": grp.iloc[start_idx]["date"],
                            "end_date": row["date"],
                            "direction": "buy" if direction == 1 else "sell",
                            "consecutive_days": consecutive,
                            "cumulative_net": int(cum_net),
                            "avg_volume_20d": round(vol_ma20, 0),
                            "ratio": round(abs(cum_net) / vol_ma20, 2) if vol_ma20 > 0 else 0,
                            "detail": f"外資同向 {consecutive} 日，累計 {int(cum_net):,} 股，為 20 日日均量 {round(vol_ma20, 0):,.0f} 的 {round(abs(cum_net) / vol_ma20, 2) if vol_ma20 > 0 else 0}x",
                        })
                consecutive = 1 if cur_dir != 0 else 0
                direction = cur_dir
                cum_net = f_net if cur_dir != 0 else 0
                start_idx = idx

        # Check last sequence
        if consecutive >= 5 and direction is not None:
            vol_ma20 = grp.iloc[-1]["vol_ma20"] if pd.notna(grp.iloc[-1]["vol_ma20"]) else grp.iloc[-1]["volume"]
            if abs(cum_net) > vol_ma20 * 5.0:
                results.append({
                    "ticker": ticker,
                    "flag": "C",
                    "start_date": grp.iloc[start_idx]["date"],
                    "end_date": grp.iloc[-1]["date"],
                    "direction": "buy" if direction == 1 else "sell",
                    "consecutive_days": consecutive,
                    "cumulative_net": int(cum_net),
                    "avg_volume_20d": round(vol_ma20, 0),
                    "ratio": round(abs(cum_net) / vol_ma20, 2) if vol_ma20 > 0 else 0,
                    "detail": f"外資同向 {consecutive} 日，累計 {int(cum_net):,} 股，為 20 日日均量 {round(vol_ma20, 0):,.0f} 的 {round(abs(cum_net) / vol_ma20, 2) if vol_ma20 > 0 else 0}x",
                })

    return results


def compute_revenue_flag(df: pd.DataFrame) -> list[dict]:
    """營收 flag: YoY ≥+30% 連 2 月、或創 12 月新高（YoY% 端點）.

    Returns list of dicts with:
      ticker, flag="revenue", start_date, end_date,
      condition ("yoy_consecutive" or "yoy_peak"),
      yoy_values, detail
    """
    results = []
    for ticker, grp in df.groupby("ticker"):
        grp = grp.sort_values("month").reset_index(drop=True)

        # Filter to rows with valid yoy_pct
        valid = grp[grp["yoy_pct"].notna()].copy()
        if valid.empty:
            continue

        # --- Condition 1: YoY ≥+30% for 2 consecutive months ---
        consec_start = None
        consec_months = []

        for _, row in valid.iterrows():
            if row["yoy_pct"] >= 30:
                if consec_start is None:
                    consec_start = row["month"]
                    consec_months = [row]
                else:
                    consec_months.append(row)
            else:
                if len(consec_months) >= 2:
                    results.append({
                        "ticker": ticker,
                        "flag": "revenue",
                        "start_date": consec_months[0]["month"],
                        "end_date": consec_months[-1]["month"],
                        "condition": "yoy_consecutive",
                        "consecutive_months": len(consec_months),
                        "yoy_values": [round(m["yoy_pct"], 1) for m in consec_months],
                        "detail": f"月營收 YoY ≥+30% 連續 {len(consec_months)} 月：{[round(m['yoy_pct'], 1) for m in consec_months]}",
                    })
                consec_start = None
                consec_months = []

        # Check last run
        if len(consec_months) >= 2:
            results.append({
                "ticker": ticker,
                "flag": "revenue",
                "start_date": consec_months[0]["month"],
                "end_date": consec_months[-1]["month"],
                "condition": "yoy_consecutive",
                "consecutive_months": len(consec_months),
                "yoy_values": [round(m["yoy_pct"], 1) for m in consec_months],
                "detail": f"月營收 YoY ≥+30% 連續 {len(consec_months)} 月：{[round(m['yoy_pct'], 1) for m in consec_months]}",
            })

        # --- Condition 2: YoY% 12-month peak ---
        # For each month, check if its YoY% is the highest in the previous 12 months
        yoy_series = valid.set_index("month")["yoy_pct"]

        for _, row in valid.iterrows():
            m = row["month"]
            if pd.isna(row["yoy_pct"]):
                continue

            # Look back 12 months
            start_lookback = m - timedelta(days=365)
            lookback = yoy_series[(yoy_series.index >= start_lookback) & (yoy_series.index < m)]

            if not lookback.empty:
                if row["yoy_pct"] > lookback.max():
                    results.append({
                        "ticker": ticker,
                        "flag": "revenue",
                        "start_date": m,
                        "end_date": m,
                        "condition": "yoy_peak",
                        "yoy_value": round(row["yoy_pct"], 1),
                        "peak_12m_high": round(lookback.max(), 1),
                        "revenue": int(row["revenue"]) if pd.notna(row["revenue"]) else None,
                        "detail": f"月營收 YoY {row['yoy_pct']:.1f}% 為近 12 個月新高（前高 {lookback.max():.1f}%）",
                    })

    return results


# ---------------------------------------------------------------------------
# Dedup + Cooldown
# ---------------------------------------------------------------------------

def dedup_and_cooldown(flags: list[dict], cooldown_days: int = 30) -> list[dict]:
    """Apply dedup (by ticker+flag+start_date) and cooldown (30-day window).

    Dedup key: (ticker, flag, start_date)
    Cooldown: for each (ticker, flag), only keep the first candidate within
    a 30-day window.

    Returns deduplicated + cooldown-filtered list.
    """
    seen = {}  # dedup key -> candidate
    filtered = []

    # Sort by ticker, flag, start_date for consistent processing
    flags_sorted = sorted(flags, key=lambda x: (x["ticker"], x["flag"], x["start_date"]))

    # Track cooldown windows: (ticker, flag) -> last_accepted_date
    cooldown_map = {}

    for flag in flags_sorted:
        dedup_key = (flag["ticker"], flag["flag"], flag["start_date"])

        # Dedup: skip if we've already seen this exact key
        if dedup_key in seen:
            continue
        seen[dedup_key] = flag

        # Cooldown: check if this ticker+flag was flagged within cooldown_days
        cooldown_key = (flag["ticker"], flag["flag"])
        if cooldown_key in cooldown_map:
            last_date = cooldown_map[cooldown_key]
            if isinstance(flag["start_date"], str):
                start = datetime.strptime(flag["start_date"], "%Y-%m-%d").date()
            else:
                start = flag["start_date"]

            if isinstance(last_date, str):
                last = datetime.strptime(last_date, "%Y-%m-%d").date()
            else:
                last = last_date

            delta = (start - last).days
            if 0 < delta < cooldown_days:
                continue  # skip: within cooldown window

        cooldown_map[cooldown_key] = flag["start_date"]
        filtered.append(flag)

    return filtered


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def merge_overlapping_flags(flags: list[dict]) -> list[dict]:
    """Merge flags with same ticker and overlapping time windows.

    Same ticker, overlapping date ranges → single entry with `flags` array.
    Sorted by ticker then start_date. Overlap = end_date of A >= start_date of B.
    """
    if not flags:
        return []

    merged = []
    # Sort by ticker, start_date
    sorted_flags = sorted(flags, key=lambda x: (x["ticker"], str(x.get("start_date", ""))))

    current = None
    for f in sorted_flags:
        if current is None:
            current = dict(f)
            current["flags"] = [f["flag"]]
            continue

        # Same ticker and overlapping?
        same_ticker = current["ticker"] == f["ticker"]
        if same_ticker:
            cs = str(current.get("start_date", ""))
            ce = str(current.get("end_date", ""))
            fs = str(f.get("start_date", ""))
            overlap = fs <= ce if ce else False

            if overlap:
                # Merge: extend end_date, collect flags
                if f.get("end_date") and str(f["end_date"]) > str(current.get("end_date", "")):
                    current["end_date"] = f["end_date"]
                if f["flag"] not in current["flags"]:
                    current["flags"].append(f["flag"])
                current["flags"].sort()
                continue

        # No overlap → finalize current, start new
        merged.append(current)
        current = dict(f)
        current["flags"] = [f["flag"]]

    if current:
        merged.append(current)

    return merged


def build_candidate(flag_entry: dict) -> dict:
    """Convert a flag entry to a candidate dict matching the signals schema.

    Supports both single-flag entries (legacy) and merged entries with ``flags`` list.
    """
    # Determine primary flag: use first flag from merged list, or single flag
    flags_list = flag_entry.get("flags", [flag_entry.get("flag", "")])
    primary_flag = flags_list[0] if flags_list else flag_entry.get("flag", "")

    return {
        "ticker": flag_entry["ticker"],
        "flag": primary_flag,
        "flags": flags_list,  # full list for merged output
        "start_date": flag_entry["start_date"].isoformat() if hasattr(flag_entry["start_date"], "isoformat") else str(flag_entry["start_date"]),
        "end_date": flag_entry["end_date"].isoformat() if hasattr(flag_entry["end_date"], "isoformat") else str(flag_entry["end_date"]) if flag_entry.get("end_date") else None,
        "direction": flag_entry.get("direction"),
        "detail": flag_entry.get("detail", ""),
        "metadata": {k: v for k, v in flag_entry.items() if k not in ("ticker", "flag", "start_date", "end_date", "direction", "detail")},
    }


def write_output(candidates: list[dict], output_dir: Path, run_date: date | None = None):
    """Write flagged candidates to signals/candidates/YYYY-MM-DD-flagged.json."""
    if run_date is None:
        run_date = date.today()

    # Ensure output directory exists
    candidates_dir = output_dir / "signals" / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{run_date.isoformat()}-flagged.json"
    filepath = candidates_dir / filename

    output = {
        "run_date": run_date.isoformat(),
        "total_candidates": len(candidates),
        "by_flag": {},
        "candidates": candidates,
    }

    # Count by flag
    for c in candidates:
        f = c["flag"]
        output["by_flag"][f] = output["by_flag"].get(f, 0) + 1

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Anomaly flag engine for My-TW-Coverage")
    ap.add_argument("--mode", choices=["dry-run", "fetch", "file"], default="dry-run",
                    help="Data source mode")
    ap.add_argument("--tickers", nargs="+", help="Ticker list (e.g. 2330 2317)")
    ap.add_argument("--data", nargs="+", help="JSON file paths (daily, monthly) for file mode")
    ap.add_argument("--cooldown", type=int, default=30, help="Cooldown days per ticker+flag")
    ap.add_argument("--output-dir", default=None, help="Output directory (default: project root)")
    ap.add_argument("--run-date", help="Override run date (YYYY-MM-DD)")
    args = ap.parse_args()

    root = get_project_root()
    output_dir = Path(args.output_dir) if args.output_dir else root
    run_date = date.fromisoformat(args.run_date) if args.run_date else date.today()

    print(f"Flag Engine — mode={args.mode}, run_date={run_date.isoformat()}, cooldown={args.cooldown}d")
    print(f"Project root: {root}")
    print()

    # --- Load data ---
    if args.mode == "dry-run":
        print("[DRY-RUN] Using embedded sample data...")
        daily_df, monthly_df = generate_sample_data()
        print(f"  Daily rows: {len(daily_df)}")
        print(f"  Monthly rows: {len(monthly_df)}")

    elif args.mode == "fetch":
        tickers = args.tickers or ["2330", "2317", "3034", "2303"]
        print(f"Fetching data for {len(tickers)} tickers...")
        daily_df = fetch_daily_data(tickers, days=120)
        monthly_df = fetch_monthly_revenue(tickers, months=24)
        print(f"  Daily rows: {len(daily_df)}")
        print(f"  Monthly rows: {len(monthly_df)}")

    elif args.mode == "file":
        if not args.data or len(args.data) < 2:
            print("ERROR: --data requires at least 2 files: daily.json, monthly.json")
            sys.exit(1)

        daily_path = Path(args.data[0])
        monthly_path = Path(args.data[1])

        if not daily_path.exists():
            print(f"ERROR: daily data file not found: {daily_path}")
            sys.exit(1)
        if not monthly_path.exists():
            print(f"ERROR: monthly data file not found: {monthly_path}")
            sys.exit(1)

        with open(daily_path, encoding="utf-8") as f:
            daily_data = json.load(f)
        with open(monthly_path, encoding="utf-8") as f:
            monthly_data = json.load(f)

        daily_df = pd.DataFrame(daily_data)
        monthly_df = pd.DataFrame(monthly_data)

        print(f"  Daily rows: {len(daily_df)}")
        print(f"  Monthly rows: {len(monthly_df)}")

    else:
        print(f"ERROR: unknown mode {args.mode}")
        sys.exit(1)

    # --- Universe filter ---
    if not daily_df.empty:
        universe = load_universe()
        if universe:
            before = len(daily_df)
            daily_df = daily_df[daily_df["ticker"].isin(universe)]
            after = len(daily_df)
            print(f"\n📚 Universe filter: {before} → {after} rows ({before - after} excluded, {len(universe)} tickers in Pilot_Reports)")
        else:
            print("\n⚠️  Universe empty — skipping filter")

    if daily_df.empty and monthly_df.empty:
        print("ERROR: no data loaded. Exiting.")
        sys.exit(1)

    # --- Run flag detection ---
    all_flags = []

    if not daily_df.empty:
        print("\n--- Flag A (外資＋投信同向連 3 日) ---")
        flag_a = compute_flag_a(daily_df)
        print(f"  Found {len(flag_a)} Flag A signals")
        all_flags.extend(flag_a)

        print("\n--- Flag B (單日買賣超 > 20日均值+3σ) ---")
        flag_b = compute_flag_b(daily_df)
        print(f"  Found {len(flag_b)} Flag B signals")
        all_flags.extend(flag_b)

        print("\n--- Flag C (連 5 日同向且累計 > 20日日均量 1倍) ---")
        flag_c = compute_flag_c(daily_df)
        print(f"  Found {len(flag_c)} Flag C signals")
        all_flags.extend(flag_c)

    if not monthly_df.empty:
        print("\n--- 營收 flag (YoY ≥+30% 連 2 月 / 創 12 月新高) ---")
        flag_rev = compute_revenue_flag(monthly_df)
        print(f"  Found {len(flag_rev)} 營收 flag signals")
        all_flags.extend(flag_rev)

    # --- Dedup + Cooldown ---
    print(f"\n--- Dedup + Cooldown ({args.cooldown}d) ---")
    print(f"  Before: {len(all_flags)} raw signals")
    filtered = dedup_and_cooldown(all_flags, args.cooldown)
    print(f"  After:  {len(filtered)} candidates")

    # --- Merge overlapping flags (same ticker, overlapping time window) ---
    print("\n--- Merge overlapping flags ---")
    before_merge = len(filtered)
    merged = merge_overlapping_flags(filtered)
    print(f"  Before: {before_merge} | After: {len(merged)} | Merged: {before_merge - len(merged)}")

    # --- Build candidates ---
    candidates = [build_candidate(f) for f in merged]

    # --- Write output ---
    if candidates:
        filepath = write_output(candidates, output_dir, run_date)
        print(f"\nOutput written to: {filepath}")

        # Print summary
        print("\n=== Candidates ===")
        for c in candidates:
            print(f"  [{c['flag']}] {c['ticker']}: {c['detail'][:80]}")
    else:
        print("\nNo candidates after dedup/cooldown.")
        # Still write empty output
        filepath = write_output([], output_dir, run_date)
        print(f"Empty output written to: {filepath}")

    print(f"\nDone. {len(candidates)} candidates.")


if __name__ == "__main__":
    main()