"""Tests for taxonomy-based configuration loader."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classification import config_loader


@pytest.fixture(autouse=True)
def reset_loader_cache(monkeypatch):
    """Ensure each test uses fresh cache to avoid cross-test contamination."""
    config_loader.get_classification_config.cache_clear()  # type: ignore[attr-defined]
    yield
    config_loader.get_classification_config.cache_clear()  # type: ignore[attr-defined]


def test_dimensions_loaded_from_shared_taxonomy(tmp_path):
    dimensions = config_loader.get_dimensions_config()
    assert "regions" in dimensions
    assert "EMEA" in dimensions["regions"]
    assert dimensions["rank"]["max_limit"] == 1000


def test_metrics_subject_map_includes_aliases():
    metrics_config = config_loader.get_metrics_config()

    # Alias should map back to canonical metric id and subject
    assert metrics_config["aliases"]["signups"] == "signup_count"
    assert metrics_config["subject_map"]["signups"] == "marketing"

    # Canonical id also maps correctly
    assert metrics_config["subject_map"]["nps"] == "customers"
    assert metrics_config["registry"]["nps"]["subject"] == "customers"


def test_subject_structure_exposes_metrics():
    taxonomy = config_loader.get_classification_config()
    revenue = taxonomy["subjects"]["revenue"]
    margin = taxonomy["subjects"]["margin"]

    assert revenue["meta"]["subject"] == "revenue"
    assert "mrr" in revenue["metrics"]
    assert "monthly_recurring_revenue" in revenue["metrics"]["mrr"]["aliases"]
    assert revenue["intents"], "Expected resolved intents list"
    assert revenue["intents"][0]["id"] == "what"
    
    # Verify margin subject has gm metrics
    assert margin["meta"]["subject"] == "margin"
    assert "gm_pct" in margin["metrics"]
    assert "gross_margin_pct" in margin["metrics"]["gm_pct"]["aliases"]


def test_intents_registry_loaded():
    taxonomy = config_loader.get_classification_config()
    intents = taxonomy.get("intents")
    assert "rank" in intents
    assert "patterns" in intents["rank"]
