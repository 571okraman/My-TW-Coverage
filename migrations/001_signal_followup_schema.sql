-- Migration: 001_signal_followup_schema
-- Description: Create signal monitoring and follow-up tracking tables
-- Created: 2026-07-01

-- 3.1 signals
CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT,
  trigger_type TEXT NOT NULL,
  status TEXT NOT NULL,
  priority TEXT,
  event_date TEXT,
  discovered_at TEXT NOT NULL,
  expires_at TEXT,
  score_total INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
-- status: radar / follow / thesis_candidate / rejected / expired / archived
-- trigger_type: policy_regulation / tech_shift / supply_demand_imbalance / supply_chain_reshuffling / anchor_customer_roadmap / financial_inflection / market_behavior_anomaly

-- 3.2 signal_sources
CREATE TABLE IF NOT EXISTS signal_sources (
  id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL,
  url TEXT,
  title TEXT,
  publisher TEXT,
  source_type TEXT,
  trust_level TEXT,
  published_at TEXT,
  extracted_summary TEXT,
  FOREIGN KEY(signal_id) REFERENCES signals(id)
);
-- source_type: government / company_disclosure / exchange / news / report / patent / paper / social / unknown
-- trust_level: high / medium / low / unverified

-- 3.3 signal_topics
CREATE TABLE IF NOT EXISTS signal_topics (
  signal_id TEXT NOT NULL,
  topic TEXT NOT NULL,
  theme_path TEXT,
  confidence TEXT,
  PRIMARY KEY(signal_id, topic)
);

-- 3.4 signal_tickers
CREATE TABLE IF NOT EXISTS signal_tickers (
  signal_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  company_name TEXT,
  report_path TEXT,
  exposure_reason TEXT,
  confidence TEXT,
  PRIMARY KEY(signal_id, ticker)
);

-- 3.5 followups
CREATE TABLE IF NOT EXISTS followups (
  id TEXT PRIMARY KEY,
  signal_id TEXT,
  title TEXT NOT NULL,
  question TEXT NOT NULL,
  followup_type TEXT NOT NULL,
  status TEXT NOT NULL,
  priority TEXT,
  due_date TEXT,
  result_summary TEXT,
  decision TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  resolved_at TEXT,
  FOREIGN KEY(signal_id) REFERENCES signals(id)
);
-- followup_type: fact_check / mapping_check / exposure_check / financial_check / market_check / repo_update_check
-- status: open / in_progress / resolved / promoted / rejected / expired

-- Indexes
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_trigger_type ON signals(trigger_type);
CREATE INDEX IF NOT EXISTS idx_signal_sources_signal_id ON signal_sources(signal_id);
CREATE INDEX IF NOT EXISTS idx_followups_signal_id ON followups(signal_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON followups(status);
