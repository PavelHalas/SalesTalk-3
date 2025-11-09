"""
AI Adapter Interface for SalesTalk

Provides abstraction layer for AI providers (Bedrock / Ollama).
Normalizes responses and handles provider-specific details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    BEDROCK = "bedrock"
    OLLAMA = "ollama"


class AIAdapter(ABC):
    """
    Abstract base class for AI provider adapters.
    
    All concrete adapters must implement this interface to ensure
    consistent behavior across different AI backends.
    """
    
    @abstractmethod
    def classify(
        self,
        question: str,
        tenant_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Classify a user question into structured components.
        
        Args:
            question: Natural language question string
            tenant_id: Tenant identifier for isolation
            request_id: Request correlation ID for logging
            
        Returns:
            Classification dict with intent, subject, measure, etc.
            
        Raises:
            AIProviderError: If the AI provider fails
            ValidationError: If response validation fails
        """
        pass
    
    @abstractmethod
    def generate_narrative(
        self,
        classification: Dict[str, Any],
        data_references: list,
        tenant_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Generate a narrative response based on classification and data.
        
        Args:
            classification: Structured classification from classify()
            data_references: List of data points with provenance
            tenant_id: Tenant identifier
            request_id: Request correlation ID
            
        Returns:
            Narrative dict with text and metadata
            
        Raises:
            AIProviderError: If the AI provider fails
        """
        pass


class AIProviderError(Exception):
    """Raised when AI provider encounters an error."""
    pass


class ValidationError(Exception):
    """Raised when AI response fails validation."""
    pass


class BedrockAdapter(AIAdapter):
    """
    AWS Bedrock adapter using Claude.
    
    Production-ready adapter for AWS Bedrock with Claude models.
    """
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-east-1"):
        """
        Initialize Bedrock adapter.
        
        Args:
            model_id: Bedrock model identifier
            region: AWS region
        """
        self.model_id = model_id
        self.region = region
        self._client = None
        
        logger.info(
            "Initialized BedrockAdapter",
            extra={"model_id": model_id, "region": region}
        )
    
    def _get_client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
            except ImportError:
                raise AIProviderError("boto3 not installed. Install with: pip install boto3")
            except Exception as e:
                raise AIProviderError(f"Failed to initialize Bedrock client: {e}")
        return self._client
    
    def classify(
        self,
        question: str,
        tenant_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """Classify using AWS Bedrock Claude model."""
        logger.info(
            "Classifying question with Bedrock",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "question_length": len(question)
            }
        )
        
        # Build classification prompt
        prompt = self._build_classification_prompt(question)
        
        try:
            client = self._get_client()
            
            # Invoke Bedrock model
            response = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.0  # Deterministic for classification
                })
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            content = response_body["content"][0]["text"]
            
            # Extract JSON from response
            classification = self._extract_json(content)
            
            # Validate classification
            self._validate_classification(classification)
            
            logger.info(
                "Classification successful",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "confidence": classification.get("confidence", {}).get("overall", 0)
                }
            )
            
            return classification
            
        except Exception as e:
            logger.error(
                "Classification failed",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIProviderError(f"Bedrock classification failed: {e}")
    
    def generate_narrative(
        self,
        classification: Dict[str, Any],
        data_references: list,
        tenant_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """Generate narrative using AWS Bedrock Claude model."""
        logger.info(
            "Generating narrative with Bedrock",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "data_points": len(data_references)
            }
        )
        
        # Build narrative prompt
        prompt = self._build_narrative_prompt(classification, data_references)
        
        try:
            client = self._get_client()
            
            response = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3  # Slightly creative for narrative
                })
            )
            
            response_body = json.loads(response["body"].read())
            narrative_text = response_body["content"][0]["text"]
            
            logger.info(
                "Narrative generation successful",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "narrative_length": len(narrative_text)
                }
            )
            
            return {
                "text": narrative_text,
                "dataReferences": data_references,
                "metadata": {
                    "model": self.model_id,
                    "provider": "bedrock"
                }
            }
            
        except Exception as e:
            logger.error(
                "Narrative generation failed",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIProviderError(f"Bedrock narrative generation failed: {e}")
    
    def _build_classification_prompt(self, question: str) -> str:
        """Build classification prompt for Bedrock."""
        return f"""You are a business intelligence classifier. Classify the following question into structured components.

Question: {question}

Return a JSON object with the following structure:
{{
  "intent": "what|why|compare|trend|forecast|rank|drill|anomaly|target|correlation",
  "subject": "revenue|margin|customers|products|sales|orders|...",
  "measure": "revenue|gm|aov|customer_count|...",
  "dimension": {{}},
  "time": {{
    "period": "Q3|last_month|ytd|...",
    "granularity": "day|week|month|quarter|year"
  }},
  "confidence": {{
    "overall": 0.0-1.0,
    "components": {{
      "intent": 0.0-1.0,
      "subject": 0.0-1.0,
      "measure": 0.0-1.0,
      "time": 0.0-1.0
    }}
  }},
  "refused": false,
  "refusal_reason": null
}}

Only return the JSON, nothing else."""
    
    def _build_narrative_prompt(
        self,
        classification: Dict[str, Any],
        data_references: list
    ) -> str:
        """Build narrative generation prompt."""
        data_str = json.dumps(data_references, indent=2)
        return f"""Generate a clear, concise business narrative based on this data.

Classification: {json.dumps(classification, indent=2)}

Data: {data_str}

Requirements:
- Use specific numbers from the data
- Keep it under 3 sentences
- Be factual and precise
- Cite your sources

Return only the narrative text, nothing else."""
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model response."""
        # Try to find JSON in response
        text = text.strip()
        
        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed to parse JSON response: {e}")
    
    def _validate_classification(self, classification: Dict[str, Any]) -> None:
        """Validate classification response."""
        required_fields = ["intent", "subject", "measure", "confidence"]
        
        for field in required_fields:
            if field not in classification:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate confidence ranges
        confidence = classification.get("confidence", {})
        overall = confidence.get("overall", 0)
        
        if not (0.0 <= overall <= 1.0):
            raise ValidationError(f"Invalid overall confidence: {overall}")
        
        # Validate component confidences if present
        components = confidence.get("components", {})
        for key, value in components.items():
            if not (0.0 <= value <= 1.0):
                raise ValidationError(f"Invalid component confidence {key}: {value}")


class OllamaAdapter(AIAdapter):
    """
    Ollama adapter for local development.
    
    Uses local Ollama instance for development and testing.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """
        Initialize Ollama adapter.
        
        Args:
            base_url: Ollama API base URL
            model: Model name
        """
        self.base_url = base_url
        self.model = model
        
        logger.info(
            "Initialized OllamaAdapter",
            extra={"base_url": base_url, "model": model}
        )
    
    def classify(
        self,
        question: str,
        tenant_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """Classify using Ollama."""
        logger.info(
            "Classifying question with Ollama",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "question_length": len(question)
            }
        )
        
        prompt = self._build_classification_prompt(question)
        
        try:
            import requests
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0
                    }
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract JSON from response
            classification = self._extract_json(result["response"])
            
            # Validate classification
            self._validate_classification(classification)
            
            logger.info(
                "Classification successful",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "confidence": classification.get("confidence", {}).get("overall", 0)
                }
            )
            
            return classification
            
        except ImportError:
            raise AIProviderError("requests library not installed. Install with: pip install requests")
        except Exception as e:
            logger.error(
                "Classification failed",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIProviderError(f"Ollama classification failed: {e}")
    
    def generate_narrative(
        self,
        classification: Dict[str, Any],
        data_references: list,
        tenant_id: str,
        request_id: str
    ) -> Dict[str, Any]:
        """Generate narrative using Ollama."""
        logger.info(
            "Generating narrative with Ollama",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "data_points": len(data_references)
            }
        )
        
        prompt = self._build_narrative_prompt(classification, data_references)
        
        try:
            import requests
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3
                    }
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            narrative_text = result["response"]
            
            logger.info(
                "Narrative generation successful",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "narrative_length": len(narrative_text)
                }
            )
            
            return {
                "text": narrative_text,
                "dataReferences": data_references,
                "metadata": {
                    "model": self.model,
                    "provider": "ollama"
                }
            }
            
        except ImportError:
            raise AIProviderError("requests library not installed. Install with: pip install requests")
        except Exception as e:
            logger.error(
                "Narrative generation failed",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise AIProviderError(f"Ollama narrative generation failed: {e}")
    
    def _build_classification_prompt(self, question: str) -> str:
        """Build classification prompt for Ollama."""
        # Same prompt structure as Bedrock
        return f"""You are a business intelligence classifier. Classify the following question into structured components.

Question: {question}

Return a JSON object with the following structure:
{{
  "intent": "what|why|compare|trend|forecast|rank|drill|anomaly|target|correlation",
  "subject": "revenue|margin|customers|products|sales|orders|...",
  "measure": "revenue|gm|aov|customer_count|...",
  "dimension": {{}},
  "time": {{
    "period": "Q3|last_month|ytd|...",
    "granularity": "day|week|month|quarter|year"
  }},
  "confidence": {{
    "overall": 0.0-1.0,
    "components": {{
      "intent": 0.0-1.0,
      "subject": 0.0-1.0,
      "measure": 0.0-1.0,
      "time": 0.0-1.0
    }}
  }},
  "refused": false,
  "refusal_reason": null
}}

Only return the JSON, nothing else."""
    
    def _build_narrative_prompt(
        self,
        classification: Dict[str, Any],
        data_references: list
    ) -> str:
        """Build narrative generation prompt."""
        data_str = json.dumps(data_references, indent=2)
        return f"""Generate a clear, concise business narrative based on this data.

Classification: {json.dumps(classification, indent=2)}

Data: {data_str}

Requirements:
- Use specific numbers from the data
- Keep it under 3 sentences
- Be factual and precise
- Cite your sources

Return only the narrative text, nothing else."""
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model response."""
        text = text.strip()
        
        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed to parse JSON response: {e}")
    
    def _validate_classification(self, classification: Dict[str, Any]) -> None:
        """Validate classification response."""
        required_fields = ["intent", "subject", "measure", "confidence"]
        
        for field in required_fields:
            if field not in classification:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate confidence ranges
        confidence = classification.get("confidence", {})
        overall = confidence.get("overall", 0)
        
        if not (0.0 <= overall <= 1.0):
            raise ValidationError(f"Invalid overall confidence: {overall}")
        
        # Validate component confidences if present
        components = confidence.get("components", {})
        for key, value in components.items():
            if not (0.0 <= value <= 1.0):
                raise ValidationError(f"Invalid component confidence {key}: {value}")


def get_adapter(provider: AIProvider = AIProvider.BEDROCK, **kwargs) -> AIAdapter:
    """
    Factory function to get the appropriate AI adapter.
    
    Args:
        provider: AI provider to use
        **kwargs: Provider-specific configuration
        
    Returns:
        Configured AIAdapter instance
        
    Example:
        >>> adapter = get_adapter(AIProvider.BEDROCK, region="us-west-2")
        >>> adapter = get_adapter(AIProvider.OLLAMA, base_url="http://localhost:11434")
    """
    if provider == AIProvider.BEDROCK:
        return BedrockAdapter(**kwargs)
    elif provider == AIProvider.OLLAMA:
        return OllamaAdapter(**kwargs)
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")
