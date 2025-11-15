"""
Unit tests for Phase 0: Dimension Extraction (DIM_EXT)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classification.dimension_extractor import (
    extract_dimensions,
    validate_dimensions,
    KNOWN_REGIONS,
    KNOWN_CHANNELS,
    KNOWN_STATUS
)


class TestDimensionExtraction:
    """Tests for dimension extraction."""
    
    def test_top_n_extraction(self):
        """Test extracting top N."""
        question = "Show me top 5 customers"
        result, extractions = extract_dimensions(question)
        
        assert result["limit"] == 5
        assert result["direction"] == "top"
        assert len(extractions) > 0
    
    def test_bottom_n_extraction(self):
        """Test extracting bottom N."""
        question = "What are the bottom 10 products?"
        result, extractions = extract_dimensions(question)
        
        assert result["limit"] == 10
        assert result["direction"] == "bottom"
    
    def test_region_extraction(self):
        """Test extracting region."""
        question = "Revenue in EMEA"
        result, extractions = extract_dimensions(question)
        
        assert result["region"] == "EMEA"
    
    def test_segment_extraction(self):
        """Test extracting segment."""
        question = "Enterprise customers count"
        result, extractions = extract_dimensions(question)
        
        assert result["segment"] == "Enterprise"
    
    def test_channel_extraction(self):
        """Test extracting channel from adjective."""
        question = "How many online sales?"
        result, extractions = extract_dimensions(question)
        
        assert result["channel"] == "online"
    
    def test_channel_extraction_heuristic(self):
        """Test channel extraction with heuristic pattern."""
        question = "Email signups this month"
        result, extractions = extract_dimensions(question)
        
        assert result["channel"] == "email"
    
    def test_status_extraction(self):
        """Test extracting status."""
        question = "How many active customers?"
        result, extractions = extract_dimensions(question)
        
        assert result["status"] == "active"
    
    def test_status_extraction_heuristic(self):
        """Test status extraction with heuristic."""
        question = "Show me inactive users"
        result, extractions = extract_dimensions(question)
        
        assert result["status"] == "inactive"
    
    def test_multiple_dimensions(self):
        """Test extracting multiple dimensions."""
        question = "Top 5 active customers in EMEA"
        result, extractions = extract_dimensions(question)
        
        assert result["limit"] == 5
        assert result["direction"] == "top"
        assert result["status"] == "active"
        assert result["region"] == "EMEA"
    
    def test_existing_dimension_preserved(self):
        """Test existing dimensions are preserved."""
        question = "Some question"
        existing = {"custom_field": "custom_value"}
        
        result, extractions = extract_dimensions(question, existing)
        
        assert result["custom_field"] == "custom_value"
    
    def test_existing_dimension_not_overwritten(self):
        """Test existing dimensions not overwritten."""
        question = "Active customers"
        existing = {"status": "churned"}  # Pre-set, should not be overwritten
        
        result, extractions = extract_dimensions(question, existing)
        
        assert result["status"] == "churned"

    def test_related_metric_extraction(self):
        """Extract related_metric for correlation phrasing."""
        question = "Is conversion rate correlated with ad spend?"
        result, extractions = extract_dimensions(question)

        assert result.get("related_metric") == "ad_spend"
        assert any("related_metric" in e for e in extractions)

    def test_product_line_detection(self):
        """Detect product line mentions using taxonomy values."""
        question = "Show pipeline value trend for Software product line"
        result, extractions = extract_dimensions(question)

        assert result.get("productLine") == "Software"

    def test_time_of_week_detection(self):
        """Detect weekday/weekend dimension."""
        question = "Compare average order value weekends vs weekdays"
        result, extractions = extract_dimensions(question)

        assert result.get("timeOfWeek") in {"weekday", "weekend"}


class TestDimensionValidation:
    """Tests for dimension validation."""
    
    def test_valid_rank_dimension(self):
        """Test valid rank dimension."""
        dimension = {"limit": 5, "direction": "top"}
        issues = validate_dimensions(dimension)
        
        assert len(issues) == 0
    
    def test_invalid_limit_negative(self):
        """Test invalid negative limit."""
        dimension = {"limit": -5, "direction": "top"}
        issues = validate_dimensions(dimension)
        
        assert any("invalid_limit" in i for i in issues)
    
    def test_invalid_limit_too_large(self):
        """Test limit too large."""
        dimension = {"limit": 10000, "direction": "top"}
        issues = validate_dimensions(dimension)
        
        assert any("limit_too_large" in i for i in issues)
    
    def test_limit_without_direction(self):
        """Test limit without direction."""
        dimension = {"limit": 5}
        issues = validate_dimensions(dimension)
        
        assert any("limit_direction_mismatch" in i for i in issues)
    
    def test_direction_without_limit(self):
        """Test direction without limit."""
        dimension = {"direction": "top"}
        issues = validate_dimensions(dimension)
        
        assert any("limit_direction_mismatch" in i for i in issues)
    
    def test_unknown_region(self):
        """Test unknown region value."""
        dimension = {"region": "ATLANTIS"}
        issues = validate_dimensions(dimension)
        
        assert any("unknown_region" in i for i in issues)
    
    def test_valid_known_values(self):
        """Test valid known values."""
        dimension = {
            "region": "EMEA",
            "channel": "online",
            "status": "active",
            "segment": "Enterprise"
        }
        issues = validate_dimensions(dimension)
        
        assert len(issues) == 0
