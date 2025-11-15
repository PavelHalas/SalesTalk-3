"""
Unit tests for Phase 0: JSON Strict Parser (JSON_STRICT)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classification.json_parser import (
    extract_json_strict,
    balance_braces,
    fix_common_json_errors,
    validate_classification_structure
)


class TestJSONExtraction:
    """Tests for JSON extraction."""
    
    def test_clean_json(self):
        """Test parsing clean JSON."""
        text = '{"intent": "what", "subject": "revenue", "measure": "mrr", "confidence": {"overall": 0.9}}'
        result, error = extract_json_strict(text)
        
        assert result is not None
        assert error is None
        assert result["intent"] == "what"
    
    def test_json_with_markdown(self):
        """Test parsing JSON in markdown code block."""
        text = '''```json
{
  "intent": "what",
  "subject": "revenue",
  "measure": "mrr",
  "confidence": {"overall": 0.9}
}
```'''
        result, error = extract_json_strict(text)
        
        assert result is not None
        assert error is None
    
    def test_json_with_prose(self):
        """Test extracting JSON from text with prose."""
        text = '''Here is the classification:
{
  "intent": "what",
  "subject": "revenue",
  "measure": "mrr",
  "confidence": {"overall": 0.9}
}
That's the result.'''
        result, error = extract_json_strict(text)
        
        assert result is not None
        assert error is None
    
    def test_json_with_missing_brace(self):
        """Test parsing JSON with missing closing brace."""
        text = '''{"intent": "what", "subject": "revenue", "measure": "mrr", "confidence": {"overall": 0.9}'''
        result, error = extract_json_strict(text)
        
        assert result is not None
        assert error is None
    
    def test_json_with_trailing_comma(self):
        """Test parsing JSON with trailing comma."""
        text = '''{"intent": "what", "subject": "revenue", "measure": "mrr", "confidence": {"overall": 0.9,},}'''
        result, error = extract_json_strict(text)
        
        assert result is not None
        assert error is None
    
    def test_empty_text(self):
        """Test empty text returns error."""
        result, error = extract_json_strict("")
        
        assert result is None
        assert error is not None


class TestBraceBalancing:
    """Tests for brace balancing."""
    
    def test_balanced_braces_no_change(self):
        """Test balanced braces unchanged."""
        text = '{"a": 1, "b": 2}'
        result, was_fixed = balance_braces(text)
        
        assert not was_fixed
        assert result == text
    
    def test_add_one_brace(self):
        """Test adding one missing brace."""
        text = '{"a": 1, "b": 2'
        result, was_fixed = balance_braces(text)
        
        assert was_fixed
        assert result == '{"a": 1, "b": 2}'
    
    def test_add_nested_braces(self):
        """Test adding nested braces."""
        text = '{"a": 1, "b": {"c": 3'
        result, was_fixed = balance_braces(text)
        
        assert was_fixed
        assert result.count('}') == 2
    
    def test_no_opening_brace(self):
        """Test text without opening brace."""
        text = '"a": 1}'
        result, was_fixed = balance_braces(text)
        
        assert not was_fixed


class TestCommonErrorFixes:
    """Tests for fixing common JSON errors."""
    
    def test_fix_trailing_comma_object(self):
        """Test fixing trailing comma in object."""
        text = '{"a": 1, "b": 2,}'
        result = fix_common_json_errors(text)
        
        assert '"b": 2}' in result
        assert ',}' not in result
    
    def test_fix_trailing_comma_array(self):
        """Test fixing trailing comma in array."""
        text = '{"arr": [1, 2, 3,]}'
        result = fix_common_json_errors(text)
        
        assert '3]' in result
        assert ',]' not in result


class TestClassificationValidation:
    """Tests for classification structure validation."""
    
    def test_valid_classification(self):
        """Test valid classification structure."""
        data = {
            "intent": "what",
            "subject": "revenue",
            "measure": "mrr",
            "confidence": {"overall": 0.9}
        }
        is_valid, error = validate_classification_structure(data)
        
        assert is_valid
        assert error == ""
    
    def test_missing_required_field(self):
        """Test missing required field."""
        data = {
            "intent": "what",
            "subject": "revenue"
            # missing measure and confidence
        }
        is_valid, error = validate_classification_structure(data)
        
        assert not is_valid
        assert "Missing required field" in error
    
    def test_confidence_not_dict(self):
        """Test confidence not a dictionary."""
        data = {
            "intent": "what",
            "subject": "revenue",
            "measure": "mrr",
            "confidence": 0.9  # Should be dict
        }
        is_valid, error = validate_classification_structure(data)
        
        assert not is_valid
        assert "confidence must be a dictionary" in error
    
    def test_confidence_out_of_range(self):
        """Test confidence out of range."""
        data = {
            "intent": "what",
            "subject": "revenue",
            "measure": "mrr",
            "confidence": {"overall": 1.5}  # Out of [0, 1]
        }
        is_valid, error = validate_classification_structure(data)
        
        assert not is_valid
        assert "must be in [0.0, 1.0]" in error
    
    def test_component_confidence_invalid(self):
        """Test component confidence invalid."""
        data = {
            "intent": "what",
            "subject": "revenue",
            "measure": "mrr",
            "confidence": {
                "overall": 0.9,
                "components": {"intent": 1.5}  # Out of range
            }
        }
        is_valid, error = validate_classification_structure(data)
        
        assert not is_valid
        assert "intent" in error
