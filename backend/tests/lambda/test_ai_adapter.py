"""
Unit tests for AI Adapter interface and implementations.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from ai_adapter import (
    AIAdapter,
    AIProvider,
    AIProviderError,
    ValidationError,
    BedrockAdapter,
    OllamaAdapter,
    get_adapter
)


class TestAIProviderEnum:
    """Tests for AIProvider enum."""
    
    def test_provider_values(self):
        """Test that provider enum has correct values."""
        assert AIProvider.BEDROCK.value == "bedrock"
        assert AIProvider.OLLAMA.value == "ollama"


class TestBedrockAdapter:
    """Tests for BedrockAdapter."""
    
    def test_initialization(self):
        """Test adapter initialization."""
        adapter = BedrockAdapter(model_id="test-model", region="us-west-2")
        
        assert adapter.model_id == "test-model"
        assert adapter.region == "us-west-2"
        assert adapter._client is None
    
    def test_build_classification_prompt(self):
        """Test classification prompt generation."""
        adapter = BedrockAdapter()
        prompt = adapter._build_classification_prompt("What is Q3 revenue?")
        
        assert "What is Q3 revenue?" in prompt
        assert "JSON" in prompt
        assert "intent" in prompt
        assert "subject" in prompt
        assert "confidence" in prompt
    
    def test_extract_json_plain(self):
        """Test JSON extraction from plain text."""
        adapter = BedrockAdapter()
        text = '{"intent": "what", "subject": "revenue"}'
        
        result = adapter._extract_json(text)
        
        assert result["intent"] == "what"
        assert result["subject"] == "revenue"
    
    def test_extract_json_markdown(self):
        """Test JSON extraction from markdown code block."""
        adapter = BedrockAdapter()
        text = '```json\n{"intent": "what", "subject": "revenue"}\n```'
        
        result = adapter._extract_json(text)
        
        assert result["intent"] == "what"
        assert result["subject"] == "revenue"
    
    def test_extract_json_invalid(self):
        """Test JSON extraction with invalid JSON."""
        adapter = BedrockAdapter()
        
        with pytest.raises(ValidationError, match="Failed to parse JSON"):
            adapter._extract_json("not valid json")
    
    def test_validate_classification_success(self):
        """Test successful classification validation."""
        adapter = BedrockAdapter()
        
        classification = {
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
        
        # Should not raise
        adapter._validate_classification(classification)
    
    def test_validate_classification_missing_field(self):
        """Test validation with missing required field."""
        adapter = BedrockAdapter()
        
        classification = {
            "intent": "what",
            "subject": "revenue"
            # Missing 'measure' and 'confidence'
        }
        
        with pytest.raises(ValidationError, match="Missing required field"):
            adapter._validate_classification(classification)
    
    def test_validate_classification_invalid_confidence(self):
        """Test validation with invalid confidence range."""
        adapter = BedrockAdapter()
        
        classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 1.5  # Invalid: > 1.0
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid overall confidence"):
            adapter._validate_classification(classification)
    
    def test_validate_classification_invalid_component_confidence(self):
        """Test validation with invalid component confidence."""
        adapter = BedrockAdapter()
        
        classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": -0.1  # Invalid: < 0.0
                }
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid component confidence"):
            adapter._validate_classification(classification)
    
    def test_classify_success(self):
        """Test successful classification with Bedrock."""
        # Setup mock
        with patch("boto3.client") as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            mock_response = {
                "body": MagicMock()
            }
            
            classification_result = {
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
            
            mock_response["body"].read.return_value = json.dumps({
                "content": [{"text": json.dumps(classification_result)}]
            }).encode()
            
            mock_client.invoke_model.return_value = mock_response
            
            # Test
            adapter = BedrockAdapter()
            result = adapter.classify(
                question="What is Q3 revenue?",
                tenant_id="test-tenant",
                request_id="test-request"
            )
            
            assert result["intent"] == "what"
            assert result["subject"] == "revenue"
            assert result["confidence"]["overall"] == 0.92
            
            # Verify client was called correctly
            mock_client.invoke_model.assert_called_once()
            call_args = mock_client.invoke_model.call_args
            assert "What is Q3 revenue?" in json.loads(call_args[1]["body"])["messages"][0]["content"]


class TestOllamaAdapter:
    """Tests for OllamaAdapter."""
    
    def test_initialization(self):
        """Test adapter initialization."""
        adapter = OllamaAdapter(base_url="http://test:11434", model="llama3")
        
        assert adapter.base_url == "http://test:11434"
        assert adapter.model == "llama3"
    
    def test_build_classification_prompt(self):
        """Test classification prompt generation."""
        adapter = OllamaAdapter()
        prompt = adapter._build_classification_prompt("What is Q3 revenue?")
        
        assert "What is Q3 revenue?" in prompt
        assert "JSON" in prompt
        assert "intent" in prompt
    
    def test_extract_json(self):
        """Test JSON extraction."""
        adapter = OllamaAdapter()
        text = '{"intent": "what", "subject": "revenue"}'
        
        result = adapter._extract_json(text)
        
        assert result["intent"] == "what"
        assert result["subject"] == "revenue"
    
    def test_validate_classification(self):
        """Test classification validation."""
        adapter = OllamaAdapter()
        
        classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 0.92
            }
        }
        
        # Should not raise
        adapter._validate_classification(classification)
    
    def test_classify_success(self):
        """Test successful classification with Ollama."""
        # Setup mock
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            
            classification_result = {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {
                    "overall": 0.92,
                    "components": {
                        "intent": 0.95
                    }
                }
            }
            
            mock_response.json.return_value = {
                "response": json.dumps(classification_result)
            }
            
            mock_post.return_value = mock_response
            
            # Test
            adapter = OllamaAdapter()
            result = adapter.classify(
                question="What is Q3 revenue?",
                tenant_id="test-tenant",
                request_id="test-request"
            )
            
            assert result["intent"] == "what"
            assert result["subject"] == "revenue"
            
            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "http://localhost:11434/api/generate" in call_args[0]


class TestGetAdapter:
    """Tests for get_adapter factory function."""
    
    def test_get_bedrock_adapter(self):
        """Test getting Bedrock adapter."""
        adapter = get_adapter(AIProvider.BEDROCK, model_id="test-model")
        
        assert isinstance(adapter, BedrockAdapter)
        assert adapter.model_id == "test-model"
    
    def test_get_ollama_adapter(self):
        """Test getting Ollama adapter."""
        adapter = get_adapter(AIProvider.OLLAMA, model="llama3")
        
        assert isinstance(adapter, OllamaAdapter)
        assert adapter.model == "llama3"
    
    def test_get_adapter_invalid_provider(self):
        """Test getting adapter with invalid provider."""
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            get_adapter("invalid")


class TestConfidenceValidation:
    """Test confidence validation across adapters."""
    
    @pytest.mark.parametrize("adapter_class", [BedrockAdapter, OllamaAdapter])
    def test_confidence_in_valid_range(self, adapter_class):
        """Test that valid confidence values pass validation."""
        adapter = adapter_class()
        
        valid_classifications = [
            {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {"overall": 0.0}
            },
            {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {"overall": 0.5}
            },
            {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {"overall": 1.0}
            },
        ]
        
        for classification in valid_classifications:
            adapter._validate_classification(classification)  # Should not raise
    
    @pytest.mark.parametrize("adapter_class", [BedrockAdapter, OllamaAdapter])
    def test_confidence_out_of_range(self, adapter_class):
        """Test that invalid confidence values fail validation."""
        adapter = adapter_class()
        
        invalid_classifications = [
            {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {"overall": -0.1}
            },
            {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {"overall": 1.1}
            },
            {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "confidence": {"overall": 2.0}
            },
        ]
        
        for classification in invalid_classifications:
            with pytest.raises(ValidationError):
                adapter._validate_classification(classification)
    
    @pytest.mark.parametrize("adapter_class", [BedrockAdapter, OllamaAdapter])
    def test_component_confidence_validation(self, adapter_class):
        """Test that component confidence values are validated."""
        adapter = adapter_class()
        
        # Valid component confidences
        valid_classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 0.95,
                    "subject": 0.91,
                    "measure": 0.90
                }
            }
        }
        
        adapter._validate_classification(valid_classification)  # Should not raise
        
        # Invalid component confidence
        invalid_classification = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "confidence": {
                "overall": 0.92,
                "components": {
                    "intent": 1.5  # Invalid
                }
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid component confidence"):
            adapter._validate_classification(invalid_classification)
