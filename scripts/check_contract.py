#!/usr/bin/env python3
"""check_contract.py — Verify My-TW-Coverage runtime supports all required features.

Usage:
  python scripts/check_contract.py

Exit 0 if all features present, exit 1 if any missing.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

CONTRACT_VERSION = "2026-07-01-provenance-v1"

REQUIRED_FEATURES = {
    "enrichment.updated_at": ("scripts/update_enrichment.py", "updated_at"),
    "enrichment.sources": ("scripts/update_enrichment.py", "sources"),
    "report.research_sources_section": ("scripts/update_enrichment.py", "研究來源"),
    "financials.source_header": ("scripts/update_financials.py", "資料來源"),
    "financials.updated_at_header": ("scripts/update_financials.py", "財務更新日期"),
    "financials.ticker_suffix_header": ("scripts/update_financials.py", "Ticker suffix"),
    "discover.generic_denylist": ("scripts/discover.py", "GENERIC_DENYLIST"),
    "discover.readonly_guard": ("scripts/discover.py", "read-only path violation"),
    "discover.concept_expansion": ("scripts/discover.py", "expand_query"),
    "alias_map.load_from_yaml": ("scripts/utils.py", "ALIAS_MAP_PATH"),
    "alias_map.validate_function": ("scripts/utils.py", "def validate_alias_map"),
    "alias_map.expand_query": ("scripts/utils.py", "def expand_query"),
    "update_enrichment.section_hard_fail": ("scripts/update_enrichment.py", "re.subn"),
}


def main():
    failures = []

    for feature, (path, marker) in REQUIRED_FEATURES.items():
        p = ROOT / path
        if not p.exists():
            failures.append({"feature": feature, "reason": f"missing file: {path}"})
            continue

        text = p.read_text(encoding="utf-8")
        if marker not in text:
            failures.append({"feature": feature, "reason": f"missing marker: {marker}"})

    result = {
        "contract": "my-tw-coverage-runtime-contract",
        "version": CONTRACT_VERSION,
        "ok": not failures,
        "features": sorted(REQUIRED_FEATURES.keys()),
        "failures": failures,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()