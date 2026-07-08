#!/usr/bin/env python3
"""extract_briefing.py — 法說簡報抽取 lane（Patch C）。

事件驅動＋回溯當期：signal 命中公司才扒，且回頭扒最近一期法說。

管線：
1. signal 命中公司 → TDCC IR Platform / MOPS 查最近一期法說
2. 下載簡報 PDF
3. 抽取分流：
   - 文字層 PDF → pymupdf（零成本）
   - 圖表密集/掃描件 → Unlimited-OCR（GPU 部署歸晉三裁，未裁前此步人工或 pymupdf 湊合）
4. 產出 markdown 進 repo：signals/docs/<ticker>/<YYYY-MM-DD>-briefing.md
5. 晉十判讀 → 回寫對應 followup

紅線：抽取產物只進 signals/docs/，不寫 enrichment/Pilot_Reports/（唯讀紅線不變）。
"""
import argparse
import os
import re
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("FATAL: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

# ── TDCC IR Platform（法說行事曆）──
TDCC_BASE = "https://irplatform.tdcc.com.tw/ir/zh/event/list"
# ── MOPS 電子書（財報/年報/股東會年報 PDF）──
MOPS_BASE = "https://mops.twse.com.tw"

# ── SSL 繞過（Debian CA 憑證庫過舊）──
def _unverified_urlopen(url, headers=None, timeout=30):
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=headers or {})
    return urllib.request.urlopen(req, context=ctx, timeout=timeout)


def _fetch_tdcc_briefings():
    """抓取 TDCC IR Platform 法說行事曆（需 JS 渲染，此處為 stub）。"""
    # TDCC 頁面需要 JS 渲染，短期用 pymupdf 直接抓已知 PDF URL
    # 完整實現需搭配 SeleniumBase / Playwright
    print("[WARN] TDCC IR Platform 需 JS 渲染，此函式為 stub")
    return []


def _fetch_mops_briefings(ticker):
    """抓取 MOPS 電子書 PDF 列表。"""
    # MOPS 電子書 URL 格式：https://mops.twse.com.tw/mops/web/ajax/mop999e
    # 完整實現需解析 MOPS 頁面結構
    print(f"[WARN] MOPS 電子書抓取需解析頁面結構，此函式為 stub (ticker={ticker})")
    return []


def _download_pdf(url, dest_path):
    """下載 PDF 到本地。"""
    resp = _unverified_urlopen(url)
    data = resp.read()
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(dest_path).write_bytes(data)
    return dest_path


def _extract_text_layer(pdf_path, output_md):
    """pymupdf 文字層抽取（零成本）。"""
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            lines.append(f"## Page {page.number + 1}\n\n{text.strip()}\n")
    doc.close()
    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md).write_text("\n".join(lines), encoding="utf-8")
    return output_md


def _ocr_stub(pdf_path, output_md):
    """Unlimited-OCR stub。GPU 部署歸晉三裁。"""
    print(f"[STUB] OCR lane 未部署，跳過: {pdf_path}")
    print(f"[STUB] 請用 pymupdf 文字層抽取替代: _extract_text_layer('{pdf_path}', '{output_md}')")
    return None


def extract_briefing(ticker, output_dir=None, date=None, method="pymupdf"):
    """主入口：抽取指定公司的法說簡報。

    Args:
        ticker: 公司代號（如 "2330"）
        output_dir: 輸出目錄（預設 signals/docs/<ticker>/）
        date: 指定日期 YYYY-MM-DD（回溯當期用）
        method: "pymupdf" 或 "ocr"（未部署時自動回退 pymupdf）

    Returns:
        輸出 markdown 路徑，或 None（無簡報可抽）
    """
    if output_dir is None:
        output_dir = Path("signals/docs") / ticker

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # TODO: 實作 TDCC / MOPS 查詢邏輯
    # 目前為 stub，回傳 None 告知需手動介入
    print(f"[INFO] extract_briefing stub: ticker={ticker}, method={method}")
    print(f"[INFO] 請手動下載簡報 PDF 到 {output_dir}/ 後執行 _extract_text_layer()")
    return None


def main():
    ap = argparse.ArgumentParser(description="法說簡報抽取 lane (Patch C)")
    ap.add_argument("--ticker", required=True, help="公司代號（如 2330）")
    ap.add_argument("--output-dir", default=None, help="輸出目錄（預設 signals/docs/<ticker>/）")
    ap.add_argument("--date", default=None, help="指定日期 YYYY-MM-DD（回溯當期用）")
    ap.add_argument("--method", choices=["pymupdf", "ocr"], default="pymupdf",
                    help="抽取方法（ocr 未部署時自動回退 pymupdf）")
    args = ap.parse_args()

    result = extract_briefing(
        ticker=args.ticker,
        output_dir=args.output_dir,
        date=args.date,
        method=args.method,
    )
    if result:
        print(f"[OK] 產出: {result}")
    else:
        print("[SKIP] 無簡報可抽（stub 模式）")


if __name__ == "__main__":
    main()
