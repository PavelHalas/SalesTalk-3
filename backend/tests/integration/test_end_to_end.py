"""
Integration tests for end-to-end classification and narrative generation.

These tests verify the complete flow from question input to narrative output.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from classify import lambda_handler as classify_handler
from chat import lambda_handler as chat_handler


@pytest.mark.integration
class TestClassificationIntegration:
    """Integration tests for classification endpoint."""
    
    @patch("classify.get_adapter")
    def test_end_to_end_classification(self, mock_get_adapter):
        """Test complete classification flow."""
        # Setup mock adapter
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "dimension": {},
            "time": {
                "period": "Q3",
                "granularity": "quarter"
            },
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 0.95,
                    "subject": 0.91,
                    "measure": 0.90,
                    "time": 0.93
                }
            },
            "refused": False,
            "refusal_reason": None
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Simulate API Gateway event
        event = {
            "body": json.dumps({
                "question": "What is our Q3 revenue?"
            }),
            "requestContext": {
                "requestId": "integration-test-request",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "acme-corp-001"
                    }
                }
            }
        }
        
        # Execute
        response = classify_handler(event, None)
        
        # Verify
        assert response["statusCode"] == 200
        
        body = json.loads(response["body"])
        assert body["classification"]["intent"] == "what"
        assert body["classification"]["subject"] == "revenue"
        assert body["classification"]["confidence"]["overall"] == 0.92
        assert body["tenantId"] == "acme-corp-001"
        
        # Verify all component confidences are in range [0.0, 1.0]
        components = body["classification"]["confidence"]["components"]
        for key, value in components.items():
            assert 0.0 <= value <= 1.0, f"Component {key} confidence {value} out of range"


@pytest.mark.integration
class TestChatIntegration:
    """Integration tests for chat endpoint."""
    
    @patch("chat.get_adapter")
    def test_end_to_end_chat_flow(self, mock_get_adapter):
        """Test complete chat flow from question to narrative."""
        # Setup mock adapter
        mock_adapter = Mock()
        
        # Mock classification
        classification_result = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "dimension": {},
            "time": {
                "period": "Q3",
                "granularity": "quarter"
            },
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 0.95,
                    "subject": 0.91
                }
            },
            "refused": False
        }
        mock_adapter.classify.return_value = classification_result
        
        # Mock narrative generation
        narrative_result = {
            "text": "Q3 2025 revenue was $2.5M, up 15% from Q2 2025 ($2.17M).",
            "dataReferences": [
                {
                    "metric": "revenue",
                    "period": "Q3",
                    "value": 2500000,
                    "unit": "USD",
                    "source": {
                        "table": "tenant-acme-corp-001-metrics",
                        "pk": "METRIC#revenue",
                        "sk": "Q3"
                    }
                }
            ],
            "metadata": {
                "model": "test-model",
                "provider": "test"
            }
        }
        mock_adapter.generate_narrative.return_value = narrative_result
        mock_get_adapter.return_value = mock_adapter
        
        # Create event
        event = {
            "body": json.dumps({
                "message": "What is our Q3 revenue?",
                "sessionId": "session-integration-test"
            }),
            "requestContext": {
                "requestId": "integration-test-request",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "acme-corp-001"
                    }
                }
            }
        }
        
        # Execute
        response = chat_handler(event, None)
        
        # Verify
        assert response["statusCode"] == 200
        
        body = json.loads(response["body"])
        
        # Verify narrative response
        assert "response" in body
        assert "$2.5M" in body["response"]
        
        # Verify classification included
        assert body["classification"]["intent"] == "what"
        assert body["classification"]["subject"] == "revenue"
        
        # Verify data references included with provenance
        assert len(body["dataReferences"]) > 0
        data_ref = body["dataReferences"][0]
        assert "source" in data_ref
        assert "table" in data_ref["source"]
        assert "pk" in data_ref["source"]
        assert "sk" in data_ref["source"]
        assert "acme-corp-001" in data_ref["source"]["table"]
        
        # Verify session tracking
        assert body["sessionId"] == "session-integration-test"
        assert body["requestId"] == "integration-test-request"


@pytest.mark.integration
class TestEvaluationIntegration:
    """Integration tests with evaluation framework."""
    
    @patch("classify.get_adapter")
    def test_classification_matches_evaluation_schema(self, mock_get_adapter):
        """Test that classification output matches evaluation schema."""
        # Load a sample question from gold dataset
        gold_dataset_path = os.path.join(
            os.path.dirname(__file__),
            "../../evaluation/gold.json"
        )
        
        with open(gold_dataset_path, "r") as f:
            gold_data = json.load(f)
        
        # Get first question
        sample_question = gold_data["questions"][0]
        
        # Setup mock to return expected classification
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": sample_question["expected"]["intent"],
            "subject": sample_question["expected"]["subject"],
            "measure": sample_question["expected"]["measure"],
            "dimension": sample_question["expected"].get("dimension", {}),
            "time": sample_question["expected"].get("time", {}),
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 0.95,
                    "subject": 0.91
                }
            },
            "refused": False
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Create event with sample question
        event = {
            "body": json.dumps({
                "question": sample_question["question"]
            }),
            "requestContext": {
                "requestId": "eval-integration-test",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        # Execute
        response = classify_handler(event, None)
        
        # Verify
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        # Verify classification matches expected schema
        classification = body["classification"]
        expected = sample_question["expected"]
        
        assert classification["intent"] == expected["intent"]
        assert classification["subject"] == expected["subject"]
        assert classification["measure"] == expected["measure"]
        
        # Verify confidence values are in valid range
        assert 0.0 <= classification["confidence"]["overall"] <= 1.0
        for value in classification["confidence"]["components"].values():
            assert 0.0 <= value <= 1.0


@pytest.mark.integration
class TestConfidenceConstraints:
    """Integration tests for confidence constraint enforcement."""
    
    @patch("chat.get_adapter")
    def test_confidence_values_within_contract_range(self, mock_get_adapter):
        """Test that all confidence values are within [0.0, 1.0]."""
        # Setup mock with valid confidence values
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 0.95,
                    "subject": 0.91,
                    "measure": 0.90,
                    "time": 0.93,
                    "dimension": 0.88
                }
            },
            "refused": False
        }
        mock_adapter.generate_narrative.return_value = {
            "text": "Test response",
            "metadata": {}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"message": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "test-request",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        response = chat_handler(event, None)
        body = json.loads(response["body"])
        
        # Verify overall confidence
        overall = body["classification"]["confidence"]["overall"]
        assert 0.0 <= overall <= 1.0, f"Overall confidence {overall} out of range"
        
        # Verify component confidences
        components = body["classification"]["confidence"]["components"]
        for component, value in components.items():
            assert 0.0 <= value <= 1.0, f"Component {component} confidence {value} out of range"


@pytest.mark.integration
class TestNarrativeStub:
    """Integration tests for narrative generation stub."""
    
    @patch("chat.get_adapter")
    def test_narrative_includes_data_references(self, mock_get_adapter):
        """Test that narrative includes proper data references."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "time": {"period": "Q3"},
            "confidence": {"overall": 0.92},
            "refused": False
        }
        mock_adapter.generate_narrative.return_value = {
            "text": "Q3 revenue was $2.5M.",
            "dataReferences": [
                {
                    "metric": "revenue",
                    "period": "Q3",
                    "value": 2500000,
                    "unit": "USD",
                    "source": {
                        "table": "tenant-test-tenant-metrics",
                        "pk": "METRIC#revenue",
                        "sk": "Q3"
                    }
                }
            ],
            "metadata": {"model": "test"}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"message": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "test-request",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        response = chat_handler(event, None)
        body = json.loads(response["body"])
        
        # Verify data references structure
        assert "dataReferences" in body
        assert len(body["dataReferences"]) > 0
        
        ref = body["dataReferences"][0]
        
        # Verify required fields per DATA_CONTRACTS.md
        required_fields = ["metric", "period", "value", "unit", "source"]
        for field in required_fields:
            assert field in ref, f"Missing required field: {field}"
        
        # Verify source traceability
        source = ref["source"]
        assert "table" in source
        assert "pk" in source
        assert "sk" in source
        
        # Verify tenant isolation in source
        assert "test-tenant" in source["table"]
