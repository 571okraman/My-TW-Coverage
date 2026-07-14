-- migration 003: backfill sources for Workpack B targets
-- node_companies id=7 (6269 台郡), id=8 (7892 元鈦), id=9 (2421 建準)
-- theme_nodes id=11 (冷卻液), id=12 (密封件)
-- NOTE: values extracted from canonical 540332b1; single-quoted SQL string holds valid JSON.

-- 台郡 6269 (node_companies id=7)
UPDATE node_companies
SET sources = '["https://news.cnyes.com/news/id/6135301", "https://uanalyze.com.tw/articles/1223251496", "https://www.sinotrade.com.tw/richclub/news/6a1dc8a3de5d6e55041a346a", "https://readmo.cmoney.tw/article/c2ae6cc1-f204-4fd2-9e2a-5d4facc57ddb", "https://blog.fugle.tw/post/flexium-analysis"]'
WHERE id = 7;

-- 元鈦 7892 (node_companies id=8)
UPDATE node_companies
SET sources = '["https://news.cnyes.com/news/id/6311694", "https://www.cmoney.tw/forum/article/178806620"]'
WHERE id = 8;

-- 建準 2421 (node_companies id=9)
UPDATE node_companies
SET sources = '["https://tw.news.yahoo.com/液冷散熱滲透率飆升-雙鴻建準進入爆發成長期-054449263.html", "https://vocus.cc/article/6a2ab3c5fd897800013f7bf7", "https://vocus.cc/article/6a0f01d6fd8978000132f598", "https://blog.fugle.tw/post/earnings-call-2421-2026-05-08", "https://news.cnyes.com/news/id/6222965", "https://www.moneydj.com/kmdj/news/newsviewer.aspx?a=a778c55a-9e33-4458-8649-738da89dc9bd", "https://readmo.cmoney.tw/article/a31e50aa-af00-45dd-ae15-c4e42bfb9add", "https://uc913.com/stock-2421/", "https://blog.fugle.tw/post/earnings-call-2421-2025-08-07"]'
WHERE id = 9;

-- 冷卻液 (theme_nodes id=11)
UPDATE theme_nodes
SET sources = '["signals/exports/2026-07-10-workpack-b-round2-report.md#41-冷卻液節點-no_tw_exposure-專節"]'
WHERE id = 11;

-- 密封件 (theme_nodes id=12)
UPDATE theme_nodes
SET sources = '["https://blog.fugle.tw/post/earnings-call-9942-2025-09-25", "https://vocus.cc/article/68dbab05fd897800015476e6", "https://readmo.cmoney.tw/article/4770fc73-3667-4149-a8c4-c5d67ec72566", "https://uc913.com/stock-9942/ (fetch-blocked 403)", "https://readmo.cmoney.tw/article/6977cbd9-9d0c-4c7a-bb87-2a2b74b9b0a2", "https://news.cnyes.com/news/id/6524742", "https://news.cnyes.com/news/id/6442772", "signals/exports/2026-07-10-workpack-b-round2-report.md#41-密封件節點-no_tw_exposure-專節"]'
WHERE id = 12;
