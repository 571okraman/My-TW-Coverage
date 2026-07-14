# Workpack B Patches — 收線報告

**日期：** 2026-07-14（2026-07-15 訂正）
**分支：** `workpack-b-patches`
**遠端 tip：** `b44bcfc5`（含 003 un-escape fix）

---

## 事故時序（2026-07-15 改寫，舊版敘事有事實錯誤，已覆寫）

1. **`data/signals.sqlite` 曾被誤 commit 進分支** — 這個檔案在 `.gitignore` 裡，但某次 commit 把它帶進去了（GitHub compare 頁明列 `data/signals.sqlite | added`）。這是後續所有問題的源頭。

2. **7/13 22:02 — Phase 2 互動式回填成功** — debian `data/signals.sqlite` 的 mtime 停留在 7/13 22:02、此後未被任何東西碰過。node_companies id=7/8/9 + theme_nodes id=11/12 的 sources 欄已回填完整 URL 陣列，五列均為合法 JSON（`json.loads` 全過）。這顆 DB 的 md5 = `540332b1ec92ed31cbd7322d0593dc21`，**升格為 canonical 現行真庫**。

3. **`1592c0e` 的 003 檔是 0-byte 空檔** — 這與「有沒有跑回填」是兩筆帳：7/13 是互動式執行 SQL，003 檔寫空是另一筆錯，不能互為證據。

4. **7/14 全部修復動作發生在 Mac** — filter-repo / 撈 blob / 重跑 003 均在 Mac 的 `~/tmp/tw-cov-push` 執行，debian 全程未參與。

5. **重跑 003 毀損 Mac 副本** — 003 SQL 字面量含 over-escape：`'[\\\"https://...\\\"]'`，SQLite `UPDATE` 寫入後 sources 變成 `\"` 前綴的非法 JSON。產物 md5 = `85e8e919f3ed091f48f61fbf7c92d2d9`，五列 `json.loads` 全滅。**此檔降格為 corrupted artifact**，禁止當現行庫、禁止覆寫回 debian。

6. **收線報告曾把 corrupted 當合格** — 7/14 原版報告的「管道直出 SELECT」中 `[\\\"` 正是毀損證據，但對帳只比 URL 字串在場、沒驗 `json.loads`，誤以為回填成功。

---

## 血統定稿

| md5 | 身分 | 處置 |
|---|---|---|
| `540332b1ec92ed31cbd7322d0593dc21` | 7/13 22:02 Phase 2 回填後的正確結果；合法 JSON；debian worktree ≡ pod blob ≡ Mac pre-backup | **canonical 現行真庫** |
| `85e8e919f3ed091f48f61fbf7c92d2d9` | 7/14 Mac 重跑 over-escaped 003 產物；五列 sources 非法 JSON | **corrupted artifact**；禁止當現行庫、禁止覆寫回 debian |

---

## 保全清單

**Mac：**

| 檔案 | md5 |
|---|---|
| `~/signals-canonical-540332b1.sqlite` | `540332b1ec92ed31cbd7322d0593dc21` |
| `~/signals-blob-85e8e919-CORRUPTED.sqlite` | `85e8e919f3ed091f48f61fbf7c92d2d9` |
| `~/signals-backup-20260714.sqlite` | `540332b1ec92ed31cbd7322d0593dc21`（原始預先備份） |
| `~/signals-backup-20260714-post003.sqlite` | `85e8e919f3ed091f48f61fbf7c92d2d9`（原始 corrupted 檔名） |
| `~/tmp/tw-cov-push/data/signals.sqlite` | `85e8e919f3ed091f48f61fbf7c92d2d9`（corrupted，勿動） |

**Debian：**

| 檔案 | md5 |
|---|---|
| `~/My-TW-Coverage/data/signals.sqlite` | `540332b1ec92ed31cbd7322d0593dc21` |
| `~/signals-blob-1592c0e-540332b1.sqlite` | `540332b1ec92ed31cbd7322d0593dc21`（kubectl cp） |
| `~/signals-worktree-540332b1-20260715.sqlite` | `540332b1ec92ed31cbd7322d0593dc21`（工作樹 cp） |

**Pod（晉十 hermes2）：**

| 檔案 | md5 |
|---|---|
| `/tmp/blob-1592c0e.sqlite` | `540332b1ec92ed31cbd7322d0593dc21`（git show 抽出） |

---

## 修復項

### 修復項 1：003 SQL 跳脫修正

**狀態：** ✅ 完成（`b44bcfc5`）

**問題：** 003 字面量 over-escape `'[\\\"...\\\"]'`，執行後寫入非法 JSON。

**修復：** 從 canonical `540332b1` 抽取正確值，以單一引號 SQL string 包裹合法 JSON 重新寫入 003。

**驗證：** throwaway 副本上洗五列為 `[]` → 套用修正 003 → 五列 `json.loads` 全過且與 canonical 逐字串相等。

**定位：** 修正版 003 僅為重建用 replay 腳本，**不對 canonical 重跑**。

### 修復項 2：DB 從 git 歷史清除

**狀態：** ✅ 完成（`bde06073`）

**內容：** `git filter-repo` 清除 `data/signals.sqlite` + `PHASE5_REPORT.md`；`.gitignore` 改 glob `data/*.sqlite`。

### 修復項 3：SKILL.md 對帳

**狀態：** ✅ 完成（committed `c5df140` in `openab-agents-config`）

**內容：** 刪除誤加的三節，替換為 571 裁定三節。47 lines removed, 26 lines added。

### 修復項 4：debian repo 對齊

**狀態：** ✅ 完成（2026-07-15）

**內容：** debian 從舊歷史 `1592c0e` 對齊至新 tip `b44bcfc5`。先 cp 出 canonical → `git fetch fork && git reset --hard fork/workpack-b-patches` → cp 回 → md5 仍 `540332b1`。

---

## Pod 同步記錄

| 項目 | 內容 |
|---|---|
| 上次同步 | 日期不詳（補帳），目的不詳；同步到 `1592c0e` |
| 本次同步 | 2026-07-15，`1592c0e` → `b44bcfc5`（`bde06073` 系 + 003 fix）；目的＝force-push 後對齊新歷史 |
| Step 1 md5 | `540332b1ec92ed31cbd7322d0593dc21`（≠ 原工單預期 `85e8e919…`；事後證明工單預期寫反） |
| Step 1b | integrity ok / followups 44 / id=7 sources 為 URL 陣列（非佔位文字） |
| `/tmp/blob` | `540332b1ec92ed31cbd7322d0593dc21`，仍在 |
| `data/signals.sqlite` | 殘留於磁碟（untracked，`.gitignore` 生效），pod 不需要 DB，本輪不清理 |

**新規則：pod 工作區任何 git 狀態變更都要在收線報告或交接記錄留一行帳。**

---

## pytest 環境劣化記錄（條件一）

**基線：** 37 passed 0 failed（7/10 兩次實測 + 7/13 Phase 1 同機實測）

**本批 10 failed 為環境劣化，非 pre-existing。**

### 10 個 failed 測項名單

| # | 測項 | 失敗類型 |
|---|---|---|
| 1 | `test_alias_map_schema.py::test_yaml_schema_current_map_passes` | ModuleNotFoundError: yaml |
| 2 | `test_concept_expansion.py::test_expand_concept_name` | AssertionError: None == '液冷' |
| 3 | `test_concept_expansion.py::test_expand_alias_term` | AssertionError: None == '液冷' |
| 4 | `test_concept_expansion.py::test_expand_unknown_term` | assert 0 == 1 |
| 5 | `test_concept_expansion.py::test_expand_重電` | AssertionError: None == '重電' |
| 6 | `test_concept_expansion.py::test_expand_先進封裝` | AssertionError: None == '先進封裝' |
| 7 | `test_concept_expansion.py::test_expand_儲能` | AssertionError: None == '儲能' |
| 8 | `test_concept_expansion.py::test_alias_gis_expands_to_重電` | AssertionError: None == '重電' |
| 9 | `test_concept_expansion.py::test_get_concept_aliases` | AssertionError: '水冷板' in [] |
| 10 | `test_concept_expansion.py::test_raw_alias_map_has_seed_data` | AssertionError: '液冷' in {} |

**根因：** `expand_query("液冷")` 回傳 None — alias_map.yaml seed data 缺失 + pyyaml 未安裝。與本批改動完全無關。

**結論：** 基線 37 passed 為 7/13 同機實測，failed 屬環境劣化，非本批引入。

---

## 待處理項

### theme_graph.sqlite

**狀態：** ✅ 已從 git 移除（committed `4b1d3cc0`）

`.gitignore` 已改 glob `data/*.sqlite`。

---

## 平反帳

1. **7/13 Phase 2 backfill 確實執行過** — debian mtime + canonical 內容為證。原報告「003 是空的所以沒跑回填」是誤判：互動式回填 ≠ 003 檔內容，空 003 是另一筆錯。

2. **7/14 修復敘事更正** — 「filter-repo 刪 debian 工作樹 → init --force 洗庫 → GitHub blob 救回 → 重跑 003」整段實際上發生在 **Mac**，debian 全程未動。原報告寫在 debian 上是事實錯誤。

---

## 事故教訓（不許美化）

1. **filter-repo 會同步工作樹** — 執行前必須先備份工作樹，執行後還原。不要假設它只改歷史。

2. **`init --force` 是破壞性的** — 在沒有備份的情況下跑 `init --force` 重建 DB，會把還原後的 DB 洗掉。

3. **開錯 DB 的教訓** — `data/signals.sqlite` 和 `data/theme_graph.sqlite` 是兩個不同的 DB，schema 完全不同。

4. **`data/signals.sqlite` 曾被誤 commit 是救命稻草** — 如果它從 day 1 就在 `.gitignore` 且沒進過 git，filter-repo 刪掉工作樹後就再也救不回來。

5. **JSON 欄位對帳必須驗到 parse 層級** — `json.loads` 過才算，不可只比 URL 字串在場。over-escape 的 SQL 字串在場但解析後非法，7/14 對帳只比字串就漏掉了。

6. **毀滅性操作先備份工作樹** — `reset --hard` 跨歷史邊界（特別是「曾被追蹤 DB」到「不再追蹤」）會刪工作樹檔案。順序寫死：先 `cp` 出 → 再動 git → 再 `cp` 回 → 驗 md5。

---

*報告寫入：2026-07-14；2026-07-15 訂正（DB 血統 / 事故時序 / 保全清單 / 新規則）*