"""
Unit tests for Phase 0: Subject-Metric Rules (RULES)
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classification.rules import (
    apply_subject_metric_rules,
    normalize_measure,
    get_subject_for_measure,
    METRIC_SUBJECT_MAP,
    METRIC_ALIASES
)


class TestSubjectMetricRules:
    """Tests for subject-metric correction rules."""
    
    def test_metric_leak_fixed_churn_rate(self):
        """Test fixing churn_rate appearing as subject."""
        classification = {
            "intent": "what",
            "subject": "churn_rate",  # WRONG - metric as subject
            "measure": "value",
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        assert result["subject"] == "customers"
        assert result["measure"] == "churn_rate"
        assert len(corrections) > 0
        assert any("metric_leak_fixed" in c for c in corrections)
    
    def test_metric_leak_fixed_pipeline(self):
        """Test fixing pipeline as subject."""
        classification = {
            "intent": "what",
            "subject": "pipeline_value",
            "measure": "",
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        assert result["subject"] == "sales"
        assert result["measure"] == "pipeline_value"
    
    def test_subject_family_constraint_arpu(self):
        """Test enforcing customers subject for arpu metric."""
        classification = {
            "intent": "what",
            "subject": "revenue",  # WRONG - should be customers
            "measure": "arpu",
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        assert result["subject"] == "customers"
        assert result["measure"] == "arpu"
        assert any("subject_family_corrected" in c for c in corrections)
    
    def test_subject_family_constraint_aov(self):
        """Test enforcing orders subject for aov metric."""
        classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "aov",
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        assert result["subject"] == "orders"
        assert result["measure"] == "aov"
    
    def test_metric_alias_normalization(self):
        """Test normalizing metric aliases."""
        classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "gross_margin",  # alias for gm
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        assert result["measure"] == "gm"
        assert any("metric_alias_normalized" in c for c in corrections)
    
    def test_multiple_corrections(self):
        """Test multiple corrections applied together."""
        classification = {
            "intent": "what",
            "subject": "nps_score",  # metric as subject + alias
            "measure": "",
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        # Should normalize alias nps_score -> nps
        # Should fix subject to customers
        assert result["subject"] == "customers"
        assert result["measure"] == "nps"
        assert len(corrections) >= 2
    
    def test_no_corrections_needed(self):
        """Test correct classification passes through unchanged."""
        classification = {
            "intent": "what",
            "subject": "customers",
            "measure": "churn_rate",
            "dimension": {},
            "time": {}
        }
        
        result, corrections = apply_subject_metric_rules(classification)
        
        assert result["subject"] == "customers"
        assert result["measure"] == "churn_rate"
        assert len(corrections) == 0


class TestNormalizeMeasure:
    """Tests for measure normalization."""
    
    def test_normalize_alias(self):
        """Test normalizing an alias."""
        assert normalize_measure("gross_margin") == "gm"
        assert normalize_measure("refund_rate") == "return_rate"
        assert normalize_measure("signups") == "signup_count"
    
    def test_normalize_canonical(self):
        """Test canonical measure returns unchanged."""
        assert normalize_measure("churn_rate") == "churn_rate"
        assert normalize_measure("revenue") == "revenue"
    
    def test_normalize_case_insensitive(self):
        """Test case insensitive normalization."""
        assert normalize_measure("GROSS_MARGIN") == "gm"
        assert normalize_measure("Refund_Rate") == "return_rate"


class TestGetSubjectForMeasure:
    """Tests for subject lookup."""
    
    def test_get_subject_customers(self):
        """Test getting subject for customer metrics."""
        assert get_subject_for_measure("churn_rate") == "customers"
        assert get_subject_for_measure("nps") == "customers"
        assert get_subject_for_measure("arpu") == "customers"
    
    def test_get_subject_orders(self):
        """Test getting subject for order metrics."""
        assert get_subject_for_measure("aov") == "orders"
        assert get_subject_for_measure("order_count") == "orders"
    
    def test_get_subject_with_alias(self):
        """Test getting subject with alias normalization."""
        assert get_subject_for_measure("nps_score") == "customers"
        assert get_subject_for_measure("refund_rate") == "orders"
    
    def test_get_subject_unknown(self):
        """Test unknown measure returns empty string."""
        assert get_subject_for_measure("unknown_metric") == ""
