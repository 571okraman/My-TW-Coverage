# Signals & Follow-ups

## 定位
Signal 是**薄層 trigger**，不重寫公司資料、不重建產業鏈、不存完整財報。
只記錄：
- 發生了什麼事件
- 來源與可信度
- topic / trigger type
- 可能關聯 themes / tickers
- 是否需要 follow-up
- status / expiry / score

Follow-up 是**由 signal 觸發的驗證問題**，需要：
- status, priority, due date, overdue query
- resolved / rejected / promoted 狀態
- 多個 signal 合併到同一個驗證問題

## 資料儲存
- **SQLite**（data/signals.sqlite）：operational state DB，source of truth
- **Markdown export**（signals/exports/）：human-readable review output
- **Pilot_Reports / themes**：既有 facts database（不修改）

## Tables
- signals — 事件主表 (status: radar/follow/thesis_candidate/rejected/expired/archived)
- signal_sources — 來源 (trust_level: high/medium/low/unverified)
- signal_topics — 關聯主題 + theme_path
- signal_tickers — 關聯個股 + exposure_reason
- followups — 驗證問題 (type: fact_check/mapping_check/exposure_check/financial_check/market_check/repo_update_check)

## Workflow
1. **Ingestion** — crawl/normalize/classify/dedupe/id signal
2. **Mapping** — signal topic → match WIKILINKS.md/themes/ → discover.py → candidate tickers
3. **Scoring** — 依 rigidity / mappability / financial_impact / time_sensitivity / verifiability 評分
4. **Follow-up** — 只有需要驗證才建立
5. **Export** — SQLite → signals/exports/ → watchlist.md → weekly_digest/

## Ingest (JSON manual)

```bash
# 從檔案 ingest
python scripts/ingest_signals.py signals/examples/input-example.json

# 從 stdin
cat signals.json | python scripts/ingest_signals.py

# 預覽不寫入
python scripts/ingest_signals.py input.json --dry-run
```

JSON 格式請參考 `signals/examples/input-example.json`。

Dedup 邏輯（優先順序）：
1. signal id 已存在 → skip
2. source URL 已存在 → skip
3. title fuzzy match (>0.85) → skip

## 初始化

