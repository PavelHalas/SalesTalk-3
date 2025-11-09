"""
Additional tests for AI adapter to increase coverage.
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from ai_adapter import BedrockAdapter, OllamaAdapter, AIProviderError


class TestBedrockAdapterNarrativeGeneration:
    """Tests for Bedrock narrative generation."""
    
    def test_generate_narrative_success(self):
        """Test successful narrative generation."""
        with patch("boto3.client") as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            mock_response = {
                "body": Mock()
            }
            mock_response["body"].read.return_value = json.dumps({
                "content": [{"text": "Q3 revenue was $2.5M."}]
            }).encode()
            
            mock_client.invoke_model.return_value = mock_response
            
            adapter = BedrockAdapter()
            classification = {"intent": "what", "subject": "revenue"}
            data_refs = [{"metric": "revenue", "value": 2500000}]
            
            result = adapter.generate_narrative(
                classification=classification,
                data_references=data_refs,
                tenant_id="test-tenant",
                request_id="test-request"
            )
            
            assert "text" in result
            assert result["text"] == "Q3 revenue was $2.5M."
            assert "dataReferences" in result
            assert result["dataReferences"] == data_refs
    
    def test_generate_narrative_error(self):
        """Test narrative generation with error."""
        with patch("boto3.client") as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            mock_client.invoke_model.side_effect = Exception("API error")
            
            adapter = BedrockAdapter()
            
            with pytest.raises(AIProviderError, match="Bedrock narrative generation failed"):
                adapter.generate_narrative(
                    classification={},
                    data_references=[],
                    tenant_id="test-tenant",
                    request_id="test-request"
                )
    
    def test_build_narrative_prompt(self):
        """Test narrative prompt building."""
        adapter = BedrockAdapter()
        classification = {"intent": "what", "subject": "revenue"}
        data_refs = [{"metric": "revenue", "value": 2500000}]
        
        prompt = adapter._build_narrative_prompt(classification, data_refs)
        
        assert "revenue" in prompt
        assert "2500000" in prompt
        assert "narrative" in prompt.lower()


class TestOllamaAdapterNarrativeGeneration:
    """Tests for Ollama narrative generation."""
    
    def test_generate_narrative_success(self):
        """Test successful narrative generation."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Q3 revenue was $2.5M."
            }
            mock_post.return_value = mock_response
            
            adapter = OllamaAdapter()
            classification = {"intent": "what", "subject": "revenue"}
            data_refs = [{"metric": "revenue", "value": 2500000}]
            
            result = adapter.generate_narrative(
                classification=classification,
                data_references=data_refs,
                tenant_id="test-tenant",
                request_id="test-request"
            )
            
            assert "text" in result
            assert result["text"] == "Q3 revenue was $2.5M."
    
    def test_generate_narrative_error(self):
        """Test narrative generation with error."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection error")
            
            adapter = OllamaAdapter()
            
            with pytest.raises(AIProviderError, match="Ollama narrative generation failed"):
                adapter.generate_narrative(
                    classification={},
                    data_references=[],
                    tenant_id="test-tenant",
                    request_id="test-request"
                )


class TestBedrockAdapterErrors:
    """Test error handling in Bedrock adapter."""
    
    def test_get_client_boto3_import_error(self):
        """Test error when boto3 is not installed."""
        with patch("boto3.client", side_effect=ImportError("No module named boto3")):
            adapter = BedrockAdapter()
            
            with pytest.raises(AIProviderError, match="boto3 not installed"):
                adapter._get_client()
    
    def test_classify_bedrock_error(self):
        """Test classification with Bedrock error."""
        with patch("boto3.client") as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            mock_client.invoke_model.side_effect = Exception("Bedrock API error")
            
            adapter = BedrockAdapter()
            
            with pytest.raises(AIProviderError, match="Bedrock classification failed"):
                adapter.classify(
                    question="What is Q3 revenue?",
                    tenant_id="test-tenant",
                    request_id="test-request"
                )


class TestOllamaAdapterErrors:
    """Test error handling in Ollama adapter."""
    
    def test_classify_requests_import_error(self):
        """Test error when requests is not installed."""
        with patch("requests.post", side_effect=ImportError("No module named requests")):
            adapter = OllamaAdapter()
            
            with pytest.raises(AIProviderError, match="requests library not installed"):
                adapter.classify(
                    question="What is Q3 revenue?",
                    tenant_id="test-tenant",
                    request_id="test-request"
                )
    
    def test_classify_connection_error(self):
        """Test classification with connection error."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            
            adapter = OllamaAdapter()
            
            with pytest.raises(AIProviderError, match="Ollama classification failed"):
                adapter.classify(
                    question="What is Q3 revenue?",
                    tenant_id="test-tenant",
                    request_id="test-request"
                )
