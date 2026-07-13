# Pod Drift Investigation Report — PS-20260714

**調查日期：** 2026-07-14
**調查者：** 晉三
**調查對象：** 晉十 pod 的 My-TW-Coverage repo 版本漂移

---

## 調查結果

### 1. Repo 位置

晉十 pod 的 repo 實際位置為 `/home/jyw-debian/My-TW-Coverage`（非 `/workspace/My-TW-Coverage`）。

### 2. Git Status

```
位於分支 workpack-b-patches
您的分支領先 'fork/master' 共 6 個提交。
沒有要提交的檔案，工作區為乾淨狀態
```

### 3. HEAD Commit

`1592c0e fix: remove duplicate content from PHASE5_REPORT.md`

### 4. 野檔檢查

- `followups.db`：**不存在**
- `followup_db.py`：**不存在**

**結論：無野檔。**

### 5. 與 origin/master 差異

branch `workpack-b-patches` 領先 `fork/master` 6 commits，差異包含：
- `PHASE5_REPORT.md`（應已移除）
- `data/signals.sqlite`（應已從歷史清除）
- `migrations/002_add_followups_sources.sql`（已對帳合格）
- `migrations/003_backfill_sources.sql`（本次修復填實）
- `scripts/create_followup.py`（已對帳合格）
- `scripts/init_signal_db.py`（已對帳合格）
- `scripts/report_scaffold.py`（已對帳合格）
- `scripts/resolve_followup.py`（已對帳合格）
- `scripts/seed_theme_graph.py`（已對帳合格）
- `signals/exports/2026-07-10-schema-migration.md`（已對帳合格）

### 6. 建議動作

Pod 應同步到 `workpack-b-patches` branch 最新 commit，而非 `fork/master`。

---

*報告完成時間：2026-07-14*