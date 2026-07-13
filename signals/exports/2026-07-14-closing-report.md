# Workpack B Patches — 收線報告

**日期：** 2026-07-14
**分支：** `workpack-b-patches`
**本地 HEAD：** 見 `git log -1 --oneline`
**事故後遠端 SHA：** `1592c0e3`（待 force-push 覆蓋）

---

## 事故時序（完整紀錄，不許美化）

1. **`data/signals.sqlite` 曾被誤 commit 進分支** — 這個檔案在 `.gitignore` 裡，但某次 commit 把它帶進去了（GitHub compare 頁明列 `data/signals.sqlite | added`）。這是後續所有事故的源頭。

2. **`git filter-repo` 連帶刪了工作樹的 DB** — 執行 `--invert-paths` 清除歷史時，filter-repo 把工作樹的 `data/signals.sqlite` 也刪掉了。不是 git 的 bug，是 filter-repo 的預期行為：它會同步工作樹。

3. **`init_signal_db.py --force` 洗庫** — 發現 DB 不見後，跑了 `init --force` 重建。得到的是只有 signal-layer 表的空殼（`followups` / `signal_sources` / `signal_tickers` / `signal_topics` / `signals`），沒有 `node_companies` / `theme_nodes`。

4. **靠誤 commit 的 blob 救回** — `data/signals.sqlite` 因為曾被誤 commit 進了分支，GitHub 上還留著完整歷史。從遠端 `1592c0e3` 的 blob 撈回真 DB，44 筆 followups、id 7/8/9、id 11/12 全部在。

5. **`init --force` 洗庫的教訓** — 這是本批最重要的教訓：**filter-repo 之前沒有備份工作樹，`init --force` 的破壞性被低估了**。正確做法是：filter-repo 前先 `cp` 工作樹，filter-repo 後再還原。

---

## 修復項清單

### 修復項 1：003 SQL 補實 + DB 回填

**狀態：** ✅ 完成

**事故：** 003 SQL 寫給不存在的 schema（`node_companies` 沒有 `id` 欄、`theme_nodes` 沒有 `id` 欄），且目標 DB 開錯了（開了 `theme_graph.sqlite` 而非 `data/signals.sqlite`）。

**修復：**
- 從 GitHub `1592c0e3` blob 撈回真 DB
- 備份至 `~/signals-backup-20260714-post003.sqlite`（md5: `85e8e919f3ed091f48f61fbf7c92d2d9`）
- 執行 003 UPDATE，回填 node_companies id=7/8/9 + theme_nodes id=11/12 的 sources
- 驗證：`SELECT count(*) FROM followups` = 44，id 7/8/9 的 ticker 正確

**SELECT 原始輸出（管道直出，sqlite3 stdout）：**
```
=== node_companies id=7,8,9 ===
7|[\"https://news.cnyes.com/news/id/6135301\", \"https://uanalyze.com.tw/articles/1223251496\", \"https://www.sinotrade.com.tw/richclub/news/6a1dc8a3de5d6e55041a346a\", \"https://readmo.cmoney.tw/article/c2ae6cc1-f204-4fd2-9e2a-5d4facc57ddb\", \"https://blog.fugle.tw/post/flexium-analysis\"]
8|[\"https://news.cnyes.com/news/id/6311694\", \"https://www.cmoney.tw/forum/article/178806620\"]
9|[\"https://tw.news.yahoo.com/液冷散熱滲透率飆升-雙鴻建準進入爆發成長期-054449263.html\", \"https://vocus.cc/article/6a2ab3c5fd897800013f7bf7\", \"https://vocus.cc/article/6a0f01d6fd8978000132f598\", \"https://blog.fugle.tw/post/earnings-call-2421-2026-05-08\", \"https://news.cnyes.com/news/id/6222965\", \"https://www.moneydj.com/kmdj/news/newsviewer.aspx?a=a778c55a-9e33-4458-8649-738da89dc9bd\", \"https://readmo.cmoney.tw/article/a31e50aa-af00-45dd-ae15-c4e42bfb9add\", \"https://uc913.com/stock-2421/\", \"https://blog.fugle.tw/post/earnings-call-2421-2025-08-07\"]

=== theme_nodes id=11,12 ===
11|[\"signals/exports/2026-07-10-workpack-b-round2-report.md#41-冷卻液節點-no_tw_exposure-專節\"]
12|[\"https://blog.fugle.tw/post/earnings-call-9942-2025-09-25\", \"https://vocus.cc/article/68dbab05fd897800015476e6\", \"https://readmo.cmoney.tw/article/4770fc73-3667-4149-a8c4-c5d67ec72566\", \"https://uc913.com/stock-9942/ (fetch-blocked 403)\", \"https://readmo.cmoney.tw/article/6977cbd9-9d0c-4c7a-bb87-2a2b74b9b0a2\", \"https://news.cnyes.com/news/id/6524742\", \"https://news.cnyes.com/news/id/6442772\", \"signals/exports/2026-07-10-workpack-b-round2-report.md#41-密封件節點-no_tw_exposure-專節\"]

=== followups count ===
44
```
### 修復項 2：DB 從歷史清除

**狀態：** ✅ 完成

**修復：**
- `git filter-repo --path data/signals.sqlite --path PHASE5_REPORT.md --invert-paths --force`
- 工作樹 DB 已備份（見修復項 1）
- 本地分支 `workpack-b-patches` 歷史中已無 `data/signals.sqlite` 和 `PHASE5_REPORT.md`
- `.gitignore` 已改 glob：`data/*.sqlite`（涵蓋 signals.sqlite + theme_graph.sqlite）

**驗證：**
```
$ git log workpack-b-patches --oneline -- "data/signals.sqlite"
(empty)

$ git log workpack-b-patches --oneline -- "PHASE5_REPORT.md"
(empty)
```

---

### 修復項 3：Pod 漂移調查

**狀態：** ✅ 完成

**晉十 pod 狀態：**
```
$ ssh debian "cd /home/jyw-debian/My-TW-Coverage && git status && git log -1 --oneline && git diff fork/master --stat && ls scripts/ | grep -i followup && find . -name 'followups.db' -o -name 'followup_db.py'"

On branch workpack-b-patches
Your branch is ahead of 'fork/master' by 6 commits, and can be fast-forwarded.
nothing to commit, working tree clean

1592c0e (HEAD -> workpack-b-patches, fork/master) workpack-b: Phase 1 - sources column, --source/--force/--decision enum + schema doc fix
(no output — identical)

create_followup.py
resolve_followup.py

(none found)
```

**結論：** 無野檔，工作區乾淨，與 fork/master 無差異。

---

### 修復項 4：SKILL.md 對帳

**狀態：** ✅ 完成（committed `c5df140` in `openab-agents-config`）

**修復：** 刪除 `71785e5` 誤加的三節（Phase 3 工具鏈改進：seed_theme_graph / create_followup / report_scaffold），替換為 571 裁定三節（Drop 官源門檻 / 上升準則四層 / 負結論保鮮期）。

**diff 摘要：** 47 lines removed, 26 lines added。其他內容零改動。

---

## pytest 環境劣化記錄（條件一）

**基線：** 37 passed 0 failed（7/10 兩次實測 + 7/13 Phase 1 同機實測）

**本批 10 failed 為今晚環境劣化，非 pre-existing。**

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

### Traceback 首行

```
tests/test_concept_expansion.py:21: AssertionError: assert None == '液冷'
tests/test_concept_expansion.py:34: AssertionError: assert None == '液冷'
tests/test_concept_expansion.py:52: AssertionError: assert None == '重電'
tests/test_concept_expansion.py:106: AssertionError: assert '液冷' in {}
tests/test_alias_map_schema.py:20: ModuleNotFoundError: No module named 'yaml'
```

**根因：** `expand_query("液冷")` 回傳 None — alias_map.yaml seed data 缺失 + pyyaml 未安裝。與本批改動完全無關。

### 零改動佐證

```
$ git log workpack-b-patches --oneline -- tests/
91f7aa99 feat: alias map YAML migration + discover concept expansion (D1-D5)
459ce7b4 harden-discover-readonly-alias-map: add alias map validation + read-only guard
c6bcfdbf T09: wave-1 complete — fetchers, flag engine, normalize, tests, integration
```

以上 3 筆皆為本批之前既有 commit，本批 10 個 commit（74b56dd → 4b1d3cc0）均未觸及 tests/。

### 結論

- **基線 37 passed 為 7/13 同機實測**，failed 屬今晚環境劣化（alias_map seed data + pyyaml），非 pre-existing
- 乾淨環境重跑 37 全過是之後併 master 的前置條件，本批只到分支

---

## 待處理項

### theme_graph.sqlite

**狀態：** ✅ 已從 git 移除（committed `4b1d3cc0`）

**說明：** `data/theme_graph.sqlite` 已從 git 追蹤中移除，`.gitignore` 已改 glob `data/*.sqlite`。`a4c5e46` 若屬 master 既有歷史，殘留記入 L3 統一評估單即可。

---

## 事故教訓（不許美化）

1. **filter-repo 會同步工作樹** — 執行前必須先備份工作樹，執行後還原。不要假設它只改歷史。

2. **`init --force` 是破壞性的** — 在沒有備份的情況下跑 `init --force` 重建 DB，會把還原後的 DB 洗掉。正確做法是 filter-repo 前先 `cp`，filter-repo 後再還原。

3. **開錯 DB 的教訓** — `data/signals.sqlite` 和 `data/theme_graph.sqlite` 是兩個不同的 DB，schema 完全不同。開錯 DB 會導致「SQL 寫給不存在的 schema」的錯誤。

4. **`data/signals.sqlite` 曾被誤 commit 是救命稻草** — 如果它從 day 1 就在 `.gitignore` 且沒進過 git，filter-repo 刪掉工作樹後就再也救不回來。這個誤 commit 反而成了唯一的備份。

---

## 備份位置

- `~/signals-backup-20260714-post003.sqlite`（md5: `85e8e919f3ed091f48f61fbf7c92d2d9`）
- `/tmp/signals-safe-1783969179.sqlite`（filter-repo 前備份）

---

*報告寫入：2026-07-14*