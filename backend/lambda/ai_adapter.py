"""
AI Adapter Interface for SalesTalk

Provides abstraction layer for AI providers (Bedrock / Ollama).
Normalizes responses and handles provider-specific details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from enum import Enum
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path for Phase 0 modules
_src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

logger = logging.getLogger(__name__)

# Prompt template directory
PROMPT_DIR = Path(__file__).parent / "prompts"


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
        data_references: List[Dict[str, Any]],
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


def _load_prompt_template(template_name: str) -> str:
    """Load a prompt template from the prompts directory.
    
    Args:
        template_name: Relative path to template file from prompts/ directory
        
    Returns:
        Template content as string
        
    Raises:
        AIProviderError: If template file not found
    """
    template_path = PROMPT_DIR / template_name
    try:
        return template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AIProviderError(f"Prompt template not found: {template_path}")
    except Exception as e:
        raise AIProviderError(f"Failed to load prompt template {template_path}: {e}")


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

            # Always-on normalization (aliases/synonyms to canonical)
            try:
                from classification.normalizer import normalize_classification
                classification = normalize_classification(classification)
            except Exception as e:
                logger.warning(f"Normalizer not applied: {e}")

            # Phase 0 enhancements
            classification = self._apply_phase_0_enhancements(
                question=question,
                classification=classification,
                request_id=request_id,
                tenant_id=tenant_id
            )

            classification = _apply_phase_1_hierarchy(
                question=question,
                classification=classification,
                tenant_id=tenant_id,
                request_id=request_id,
            )

            # Optional TRM-inspired self-repair pass to fix common misses (dimension/time/subject-family)
            if _should_self_repair():
                classification = self._recursive_repair(
                    question=question,
                    initial=classification,
                    request_id=request_id,
                    tenant_id=tenant_id,
                )
            
            logger.info(
                "Classification successful",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "confidence": classification.get("confidence", {}).get("overall", 0),
                    "corrections_applied": classification.get("metadata", {}).get("corrections_applied", []),
                    "parse_attempts": classification.get("metadata", {}).get("parse_attempts", 1)
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
        data_references: List[Dict[str, Any]],
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
        """Build classification prompt for Bedrock using external template."""
        template = _load_prompt_template("classification/bedrock_classification.txt")
        return template.format(question=question)

    def _build_repair_prompt(self, question: str, current: Dict[str, Any], issues: List[str]) -> str:
        """Build repair prompt using external template."""
        template = _load_prompt_template("classification/repair_prompt.txt")
        return template.format(
            question=question,
            current_json=json.dumps(current, ensure_ascii=False),
            issues=json.dumps(issues, ensure_ascii=False)
        )

    def _recursive_repair(
        self,
        question: str,
        initial: Dict[str, Any],
        tenant_id: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Attempt up to N focused repair steps using the provider to correct common misses."""
        steps = _self_repair_steps()
        current = dict(initial)
        for i in range(steps):
            issues = _detect_issues(question, current)
            if not issues:
                break
            try:
                client = self._get_client()
                prompt = self._build_repair_prompt(question, current, issues)
                response = client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 512,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.0
                    })
                )
                response_body = json.loads(response["body"].read())
                content = response_body["content"][0]["text"]
                repaired = self._extract_json(content)
                self._validate_classification(repaired)
                current = repaired
                logger.info(
                    "Self-repair step applied",
                    extra={"tenant_id": tenant_id, "request_id": request_id, "step": i + 1}
                )
            except Exception as e:
                logger.warning(
                    "Self-repair step failed; keeping previous JSON",
                    extra={"tenant_id": tenant_id, "request_id": request_id, "step": i + 1, "error": str(e)}
                )
                break
        return current
    
    def _apply_phase_0_enhancements(
        self,
        question: str,
        classification: Dict[str, Any],
        request_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Apply Phase 0 enhancements: RULES, TIME_EXT, DIM_EXT.
        
        Tracks corrections and extractions in metadata.
        """
        result = dict(classification)
        all_corrections = []
        
        # Initialize metadata if not present
        if "metadata" not in result:
            result["metadata"] = {}
        
        # Track parse attempts (simplified - would be set by json_parser)
        if "parse_attempts" not in result["metadata"]:
            result["metadata"]["parse_attempts"] = 1
        
        try:
            # Phase 0.1: Apply RULES (subject-metric corrections)
            from classification.rules import apply_subject_metric_rules
            
            result, rules_corrections = apply_subject_metric_rules(result)
            all_corrections.extend(rules_corrections)
            
        except ImportError:
            logger.warning("Phase 0 rules module not available")
        except Exception as e:
            logger.warning(f"Phase 0 rules failed: {e}")
        
        try:
            # Phase 0.2: Apply TIME_EXT (time token extraction)
            from classification.time_extractor import extract_time_tokens
            
            existing_time = result.get("time", {})
            enhanced_time = extract_time_tokens(question, existing_time)
            
            if enhanced_time != existing_time:
                result["time"] = enhanced_time
                all_corrections.append("time_tokens_enhanced")
            
        except ImportError:
            logger.warning("Phase 0 time_extractor module not available")
        except Exception as e:
            logger.warning(f"Phase 0 time extraction failed: {e}")
        
        try:
            # Phase 0.3: Apply DIM_EXT (dimension extraction)
            from classification.dimension_extractor import extract_dimensions
            
            existing_dim = result.get("dimension", {})
            enhanced_dim, dim_corrections = extract_dimensions(question, existing_dim)
            
            if enhanced_dim != existing_dim:
                result["dimension"] = enhanced_dim
                all_corrections.extend(dim_corrections)
            
        except ImportError:
            logger.warning("Phase 0 dimension_extractor module not available")
        except Exception as e:
            logger.warning(f"Phase 0 dimension extraction failed: {e}")

        try:
            # Phase 0.4: Intent corrections based on cues/dimensions
            from classification.rules import apply_intent_rules
            result, intent_corr = apply_intent_rules(question, result)
            all_corrections.extend(intent_corr)
        except ImportError:
            logger.warning("Phase 0 intent rules not available")
        except Exception as e:
            logger.warning(f"Phase 0 intent correction failed: {e}")

        try:
            # Phase 0.5: Measure corrections from text cues and re-apply subject enforcement
            from classification.rules import apply_measure_text_corrections, apply_subject_metric_rules
            corrected, meas_corr = apply_measure_text_corrections(question, result)
            if corrected != result:
                result = corrected
                all_corrections.extend(meas_corr)
                # Enforce subject family after measure change
                result, fam_corr = apply_subject_metric_rules(result)
                all_corrections.extend(fam_corr)
        except ImportError:
            logger.warning("Phase 0 measure text rules not available")
        except Exception as e:
            logger.warning(f"Phase 0 measure correction failed: {e}")
        
        # Store all corrections in metadata
        if all_corrections:
            result["metadata"]["corrections_applied"] = all_corrections
        
        logger.info(
            "Phase 0 enhancements applied",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "corrections_count": len(all_corrections)
            }
        )
        
        return result
    
    def _build_narrative_prompt(
        self,
        classification: Dict[str, Any],
        data_references: List[Dict[str, Any]]
    ) -> str:
        """Build narrative generation prompt using external template."""
        template = _load_prompt_template("narrative/narrative_generation.txt")
        return template.format(
            classification=json.dumps(classification, indent=2),
            data_references=json.dumps(data_references, indent=2)
        )
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model response using Phase 0 strict parser."""
        # Use Phase 0 JSON_STRICT parser
        try:
            from classification.json_parser import extract_json_strict
            
            parsed, error = extract_json_strict(text)
            if parsed is not None:
                return parsed
            else:
                raise ValidationError(f"Failed to parse JSON response: {error}")
        except ImportError:
            # Fallback to original parsing if Phase 0 module not available
            logger.warning("Phase 0 json_parser not available, using fallback")
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
                timeout=120  # Increased for larger models (20B+)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract JSON from response
            classification = self._extract_json(result["response"])

            # Validate classification
            self._validate_classification(classification)

            # Always-on normalization (aliases/synonyms to canonical)
            try:
                from classification.normalizer import normalize_classification
                classification = normalize_classification(classification)
            except Exception as e:
                logger.warning(f"Normalizer not applied: {e}")

            # Phase 0 enhancements
            classification = self._apply_phase_0_enhancements(
                question=question,
                classification=classification,
                request_id=request_id,
                tenant_id=tenant_id
            )
            classification = _apply_phase_1_hierarchy(
                question=question,
                classification=classification,
                tenant_id=tenant_id,
                request_id=request_id,
            )

            # Optional TRM-inspired self-repair pass
            if _should_self_repair():
                classification = self._recursive_repair(
                    question=question,
                    initial=classification,
                    request_id=request_id,
                    tenant_id=tenant_id,
                )
            
            logger.info(
                "Classification successful",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "confidence": classification.get("confidence", {}).get("overall", 0),
                    "corrections_applied": classification.get("metadata", {}).get("corrections_applied", []),
                    "parse_attempts": classification.get("metadata", {}).get("parse_attempts", 1)
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
        data_references: List[Dict[str, Any]],
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
        """Build classification prompt for Ollama using external template."""
        template = _load_prompt_template("classification/ollama_classification.txt")
        return template.format(question=question)

    def _build_repair_prompt(self, question: str, current: Dict[str, Any], issues: List[str]) -> str:
        """Build repair prompt using external template."""
        template = _load_prompt_template("classification/repair_prompt.txt")
        return template.format(
            question=question,
            current_json=json.dumps(current, ensure_ascii=False),
            issues=json.dumps(issues, ensure_ascii=False)
        )

    def _recursive_repair(
        self,
        question: str,
        initial: Dict[str, Any],
        tenant_id: str,
        request_id: str,
    ) -> Dict[str, Any]:
        steps = _self_repair_steps()
        current = dict(initial)
        for i in range(steps):
            issues = _detect_issues(question, current)
            if not issues:
                break
            try:
                import requests
                prompt = self._build_repair_prompt(question, current, issues)
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.0},
                    },
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()
                repaired = self._extract_json(result["response"])
                self._validate_classification(repaired)
                current = repaired
                logger.info(
                    "Self-repair step applied",
                    extra={"tenant_id": tenant_id, "request_id": request_id, "step": i + 1}
                )
            except Exception as e:
                logger.warning(
                    "Self-repair step failed; keeping previous JSON",
                    extra={"tenant_id": tenant_id, "request_id": request_id, "step": i + 1, "error": str(e)}
                )
                break
        return current
    
    def _apply_phase_0_enhancements(
        self,
        question: str,
        classification: Dict[str, Any],
        request_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Apply Phase 0 enhancements: RULES, TIME_EXT, DIM_EXT.
        
        Tracks corrections and extractions in metadata.
        """
        result = dict(classification)
        all_corrections = []
        
        # Initialize metadata if not present
        if "metadata" not in result:
            result["metadata"] = {}
        
        # Track parse attempts (simplified - would be set by json_parser)
        if "parse_attempts" not in result["metadata"]:
            result["metadata"]["parse_attempts"] = 1
        
        try:
            # Phase 0.1: Apply RULES (subject-metric corrections)
            from classification.rules import apply_subject_metric_rules
            
            result, rules_corrections = apply_subject_metric_rules(result)
            all_corrections.extend(rules_corrections)
            
        except ImportError:
            logger.warning("Phase 0 rules module not available")
        except Exception as e:
            logger.warning(f"Phase 0 rules failed: {e}")
        
        try:
            # Phase 0.2: Apply TIME_EXT (time token extraction)
            from classification.time_extractor import extract_time_tokens
            
            existing_time = result.get("time", {})
            enhanced_time = extract_time_tokens(question, existing_time)
            
            if enhanced_time != existing_time:
                result["time"] = enhanced_time
                all_corrections.append("time_tokens_enhanced")
            
        except ImportError:
            logger.warning("Phase 0 time_extractor module not available")
        except Exception as e:
            logger.warning(f"Phase 0 time extraction failed: {e}")
        
        try:
            # Phase 0.3: Apply DIM_EXT (dimension extraction)
            from classification.dimension_extractor import extract_dimensions
            
            existing_dim = result.get("dimension", {})
            enhanced_dim, dim_corrections = extract_dimensions(question, existing_dim)
            
            if enhanced_dim != existing_dim:
                result["dimension"] = enhanced_dim
                all_corrections.extend(dim_corrections)
            
        except ImportError:
            logger.warning("Phase 0 dimension_extractor module not available")
        except Exception as e:
            logger.warning(f"Phase 0 dimension extraction failed: {e}")
        
        # Store all corrections in metadata
        if all_corrections:
            result["metadata"]["corrections_applied"] = all_corrections
        
        logger.info(
            "Phase 0 enhancements applied",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "corrections_count": len(all_corrections)
            }
        )
        
        return result
    
    def _build_narrative_prompt(
        self,
        classification: Dict[str, Any],
        data_references: List[Dict[str, Any]]
    ) -> str:
        """Build narrative generation prompt using external template."""
        template = _load_prompt_template("narrative/narrative_generation.txt")
        return template.format(
            classification=json.dumps(classification, indent=2),
            data_references=json.dumps(data_references, indent=2)
        )
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model response using Phase 0 strict parser."""
        # Use Phase 0 JSON_STRICT parser
        try:
            from classification.json_parser import extract_json_strict
            
            parsed, error = extract_json_strict(text)
            if parsed is not None:
                return parsed
            else:
                raise ValidationError(f"Failed to parse JSON response: {error}")
        except ImportError:
            # Fallback to original parsing if Phase 0 module not available
            logger.warning("Phase 0 json_parser not available, using fallback")
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


def get_adapter(provider: AIProvider = AIProvider.BEDROCK, **kwargs: Any) -> AIAdapter:
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


# ---- TRM-inspired self-repair helpers (provider-agnostic) ----

def _should_self_repair() -> bool:
    return os.getenv("USE_SELF_REPAIR", "false").lower() in {"1", "true", "yes"}


def _self_repair_steps() -> int:
    try:
        return max(0, int(os.getenv("SELF_REPAIR_STEPS", "1")))
    except Exception:
        return 1


def _should_use_hierarchical_passes() -> bool:
    return os.getenv("USE_HIER_PASSES", "false").lower() in {"1", "true", "yes"}


def _apply_phase_1_hierarchy(
    question: str,
    classification: Dict[str, Any],
    tenant_id: str,
    request_id: str,
) -> Dict[str, Any]:
    if not _should_use_hierarchical_passes():
        return classification

    # Harmonize time based on cues (window/granularity)
    try:
        ql = (question or "").lower()
        time_payload = classification.get("time", {}) or {}
        changed = False
        # Load taxonomy time config for patterns
        try:
            from classification.config_loader import get_classification_config
            cfg = get_classification_config()
            time_cfg = cfg.get("time", {}) or {}
            window_patterns = time_cfg.get("window_patterns", []) or []
        except Exception:
            window_patterns = []
        for pattern in window_patterns:
            matches = pattern.get("match", []) if isinstance(pattern, dict) else []
            if not isinstance(matches, list):
                continue
            if any(m in ql for m in matches):
                # Apply pattern mappings if not already set or if different
                new_window = pattern.get("window")
                new_gran = pattern.get("granularity")
                new_period = pattern.get("period")
                updated = dict(time_payload)
                if new_period and updated.get("period") != new_period:
                    updated["period"] = new_period
                if new_window and updated.get("window") != new_window:
                    updated["window"] = new_window
                if new_gran and updated.get("granularity") != new_gran:
                    updated["granularity"] = new_gran
                if updated != time_payload:
                    time_payload = updated
                    changed = True
        if changed:
            classification["time"] = time_payload
            meta = classification.setdefault("metadata", {})
            corr = meta.setdefault("corrections_applied", [])
            if "time_tokens_harmonized" not in corr:
                corr.append("time_tokens_harmonized")
    except Exception:
        pass

    try:
        hierarchy_module = __import__(
            "classification.hierarchy",
            fromlist=["PhaseOneClassificationError", "run_hierarchical_pipeline"],
        )
        run_hierarchical_pipeline = getattr(hierarchy_module, "run_hierarchical_pipeline")
        phase_one_error = getattr(hierarchy_module, "PhaseOneClassificationError")
    except ImportError:
        logger.warning("Phase 1 hierarchy module not available; skipping")
        return classification

    try:
        updated = run_hierarchical_pipeline(question, classification)
        # Preserve dimensions if Phase 1 dropped them
        try:
            orig_dim = classification.get("dimension", {})
            upd_dim = updated.get("dimension") if isinstance(updated, dict) else None
            if isinstance(orig_dim, dict) and orig_dim and (not isinstance(upd_dim, dict) or not upd_dim):
                updated["dimension"] = orig_dim
                meta = updated.setdefault("metadata", {})
                corr = meta.setdefault("corrections_applied", [])
                if "dimension_preserved_phase1" not in corr:
                    corr.append("dimension_preserved_phase1")
        except Exception:
            pass
        logger.info(
            "Phase 1 hierarchical passes applied",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "phase1_status": updated.get("metadata", {}).get("phase1", {}).get("status"),
            },
        )
        return updated
    except phase_one_error as exc:  # type: ignore[misc]
        refused = dict(classification)
        refused["refused"] = True
        refused["refusal_reason"] = str(exc)
        metadata = refused.setdefault("metadata", {})
        phase_meta = metadata.setdefault("phase1", {})
        phase_meta["status"] = "error"
        phase_meta["error"] = str(exc)
        logger.warning(
            "Phase 1 hierarchical pass failed; refusing classification",
            extra={"tenant_id": tenant_id, "request_id": request_id, "error": str(exc)},
        )
        return refused
    except Exception as exc:
        logger.warning(
            "Phase 1 hierarchy pipeline errored; ignoring",
            extra={"tenant_id": tenant_id, "request_id": request_id, "error": str(exc)},
        )
        return classification


def _detect_issues(question: str, classification: Dict[str, Any]) -> List[str]:
    """Lightweight heuristics to trigger repair for known problem patterns."""
    q = (question or "").lower()
    issues: List[str] = []

    subject = classification.get("subject", "")
    measure = classification.get("measure", "")
    dimension_data = classification.get("dimension")
    dimension = dimension_data if isinstance(dimension_data, dict) else {}
    time_data = classification.get("time")
    time = time_data if isinstance(time_data, dict) else {}

    # Dimension cues
    if ("active" in q or "inactive" in q) and "status" not in dimension:
        issues.append("missing_status_dimension_for_active_inactive")
    channel_cues = ["online", "offline", "email", "web", "mobile"]
    if any(tok in q for tok in channel_cues) and "channel" not in dimension:
        issues.append("missing_channel_dimension_for_channel_cue")

    # Time cues
    if ("year to date" in q or "ytd" in q) and "window" not in time:
        issues.append("ytd_should_use_window_token")

    # Subject/measure family constraints
    customers_metrics = {"customer_count", "churn_rate", "ltv", "nps", "cac", "arpu"}
    orders_metrics = {"order_count", "aov", "return_rate"}
    if measure in customers_metrics and subject != "customers":
        issues.append("customers_metric_requires_customers_subject")
    if measure in orders_metrics and subject != "orders":
        issues.append("orders_metric_requires_orders_subject")

    return issues
