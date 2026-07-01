# My-TW-Coverage Runtime Contract

## Contract Version

`my-tw-coverage-runtime-contract: 2026-07-01-provenance-v1`

## Required Runtime Features

| Feature | Required | Implemented by |
|---|---:|---|
| `enrichment.updated_at` | yes | `scripts/update_enrichment.py` |
| `enrichment.sources[]` | yes | `scripts/update_enrichment.py` |
| `report.research_sources_section` | yes | `scripts/update_enrichment.py` |
| `financials.source_header` | yes | `scripts/update_financials.py` |
| `financials.updated_at_header` | yes | `scripts/update_financials.py` |
| `financials.ticker_suffix_header` | yes | `scripts/update_financials.py` |
| `discover.generic_denylist` | yes | `scripts/discover.py` |
| `update_enrichment.section_hard_fail` | yes | `scripts/update_enrichment.py` |

## Enrichment JSON Schema

```json
{
  "2330": {
    "updated_at": "YYYY-MM-DD",
    "sources": [
      {
        "title": "source title",
        "url": "https://...",
        "type": "annual_report | investor_conference | company_ir | official_release | industry_media | news | other",
        "date": "YYYY-MM-DD or YYYY-MM"
      }
    ],
    "desc": "...",
    "supply_chain": "...",
    "cust": "..."
  }
}
```

## Compatibility Rule

OpenAB skills that write enrichment content must require this contract version or newer.
