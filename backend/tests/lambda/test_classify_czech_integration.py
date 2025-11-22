"""
Test Czech integration in classify handler.

Validates that language detection and normalization work correctly
when ENABLE_LANG_DETECT is enabled.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent.parent / 'lambda'
sys.path.insert(0, str(lambda_dir))

import classify


def create_mock_event(question: str, tenant_id: str = "test-tenant-001") -> dict:
    """Create mock API Gateway event."""
    return {
        "body": json.dumps({"question": question}),
        "requestContext": {
            "requestId": "test-request-123",
            "authorizer": {
                "claims": {
                    "custom:tenant_id": tenant_id
                }
            }
        }
    }


def test_classify_english_question():
    """Test classification of English question (no normalization)."""
    # Mock the AI adapter
    mock_classification = {
        "intent": "what",
        "subject": "revenue",
        "measure": "revenue",
        "confidence": {"overall": 0.95}
    }
    
    mock_adapter = Mock()
    mock_adapter.classify.return_value = mock_classification
    
    with patch.dict(os.environ, {"ENABLE_LANG_DETECT": "false"}):
        with patch("classify.get_adapter", return_value=mock_adapter):
            event = create_mock_event("What is our revenue in Q3?")
            context = {}
            
            response = classify.lambda_handler(event, context)
            
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            
            # Should NOT have language metadata when disabled
            assert "language" not in body["metadata"]
            
            print("✅ English question (lang detect disabled): OK")


def test_classify_czech_question_with_diacritics():
    """Test classification of Czech question WITH diacritics."""
    mock_classification = {
        "intent": "what",
        "subject": "revenue",
        "measure": "revenue",
        "confidence": {"overall": 0.92}
    }
    
    mock_adapter = Mock()
    mock_adapter.classify.return_value = mock_classification
    
    with patch.dict(os.environ, {"ENABLE_LANG_DETECT": "true"}):
        with patch("classify.get_adapter", return_value=mock_adapter):
            event = create_mock_event("Jaké jsou naše tržby v Q3?")
            context = {}
            
            response = classify.lambda_handler(event, context)
            
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            
            # Should have language metadata
            assert "language" in body["metadata"]
            lang_meta = body["metadata"]["language"]
            
            assert lang_meta["detected_language"] == "cs"
            assert lang_meta["language_confidence"] >= 0.8
            assert lang_meta["has_diacritics"] is True
            assert lang_meta["normalization_coverage"] > 0
            
            # Check that normalized question was used
            assert "normalizedQuestion" in body["metadata"]
            assert "originalQuestion" in body["metadata"]
            
            # Verify adapter was called with normalized text
            called_question = mock_adapter.classify.call_args[1]["question"]
            assert "revenue" in called_question.lower() or "trzby" in called_question.lower()
            
            print(f"✅ Czech with diacritics: {lang_meta}")


def test_classify_czech_question_without_diacritics():
    """Test classification of Czech question WITHOUT diacritics (CRITICAL)."""
    mock_classification = {
        "intent": "what",
        "subject": "revenue",
        "measure": "revenue",
        "confidence": {"overall": 0.92}
    }
    
    mock_adapter = Mock()
    mock_adapter.classify.return_value = mock_classification
    
    with patch.dict(os.environ, {"ENABLE_LANG_DETECT": "true"}):
        with patch("classify.get_adapter", return_value=mock_adapter):
            # Diacritic-free Czech
            event = create_mock_event("Jake jsou nase trzby v Q3?")
            context = {}
            
            response = classify.lambda_handler(event, context)
            
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            
            # Should detect as Czech even without diacritics
            assert "language" in body["metadata"]
            lang_meta = body["metadata"]["language"]
            
            assert lang_meta["detected_language"] == "cs", \
                f"Failed to detect diacritic-free Czech! Got: {lang_meta['detected_language']}"
            assert lang_meta["language_confidence"] >= 0.65
            assert lang_meta["has_diacritics"] is False
            
            # Should still normalize
            assert lang_meta["normalization_coverage"] > 0
            
            print(f"✅ Czech WITHOUT diacritics (MANDATORY): {lang_meta}")


def test_classify_english_with_lang_detect_enabled():
    """Test that English works correctly when lang detect is enabled."""
    mock_classification = {
        "intent": "what",
        "subject": "revenue",
        "measure": "revenue",
        "confidence": {"overall": 0.95}
    }
    
    mock_adapter = Mock()
    mock_adapter.classify.return_value = mock_classification
    
    with patch.dict(os.environ, {"ENABLE_LANG_DETECT": "true"}):
        with patch("classify.get_adapter", return_value=mock_adapter):
            event = create_mock_event("What is our revenue in Q3?")
            context = {}
            
            response = classify.lambda_handler(event, context)
            
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            
            # Should detect as English
            assert "language" in body["metadata"]
            lang_meta = body["metadata"]["language"]
            
            assert lang_meta["detected_language"] == "en"
            
            # English should NOT have normalization
            assert "normalizedQuestion" not in body["metadata"]
            
            print(f"✅ English with lang detect enabled: {lang_meta}")


def test_classify_czech_colloquial_patterns():
    """Test colloquial Czech phrases trigger pattern rewrite and metadata."""
    mock_classification = {
        "intent": "what",
        "subject": "overall",
        "measure": "performance",
        "confidence": {"overall": 0.90}
    }

    mock_adapter = Mock()
    mock_adapter.classify.return_value = mock_classification

    colloquial_inputs = [
        "jak se nam vede",
        "proc jdeme dolu",
        "kdo nam odchazi",
        # Fuzzy-only near misses
        "proc jdem dolu",
        "kdo nam odchazii",
        # Exemplar-driven variant (not in patterns/fuzzy anchors)
        "proc klesly prijmy"
    ]

    with patch.dict(os.environ, {"ENABLE_LANG_DETECT": "true"}):
        with patch("classify.get_adapter", return_value=mock_adapter):
            for q in colloquial_inputs:
                event = create_mock_event(q)
                response = classify.lambda_handler(event, {})
                assert response["statusCode"] == 200
                body = json.loads(response["body"])
                lang_meta = body["metadata"]["language"]
                # Ensure we matched via patterns/fuzzy or exemplars
                has_pattern = bool(lang_meta.get("patternMatched"))
                has_exemplar = bool(lang_meta.get("exemplarMatches"))
                assert has_pattern or has_exemplar, f"No pattern or exemplar match for: {q}"
                # If rewrite exists, ensure adapter received rewritten English question
                rewrite = lang_meta.get("patternRewrite")
                called_question = mock_adapter.classify.call_args[1]["question"]
                if rewrite:
                    assert called_question == rewrite
                else:
                    # If exemplar rewrote, ensure it was used
                    ex_rw = lang_meta.get("exemplarRewrite")
                    if ex_rw:
                        assert called_question == ex_rw
                    else:
                        # Fallback ensures normalization still processed
                        assert called_question
            print("✅ Colloquial Czech pattern matching: OK")


if __name__ == '__main__':
    print("=" * 80)
    print("TESTING CZECH INTEGRATION IN CLASSIFY HANDLER")
    print("=" * 80)
    
    test_classify_english_question()
    test_classify_czech_question_with_diacritics()
    test_classify_czech_question_without_diacritics()
    test_classify_english_with_lang_detect_enabled()
    test_classify_czech_colloquial_patterns()
    
    print("\n" + "=" * 80)
    print("✅ ALL CLASSIFY INTEGRATION TESTS PASSED")
    print("=" * 80)
