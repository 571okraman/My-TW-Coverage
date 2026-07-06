#!/usr/bin/env python3
"""Seed theme_graph.sqlite from handoff v3.1 spec (附錄 A/B/C)."""

import sqlite3
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "theme_graph.sqlite"
ALIAS_PATH = REPO_ROOT / "data" / "alias_map.yaml"

THEMES = [
    ("THEME-liquid-cooling", "AI Server 液冷",
     "NVIDIA GB300/Rubin 平台單晶片 TDP 突破 1,000W，液冷從選配轉標配",
     "2026 放量年（結構性）", "crowded",
     "Seed 1 Dry-run — AI Server 液冷 Supply Chain Expansion Card v0"),
    ("THEME-cowos-adv-pkg", "CoWoS / 先進封裝",
     "2026 全球 CoWoS 需求上看 100–131 萬片；TSMC+OSAT 產能全開仍有 10–20% 缺口",
     "2026–2027（2027 起缺口收斂/過剩風險）", "confirmed",
     "Seed 2 Dry-run — CoWoS / 先進封裝 Supply Chain Expansion Card v0.1"),
    ("THEME-heavy-electric", "電力基建 / 重電",
     "台電 10 年 5,645 億強韌電網執行高峰 + 半導體/AI 新增用電 5GW + 美國變壓器缺口至 2030",
     "2026–2030", "confirmed",
     "Seed 3 Dry-run — 重電 / 電網 Supply Chain Expansion Card v0.1"),
]

NODES = [
    ("NODE-cold-plate", "水冷板 Cold Plate", "component",
     "用量增加+規格升級（VR CPX 單機 5 片）", "medium", None, "strong", "medium"),
    ("NODE-cdu", "CDU（機櫃級）", "equipment",
     "高單價設備放量", "medium", None, "strong", "medium"),
    ("NODE-manifold", "分歧管 Manifold/CDM", "component",
     "用量增加", "medium", None, "strong", "medium"),
    ("NODE-qd", "快接頭 QD/UQD", "component",
     "用量倍增+標準化", "high", None, "medium", "medium"),
    ("NODE-vapor-chamber", "均熱片 / vapor chamber", "component",
     "規格升級", "medium", None, "strong", "medium"),
    ("NODE-plate-heat-exchanger", "板式熱交換器", "component",
     "用量增加", "medium", None, "strong", "medium"),
    ("NODE-fan-wall", "風扇牆 / 混合氣流", "equipment",
     "滲透率提升", "low", None, "strong", "medium"),
    ("NODE-liquid-cabinet", "液冷機櫃 / 統包工程", "module",
     "需求擴散", "medium", None, "strong", "medium"),
    ("NODE-cowos-frontend", "CoWoS 前段（CoW/interposer）", "equipment",
     "用量增加", "high", "n/a", "weak", "high"),
    ("NODE-osat", "OSAT 後段外包（WoS/CoWoS-like）", "service",
     "用量增加+外包比重升", "medium", "持平", "strong", "medium"),
    ("NODE-abf", "ABF 載板", "material",
     "規格升級+面積消耗放大", "high", "上升", "strong", "high"),
    ("NODE-packaging-eq", "封裝設備（濕製程/檢測/貼合）", "equipment",
     "產能擴張 capex", "medium", "持平", "strong", "medium"),
    ("NODE-test-interface", "測試介面（探針卡/測試座/burn-in）", "equipment",
     "規格升級（HBM4、大尺寸 2.5D）", "medium", "上升", "strong", "medium"),
    ("NODE-specialty-chem", "特用化學材料（清洗液/特氣/光阻配套）", "material",
     "用量增加+國產替代", "medium", "上升", "medium", "medium"),
    ("NODE-carrier", "載具/耗材（wafer carrier、鑽石碟）", "material",
     "耗材化", "low-medium", "持平", "medium", "low"),
    ("NODE-cleanroom", "無塵室/廠務工程", "service",
     "capex 一次性標案", "low", "n/a", "medium", "low"),
    ("NODE-asic-design", "ASIC 設計服務", "service",
     "需求端投片放大", "low", "n/a", "strong", "medium"),
    ("NODE-transformer", "大型電力變壓器", "equipment",
     "規格升級+出口缺口", "high", "上升", "strong", "high"),
    ("NODE-gis", "GIS 開關設備", "equipment",
     "用量增加", "medium-high", "上升", "strong", "high"),
    ("NODE-switchboard", "配電盤", "equipment",
     "用量增加", "medium", "持平", "strong", "medium"),
    ("NODE-cable", "輸配電纜", "equipment",
     "用量增加", "medium", "持平偏升", "strong", "high"),
    ("NODE-ess", "儲能系統", "equipment",
     "用量增加", "medium", "下滑", "medium", "medium"),
    ("NODE-epc", "EPC 統包", "service",
     "用量增加", "medium", "持平", "medium", "medium"),
    ("NODE-upstream-material", "上游材料（矽鋼片/非晶質）", "material",
     "用量增加", "unknown", "unknown", "unknown", "low"),
]

SEED1_COMPANIES = [
    ("3017", "奇鋐", "NODE-cold-plate", "一條龍龍頭，冷板市佔 55%+", "龍頭", "high", "CDU、水冷板", "high", "medium"),
    ("3324", "雙鴻", "NODE-cdu", "水對水 CDU 大單", "龍頭", "high", "CDU、水冷板", "high", "medium"),
    ("3653", "健策", "NODE-vapor-chamber", "精密鍛造切入高階 GPU 水冷板", None, None, "均熱片", "medium-high", "medium"),
    ("8996", "高力", "NODE-plate-heat-exchanger", "In-Rack D2C", None, None, None, "medium", "medium"),
    ("6805", "富世達", "NODE-qd", "快接頭", None, None, None, "medium", "medium"),
    ("2421", "建準", "NODE-fan-wall", "混合氣流+水冷板放量", None, None, "CDU、液冷散熱", "medium", "medium"),
    ("8210", "勤誠", "NODE-liquid-cabinet", "機殼升級液冷機櫃", None, None, None, "medium", "medium"),
    ("6125", "廣運", "NODE-liquid-cabinet", "機房統包+監控", None, None, "CDU、快接頭", "low-medium", "low"),
]

SEED2_COMPANIES = [
    ("2330", "台積電", "NODE-cowos-frontend", "產能供給者", "龍頭", "high", None, None, "high"),
    ("3711", "日月光投控", "NODE-osat", "CoWoS-like 承接", "龍頭", "high", "CoWoS", None, "high"),
    ("6239", "力成", "NODE-osat", "外包+記憶體封測", "二階", "medium", "CoWoS", None, "medium"),
    ("3037", "欣興", "NODE-abf", "高階 ABF 佈局最完整", "龍頭", "high", "CoWoS", None, "high"),
    ("8046", "南電", "NODE-abf", "高層數 ASP 彈性最大", "龍頭", "high", "ABF、載板、先進封裝", None, "high"),
    ("3189", "景碩", "NODE-abf", "三雄之一", "龍頭", "high", "ABF、載板", None, "medium"),
    ("3131", "弘塑", "NODE-packaging-eq", "CoWoS 擴產 capex", "二階", "medium", "CoWoS", None, "medium"),
    ("3583", "辛耘", "NODE-packaging-eq", "擴產 capex", "二階", "medium", "CoWoS", None, "medium"),
    ("6187", "萬潤", "NODE-packaging-eq", "擴產 capex", "二階", "medium", "CoWoS", None, "medium"),
    ("6515", "穎崴", "NODE-test-interface", "高階測試座/socket", "龍頭", "high", "CoWoS", None, "medium"),
    ("6223", "旺矽", "NODE-test-interface", "高階探針卡", "龍頭", "high", "探針卡", None, "medium"),
    ("3680", "家登", "NODE-carrier", "wafer carrier/pod", "龍頭", "medium", "CoWoS", None, "medium"),
    ("3443", "創意", "NODE-asic-design", "CoWoS 需求方", "二階", "medium-high", "CoWoS", None, "medium"),
    ("3661", "世芯-KY", "NODE-asic-design", "CoWoS 需求方", "二階", "medium-high", "CoWoS", None, "medium"),
    ("4770", "上品", "NODE-specialty-chem", "先進製程建廠", "二階", "low-medium", None, None, "medium"),
    ("4772", "台特化", "NODE-specialty-chem", "先進製程用氣", "二階", "low-medium", None, None, "medium"),
    ("4749", "新應材", "NODE-specialty-chem", "CoWoS 材料", "二階", "low-medium", None, None, "medium"),
    ("1717", "長興", "NODE-specialty-chem", "材料供應商轉型", "二階", "low", "CoWoS", None, "medium"),
    ("6139", "亞翔", "NODE-cleanroom", "建廠標案", "二階", "medium", "CoWoS", None, "low"),
    ("6691", "洋基工程", "NODE-cleanroom", "機電工程 (跨 theme repeat)", "三階", "low", "載板、先進封裝", None, "low"),
    ("6903", "巨漢", "NODE-cleanroom", "機電/統包 (跨 theme repeat)", "三階", "low", "CoWoS", None, "low"),
    ("2404", "漢唐", "NODE-cleanroom", "廠務 EPC (跨 theme repeat)", "三階", "low", "統包工程", None, "low"),
]

SEED3_COMPANIES = [
    ("1519", "華城", "NODE-transformer", "龍頭", "龍頭", "high", "變壓器、配電盤、重電", None, "high"),
    ("1513", "中興電", "NODE-gis", "龍頭", "龍頭", "high", "配電盤、GIS、重電、統包工程", None, "high"),
    ("1503", "士電", "NODE-transformer", "龍頭", "龍頭", "high", "變壓器、配電盤、重電", None, "high"),
    ("1514", "亞力", "NODE-transformer", "龍頭", "龍頭", "medium-high", "變壓器、配電盤、重電", None, "high"),
    ("1605", "華新", "NODE-cable", "龍頭", "龍頭", "medium", "電線電纜", None, "high"),
    ("9933", "中鼎", "NODE-epc", "龍頭", "龍頭", "medium", "統包工程", None, "medium"),
    ("2371", "大同", "NODE-transformer", "二階", "二階", "medium", "變壓器、配電盤、GIS、重電", None, "medium"),
    ("1504", "東元", "NODE-ess", "二階", "二階", "medium", "儲能", None, "medium"),
    ("1609", "大亞", "NODE-cable", "二階", "二階", "low-medium", "儲能、電線電纜", None, "medium"),
    ("1612", "宏泰", "NODE-cable", "二階", "二階", "low-medium", "電線電纜", None, "medium"),
    ("1608", "華榮", "NODE-cable", "二階", "二階", "low", "電線電纜", None, "low"),
    ("1618", "合機", "NODE-cable", "三階", "三階", "low", "電線電纜、統包工程", None, "low"),
    ("5536", "聖暏", "NODE-epc", "二階", "二階", "medium", "統包工程", None, "medium"),
    ("2404", "漢唐", "NODE-epc", "廠務 EPC", "二階", "medium", "統包工程（跨 theme：Seed 2 亦命中）", None, "medium"),
    ("1529", "樂事綠能", "NODE-transformer", "三階", "三階", "low", "變壓器、配電盤、重電", None, "low"),
    ("6750", "泰創工程", "NODE-epc", "重電工程", "三階", "low", "重電、電線電纜、統包工程", None, "low"),
    ("6691", "洋基工程", "NODE-epc", "機電工程", "三階", "low", "重電、電線電纜、統包（跨 theme：Seed 2 載板、先進封裝）", None, "low"),
    ("6839", "開陽能源", "NODE-ess", "綠能開發/儲能", "三階", "low", "配電盤、重電、儲能、統包", None, "low"),
    ("6873", "泓德能源", "NODE-ess", "綠能開發/儲能", "三階", "low", "變壓器、重電、儲能", None, "low"),
    ("3628", "盈正", "NODE-ess", "儲能 PCS", "三階", "low", "儲能", None, "medium"),
    ("6903", "巨漢", "NODE-epc", "機電/統包", "三階", "low", "配電盤、統包（跨 theme：Seed 2 CoWoS）", None, "low"),
]

PENDING_MANUAL_REVIEW = [
    ("2308", "台達電", "NODE-transformer", "重電",
     "詞義漂移：「變壓器」命中語境待查（重電 vs 電源供應器）"),
]

def load_alias_map():
    with open(ALIAS_PATH) as f:
        data = yaml.safe_load(f)
    result = {}
    for concept, info in data.items():
        terms = [a["term"] for a in info.get("aliases", []) if a.get("status") == "validated"]
        result[concept] = terms
    return result

def determine_evidence(node_id, ticker, repo_hit, confidence_note=None):
    evidences = []
    entity_key = f"{node_id}|{ticker}"
    if repo_hit:
        evidences.append(("node_company", entity_key, "repo_wikilink", repo_hit, 3, "wikilink命中"))
    else:
        evidences.append(("node_company", entity_key, "news", "handoff_card", None, "卡片引用，未命中wikilink"))
    if confidence_note and "⚠️" in confidence_note:
        evidences.append(("node_company", entity_key, "ir", "handoff_card", None, "法人推估，待驗證"))
    return evidences

def seed_db(conn):
    cur = conn.cursor()

    # Themes
    for t in THEMES:
        cur.execute("INSERT INTO themes (id, name, demand_shock, time_horizon, market_status, card_url) VALUES (?, ?, ?, ?, ?, ?)", t)

    # Nodes
    for n in NODES:
        nid, name, ntype = n[0], n[1], n[2]
        cur.execute("INSERT INTO nodes (id, name, node_type, created_at) VALUES (?, ?, ?, datetime('now'))", (nid, name, ntype))

    # Theme_nodes
    seed1_nodes = set(n[0] for n in NODES[:8])
    seed2_nodes = set(n[0] for n in NODES[8:17])
    seed3_nodes = set(n[0] for n in NODES[17:])

    theme_map = {
        "THEME-liquid-cooling": seed1_nodes,
        "THEME-cowos-adv-pkg": seed2_nodes,
        "THEME-heavy-electric": seed3_nodes,
    }

    for theme_id, node_ids in theme_map.items():
        for n in NODES:
            if n[0] in node_ids:
                nid, name, ntype, di, br, asp, te, conf = n
                cur.execute(
                    "INSERT INTO theme_nodes (theme_id, node_id, demand_impact, bottleneck_risk, asp_trend, taiwan_exposure, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (theme_id, nid, di, br, asp, te, conf)
                )

    # Node companies
    all_companies = SEED1_COMPANIES + SEED2_COMPANIES + SEED3_COMPANIES
    for c in all_companies:
        ticker, name, node_id, role, mpos, crowd, hit, rev, conf = c
        cur.execute(
            "INSERT INTO node_companies (node_id, ticker, company_name, role, market_position, crowdedness, repo_hit, revenue_exposure, confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (node_id, ticker, name, role, mpos, crowd, hit, rev, conf)
        )

    # Evidence - company edges
    evidence_id = 1
    for c in all_companies:
        ticker, name, node_id, role, mpos, crowd, hit, rev, conf = c
        for ev in determine_evidence(node_id, ticker, hit, conf):
            etype, ekey, stype, sref, vscore, note = ev
            cur.execute(
                "INSERT INTO evidence (id, entity_type, entity_key, source_type, source_ref, verify_score, note, observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (evidence_id, etype, ekey, stype, sref, vscore, note)
            )
            evidence_id += 1

    # Evidence - theme_node edges
    for n in NODES:
        nid, name, ntype, di, br, asp, te, conf = n
        theme_id = None
        if nid in seed1_nodes:
            theme_id = "THEME-liquid-cooling"
        elif nid in seed2_nodes:
            theme_id = "THEME-cowos-adv-pkg"
        elif nid in seed3_nodes:
            theme_id = "THEME-heavy-electric"
        if theme_id:
            cur.execute(
                "INSERT INTO evidence (id, entity_type, entity_key, source_type, source_ref, verify_score, note, observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (evidence_id, "theme_node", f"{theme_id}|{nid}", "handoff_card", "handoff_card", None, f"節點 {name} 在 {theme_id}")
            )
            evidence_id += 1

    # Node aliases
    alias_map = load_alias_map()
    # 571 ruling (2026-07-06):
    # - NODE-ess: dual挂 (儲能 + 重電)
    # - NODE-upstream-material: remove (per §5.5 "對不到就不掛", appendix C explicit)
    # - Rest 22 rows stay
    # Final: 24 rows (8 liquid + 9 advanced pkg + 6 heavy electric + 1 energy storage)
    concept_node_map = {
        "NODE-cold-plate": "液冷", "NODE-cdu": "液冷", "NODE-manifold": "液冷",
        "NODE-qd": "液冷", "NODE-vapor-chamber": "液冷",
        "NODE-fan-wall": "液冷", "NODE-plate-heat-exchanger": "液冷",
        "NODE-liquid-cabinet": "液冷",
        "NODE-cowos-frontend": "先進封裝", "NODE-osat": "先進封裝",
        "NODE-abf": "先進封裝", "NODE-packaging-eq": "先進封裝",
        "NODE-test-interface": "先進封裝", "NODE-specialty-chem": "先進封裝",
        "NODE-carrier": "先進封裝",
        "NODE-asic-design": "先進封裝",
        "NODE-cleanroom": "先進封裝",
        "NODE-transformer": "重電", "NODE-gis": "重電",
        "NODE-switchboard": "重電", "NODE-cable": "重電",
        "NODE-ess": "重電", "NODE-epc": "重電",
    }
    for node_id, concept in concept_node_map.items():
        cur.execute("INSERT OR IGNORE INTO node_aliases (node_id, concept) VALUES (?, ?)", (node_id, concept))
    # 571 ruling: NODE-ess dual挂 (energy storage)
    cur.execute("INSERT OR IGNORE INTO node_aliases (node_id, concept) VALUES (?, ?)", ("NODE-ess", "儲能"))

    conn.commit()

def verify_counts(conn):
    cur = conn.cursor()
    expected = {
        "distinct_tickers": 48, "node_companies_rows": 51,
        "nodes": 24, "theme_nodes": 24, "themes": 3,
    }
    results = {}
    results["distinct_tickers"] = cur.execute("SELECT COUNT(DISTINCT ticker) FROM node_companies").fetchone()[0]
    results["node_companies_rows"] = cur.execute("SELECT COUNT(*) FROM node_companies").fetchone()[0]
    results["nodes"] = cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    results["theme_nodes"] = cur.execute("SELECT COUNT(*) FROM theme_nodes").fetchone()[0]
    results["themes"] = cur.execute("SELECT COUNT(*) FROM themes").fetchone()[0]
    all_ok = True
    for k, exp in expected.items():
        actual = results[k]
        status = "✓" if actual == exp else "✗ FAIL"
        print(f"  {k}: {actual} (expected {exp}) {status}")
        if actual != exp:
            all_ok = False
    return results, all_ok

def verify_q1(conn):
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT nc.ticker, nc.company_name,
               COUNT(DISTINCT tn.theme_id) AS theme_count,
               GROUP_CONCAT(DISTINCT tn.theme_id) AS themes
        FROM node_companies nc
        JOIN theme_nodes tn ON tn.node_id = nc.node_id
        GROUP BY nc.ticker
        HAVING theme_count >= 2
        ORDER BY theme_count DESC
    """).fetchall()
    print(f"\nQ1 Cross-theme repeat: {len(rows)} rows (expected exactly 3)")
    for r in rows:
        print(f"  {r[0]} {r[1]} (themes: {r[3]})")
    return rows

def verify_q4(conn):
    cur = conn.cursor()
    tn_missing = cur.execute("""
        SELECT tn.theme_id, tn.node_id
        FROM theme_nodes tn
        LEFT JOIN evidence e ON e.entity_type = 'theme_node' AND e.entity_key = tn.theme_id || '|' || tn.node_id
        WHERE e.id IS NULL
    """).fetchall()
    nc_missing = cur.execute("""
        SELECT nc.node_id, nc.ticker
        FROM node_companies nc
        LEFT JOIN evidence e ON e.entity_type = 'node_company' AND e.entity_key = nc.node_id || '|' || nc.ticker
        WHERE e.id IS NULL
    """).fetchall()
    print(f"\nQ4 護欄:")
    print(f"  theme_nodes without evidence: {len(tn_missing)} (expected 0)")
    print(f"  node_companies without evidence: {len(nc_missing)} (expected 0)")
    return len(tn_missing) == 0 and len(nc_missing) == 0

def verify_llm_draft(conn):
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM evidence WHERE source_type = 'llm_draft'").fetchone()[0]
    print(f"\nllm_draft evidence count: {count} (expected 0)")
    return count == 0


def verify_q2(conn):
    """Q2: 給定 node -> 全部公司，排除 龍頭×crowdedness high"""
    cur = conn.cursor()
    q2 = """
        SELECT nc.node_id, n.name, nc.ticker, nc.company_name,
               nc.market_position, nc.crowdedness, nc.repo_hit, nc.confidence
        FROM node_companies nc
        JOIN nodes n ON n.id = nc.node_id
        WHERE NOT (nc.market_position = '龍頭' AND nc.crowdedness = 'high')
        ORDER BY nc.node_id, nc.ticker
    """
    rows = cur.execute(q2).fetchall()
    print(f"Q2 (排除龍頭×high): {len(rows)} rows")
    return len(rows) > 0

def verify_q3(conn):
    """Q3: 給定 ticker -> 反查所有 theme/node/role"""
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT nc.ticker, nc.company_name, tn.theme_id, n.name AS node_name, nc.role
        FROM node_companies nc
        JOIN theme_nodes tn ON tn.node_id = nc.node_id
        JOIN nodes n ON n.id = nc.node_id
        WHERE nc.ticker = ?
        ORDER BY tn.theme_id, n.name
    """, ('3017',)).fetchall()
    print(f"Q3 (3017 奇鋐): {len(rows)} edges (expected 1)")
    rows2 = cur.execute("""
        SELECT nc.ticker, tn.theme_id, n.name AS node_name
        FROM node_companies nc
        JOIN theme_nodes tn ON tn.node_id = nc.node_id
        JOIN nodes n ON n.id = nc.node_id
        WHERE nc.ticker = ?
        ORDER BY tn.theme_id
    """, ('6691',)).fetchall()
    print(f"Q3 (6691 洋基工程): {len(rows2)} edges (expected 2)")
    return len(rows) == 1 and len(rows2) == 2

def verify_q5(conn):
    """Q5: node -> alias_map 概念詞"""
    cur = conn.cursor()
    q5 = """
        SELECT COUNT(DISTINCT na.node_id) AS nodes_with_aliases,
               COUNT(*) AS total_alias_entries
        FROM node_aliases na
    """
    row = cur.execute(q5).fetchone()
    print(f"Q5 (node_aliases): {row[0]} nodes, {row[1]} total entries")
    return row[0] > 0 and row[1] > 0

def main():
    print("=" * 60)
    print("Theme Graph Seeding — Handoff v3.1")
    print("=" * 60)
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run migration first.")
        return
    conn = sqlite3.connect(str(DB_PATH))
    seed_db(conn)

    print("\n--- Count assertions ---")
    counts, counts_ok = verify_counts(conn)

    print("\n--- Q1 Cross-theme repeat ---")
    q1_rows = verify_q1(conn)
    q1_ok = len(q1_rows) == 3 and set(r[0] for r in q1_rows) == {"6691", "6903", "2404"}

    print("\n--- Q4 護欄 ---")
    q4_ok = verify_q4(conn)

    print("\n--- llm_draft 禁令 ---")
    llm_ok = verify_llm_draft(conn)

    print("\n--- Pending manual review ---")
    for p in PENDING_MANUAL_REVIEW:
        print(f"  {p[0]} {p[1]}: {p[4]}")

    print("\n--- Q2 護欄 (排除龍頭×high) ---")
    q2_ok = verify_q2(conn)

    print("\n--- Q3 ticker 反查 ---")
    q3_ok = verify_q3(conn)

    print("\n--- Q5 alias_map 概念詞 ---")
    q5_ok = verify_q5(conn)

    print("\n" + "=" * 60)
    all_pass = counts_ok and q1_ok and q4_ok and llm_ok and q2_ok and q3_ok and q5_ok
    if all_pass:
        print("ALL CHECKS PASSED ✓")
    else:
        print("SOME CHECKS FAILED ✗")
        if not counts_ok: print("  → Count assertions failed")
        if not q1_ok: print("  → Q1 cross-theme repeat failed")
        if not q4_ok: print("  → Q4 evidence guard failed")
        if not llm_ok: print("  → llm_draft evidence found (should be 0)")
        if not q2_ok: print("  → Q2 filter failed")
        if not q3_ok: print("  → Q3 ticker lookup failed")
        if not q5_ok: print("  → Q5 alias_map failed")
    print("=" * 60)
    conn.close()

if __name__ == "__main__":
    main()
