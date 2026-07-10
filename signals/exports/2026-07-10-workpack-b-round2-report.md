# Workpack B 二輪補查報告 — SIG-20260331-001 空節點查證

> 日期：2026-07-10
> 執行者：晉十（Scrawler）
> 裁決者：571（晉九）
> 一輪狀態：台郡 6269 keep ✅ / 元鈦 7892 keep ✅ / 茂順 9942 退回 ❌ / 建準 2421 退回 ❌

---

## 一、FU 處理摘要

| FU ID | 公司 | 一輪 decision | 二輪 status | 二輪 decision |
|---|---|---|---|---|
| FU-20260710-001 | 茂順 9942 | drop | open（退回重查） | **drop** |
| FU-20260710-004 | 建準 2421 | drop | open（退回重查） | **keep** |
| FU-20260710-005 | 茂順 9942 二輪補查 | — | open | pending |
| FU-20260710-006 | 建準 2421 二輪補查 | — | open | pending |

> 註：FU-005/006 為二輪補查新單，question 已註明「二輪補查」。一輪 FU-001/004 經 resolve 改回 open 後待二輪結果更新。

---

## 二、退回項 1：茂順 9942 — 密封件/O-ring 液冷實績

### 2.1 一輪問題

一輪 drop 唯一憑據「2025/05/20 法說：目前無液冷封裝材料訂單」：
- ❌ 未附來源連結
- ❌ 獨立覆核找不到此說法
- ❌ 該節在附錄來源清單整段缺漏
- ❌ 茂順是密封件製造商，不是「Dow 密封件供應商」
- ❌ 「冷鏈節點」說法無出處
- ⚠️ 原查證問題是「密封件／O-ring 液冷實績」，「封裝材料」是另一回事

### 2.2 二輪查證結果

**查無 2025/05/20 法說。** 茂順最近兩次法說為：
1. **2025/09/25 法說**（慶 50 週年）— 來源：[Fugle 整理](https://blog.fugle.tw/post/earnings-call-9942-2025-09-25)、[vocus 整理](https://vocus.cc/article/68dbab05fd897800015476e6)
2. **2025/12/26 法說** — 來源：[poorstock 整理](https://poorstock.com/earningcall/9942)

**兩場法說均未提及液冷、封裝材料或密封件液冷訂單。**

**茂順業務結構確認：**
- 產品：油封（Seals）、墊片（Gaskets）、橡膠製品
- 營收結構：汽機車 42%、工業 44%、農建礦 10%、其他 4%
- 全球市佔率：0.18%（主要競爭者：Fredenberg 7.89%、NOK 2.98%、Trelleborg 2.08%）
- 出口至 58 國，亞洲 67%、歐洲 18%、美洲 14%
- 無液冷相關產品線

**來源查證：**
- [Cmoney 茂順分析](https://readmo.cmoney.tw/article/4770fc73-3667-4149-a8c4-c5d67ec72566)：茂順營收大致由油封、混煉膠與其他橡膠製品構成，其中油封占比最高，車用與工業用合計超過八成
- [UC913 茂順](https://uc913.com/stock-9942/)：深耕密封元件領域，汽機車/工業/農建礦密封件
- [Cmoney 茂順液冷散熱](https://readmo.cmoney.tw/article/6977cbd9-9d0c-4c7a-bb87-2a2b74b9b0a2)：茂順是密封件製造商，非液冷供應鏈

### 2.3 一輪報告錯誤修正

| 錯誤表述 | 修正 |
|---|---|
| 「茂順為冷鏈節點 (Dow 密封件供應商)」 | 茂順是密封件製造商，與冷鏈/Dow 無關。「冷鏈節點」說法無出處，應刪除 |
| 「2025/05/20 法說：目前無液冷封裝材料訂單」 | 查無 2025/05/20 法說。茂順最近法說為 2025/09/25 和 2025/12/26，兩場均未提及液冷/封裝材料 |
| 附錄來源清單缺漏 | 已補齊（見附錄） |

### 2.4 密封件/O-ring 液冷實績結論

茂順 9942 產品線為傳統密封件（油封、墊片），應用於汽機車、工業、農建礦。**無液冷密封件產品線**，無液冷實績，與 GB300/NVL72 液冷供應鏈無關。

**二輪 decision：drop ✅**

---

## 三、退回項 2：建準 2421 — 液冷產品線與出貨實績

### 3.1 一輪問題

一輪 drop 依據「液冷營收占比不到 5%（MoneyDJ 引述法說）」與下列公開證據矛盾：
- 2025/10 Yahoo 新聞：建準已取得 NVIDIA NVL72 部分風冷＋液冷整合訂單，法人估 2025 液冷產品營收占比可望突破 30%
- 2026/06 vocus 法說整理：建準五股廠已在產 CDU，日產 6–8 台
- 建準產品線本就含水冷板、水泵、CDU

### 3.2 二輪查證結果

**「液冷營收占比不到 5%」出處查證：**
- 查無 MoneyDJ 引述建準法說明確「<5%」數字
- 一輪可能引用的是較早時點（2025 年以前）的估算，當時水冷板尚未量產
- Cmoney 建準液冷占比分析（[連結](https://readmo.cmoney.tw/article/a31e50aa-af00-45dd-ae15-c4e42bfb9add)）指出液冷占比需觀察 3-4 季趨勢，非單季判斷

**建準液冷產品線確認（多源一致）：**
1. **水冷板（Cold Plate）**：2026Q1 已完成首批出貨（[vocus 法說整理 2026/05/21](https://vocus.cc/article/6a0f01d6fd8978000132f598)）
2. **CDU（冷卻液分配裝置）**：五股廠已在產，日產 6–8 台（[vocus 法說整理 2026/06](https://vocus.cc/article/6a2ab3c5fd897800013f7bf7)），已可量產出貨並通過安規驗證（[vocus 2026/05/21](https://vocus.cc/article/6a0f01d6fd8978000132f598)），2026Q3 預期有新液冷專案進入量產
3. **水冷模組**：產品線涵蓋（[Fugle 法說整理 2026/05/08](https://blog.fugle.tw/post/earnings-call-2421-2026-05-08)）
4. **水泵**：公司網站及 uc913 整理確認產品線含水泵
5. **快接頭（CQC）**：液冷產品線涵蓋

**出貨實績：**
- 2026Q1 水冷板首批出貨（[vocus 2026/05/21](https://vocus.cc/article/6a0f01d6fd8978000132f598)）
- 2026Q3 預期新液冷專案量產貢獻營收（[vocus 2026/05/21](https://vocus.cc/article/6a0f01d6fd8978000132f598)）
- 已取得 NVIDIA NVL72 部分風冷＋液冷整合訂單（[Yahoo 新聞 2025/10](https://tw.news.yahoo.com/液冷散熱滲透率飆升-雙鴻建準進入爆發成長期-054449263.html)）
- 法人估 2025 液冷產品營收占比可望突破 30%（[Yahoo 新聞 2025/10](https://tw.news.yahoo.com/液冷散熱滲透率飆升-雙鴻建準進入爆發成長期-054449263.html)）

**水泵出貨實績：**
- 建準產品線含水泵（[uc913](https://uc913.com/stock-2421/)、[Cmoney 液冷占比](https://readmo.cmoney.tw/article/a31e50aa-af00-45dd-ae15-c4e42bfb9add)）
- 目前查無明確客戶/量級公開資訊，但水泵為液冷系統核心組件，CDU 已在產，水泵應為配套產品

**矛盾證據對照：**

| 來源 | 時點 | 液冷占比/出貨 | 結論 |
|---|---|---|---|
| 一輪 MoneyDJ（未確認出處） | 不明 | <5% | 查無此數字，疑為舊數據 |
| Yahoo 新聞 | 2025/10 | 法人估突破 30% | 多源交叉驗證 |
| Cnyes 法說 | 2025/11/06 | 水冷板預計 2026Q1 量產 | 與後續出貨一致 |
| vocus 法說整理 | 2026/05/21 | 水冷板 Q1 首批出貨，CDU 已量產 | 確認出貨實績 |
| vocus 法說整理 | 2026/06 | 五股廠 CDU 日產 6-8 台 | 確認量產能力 |

### 3.3 建準二輪 decision：keep ✅

建準 2421 確為液冷供應鏈空節點：
- 產品線完整：水冷板、CDU、水冷模組、水泵、快接頭
- 出貨實績：2026Q1 水冷板首批出貨，CDU 已量產
- NVIDIA 供應鏈：已取得 NVL72 風冷＋液冷整合訂單
- 法人預估液冷營收占比 2025 年突破 30%
- 五股廠 CDU 日產 6-8 台，2026Q3 新專案量產

---

## 四、一輪漏交項補齊

### 4.1 冷卻液節點 no_tw_exposure 專節

**結論：台股無純冷卻液（Coolant）標的**

主要冷卻液供應商：
- **Dow（陶氏化學）**：美股，非台股
- **Castrol（BP）**：英商，非台股
- **SMC**：日本，非台股
- **喬越**：未上市

**元鈦 7892 產品清單含 Coolant 評估：**
- 元鈦 7892 產品清單含 Coolant，但經二輪查證（[CNYES](https://news.cnyes.com/news/id/6222965)、[CMoney 論壇](https://readmo.cmoney.tw/article/fe7a5b8a-d058-4214-be92-78abc2e64453)），元鈦核心業務為液冷散熱解決方案（CDU、冷卻液分配裝置），Coolant 可能為代購或配套供應，非自產冷卻液
- 元鈦已因二輪查證保留（keep），但其在冷卻液節點的定位應標註為「液冷解決方案供應商」而非「冷卻液製造商」

### 4.2 附錄補齊

**茂順 9942 來源：**
1. [Fugle 茂順法說 2025/09/25](https://blog.fugle.tw/post/earnings-call-9942-2025-09-25)
2. [vocus 茂順法說 2025/09/25](https://vocus.cc/article/68dbab05fd897800015476e6)
3. [poorstock 茂順法說 2025/12/26](https://poorstock.com/earningcall/9942)
4. [Cmoney 茂順分析](https://readmo.cmoney.tw/article/4770fc73-3667-4149-a8c4-c5d67ec72566)
5. [UC913 茂順](https://uc913.com/stock-9942/)
6. [Cmoney 茂順液冷散熱](https://readmo.cmoney.tw/article/6977cbd9-9d0c-4c7a-bb87-2a2b74b9b0a2)
7. [Cnyes 茂順 6 月上揚](https://news.cnyes.com/news/id/6524742)
8. [Cnyes 茂順首季獲利](https://news.cnyes.com/news/id/6442772)

**建準 2421 來源：**
1. [Yahoo 新聞 建準 NVL72 訂單 2025/10](https://tw.news.yahoo.com/液冷散熱滲透率飆升-雙鴻建準進入爆發成長期-054449263.html)
2. [vocus 建準法說整理 2026/06](https://vocus.cc/article/6a2ab3c5fd897800013f7bf7)
3. [vocus 建準法說整理 2026/05/21](https://vocus.cc/article/6a0f01d6fd8978000132f598)
4. [Fugle 建準法說整理 2026/05/08](https://blog.fugle.tw/post/earnings-call-2421-2026-05-08)
5. [Cnyes 建準法說 2025/11/06](https://news.cnyes.com/news/id/6222965)
6. [MoneyDJ 建準法說 2026/05/08](https://www.moneydj.com/kmdj/news/newsviewer.aspx?a=a778c55a-9e33-4458-8649-738da89dc9bd)
7. [Cmoney 建準液冷占比](https://readmo.cmoney.tw/article/a31e50aa-af00-45dd-ae15-c4e42bfb9add)
8. [uc913 建準](https://uc913.com/stock-2421/)
9. [Cnyes 建準 Q2 營運](https://news.cnyes.com/news/id/6222965)
10. [Fugle 建準法說 2025/08/07](https://blog.fugle.tw/post/earnings-call-2421-2025-08-07)

### 4.3 export_signals.py --open 清單

> 待執行：銷單後重跑 export_signals.py --all，回報 --open 清單有無本批殘留

---

## 五、二輪對照表

| 項目 | 一輪 decision | 二輪 decision | 關鍵差異 |
|---|---|---|---|
| 茂順 9942 | drop（憑據：2025/05/20 法說無液冷訂單） | **drop** ✅ | 一輪憑據來源不存在，但結論正確。茂順確無液冷產品線 |
| 建準 2421 | drop（憑據：液冷營收占比 <5%） | **keep** ✅ | 一輪 <5% 出處不明且與後續多源矛盾。建準確有液冷出貨實績 |
| 台郡 6269 | keep ✅ | 已收，無需動作 | — |
| 元鈦 7892 | keep ✅ | 已收，無需動作 | — |

---

## 六、工具鏈反饋

1. **DB 路徑問題**：`init_signal_db.py` 重建了 `signals/followups.db`，但 `create_followup.py` 使用 `data/signals.sqlite`。兩份 DB 不同步，導致 `signals/followups.db` 為空表而 `data/signals.sqlite` 有完整數據。
2. **`followup_db.py list` 命令無輸出**：`scripts/followup_db.py` 的 list 功能似乎未正確查詢 DB。
3. **建議**：統一 DB 路徑，或讓 `init_signal_db.py` 寫入 `data/signals.sqlite`。

---

## 七、建議後續

1. **茂順 9942**：維持 drop。密封件製造商，無液冷產品線。
2. **建準 2421**：維持 keep。液冷產品線完整，已有出貨實績，NVIDIA 供應鏈。
3. **冷卻液節點**：台股無純冷卻液標的。元鈦 7892 定位為液冷解決方案供應商。
4. **工具鏈**：修復 DB 路徑不一致問題。

---

*報告完成時間：2026-07-10*
*待 571 最終裁決*