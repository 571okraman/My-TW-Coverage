#!/usr/bin/env python3
"""test_alias_map.py — Contract tests for WIKILINK_ALIASES validation.

Tests that validate_alias_map correctly enforces alias map invariants:
- No self-mapping (key == value)
- No empty values
- No duplicate keys (handled by dict structure, but validator should detect
  if called with a list-of-tuples or similar)
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

# validate_alias_map does not exist yet → this import fails → RED
from utils import WIKILINK_ALIASES, validate_alias_map


def test_current_alias_map_passes_validation():
    """Acceptance: alias-map-contract / Current alias map passes validation"""
    violations = validate_alias_map(WIKILINK_ALIASES)
    assert violations == [], f"Expected no violations, got: {violations}"


def test_validator_detects_selfmap():
    """Acceptance: alias-map-contract / Self-mapping is detected"""
    bad_map = {"台積電": "台積電"}
    violations = validate_alias_map(bad_map)
    assert len(violations) > 0, "Self-mapping should be detected"
    assert any("self" in v.lower() or "self-map" in v.lower() or "自身" in v for v in violations), \
        f"Violation message should mention self-map: {violations}"


def test_validator_detects_empty_value():
    """Acceptance: alias-map-contract / Empty values are detected"""
    bad_map = {"X": ""}
    violations = validate_alias_map(bad_map)
    assert len(violations) > 0, "Empty value should be detected"
    assert any("empty" in v.lower() or "空" in v or "空白" in v for v in violations), \
        f"Violation message should mention empty: {violations}"