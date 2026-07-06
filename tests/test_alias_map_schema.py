#!/usr/bin/env python3
"""test_alias_map_schema.py — Schema-level tests for alias_map.yaml.

Tests the YAML structure:
- status ∈ {draft, validated, deprecated}
- deprecated entries require reason+date
- context_exclude is a list when present
- validates via validate_alias_map with full schema dict
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from utils import validate_alias_map, ALIAS_MAP_PATH


def _load_raw_yaml():
    """Load the raw YAML as a dict (before flattening)."""
    import yaml as _yaml
    with open(ALIAS_MAP_PATH, "r", encoding="utf-8") as f:
        return _yaml.safe_load(f)


def test_yaml_schema_current_map_passes():
    """Acceptance: alias-map-schema / Current YAML passes validation."""
    raw = _load_raw_yaml()
    violations = validate_alias_map(raw)
    assert violations == [], f"Expected no violations, got: {violations}"


def test_yaml_schema_invalid_status():
    """Acceptance: alias-map-schema / Invalid status is detected."""
    raw = {
        "TestConcept": {
            "aliases": [
                {"term": "foo", "status": "bogus_status"}
            ]
        }
    }
    violations = validate_alias_map(raw)
    assert len(violations) > 0
    assert any("status" in v.lower() for v in violations)


def test_yaml_schema_deprecated_missing_reason():
    """Acceptance: alias-map-schema / Deprecated entry without reason is caught."""
    raw = {
        "TestConcept": {
            "aliases": [],
            "deprecated": [
                {"term": "old_alias", "date": "2026-07-03"}
                # missing reason
            ]
        }
    }
    violations = validate_alias_map(raw)
    assert len(violations) > 0
    assert any("reason" in v.lower() for v in violations)


def test_yaml_schema_deprecated_missing_date():
    """Acceptance: alias-map-schema / Deprecated entry without date is caught."""
    raw = {
        "TestConcept": {
            "aliases": [],
            "deprecated": [
                {"term": "old_alias", "reason": "no longer relevant"}
                # missing date
            ]
        }
    }
    violations = validate_alias_map(raw)
    assert len(violations) > 0
    assert any("date" in v.lower() for v in violations)


def test_yaml_schema_context_exclude_not_a_list():
    """Acceptance: alias-map-schema / context_exclude must be list when present."""
    raw = {
        "TestConcept": {
            "aliases": [
                {"term": "word", "status": "validated", "context_exclude": "not_a_list"}
            ]
        }
    }
    violations = validate_alias_map(raw)
    assert len(violations) > 0
    assert any("context_exclude" in v for v in violations)


def test_flat_backward_compatible():
    """Acceptance: alias-map-schema / Old-style flat dict still works."""
    from utils import WIKILINK_ALIASES  # noqa — loaded at module time
    assert len(WIKILINK_ALIASES) > 0
    assert isinstance(list(WIKILINK_ALIASES.values())[0], str)


def test_yaml_schema_template_skipped():
    """Acceptance: alias-map-schema / _-prefixed keys are skipped."""
    raw = {
        "_private": {
            "aliases": [{"term": "x", "status": "draft2"}]
        }
    }
    violations = validate_alias_map(raw)
    assert violations == [], f"_private should be skipped: {violations}"
