"""
Unit tests for Phase 0: Time Token Extraction (TIME_EXT)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classification.time_extractor import (
    extract_time_tokens,
    validate_time_tokens,
    CANONICAL_PERIODS,
    CANONICAL_WINDOWS
)


class TestTimeExtraction:
    """Tests for time token extraction."""
    
    def test_ytd_extraction(self):
        """Test extracting year-to-date."""
        question = "What is the revenue year to date?"
        result = extract_time_tokens(question)
        
        assert result["window"] == "ytd"
        assert result["granularity"] == "month"
    
    def test_ytd_abbreviated(self):
        """Test YTD abbreviation."""
        question = "Show me YTD revenue"
        result = extract_time_tokens(question)
        
        assert result["window"] == "ytd"
        assert result["granularity"] == "month"
    
    def test_last_3_months(self):
        """Test last 3 months extraction."""
        question = "Revenue for last 3 months"
        result = extract_time_tokens(question)
        
        assert result["window"] == "l3m"
        assert result["granularity"] == "month"
    
    def test_last_30_days(self):
        """Test last 30 days extraction."""
        question = "Orders in the last 30 days"
        result = extract_time_tokens(question)
        
        assert result["window"] == "l30d"
        assert result["granularity"] == "day"
    
    def test_quarter_extraction(self):
        """Test Q3 extraction."""
        question = "What was Q3 revenue?"
        result = extract_time_tokens(question)
        
        assert result["period"] == "Q3"
        assert result["granularity"] == "quarter"
    
    def test_this_month(self):
        """Test this month extraction."""
        question = "Revenue this month"
        result = extract_time_tokens(question)
        
        assert result["period"] == "this_month"
        assert result["granularity"] == "month"
    
    def test_next_month(self):
        """Test next month extraction (Phase 0 addition)."""
        question = "Forecast for next month"
        result = extract_time_tokens(question)
        
        assert result["period"] == "next_month"
        assert result["granularity"] == "month"
    
    def test_last_8_quarters(self):
        """Test last 8 quarters (Phase 0 addition)."""
        question = "Show trend for last 8 quarters"
        result = extract_time_tokens(question)
        
        assert result["window"] == "l8q"
        assert result["granularity"] == "quarter"
    
    def test_existing_time_preserved(self):
        """Test that existing complete time is preserved."""
        question = "Some question"
        existing = {"period": "Q2", "granularity": "quarter"}
        
        result = extract_time_tokens(question, existing)
        
        assert result["period"] == "Q2"
        assert result["granularity"] == "quarter"
    
    def test_existing_time_enhanced(self):
        """Test that incomplete existing time is enhanced."""
        question = "Revenue year to date"
        existing = {}  # Empty
        
        result = extract_time_tokens(question, existing)
        
        assert result["window"] == "ytd"
        assert result["granularity"] == "month"

    def test_window_precedence_over_existing_period(self):
        """If LLM outputs period but question indicates a window, prefer window and drop period."""
        question = "Revenue year to date"
        existing = {"period": "this_year", "granularity": "year"}

        result = extract_time_tokens(question, existing)

        assert "period" not in result
        assert result["window"] == "ytd"
        assert result["granularity"] == "month"


class TestTimeValidation:
    """Tests for time token validation."""
    
    def test_valid_period(self):
        """Test valid period time."""
        time_obj = {"period": "Q3", "granularity": "quarter"}
        issues = validate_time_tokens(time_obj)
        
        assert len(issues) == 0
    
    def test_valid_window(self):
        """Test valid window time."""
        time_obj = {"window": "ytd", "granularity": "month"}
        issues = validate_time_tokens(time_obj)
        
        assert len(issues) == 0
    
    def test_both_period_and_window(self):
        """Test invalid: both period and window."""
        time_obj = {"period": "Q3", "window": "ytd", "granularity": "month"}
        issues = validate_time_tokens(time_obj)
        
        assert any("both_period_and_window" in i for i in issues)
    
    def test_missing_granularity(self):
        """Test missing granularity."""
        time_obj = {"period": "Q3"}
        issues = validate_time_tokens(time_obj)
        
        assert any("missing_granularity" in i for i in issues)
    
    def test_non_canonical_period(self):
        """Test non-canonical period value."""
        time_obj = {"period": "this month", "granularity": "month"}  # Should be this_month
        issues = validate_time_tokens(time_obj)
        
        assert any("non_canonical_period" in i for i in issues)
    
    def test_empty_time(self):
        """Test empty time object is valid."""
        time_obj = {}
        issues = validate_time_tokens(time_obj)
        
        assert len(issues) == 0
