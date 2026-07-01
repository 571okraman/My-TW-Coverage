"""
update_enrichment.py — Update enrichment content (desc, supply chain, customers)
in ticker reports. Preserves financial tables.

This script applies enrichment data from a JSON file or inline DATA dict
to ticker report files. It replaces 業務簡介, 供應鏈位置, and 主要客戶及供應商
sections while preserving metadata and 財務概況.

Usage:
  python scripts/update_enrichment.py --data enrichment.json          # From JSON file
  python scripts/update_enrichment.py --data enrichment.json 2330     # Single ticker from JSON
  python scripts/update_enrichment.py --data enrichment.json --batch 101
  python scripts/update_enrichment.py --data enrichment.json --sector Semiconductors

JSON format:
{
  "2330": {
    "desc": "Traditional Chinese description with [[wikilinks]]...",
    "supply_chain": "**上游:**\\n- ...\\n**中游:**\\n- ...\\n**下游:**\\n- ...",
    "cust": "### 主要客戶\\n- ...\\n\\n### 主要供應商\\n- ..."
  }
}

When called by Claude via /update-enrichment skill, Claude:
1. Researches tickers via web search
2. Writes enrichment.json
3. Runs this script
"""

import os
import re
import sys
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import find_ticker_files, parse_scope_args, PROJECT_ROOT, normalize_wikilinks


def build_research_sources_section(data):
    """Build the ## 研究來源 section from enrichment data sources."""
    updated_at = data.get("updated_at") or date.today().isoformat()
    sources = data.get("sources") or []

    lines = ["## 研究來源", f"**內容更新日期:** {updated_at}", ""]

    if sources:
        for s in sources:
            title = s.get("title", "未命名來源")
            url = s.get("url", "")
            typ = s.get("type", "source")
            src_date = s.get("date", "")
            label = f"{typ}, {src_date}".strip(", ")
            if url:
                lines.append(f"- [{title}]({url}) — {label}")
            else:
                lines.append(f"- {title} — {label}")
    else:
        lines.append("- ⚠️ 待補")

    return "\n".join(lines) + "\n"


def replace_section(content, pattern, repl, ticker, section_name):
    """Replace exactly once; hard-fail if pattern doesn't match exactly once."""
    new_content, n = re.subn(pattern, repl, content, flags=re.DOTALL)
    if n != 1:
        raise ValueError(
            f"{ticker}: failed to replace {section_name}; "
            f"expected 1 match, got {n}"
        )
    return new_content


def apply_enrichment(filepath, ticker, data):
    """Apply enrichment data to a single file. Preserves metadata and financials.
    
    Raises ValueError if any required section replacement fails.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Add metadata block if missing
    if "**板塊:**" not in content and "**市值:**" not in content:
        sector = data.get("sector", "N/A")
        industry = data.get("industry", "N/A")
        meta = f"**板塊:** {sector}\n**產業:** {industry}\n**市值:** N/A 百萬台幣\n**企業價值:** N/A 百萬台幣\n\n"
        content = content.replace("## 業務簡介\n", "## 業務簡介\n" + meta, 1)

    # Replace business description (preserve metadata block above it)
    if "desc" in data:
        def repl_desc(m):
            return f"{m.group(1)}{data['desc']}\n"
        content = replace_section(
            content,
            r"(## 業務簡介\n(?:.*?企業價值:.*?\n\n|))(.*?)(?=\n## 供應鏈位置)",
            repl_desc,
            ticker,
            "業務簡介",
        )

    # Replace supply chain section
    if "supply_chain" in data:
        sc = data["supply_chain"] + "\n"
        content = replace_section(
            content,
            r"(## 供應鏈位置\n)(.*?)(?=\n## 主要客戶及供應商)",
            rf"\g<1>{sc}",
            ticker,
            "供應鏈位置",
        )

    # Replace customers/suppliers section
    if "cust" in data:
        ct = data["cust"] + "\n"
        content = replace_section(
            content,
            r"(## 主要客戶及供應商\n)(.*?)(?=\n## 財務概況)",
            rf"\g<1>{ct}",
            ticker,
            "主要客戶及供應商",
        )

    # Insert/update 研究來源 section before 財務概況
    research_section = build_research_sources_section(data)

    # Check if 研究來源 already exists in the file
    if "## 研究來源" in content:
        # Replace entire 研究來源 block: from ## 研究來源 through to ## 財務概況
        # (this handles both single and stale duplicate blocks)
        content, n = re.subn(
            r"(## 研究來源\n).*?(?=\n## 財務概況)",
            research_section,
            content,
            count=1,
            flags=re.DOTALL,
        )
        if n != 1:
            raise ValueError(
                f"{ticker}: failed to update 研究來源; expected 1 match, got {n}"
            )
    else:
        # Insert 研究來源 before 財務概況
        content, n = re.subn(
            r"(## 財務概況)",
            research_section + r"\1",
            content,
            count=1,
        )
        if n != 1:
            raise ValueError(
                f"{ticker}: 財務概況 section not found for research sources insertion"
            )

    # Normalize wikilinks: standardize aliases, collapse duplicates
    content = normalize_wikilinks(content)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        print(f"  {ticker}: ENRICHED ({os.path.basename(filepath)})")
    except UnicodeEncodeError:
        print(f"  {ticker}: ENRICHED")
    return True


def load_enrichment_data(json_path):
    """Load enrichment data from a JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = [a for a in sys.argv[1:]]

    # Extract --data flag
    json_path = None
    if "--data" in args:
        idx = args.index("--data")
        json_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if not json_path:
        print("Usage: python scripts/update_enrichment.py --data <json_file> [scope]")
        print("  Scope: 2330 | 2330 2317 | --batch 101 | --sector Semiconductors | (none=all)")
        return

    # Load enrichment data
    if not os.path.isabs(json_path):
        json_path = os.path.join(PROJECT_ROOT, json_path)
    enrichment_data = load_enrichment_data(json_path)
    print(f"Loaded {len(enrichment_data)} ticker entries from {os.path.basename(json_path)}")

    # Parse scope
    tickers, sector, desc = parse_scope_args(args)
    print(f"Scope: {desc}\n")

    # Find matching files
    # If specific tickers given, intersect with enrichment data
    available_tickers = list(enrichment_data.keys())
    if tickers:
        target_tickers = [t for t in tickers if t in enrichment_data]
    else:
        target_tickers = available_tickers

    files = find_ticker_files(target_tickers, sector)

    if not files:
        print("No matching files found.")
        return

    enriched = skipped = failed = 0
    for ticker in sorted(files.keys()):
        if ticker in enrichment_data:
            try:
                apply_enrichment(files[ticker], ticker, enrichment_data[ticker])
                enriched += 1
            except Exception as e:
                failed += 1
                print(f"  {ticker}: FAILED ({e})")
        else:
            skipped += 1

    print(f"\nDone. Enriched: {enriched} | Skipped: {skipped} | Failed: {failed}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
