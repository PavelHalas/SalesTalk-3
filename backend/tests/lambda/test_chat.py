"""
Unit tests for chat Lambda handler.
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from chat import (
    extract_tenant_id,
    validate_request,
    fetch_data_stub,
    lambda_handler
)


class TestValidateRequest:
    """Tests for chat request validation."""
    
    def test_validate_request_success(self):
        """Test successful request validation."""
        body = {"message": "What is Q3 revenue?"}
        
        # Should not raise
        validate_request(body)
    
    def test_validate_request_with_session_id(self):
        """Test validation with session ID."""
        body = {
            "message": "What is Q3 revenue?",
            "sessionId": "session-123"
        }
        
        # Should not raise
        validate_request(body)
    
    def test_validate_request_missing_message(self):
        """Test validation with missing message."""
        body = {"other_field": "value"}  # Non-empty body but missing message
        
        with pytest.raises(ValueError, match="message field is required"):
            validate_request(body)
    
    def test_validate_request_invalid_session_id(self):
        """Test validation with invalid session ID type."""
        body = {
            "message": "What is Q3 revenue?",
            "sessionId": 123  # Should be string
        }
        
        with pytest.raises(ValueError, match="sessionId must be a string"):
            validate_request(body)


class TestFetchDataStub:
    """Tests for data fetching stub."""
    
    def test_fetch_data_stub_returns_references(self):
        """Test that stub returns data references."""
        classification = {
            "measure": "revenue",
            "time": {"period": "Q3"}
        }
        
        data = fetch_data_stub(classification, "test-tenant")
        
        assert len(data) > 0
        assert "metric" in data[0]
        assert "value" in data[0]
        assert "source" in data[0]
    
    def test_fetch_data_stub_includes_tenant_in_source(self):
        """Test that stub includes tenant ID in source."""
        classification = {
            "measure": "revenue",
            "time": {"period": "Q3"}
        }
        
        data = fetch_data_stub(classification, "acme-corp-001")
        
        assert "tenant-acme-corp-001-metrics" in data[0]["source"]["table"]


class TestLambdaHandler:
    """Tests for chat Lambda handler."""
    
    @patch("chat.get_adapter")
    def test_lambda_handler_success(self, mock_get_adapter):
        """Test successful chat request."""
        # Setup mock adapter
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
            "metadata": {"model": "test"}
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Create event
        event = {
            "body": json.dumps({
                "message": "What is Q3 revenue?",
                "sessionId": "session-123"
            }),
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        # Call handler
        response = lambda_handler(event, None)
        
        # Verify response
        assert response["statusCode"] == 200
        assert "X-Request-Id" in response["headers"]
        assert "X-Session-Id" in response["headers"]
        
        body = json.loads(response["body"])
        assert "response" in body
        assert body["sessionId"] == "session-123"
        assert body["requestId"] == "test-request-id"
        assert "classification" in body
        assert "dataReferences" in body
    
    @patch("chat.get_adapter")
    def test_lambda_handler_generates_session_id(self, mock_get_adapter):
        """Test that handler generates session ID if not provided."""
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
            "metadata": {"model": "test"}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"message": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "sessionId" in body
        assert body["sessionId"]  # Not empty
    
    @patch("chat.get_adapter")
    def test_lambda_handler_refused_classification(self, mock_get_adapter):
        """Test handler with refused classification."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "unknown",
            "subject": "unknown",
            "measure": "unknown",
            "confidence": {"overall": 0.3},
            "refused": True,
            "refusal_reason": "I'm not confident I understood your question."
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"message": "ambiguous question"}),
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "refused" in body["metadata"]
        assert body["metadata"]["refused"] is True
        assert "not confident" in body["response"]
    
    @patch("chat.get_adapter")
    def test_lambda_handler_calls_both_classify_and_narrative(self, mock_get_adapter):
        """Test that handler calls both classify and generate_narrative."""
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
            "metadata": {"model": "test"}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"message": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        lambda_handler(event, None)
        
        # Verify both methods were called
        assert mock_adapter.classify.called
        assert mock_adapter.generate_narrative.called
    
    def test_lambda_handler_validation_error(self):
        """Test handler with validation error."""
        event = {
            "body": json.dumps({}),  # Missing message
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "ValidationError"


class TestTenantIsolation:
    """Tests for tenant isolation in chat handler."""
    
    @patch("chat.get_adapter")
    def test_tenant_id_passed_to_all_operations(self, mock_get_adapter):
        """Test that tenant ID is passed to all operations."""
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
            "metadata": {"model": "test"}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"message": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "acme-corp-001"
                    }
                }
            }
        }
        
        lambda_handler(event, None)
        
        # Verify tenant ID was passed to classify
        classify_args = mock_adapter.classify.call_args
        assert classify_args[1]["tenant_id"] == "acme-corp-001"
        
        # Verify tenant ID was passed to generate_narrative
        narrative_args = mock_adapter.generate_narrative.call_args
        assert narrative_args[1]["tenant_id"] == "acme-corp-001"


class TestDataReferenceIntegration:
    """Tests for data reference integration."""
    
    @patch("chat.get_adapter")
    def test_data_references_included_in_response(self, mock_get_adapter):
        """Test that data references are included in response."""
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
                        "table": "tenant-test-metrics",
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
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "test-tenant"
                    }
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        body = json.loads(response["body"])
        assert "dataReferences" in body
        assert len(body["dataReferences"]) > 0
        assert "source" in body["dataReferences"][0]
