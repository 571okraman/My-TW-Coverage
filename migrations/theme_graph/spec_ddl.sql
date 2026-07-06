-- themes：投資主題（v0 theme/subtheme 攤平，card 一張 = 一列）
CREATE TABLE themes (
  id            TEXT PRIMARY KEY,   -- THEME-liquid-cooling
  name          TEXT NOT NULL,      -- AI Server 液冷
  demand_shock  TEXT,
  time_horizon  TEXT,
  market_status TEXT CHECK(market_status IN
    ('early','confirmed','crowded','exhausted','invalidated')),
  card_url      TEXT,               -- 回連 Notion Expansion Card
  created_at    TEXT, updated_at TEXT
);

-- nodes：供應鏈節點（跨 theme 共用）
CREATE TABLE nodes (
  id         TEXT PRIMARY KEY,      -- NODE-cold-plate
  name       TEXT NOT NULL,         -- 水冷板
  node_type  TEXT,                  -- material/equipment/component/module/service
  created_at TEXT
);

-- theme_nodes：theme ↔ node 邊（theme 語境屬性放這）
CREATE TABLE theme_nodes (
  theme_id        TEXT REFERENCES themes(id),
  node_id         TEXT REFERENCES nodes(id),
  demand_impact   TEXT,             -- 用量增加/滲透率/規格升級/耗材化/國產替代…
  bottleneck_risk TEXT,             -- low/medium/high/unknown
  asp_trend       TEXT,             -- 上升/持平/下滑/unknown（card §4.4）
  taiwan_exposure TEXT,
  confidence      TEXT,
  PRIMARY KEY (theme_id, node_id)
);

-- node_companies：node ↔ 台股公司邊（card §4.5 一列 = 這裡一列）
CREATE TABLE node_companies (
  node_id         TEXT REFERENCES nodes(id),
  ticker          TEXT NOT NULL,    -- 對齊 Pilot_Reports 代號
  company_name    TEXT,
  role            TEXT,
  market_position TEXT,             -- 龍頭/二階/三階
  crowdedness     TEXT,             -- 公司級 low/medium/high
  repo_hit        TEXT,             -- 命中詞；NULL = 未命中
  revenue_exposure TEXT,
  confidence      TEXT,
  PRIMARY KEY (node_id, ticker)
);

-- evidence：所有邊/節點的 provenance（護欄：無 source 不得入庫）
CREATE TABLE evidence (
  id           INTEGER PRIMARY KEY,
  entity_type  TEXT,                -- theme/theme_node/node_company
  entity_key   TEXT,                -- 複合 key 序列化
  source_type  TEXT,                -- repo_wikilink/mops/ir/news/t09_signal/llm_draft
  source_ref   TEXT,                -- URL / signal_id / 命中詞
  verify_score INTEGER,             -- 對齊 T09；<3 = ⚠️ 待驗證
  note         TEXT,
  observed_at  TEXT
);

-- node_aliases：node ↔ alias_map 概念詞（discover 自動掃 node；不另立收詞真值）
CREATE TABLE node_aliases (
  node_id TEXT REFERENCES nodes(id),
  concept TEXT NOT NULL,            -- alias_map.yaml 概念詞 key
  PRIMARY KEY (node_id, concept)
);
