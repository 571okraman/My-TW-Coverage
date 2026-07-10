# Workpack A — Schema Migration

- **日期**: 2026-07-10
- **目的**: 新增 `nodes`、`theme_nodes`、`node_companies` 三表，支援 theme_graph 空節點回填。
- **驗證**: pytest 37 passed, DDL 符合 B2 規範。

## 新增表格

### `nodes`
```
- id: INTEGER (PK, AUTOINCREMENT)
- name: TEXT (UNIQUE)
- listing_status: TEXT DEFAULT 'unlisted'
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```
  - id: INTEGER (PK)
  - name: TEXT NOT NULL
  - listing_status: TEXT DEFAULT 'unlisted'
  - created_at: TEXT DEFAULT datetime('now')
  - updated_at: TEXT DEFAULT datetime('now')

### `theme_nodes`
```
- id: INTEGER (PK, AUTOINCREMENT)
- theme_id: TEXT
- node_id: INTEGER (FK → nodes.id)
- status: TEXT
- verified_date: TEXT
- sources: TEXT (JSON array)
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```
  - id: INTEGER (PK)
  - theme_id: TEXT NOT NULL
  - node_id: INTEGER NOT NULL
  - status: TEXT NOT NULL DEFAULT 'empty_unverified'
  - verified_date: TEXT
  - sources: TEXT
  - created_at: TEXT DEFAULT datetime('now')
  - updated_at: TEXT DEFAULT datetime('now')

### `node_companies`
```
- id: INTEGER (PK, AUTOINCREMENT)
- node_id: INTEGER (FK → nodes.id)
- ticker: TEXT
- role: TEXT
- market_position: TEXT
- crowdedness: INTEGER
- repo_hit: INTEGER
- confidence: TEXT
- sources: TEXT (JSON array)
- listing_status: TEXT DEFAULT '上市'
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```
  - id: INTEGER (PK)
  - node_id: INTEGER NOT NULL
  - ticker: TEXT NOT NULL
  - role: TEXT
  - market_position: TEXT
  - crowdedness: TEXT
  - repo_hit: INTEGER DEFAULT 0
  - confidence: TEXT
  - sources: TEXT
  - created_at: TEXT DEFAULT datetime('now')
  - updated_at: TEXT DEFAULT datetime('now')
  - listing_status: TEXT DEFAULT '上市'

## 變更摘要
- 新增 `nodes` 表（含 `listing_status` 欄位）
- 新增 `theme_nodes` 表（含 `status`、`verified_date`、`sources` 三欄）
- 新增 `node_companies` 表（含 `sources`、`listing_status` 欄位）
