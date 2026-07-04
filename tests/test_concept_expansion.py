#!/usr/bin/env python3
"""test_concept_expansion.py — Tests for alias-based query expansion.

Tests that expand_query correctly:
- Expands concept keys to their validated aliases
- Resolves alias terms to parent concept
- Does NOT include draft or deprecated aliases by default
- Falls through for unknown terms (with warning)
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from utils import expand_query, get_concept_aliases, load_raw_alias_map


def test_expand_concept_name():
    """Expanding a concept key returns all validated aliases + the concept itself."""
    concept, terms, warnings = expand_query("液冷")
    assert concept == "液冷"
    assert "水冷板" in terms
    assert "CDU" in terms
    assert "均熱片" in terms
    assert "快接頭" in terms
    assert "液冷" in terms  # concept itself included
    assert "液冷散熱" in terms
    assert len(warnings) == 0


def test_expand_alias_term():
    """Expanding an alias term returns the parent concept's aliases."""
    concept, terms, warnings = expand_query("CDU")
    assert concept == "液冷"
    assert "水冷板" in terms
    assert "CDU" in terms
    assert "液冷" in terms
    assert len(warnings) == 0


def test_expand_unknown_term():
    """Unknown terms fall through with warning."""
    concept, terms, warnings = expand_query("隨機不存在詞")
    assert concept is None
    assert terms == ["隨機不存在詞"]
    assert len(warnings) == 1


def test_expand_重電():
    """重電 expands to all its validated aliases."""
    concept, terms, warnings = expand_query("重電")
    assert concept == "重電"
    assert "變壓器" in terms
    assert "配電盤" in terms
    assert "GIS" in terms
    assert "重電" in terms
    assert "電線電纜" in terms
    assert "統包工程" in terms
    assert len(warnings) == 0


def test_expand_先進封裝():
    """先進封裝 expands to CoWoS/載板/ABF etc."""
    concept, terms, warnings = expand_query("先進封裝")
    assert concept == "先進封裝"
    assert "CoWoS" in terms
    assert "載板" in terms
    assert "ABF" in terms
    assert "先進封裝" in terms


def test_expand_儲能():
    """儲能 has no validated aliases, returns just itself."""
    concept, terms, warnings = expand_query("儲能")
    assert concept == "儲能"
    assert terms == ["儲能"]
    assert len(warnings) == 0


def test_deprecated_excluded():
    """Deprecated aliases like 'cold plate' should NOT be in expansion."""
    concept, terms, warnings = expand_query("液冷")
    assert "cold plate" not in terms


def test_alias_gis_expands_to_重電():
    """GIS alias resolves to 重電 parent concept."""
    concept, terms, warnings = expand_query("GIS")
    assert concept == "重電"
    assert "GIS" in terms
    assert "變壓器" in terms
    assert "重電" in terms


def test_get_concept_aliases():
    """get_concept_aliases returns only validated aliases."""
    aliases = get_concept_aliases("液冷")
    assert "水冷板" in aliases
    assert "CDU" in aliases
    assert "cold plate" not in aliases  # deprecated


def test_raw_alias_map_has_seed_data():
    """load_raw_alias_map returns seed concepts."""
    raw = load_raw_alias_map()
    assert "液冷" in raw
    assert "先進封裝" in raw
    assert "重電" in raw
    assert "儲能" in raw