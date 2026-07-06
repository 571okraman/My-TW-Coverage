# Pending Manual Review

> Source: theme_graph.sqlite seed (PS-20260701-001-T04)
> Generated: 2026-07-06 04:09 UTC
> Status: awaiting 571 approval before灌庫

---

## 1. 台達電 2308 — 詞義漂移（resolved）

| Field | Value |
|---|---|
| Ticker | 2308 |
| Company | 台達電 |
| Node | NODE-transformer（大型電力變壓器） |
| Theme | THEME-heavy-electric |
| Reason | 「變壓器」命中語境待查：重電 vs 電源供應器 |
| **裁決** | **resolved（2026-07-07，571）**：「變壓器」命中 = 電源供應器／SST 固態變壓器語境（磁性元件＋Grid-to-Chip SST，均非油浸式大型電力變壓器） |
| Action | **不灌 NODE-transformer↔2308**；node_companies 24 列不動 |

> 附註：「AIDC 電力架構（HVDC／SST）」登記為未來 node 候選（台達電 2308／光寶科 2301／漢磊 3707 同鏈；屬新 node/theme 評估，非重電 theme 擴列）。

## 2. GIS 縮寫撞名（已剔除，不灌庫）

| Ticker | Company | Reason |
|---|---|---|
| 6456 | GIS-KY | 氣體絕緣開關（非台灣台股標的，撞名） |
| 6486 | 互動 | GIS 撞名 |
| 8067 | 志旭 | GIS 撞名 |

> 真正 GIS 命中：中興電 1513、大同 2371（已灌庫）

## 3. HBM 詞義漂移（候選池，不影響正式映射）

| Field | Value |
|---|---|
| Seed | Seed 2（CoWoS / 先進封裝） |
| Issue | HBM 詞義漂移屬候選池問題，正式映射表不受影響 |
| Action | 不灌庫，等 spot check 後另批 task |

---

*總計：3 項 pending → 1 resolved（不灌）+ 2 已剔除/候選池；無待核可項*
