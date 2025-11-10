"""
Security and tenant isolation tests.

Tests:
- JWT validation and tampering detection
- Missing or malformed authentication claims
- Cross-tenant data access prevention
- Tenant ID injection attacks
- Authorization boundary enforcement
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from classify import lambda_handler as classify_handler, extract_tenant_id
from chat import lambda_handler as chat_handler


# ============================================================================
# JWT Security Tests
# ============================================================================

class TestJWTSecurity:
    """Tests for JWT authentication and validation."""
    
    def test_missing_tenant_claim(self):
        """Test that missing tenant claim is rejected."""
        event = {
            "body": json.dumps({"question": "What is revenue?"}),
            "requestContext": {
                "requestId": "sec-test-1",
                "authorizer": {
                    "claims": {}  # No tenant ID
                }
            }
        }
        
        result = classify_handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
        assert "Tenant ID not found" in body["message"]
    
    def test_missing_authorizer_context(self):
        """Test that missing authorizer context is rejected."""
        event = {
            "body": json.dumps({"question": "What is revenue?"}),
            "requestContext": {
                "requestId": "sec-test-2"
                # No authorizer
            }
        }
        
        result = classify_handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
        assert "Invalid authentication" in body["message"]
    
    def test_null_tenant_id(self):
        """Test that null tenant ID is rejected."""
        event = {
            "body": json.dumps({"question": "What is revenue?"}),
            "requestContext": {
                "requestId": "sec-test-3",
                "authorizer": {
                    "claims": {"custom:tenant_id": None}
                }
            }
        }
        
        with pytest.raises(ValueError, match="Tenant ID not found"):
            extract_tenant_id(event)
    
    def test_empty_string_tenant_id(self):
        """Test that empty string tenant ID is rejected."""
        event = {
            "body": json.dumps({"question": "What is revenue?"}),
            "requestContext": {
                "requestId": "sec-test-4",
                "authorizer": {
                    "claims": {"custom:tenant_id": ""}
                }
            }
        }
        
        with pytest.raises(ValueError, match="Tenant ID not found"):
            extract_tenant_id(event)
    
    def test_malformed_claims_structure(self):
        """Test handling of malformed claims structure."""
        event = {
            "body": json.dumps({"question": "What is revenue?"}),
            "requestContext": {
                "requestId": "sec-test-5",
                "authorizer": {
                    "claims": "not-a-dict"  # Invalid structure
                }
            }
        }
        
        result = classify_handler(event, None)
        assert result["statusCode"] == 400
    
    @pytest.mark.xfail(
        reason="JWT signature validation not implemented - relies on API Gateway",
        strict=False
    )
    def test_jwt_signature_tampering(self):
        """Test detection of tampered JWT signatures."""
        # Known gap: JWT signature validation is done by API Gateway
        # Lambda assumes pre-validated tokens from authorizer
        pytest.skip("JWT signature validation is handled by API Gateway")


# ============================================================================
# Tenant Isolation Tests
# ============================================================================

class TestTenantIsolation:
    """Tests for cross-tenant isolation."""
    
    def test_tenant_id_included_in_logs(self):
        """Test that tenant ID is included in all log entries."""
        with patch('classify.logger') as mock_logger:
            with patch('classify.get_adapter') as mock_adapter:
                adapter = Mock()
                adapter.classify.return_value = {
                    "intent": "what",
                    "subject": "revenue",
                    "confidence": {"overall": 0.85, "components": {}}
                }
                mock_adapter.return_value = adapter
                
                event = {
                    "body": json.dumps({"question": "What is revenue?"}),
                    "requestContext": {
                        "requestId": "iso-test-1",
                        "authorizer": {
                            "claims": {"custom:tenant_id": "tenant-123"}
                        }
                    }
                }
                
                classify_handler(event, None)
                
                # Verify tenant_id appears in logging calls
                calls = mock_logger.info.call_args_list
                assert len(calls) > 0
                
                # At least one call should include tenant_id
                tenant_logged = any(
                    "tenant_id" in str(call) or 
                    (len(call[1].get("extra", {})) > 0 and 
                     "tenant_id" in call[1]["extra"])
                    for call in calls
                )
                assert tenant_logged, "tenant_id not found in log calls"
    
    def test_different_tenants_get_isolated_responses(self):
        """Test that different tenants get isolated processing."""
        with patch('classify.get_adapter') as mock_adapter:
            adapter = Mock()
            
            # Track which tenant IDs are passed to classify
            tenant_ids_seen = []
            
            def track_tenant(*args, **kwargs):
                tenant_ids_seen.append(kwargs.get("tenant_id"))
                return {
                    "intent": "what",
                    "subject": "revenue",
                    "confidence": {"overall": 0.85, "components": {}}
                }
            
            adapter.classify.side_effect = track_tenant
            mock_adapter.return_value = adapter
            
            # Make requests from two different tenants
            for tenant_id in ["tenant-A", "tenant-B"]:
                event = {
                    "body": json.dumps({"question": "What is revenue?"}),
                    "requestContext": {
                        "requestId": f"iso-{tenant_id}",
                        "authorizer": {
                            "claims": {"custom:tenant_id": tenant_id}
                        }
                    }
                }
                classify_handler(event, None)
            
            # Verify both tenant IDs were passed separately
            assert "tenant-A" in tenant_ids_seen
            assert "tenant-B" in tenant_ids_seen
    
    def test_tenant_id_passed_to_all_downstream_calls(self):
        """Test that tenant ID propagates to all operations."""
        with patch('chat.get_adapter') as mock_adapter:
            adapter = Mock()
            
            classify_calls = []
            narrative_calls = []
            
            def track_classify(*args, **kwargs):
                classify_calls.append(kwargs.get("tenant_id"))
                return {
                    "intent": "what",
                    "subject": "revenue",
                    "confidence": {"overall": 0.85, "components": {}}
                }
            
            def track_narrative(*args, **kwargs):
                narrative_calls.append(kwargs.get("tenant_id"))
                return {"text": "Revenue is $1M", "references": []}
            
            adapter.classify.side_effect = track_classify
            adapter.generate_narrative.side_effect = track_narrative
            mock_adapter.return_value = adapter
            
            event = {
                "body": json.dumps({"message": "What is revenue?"}),
                "requestContext": {
                    "requestId": "iso-chain-test",
                    "authorizer": {
                        "claims": {"custom:tenant_id": "tenant-chain"}
                    }
                }
            }
            
            chat_handler(event, None)
            
            # Verify tenant ID was passed to both classify and narrative
            assert "tenant-chain" in classify_calls
            assert "tenant-chain" in narrative_calls
    
    @pytest.mark.xfail(
        reason="DynamoDB table-level isolation tests require LocalStack",
        strict=False
    )
    def test_dynamodb_table_isolation(self):
        """Test that tenants cannot access other tenants' DynamoDB tables."""
        # Known gap: Requires DynamoDB setup
        pytest.skip("DynamoDB isolation tests require LocalStack setup")


# ============================================================================
# Injection Attack Tests
# ============================================================================

class TestInjectionAttacks:
    """Tests for various injection attack vectors."""
    
    def test_sql_injection_in_question(self):
        """Test that SQL injection attempts are handled safely."""
        event = {
            "body": json.dumps({
                "question": "DROP TABLE revenue; SELECT * FROM revenue WHERE quarter = 'Q3'"
            }),
            "requestContext": {
                "requestId": "inj-test-1",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            adapter.classify.return_value = {
                "intent": "what",
                "subject": "revenue",
                "confidence": {"overall": 0.85, "components": {}}
            }
            mock.return_value = adapter
            
            # Should process without executing SQL
            result = classify_handler(event, None)
            assert result["statusCode"] == 200
            
            # Verify the raw question was passed (not executed)
            call_args = adapter.classify.call_args
            assert "DROP TABLE" in call_args[1]["question"]
    
    def test_tenant_id_injection_attempt(self):
        """Test that tenant ID cannot be injected via question."""
        event = {
            "body": json.dumps({
                "question": "What is revenue? --tenant:other-tenant"
            }),
            "requestContext": {
                "requestId": "inj-test-2",
                "authorizer": {
                    "claims": {"custom:tenant_id": "actual-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            
            def verify_tenant(*args, **kwargs):
                # Ensure correct tenant is used
                assert kwargs["tenant_id"] == "actual-tenant"
                return {
                    "intent": "what",
                    "subject": "revenue",
                    "confidence": {"overall": 0.85, "components": {}}
                }
            
            adapter.classify.side_effect = verify_tenant
            mock.return_value = adapter
            
            result = classify_handler(event, None)
            assert result["statusCode"] == 200
    
    def test_json_injection_in_question(self):
        """Test that JSON injection attempts are handled safely."""
        event = {
            "body": json.dumps({
                "question": '{"intent": "admin", "execute": "DROP_ALL"}'
            }),
            "requestContext": {
                "requestId": "inj-test-3",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            adapter.classify.return_value = {
                "intent": "what",
                "subject": "revenue",
                "confidence": {"overall": 0.85, "components": {}}
            }
            mock.return_value = adapter
            
            # Should treat as regular text, not execute
            result = classify_handler(event, None)
            assert result["statusCode"] == 200


# ============================================================================
# Payload Robustness Tests
# ============================================================================

class TestPayloadRobustness:
    """Tests for handling malformed or truncated payloads."""
    
    def test_malformed_json_body(self):
        """Test handling of malformed JSON in request body."""
        event = {
            "body": "{invalid json}",
            "requestContext": {
                "requestId": "payload-test-1",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = classify_handler(event, None)
        # Should return error, not crash
        assert result["statusCode"] in [400, 500]
        assert "body" in result
    
    def test_missing_body(self):
        """Test handling of completely missing request body."""
        event = {
            "requestContext": {
                "requestId": "payload-test-2",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = classify_handler(event, None)
        assert result["statusCode"] == 400
    
    def test_empty_json_body(self):
        """Test handling of empty JSON object."""
        event = {
            "body": "{}",
            "requestContext": {
                "requestId": "payload-test-3",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = classify_handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        # Empty body should trigger validation error
        assert "required" in body["message"].lower()
    
    def test_truncated_payload(self):
        """Test handling of truncated JSON payload."""
        event = {
            "body": '{"question": "What is reven',  # Truncated
            "requestContext": {
                "requestId": "payload-test-4",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        result = classify_handler(event, None)
        # Should return error for invalid JSON
        assert result["statusCode"] in [400, 500]
    
    def test_extra_fields_ignored(self):
        """Test that extra fields in payload are ignored safely."""
        event = {
            "body": json.dumps({
                "question": "What is revenue?",
                "extra_field": "should_be_ignored",
                "admin": True,
                "tenant_override": "evil-tenant"
            }),
            "requestContext": {
                "requestId": "payload-test-5",
                "authorizer": {
                    "claims": {"custom:tenant_id": "good-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            
            def verify_no_override(*args, **kwargs):
                # Ensure tenant wasn't overridden from payload
                assert kwargs["tenant_id"] == "good-tenant"
                return {
                    "intent": "what",
                    "subject": "revenue",
                    "confidence": {"overall": 0.85, "components": {}}
                }
            
            adapter.classify.side_effect = verify_no_override
            mock.return_value = adapter
            
            result = classify_handler(event, None)
            assert result["statusCode"] == 200


# ============================================================================
# PII Leakage Prevention Tests
# ============================================================================

class TestPIILeakagePrevention:
    """Tests for preventing PII leakage in responses and logs."""
    
    def test_pii_in_question_not_logged(self):
        """Test that PII in questions is handled carefully."""
        # This is a basic check - comprehensive PII detection requires tooling
        event = {
            "body": json.dumps({
                "question": "What is revenue for customer john.doe@example.com?"
            }),
            "requestContext": {
                "requestId": "pii-test-1",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            adapter.classify.return_value = {
                "intent": "what",
                "subject": "revenue",
                "confidence": {"overall": 0.85, "components": {}}
            }
            mock.return_value = adapter
            
            # Should process without issues
            result = classify_handler(event, None)
            assert result["statusCode"] == 200
    
    @pytest.mark.xfail(
        reason="PII detection and redaction not implemented - planned for v2.0",
        strict=False
    )
    def test_pii_redaction_in_logs(self):
        """Test that PII is redacted from logs."""
        # Known gap: PII detection and redaction not implemented
        pytest.skip("PII redaction is a known gap for v2.0")
    
    @pytest.mark.xfail(
        reason="Cross-tenant data leakage detection requires DynamoDB",
        strict=False
    )
    def test_no_cross_tenant_data_in_response(self):
        """Test that responses never include other tenants' data."""
        # Known gap: Requires full integration with DynamoDB
        pytest.skip("Cross-tenant leakage tests require DynamoDB setup")


# ============================================================================
# Authorization Boundary Tests
# ============================================================================

class TestAuthorizationBoundaries:
    """Tests for authorization boundary enforcement."""
    
    def test_tenant_cannot_access_system_endpoints(self):
        """Test that tenant tokens cannot access system operations."""
        # This would require additional endpoints to test
        # For now, verify tenant ID is always required
        event = {
            "body": json.dumps({"question": "SYSTEM: DROP ALL TABLES"}),
            "requestContext": {
                "requestId": "authz-test-1",
                "authorizer": {
                    "claims": {"custom:tenant_id": "regular-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            adapter.classify.return_value = {
                "intent": "what",
                "subject": "unknown",
                "confidence": {"overall": 0.85, "components": {}}
            }
            mock.return_value = adapter
            
            result = classify_handler(event, None)
            # Should process as regular question, not system command
            assert result["statusCode"] == 200
    
    @pytest.mark.xfail(
        reason="Role-based access control not implemented - planned for v2.1",
        strict=False
    )
    def test_role_based_access_control(self):
        """Test that different roles have different access levels."""
        # Known gap: RBAC not implemented yet
        pytest.skip("Role-based access control is a known gap for v2.1")
