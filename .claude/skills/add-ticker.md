---
name: tw-coverage-add-ticker
description: 新增台股公司到 My-TW-Coverage 資料庫，生成報告並 AI 研究補充內容
deprecated: true
absorbed_into: my-tw-coverage
---

# 新增台股公司報告

將一家台灣上市公司加入資料庫，生成 .md 報告檔並補充業務內容。

## 前置條件

專案路徑：`/home/jyw-debian/My-TW-Coverage`
虛擬環境：`source /home/jyw-debian/My-TW-Coverage/venv/bin/activate`

## 使用方式

- `add-ticker 2330 台積電` — 自動偵測產業
- `add-ticker 2330 台積電 --sector Semiconductors` — 指定產業

## 執行步驟

### Step 1: 生成基礎報告

```bash
cd /home/jyw-debian/My-TW-Coverage && source venv/bin/activate && python scripts/add_ticker.py <代號> <公司名> [--sector <產業>]
```

會生成 .md 檔，包含 yfinance 財務數據 + 佔位符 enrichment 區塊。

### Step 2: AI 研究與補充

1. 網路搜尋：`[代號] 法說會`、`[代號] 年報 主要客戶`、`[公司名] supplier customer`
2. **驗證**：檔名公司名是否與研究一致（Golden Rule #2 — 檔名是 ground truth）
3. 準備 JSON 格式的 enrichment 數據：
```json
{
  "2330": {
    "desc": "繁體中文描述，含 [[wikilinks]]，**標註來源**（如「根據 2026 Q1 法說會...」、「2025 年報披露...」）...",
    "supply_chain": "**上游:**\n- ...\n**中游:**\n- ...\n**下游:**\n- ...",
    "cust": "### 主要客戶\n- ...\n\n### 主要供應商\n- ..."
  }
}
```
4. 儲存為 temp 檔並套用：
```bash
python scripts/update_enrichment.py --data /tmp/enrich.json <代號>
```

### Step 3: 品質稽核

```bash
python scripts/audit_batch.py --all -v 2>&1 | grep <代號>
```

或讀取檔案確認符合 Golden Rules（8+ wikilinks、無通用詞、無英文）。

### Step 4: 重建索引

寫入新公司的 wikilinks 後，索引必須跟著更新：

```bash
cd /home/jyw-debian/My-TW-Coverage && source venv/bin/activate && python scripts/build_wikilink_index.py
```

確認 `WIKILINKS.md` 已包含新公司。

### Step 5: 加入 task.md

如果屬於現有 batch 就加入，否則標記為獨立新增。

## 品質規則

- 每個 `[[wikilink]]` 必須是具體專有名詞
- 每檔至少 8 個 wikilinks
- 科技/材料 wikilinks 與公司同等重要：`[[CoWoS]]`、`[[HBM]]`、`[[光阻液]]`
- **禁用通用詞**：大廠、供應商、客戶、廠商、原廠、經銷商、製造商、業者、企業、公司
- 全部繁體中文
- 供應鏈要分段，不能單行
- 檔名是公司身份 ground truth，絕不能寫錯檔案