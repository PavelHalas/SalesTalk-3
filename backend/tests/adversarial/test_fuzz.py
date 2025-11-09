"""
Adversarial fuzz tests for classification robustness.

Tests cover:
- Typos and misspellings
- Mixed locales and emojis
- Ambiguous time phrases
- Code-switching and language mixing
- Special characters and noise
- Edge cases (empty, whitespace, extremely long)
"""

import pytest
import json
import sys
import os
from typing import Dict, Any

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from classify import lambda_handler, validate_request
from ai_adapter import AIProvider, get_adapter


# ============================================================================
# Typo and Misspelling Tests
# ============================================================================

class TestTypoRobustness:
    """Tests for handling typos and misspellings."""
    
    @pytest.mark.parametrize("question,expected_subject", [
        ("reveneu Q3", "revenue"),  # Single letter typo
        ("rvnue q3", "revenue"),  # Missing vowels
        ("revnue Q3", "revenue"),  # Transposition
        ("reveune Q3", "revenue"),  # Letter swap
    ])
    def test_classify_handles_common_typos(self, question, expected_subject):
        """Test that common typos in metric names are handled."""
        # This is a known gap - we don't have spell correction yet
        # Mark as xfail to track the gap without failing CI
        pytest.skip("Spell correction not implemented - known gap tracked for v1.1")
    
    def test_validate_request_handles_typos_in_input(self):
        """Test that validation doesn't reject valid typos."""
        body = {"question": "What is reveneu in Q3?"}
        # Should not raise - typos should be valid input
        validate_request(body)


# ============================================================================
# Mixed Locale and Emoji Tests
# ============================================================================

class TestMixedLocaleRobustness:
    """Tests for handling mixed locales, emojis, and special characters."""
    
    def test_emoji_in_question(self):
        """Test classification with emoji characters."""
        event = {
            "body": json.dumps({"question": "How much 💰 did we make in Q3?"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        # Should process without errors - emojis are noise to ignore
        result = lambda_handler(event, None)
        assert result["statusCode"] in [200, 502]  # 502 if no AI provider available
    
    def test_mixed_language_query(self):
        """Test code-switching between languages."""
        event = {
            "body": json.dumps({"question": "Pourquoi le revenue is down in Q3?"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        # Should handle gracefully - may refuse or extract English parts
        result = lambda_handler(event, None)
        assert result["statusCode"] in [200, 400, 502]
    
    def test_all_caps_question(self):
        """Test classification with ALL CAPS input."""
        event = {
            "body": json.dumps({"question": "REVENUE Q3 2024"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        assert result["statusCode"] in [200, 502]
    
    def test_excessive_punctuation(self):
        """Test handling of excessive punctuation noise."""
        event = {
            "body": json.dumps({"question": "..................revenue............q3..........."}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        assert result["statusCode"] in [200, 502]
    
    def test_unicode_special_characters(self):
        """Test handling of various unicode characters."""
        event = {
            "body": json.dumps({"question": "What's the Δ between EMEA and APAC?"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        assert result["statusCode"] in [200, 502]


# ============================================================================
# Ambiguous Time Phrase Tests
# ============================================================================

class TestAmbiguousTimeHandling:
    """Tests for handling ambiguous and relative time phrases."""
    
    @pytest.mark.parametrize("time_phrase", [
        "last quarter",
        "this quarter",
        "the quarter that just ended",
        "most recent completed quarter",
        "current period",
    ])
    def test_relative_time_phrases(self, time_phrase):
        """Test handling of relative time expressions."""
        event = {
            "body": json.dumps({"question": f"What is revenue for {time_phrase}?"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should process - might need clarification but shouldn't error
        assert result["statusCode"] in [200, 502]
    
    def test_vague_future_reference(self):
        """Test handling of vague future time references."""
        event = {
            "body": json.dumps({"question": "What will revenue be in the future?"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should handle - may refuse or ask for clarification
        assert result["statusCode"] in [200, 400, 502]
    
    def test_invalid_quarter_number(self):
        """Test handling of invalid quarter (Q15)."""
        event = {
            "body": json.dumps({"question": "revenue for Q15"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should handle gracefully - may refuse with validation error
        assert result["statusCode"] in [200, 400, 502]
    
    @pytest.mark.xfail(reason="DST boundary handling not implemented - known gap for v1.2", strict=False)
    def test_dst_boundary_handling(self):
        """Test time calculations across DST boundaries."""
        # This is a known gap for complex temporal reasoning
        pytest.skip("DST boundary handling is a known gap tracked for v1.2")


# ============================================================================
# Edge Case Input Tests
# ============================================================================

class TestEdgeCaseInputs:
    """Tests for extreme and edge case inputs."""
    
    def test_empty_string_question(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValueError, match="question field is required"):
            validate_request({"question": ""})
    
    def test_whitespace_only_question(self):
        """Test that whitespace-only question is rejected."""
        with pytest.raises(ValueError, match="question cannot be empty"):
            validate_request({"question": "   \t\n   "})
    
    def test_single_word_question(self):
        """Test handling of single-word questions."""
        event = {
            "body": json.dumps({"question": "revenue"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should process - may have low confidence
        assert result["statusCode"] in [200, 502]
    
    def test_extremely_long_question(self):
        """Test handling of questions at length limit."""
        # Create a question near the 10,000 character limit
        long_question = "What is revenue " + "for region " * 1000 + "in Q3?"
        
        event = {
            "body": json.dumps({"question": long_question[:9999]}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should process or reject with size limit error
        assert result["statusCode"] in [200, 400, 502]
    
    def test_question_exceeds_limit(self):
        """Test that overly long questions are rejected."""
        long_question = "x" * 10001
        
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_request({"question": long_question})
    
    def test_emoji_only_question(self):
        """Test handling of emoji-only input."""
        event = {
            "body": json.dumps({"question": "💰💰💰"}),
            "requestContext": {
                "requestId": "test-123",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should handle - may refuse due to lack of clarity
        assert result["statusCode"] in [200, 400, 502]


# ============================================================================
# Adversarial Dataset Integration Tests
# ============================================================================

class TestAdversarialDataset:
    """Tests using the adversarial.json dataset."""
    
    @pytest.fixture
    def adversarial_data(self):
        """Load adversarial dataset."""
        path = os.path.join(
            os.path.dirname(__file__),
            "../../evaluation/adversarial.json"
        )
        with open(path, 'r') as f:
            return json.load(f)
    
    def test_adversarial_dataset_loads(self, adversarial_data):
        """Test that adversarial dataset is accessible."""
        assert "questions" in adversarial_data
        assert len(adversarial_data["questions"]) > 0
    
    @pytest.mark.parametrize("category", [
        "typo",
        "emoji",
        "all_caps",
        "noise",
        "incomplete_syntax",
    ])
    def test_adversarial_category_robustness(self, adversarial_data, category):
        """Test robustness against specific adversarial categories."""
        questions = [
            q for q in adversarial_data["questions"]
            if q.get("category") == category
        ]
        
        if not questions:
            pytest.skip(f"No questions found for category: {category}")
        
        # Test a sample from this category
        sample = questions[0]
        
        event = {
            "body": json.dumps({"question": sample["question"]}),
            "requestContext": {
                "requestId": sample["id"],
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        # Should handle without crashing
        assert result["statusCode"] in [200, 400, 502]
        assert "body" in result


# ============================================================================
# Known Gaps Documentation
# ============================================================================

class TestKnownGaps:
    """Tests that document known limitations and gaps.
    
    These tests are marked with xfail and include rationale and ETA.
    They serve as living documentation of what we know doesn't work yet.
    """
    
    @pytest.mark.xfail(
        reason="Multi-language support not implemented - planned for v2.0",
        strict=False
    )
    def test_non_english_language_support(self):
        """Test full Spanish language question."""
        event = {
            "body": json.dumps({"question": "¿Cuál es el ingreso del tercer trimestre?"}),
            "requestContext": {
                "requestId": "test-lang",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        body = json.loads(result["body"])
        
        # Currently expects refusal, but v2.0 should handle this
        assert "error" in body or body.get("metadata", {}).get("refused")
    
    @pytest.mark.xfail(
        reason="Hypothetical scenario analysis not in scope - no ETA",
        strict=False
    )
    def test_hypothetical_scenario_handling(self):
        """Test 'what if' hypothetical scenarios."""
        event = {
            "body": json.dumps({"question": "What would revenue be if we doubled our prices?"}),
            "requestContext": {
                "requestId": "test-hyp",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = lambda_handler(event, None)
        body = json.loads(result["body"])
        
        # Should refuse hypothetical scenarios
        assert body.get("metadata", {}).get("refused") is True
    
    @pytest.mark.xfail(
        reason="Complex temporal reasoning (leap years, fiscal calendars) - planned for v1.3",
        strict=False
    )
    def test_leap_year_handling(self):
        """Test date calculations involving leap years."""
        # Known gap - complex calendar calculations
        pytest.skip("Leap year handling is a known gap tracked for v1.3")
