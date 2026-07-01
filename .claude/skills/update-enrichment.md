---
name: tw-coverage-update-enrichment
description: 更新現有個股報告的業務簡介、供應鏈、客戶供應商內容（保留財務數據）
deprecated: true
absorbed_into: my-tw-coverage
---

# 更新個股報告內容

重新研究並更新現有報告的業務簡介、供應鏈位置、主要客戶及供應商。財務數據不變。

## 前置條件

專案路徑：`/home/jyw-debian/My-TW-Coverage`
虛擬環境：`source /home/jyw-debian/My-TW-Coverage/venv/bin/activate`

## 使用方式

- `update-enrichment 2330` — 單個
- `update-enrichment 2330 2317 3034` — 多個
- `update-enrichment --batch 101` — 整批
- `update-enrichment --sector Semiconductors` — 整產業
- `update-enrichment` — 全部（需確認）

## 執行步驟

### Step 1: 確認範圍

解析使用者指定的範圍。如果範圍太大（>50 檔），先問確認。

### Step 2: 研究

對每個標的：
1. 讀取現有檔案內容
2. 網路搜尋：`[代號] 法說會`、`[代號] 年報 主要客戶`、`[公司名] supplier customer`
3. **驗證**：檔名公司名是否一致（Golden Rule #2 — 檔名是 ground truth）
4. 準備 enrichment：
   - `desc`: 繁體中文業務描述，含 [[wikilinks]]，**標註來源**（如「根據 2026 Q1 法說會...」、「2025 年報披露...」）
   - `supply_chain`: 分段上下游，含具體名稱
   - `cust`: 按業務部門的客戶與供應商

### Step 3: 套用

寫 JSON 檔後執行：
```bash
cd /home/jyw-debian/My-TW-Coverage && source venv/bin/activate && python scripts/update_enrichment.py --data enrichment.json [範圍]
```

範圍選項：`2330`、`2330 2317`、`--batch 101`、`--sector Semiconductors`，或省略 JSON 內所有項目。

### Step 4: 稽核

```bash
python scripts/audit_batch.py <batch> -v
```

確認全部通過（8+ wikilinks、無通用詞、無佔位符、無英文）。

### Step 5: 重建索引

只要這次更新有新增或修改 wikilink（幾乎每次都會），執行：

```bash
cd /home/jyw-debian/My-TW-Coverage && source venv/bin/activate && python scripts/build_wikilink_index.py
```

避免 `WIKILINKS.md`、`network/index.html`、`themes/` 跟報告內容脫節。

## 品質規則

- 每個 `[[wikilink]]` 必須是具體專有名詞
- 每檔至少 8 個 wikilinks
- 科技/材料 wikilinks 同等重要：`[[CoWoS]]`、`[[HBM]]`、`[[光阻液]]`、`[[碳化矽]]`
- **禁用通用詞**（禁止放在 `[[...]]` 內）：大廠、供應商、客戶、廠商、原廠、經銷商、製造商、業者、企業、公司
- 全部繁體中文
- 供應鏈要分段，不能單行
- 檔名是公司身份 ground truth，絕不能寫錯檔案