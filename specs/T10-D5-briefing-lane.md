# T10-D5: 法說簡報抽取 lane

**依據**：571 裁定（2026-07-08）——事件驅動＋回溯當期。
**掛**：T10 spec D5。

## 定位

Signal 命中公司 → 自動回溯最近一期法說簡報 → 抽取文字層 → 產出 markdown → 晉十判讀。

## 管線

1. **觸發**：signal 命中公司（ticker）→ 檢查  是否已有簡報
2. **查詢**：TDCC IR Platform / MOPS 電子書 → 取得最近一期法說簡報 PDF URL
3. **下載**：
4. **抽取分流**：
   - 文字層 PDF → （零成本，預設路徑）
   - 圖表密集/掃描件 → Unlimited-OCR（GPU 部署歸晉三裁，未裁前此步人工或 pymupdf 湊合）
5. **產出**：（committed，對齊 .gitignore 慣例）
6. **判讀**：晉十 → 回寫對應 followup； 必含「公布時點→發酵時長」一句

## 紅線

- 抽取產物只進 ，不寫 enrichment / Pilot_Reports/（唯讀紅線不變）
- 不重建 themes / network / WIKILINKS（financial-only 同理）
- 不 commit （已 gitignore）

## 事件驅動＋回溯當期

- 不做全量掃描
- signal 命中公司才扒
- 回頭扒「最近一期」法說
- 判讀除內容外必記**公布時點**，供 priced_in 校準（市場發酵時長）
- FU-005 為判例：事件 2024-11 已公布、研報 2026-03 才寫 → priced_in 上修

## 實現狀態

- ：stub（TDCC 需 JS 渲染，MOPS 需解析頁面結構）
- pymupdf：已安裝，文字層抽取可用
- Unlimited-OCR：GPU 部署歸晉三裁，未裁前此步人工或 pymupdf 湊合

## 驗收條件

1.  執行無 error
2. 手動下載 PDF 到  後， 可成功產出 markdown
3. 產出 markdown 格式一致（## Page N → 文字內容）
