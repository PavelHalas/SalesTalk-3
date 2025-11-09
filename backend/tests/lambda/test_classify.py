"""
Unit tests for classification Lambda handler.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from classify import (
    extract_tenant_id,
    validate_request,
    lambda_handler
)


class TestExtractTenantId:
    """Tests for tenant ID extraction."""
    
    def test_extract_tenant_id_success(self):
        """Test successful tenant ID extraction."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "acme-corp-001"
                    }
                }
            }
        }
        
        tenant_id = extract_tenant_id(event)
        assert tenant_id == "acme-corp-001"
    
    def test_extract_tenant_id_alternative_claim(self):
        """Test extraction with alternative claim name."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "tenantId": "techstart-inc-001"
                    }
                }
            }
        }
        
        tenant_id = extract_tenant_id(event)
        assert tenant_id == "techstart-inc-001"
    
    def test_extract_tenant_id_missing(self):
        """Test extraction with missing tenant ID."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {}
                }
            }
        }
        
        with pytest.raises(ValueError, match="Tenant ID not found"):
            extract_tenant_id(event)
    
    def test_extract_tenant_id_no_authorizer(self):
        """Test extraction with missing authorizer."""
        event = {
            "requestContext": {}
        }
        
        with pytest.raises(ValueError, match="Invalid authentication"):
            extract_tenant_id(event)


class TestValidateRequest:
    """Tests for request validation."""
    
    def test_validate_request_success(self):
        """Test successful request validation."""
        body = {"question": "What is Q3 revenue?"}
        
        # Should not raise
        validate_request(body)
    
    def test_validate_request_empty_body(self):
        """Test validation with empty body."""
        with pytest.raises(ValueError, match="Request body is required"):
            validate_request(None)
    
    def test_validate_request_missing_question(self):
        """Test validation with missing question."""
        body = {"other_field": "value"}  # Non-empty body but missing question
        
        with pytest.raises(ValueError, match="question field is required"):
            validate_request(body)
    
    def test_validate_request_non_string_question(self):
        """Test validation with non-string question."""
        body = {"question": 123}
        
        with pytest.raises(ValueError, match="question must be a string"):
            validate_request(body)
    
    def test_validate_request_too_long(self):
        """Test validation with question exceeding max length."""
        body = {"question": "a" * 10001}
        
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_request(body)
    
    def test_validate_request_empty_question(self):
        """Test validation with empty question."""
        body = {"question": "   "}
        
        with pytest.raises(ValueError, match="question cannot be empty"):
            validate_request(body)


class TestLambdaHandler:
    """Tests for classification Lambda handler."""
    
    @patch("classify.get_adapter")
    def test_lambda_handler_success(self, mock_get_adapter):
        """Test successful classification request."""
        # Setup mock adapter
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 0.95,
                    "subject": 0.91
                }
            }
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Create event
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
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
        
        body = json.loads(response["body"])
        assert body["classification"]["intent"] == "what"
        assert body["classification"]["subject"] == "revenue"
        assert body["tenantId"] == "test-tenant"
        assert body["requestId"] == "test-request-id"
        
        # Verify adapter was called with correct params
        mock_adapter.classify.assert_called_once_with(
            question="What is Q3 revenue?",
            tenant_id="test-tenant",
            request_id="test-request-id"
        )
    
    def test_lambda_handler_missing_tenant_id(self):
        """Test handler with missing tenant ID."""
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "test-request-id",
                "authorizer": {
                    "claims": {}
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "ValidationError"
        assert "Tenant ID" in body["message"]
    
    def test_lambda_handler_invalid_request(self):
        """Test handler with invalid request."""
        event = {
            "body": json.dumps({"other_field": "value"}),  # Missing question
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
        assert "question" in body["message"]
    
    @patch("classify.get_adapter")
    def test_lambda_handler_ai_provider_error(self, mock_get_adapter):
        """Test handler with AI provider error."""
        from ai_adapter import AIProviderError
        
        # Setup mock adapter to raise error
        mock_adapter = Mock()
        mock_adapter.classify.side_effect = AIProviderError("AI service unavailable")
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
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
        
        assert response["statusCode"] == 502
        body = json.loads(response["body"])
        assert body["error"] == "AIProviderError"
        assert "temporarily unavailable" in body["message"]
    
    @patch("classify.get_adapter")
    def test_lambda_handler_unexpected_error(self, mock_get_adapter):
        """Test handler with unexpected error."""
        # Setup mock adapter to raise unexpected error
        mock_adapter = Mock()
        mock_adapter.classify.side_effect = Exception("Unexpected error")
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
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
        
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"] == "InternalServerError"
    
    @patch.dict(os.environ, {"AI_PROVIDER": "ollama", "OLLAMA_BASE_URL": "http://test:11434"})
    @patch("classify.get_adapter")
    def test_lambda_handler_ollama_provider(self, mock_get_adapter):
        """Test handler with Ollama provider."""
        from ai_adapter import AIProvider
        
        # Setup mock adapter
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {"overall": 0.92}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
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
        
        # Verify get_adapter was called with Ollama provider
        call_args = mock_get_adapter.call_args
        assert call_args[0][0] == AIProvider.OLLAMA
        assert call_args[1]["base_url"] == "http://test:11434"


class TestTenantIsolation:
    """Tests for tenant isolation enforcement."""
    
    @patch("classify.get_adapter")
    def test_tenant_id_passed_to_classifier(self, mock_get_adapter):
        """Test that tenant ID is passed to classifier."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {"overall": 0.92}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
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
        call_args = mock_adapter.classify.call_args
        assert call_args[1]["tenant_id"] == "acme-corp-001"
    
    @patch("classify.get_adapter")
    def test_different_tenants_isolated(self, mock_get_adapter):
        """Test that different tenants are isolated."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {"overall": 0.92}
        }
        mock_get_adapter.return_value = mock_adapter
        
        # First tenant
        event1 = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "request-1",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "tenant-1"
                    }
                }
            }
        }
        
        response1 = lambda_handler(event1, None)
        body1 = json.loads(response1["body"])
        
        # Second tenant
        event2 = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "request-2",
                "authorizer": {
                    "claims": {
                        "custom:tenant_id": "tenant-2"
                    }
                }
            }
        }
        
        response2 = lambda_handler(event2, None)
        body2 = json.loads(response2["body"])
        
        # Verify different tenant IDs in responses
        assert body1["tenantId"] == "tenant-1"
        assert body2["tenantId"] == "tenant-2"
        assert body1["tenantId"] != body2["tenantId"]


class TestLogging:
    """Tests for structured logging."""
    
    @patch("classify.logger")
    @patch("classify.get_adapter")
    def test_logging_includes_tenant_and_request_id(self, mock_get_adapter, mock_logger):
        """Test that logs include tenant and request IDs."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {"overall": 0.92}
        }
        mock_get_adapter.return_value = mock_adapter
        
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
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
        
        # Verify info logs were called with tenant and request ID
        info_calls = mock_logger.info.call_args_list
        
        # Check at least one log has both tenant_id and request_id
        found_correct_log = False
        for call in info_calls:
            if len(call[1]) > 0 and "extra" in call[1]:
                extra = call[1]["extra"]
                if "tenant_id" in extra and "request_id" in extra:
                    assert extra["tenant_id"] == "test-tenant"
                    assert extra["request_id"] == "test-request-id"
                    found_correct_log = True
                    break
        
        assert found_correct_log, "Expected log with tenant_id and request_id"
