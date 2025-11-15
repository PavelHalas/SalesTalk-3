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

# Add src to path for Phase 0 modules
_src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

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
            """Build classification prompt for Bedrock (improved separation of subject vs measure + clearer intents and new dimensions)."""
            return f"""You are a strict business-intelligence classifier. Produce ONLY a JSON object.

Question: {question}

1) intent: choose ONE from [what, why, compare, trend, forecast, rank, breakdown, target, correlation, anomaly]
    Intent cues (default to what unless explicit cues for others):
    - what: what|how many|how much|show|list (no words about trend/next/forecast)
    - compare: vs|versus|compare|than
    - breakdown: by <dimension> (by region/segment/product/channel/status/product line)
    - rank: top|bottom|best|worst|highest|lowest|top N|bottom N
    - trend: trend|trending|increase|decrease|over time (must mention trend/time behavior)
    - anomaly: spike|drop|outlier|unusual|sudden
    - target: on track|target|goal|hit|miss|ahead|behind
    - forecast: will|projected|expected next|next quarter/month/year (future terms required)
    - correlation: correlate|correlation|impact|affect|related to

2) subject: the BUSINESS ENTITY (lowercase, singular). MUST be one of:
    [revenue, margin, profit, customers, orders, sales, marketing, products, regions, segments, reps, productLines, timePeriods]
    - Never put a METRIC name here.
    - If the question explicitly mentions an entity (e.g., customers/orders/marketing), USE THAT as subject even if the metric belongs to another family (e.g., MRR for active customers → subject=customers).
    - If the measure is from the customers set (e.g., churn_rate, ltv, cac, nps, arpu), subject MUST be customers.
    - If the measure is from the marketing set (e.g., conversion_rate, signup_count, lead_count), subject is typically marketing.
    - If the measure is from the orders set (e.g., aov, order_count, return_rate), subject MUST be orders.

3) measure: the SPECIFIC METRIC (lowercase, snake_case). Use canonical names:
    revenue: [revenue, mrr, arr, gm, gm_pct, gross_profit]
    customers: [customer_count, churn_rate, ltv, nps, cac, arpu]
    orders: [order_count, aov, return_rate]
    sales: [pipeline_value, win_rate, deal_count]
    marketing: [conversion_rate, signup_count, lead_count]
    aliases → canonical: gross_margin→gm, margin_pct→gm_pct, refund_rate→return_rate, nps_score→nps,
                             pipeline→pipeline_value, signups→signup_count, orders_count→order_count,
                             average_revenue_per_user→arpu, gross_profit_margin→gm

4) dimension: include filters/breakdowns ONLY if explicit words like by/for/in or known values appear.
        MUST map common adjectives to keys:
            - active/inactive → {{"status":"active|inactive"}}
            - online/offline/email/web/mobile → {{"channel":"online|offline|email|web|mobile"}}
    For correlation intent, include the other metric as {{"related_metric":"<metric>"}} when stated (e.g., "correlate with ad spend").
    For product lines, use {{"productLine":"Software|Hardware|Services|Platform"}}.
    For weekday/weekend comparisons, use {{"timeOfWeek":"weekday|weekend"}}.
        Examples: {{"segment":"Enterprise"}}, {{"region":"EMEA"}}, {{"channel":"email"}}, {{"status":"active"}}, {{"limit":5,"direction":"top"}}

5) time: ALWAYS include BOTH period and granularity if any time is mentioned. Use these CANONICAL tokens:
    period: [today, yesterday, this_week, last_week, this_month, last_month, this_quarter, last_quarter, this_year, last_year, Q1, Q2, Q3, Q4]
    window: [ytd, qtd, mtd, l3m, l6m, l12m]  (use when phrases like "year-to-date", "YTD", "last 12 months" appear)
    granularity: [day, week, month, quarter, year]
    examples: {{"period":"Q3","granularity":"quarter"}}, {{"period":"last_month","granularity":"month"}}, {{"period":"this_quarter","granularity":"quarter"}}, {{"window":"ytd","granularity":"month"}}, {{"window":"l12m","granularity":"month"}}, {{"window":"l6m","granularity":"month"}}, {{"window":"l8q","granularity":"quarter"}}
    Do NOT output free text like "this month"; always use snake_case canonical tokens.

Disambiguation (RIGHT vs WRONG):
 - RIGHT: subject=marketing, measure=conversion_rate   | WRONG: subject=conversion_rate
 - RIGHT: subject=customers, measure=churn_rate        | WRONG: subject=churn_rate
 - RIGHT: subject=sales,     measure=pipeline_value    | WRONG: subject=pipeline_value
 - RIGHT: subject=orders,    measure=aov               | WRONG: subject=aov
 - RIGHT: subject=revenue,   measure=mrr/arr/revenue   | WRONG: subject=mrr/arr
 - RIGHT: subject=revenue,   measure=revenue (generic "revenue" asked) | WRONG: measure=mrr/arr when not asked
 - RIGHT: subject=customers, measure=arpu              | WRONG: subject=revenue, measure=arpu
 - RIGHT: subject=profit,    measure=gross_profit      | WRONG: subject=margin,  measure=gross_margin
 - RIGHT: include dimension channel/status when words like online/email/active appear | WRONG: missing dimension
 - RIGHT: "How many active customers" → dimension={{"status":"active"}}
 - RIGHT: "online sales" → dimension={{"channel":"online"}}
 - RIGHT: "year to date" → time={{"window":"ytd","granularity":"month"}}
 - RIGHT: "last 6 months" → time={{"window":"l6m","granularity":"month"}}
 - RIGHT: "over last 8 quarters" → time={{"window":"l8q","granularity":"quarter"}}
 - RIGHT: "correlate conversion rate with ad spend" → intent=correlation, dimension={{"related_metric":"ad_spend"}}
 - RIGHT: "compare by product line" → intent=breakdown, dimension may include breakdown fields but JSON stays in the fixed schema

ALWAYS include ALL keys below (even if dimension/time are empty). Return ONLY this JSON structure (no prose):
{{
  "intent": "<one>",
  "subject": "<entity>",
  "measure": "<metric>",
  "dimension": {{}} ,
  "time": {{}} ,
  "confidence": {{
     "overall": 0.9,
     "components": {{"intent": 0.9, "subject": 0.9, "measure": 0.9, "time": 0.8, "dimension": 0.8}}
  }},
  "refused": false,
  "refusal_reason": null
}}"""

    def _build_repair_prompt(self, question: str, current: Dict[str, Any], issues: List[str]) -> str:
        """Build a focused repair prompt that updates only the JSON to satisfy constraints.

        TRM-inspired: iteratively improve answer y given constraints and detected issues.
        """
        return (
            "You produced the following JSON classification, but it has issues to fix.\n"
            "Fix ONLY the JSON to satisfy the constraints and detected issues. Do not add prose.\n\n"
            f"Question: {question}\n\n"
            f"Current JSON: {json.dumps(current, ensure_ascii=False)}\n\n"
            "Constraints (must all be satisfied):\n"
            "- subject must be a business entity (not a metric) from: [revenue, margin, profit, customers, orders, sales, marketing, products, regions, segments, reps, productLines, timePeriods].\n"
            "- If measure in customers set [customer_count, churn_rate, ltv, nps, cac, arpu], subject MUST be customers.\n"
            "- If measure in orders set [order_count, aov, return_rate], subject MUST be orders.\n"
            "- Map adjectives to dimensions: active/inactive -> {\"status\":\"active|inactive\"}; online/offline/email/web/mobile -> {\"channel\":\"online|offline|email|web|mobile\"}.\n"
            "- If phrase 'year to date' or 'ytd' appears, time.window MUST be 'ytd' with granularity 'month'.\n"
            "- Time tokens must be canonical as defined previously.\n\n"
            f"Detected issues: {json.dumps(issues, ensure_ascii=False)}\n\n"
            "Return ONLY the corrected JSON object."
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
        """Build classification prompt for Ollama (clearer intents + new dimensions)."""
        return f"""You are a strict business-intelligence classifier. Produce ONLY a JSON object.

Question: {question}

1) intent: choose ONE from [what, why, compare, trend, forecast, rank, breakdown, target, correlation, anomaly]
    Intent cues (default to what unless explicit cues for others):
    - what: what|how many|how much|show|list (no words about trend/next/forecast)
    - compare: vs|versus|compare|than
    - breakdown: by <dimension> (by region/segment/product/channel/status/product line)
    - rank: top|bottom|best|worst|highest|lowest|top N|bottom N
    - trend: trend|trending|increase|decrease|over time (must mention trend/time behavior)
    - anomaly: spike|drop|outlier|unusual|sudden
    - target: on track|target|goal|hit|miss|ahead|behind
    - forecast: will|projected|expected next|next quarter/month/year (future terms required)
    - correlation: correlate|correlation|impact|affect|related to

2) subject: the BUSINESS ENTITY (lowercase, singular). MUST be one of:
    [revenue, margin, profit, customers, orders, sales, marketing, products, regions, segments, reps, productLines, timePeriods]
    - Never put a METRIC name here.
    - If the question explicitly mentions an entity (e.g., customers/orders/marketing), USE THAT as subject even if the metric belongs to another family (e.g., MRR for active customers → subject=customers).
    - If the measure is from the customers set (e.g., churn_rate, ltv, cac, nps, arpu), subject MUST be customers.
    - If the measure is from the marketing set (e.g., conversion_rate, signup_count, lead_count), subject is typically marketing.
    - If the measure is from the orders set (e.g., aov, order_count, return_rate), subject MUST be orders.

3) measure: the SPECIFIC METRIC (lowercase, snake_case). Use canonical names:
    revenue: [revenue, mrr, arr, gm, gm_pct, gross_profit]
    customers: [customer_count, churn_rate, ltv, nps, cac, arpu]
    orders: [order_count, aov, return_rate]
    sales: [pipeline_value, win_rate, deal_count]
    marketing: [conversion_rate, signup_count, lead_count]
    aliases → canonical: gross_margin→gm, margin_pct→gm_pct, refund_rate→return_rate, nps_score→nps,
                             pipeline→pipeline_value, signups→signup_count, orders_count→order_count,
                             average_revenue_per_user→arpu, gross_profit_margin→gm

4) dimension: include filters/breakdowns ONLY if explicit words like by/for/in or known values appear.
        MUST map common adjectives to keys:
            - active/inactive → {{"status":"active|inactive"}}
            - online/offline/email/web/mobile → {{"channel":"online|offline|email|web|mobile"}}
    For correlation intent, include the other metric as {{"related_metric":"<metric>"}} when stated (e.g., "correlate with ad spend").
    For product lines, use {{"productLine":"Software|Hardware|Services|Platform"}}.
    For weekday/weekend comparisons, use {{"timeOfWeek":"weekday|weekend"}}.
        Examples: {{"segment":"Enterprise"}}, {{"region":"EMEA"}}, {{"channel":"email"}}, {{"status":"active"}}, {{"limit":5,"direction":"top"}}

5) time: ALWAYS include BOTH period and granularity if any time is mentioned. Use these CANONICAL tokens:
    period: [today, yesterday, this_week, last_week, this_month, last_month, this_quarter, last_quarter, this_year, last_year, Q1, Q2, Q3, Q4]
    window: [ytd, qtd, mtd, l3m, l6m, l12m]  (use when phrases like "year-to-date", "YTD", "last 12 months" appear)
    granularity: [day, week, month, quarter, year]
    examples: {{"period":"Q3","granularity":"quarter"}}, {{"period":"last_month","granularity":"month"}}, {{"period":"this_quarter","granularity":"quarter"}}, {{"window":"ytd","granularity":"month"}}, {{"window":"l12m","granularity":"month"}}, {{"window":"l6m","granularity":"month"}}, {{"window":"l8q","granularity":"quarter"}}
    Do NOT output free text like "this month"; always use snake_case canonical tokens.

Disambiguation (RIGHT vs WRONG):
 - RIGHT: subject=marketing, measure=conversion_rate   | WRONG: subject=conversion_rate
 - RIGHT: subject=customers, measure=churn_rate        | WRONG: subject=churn_rate
 - RIGHT: subject=sales,     measure=pipeline_value    | WRONG: subject=pipeline_value
 - RIGHT: subject=orders,    measure=aov               | WRONG: subject=aov
 - RIGHT: subject=revenue,   measure=mrr/arr/revenue   | WRONG: subject=mrr/arr
 - RIGHT: subject=customers, measure=arpu              | WRONG: subject=revenue, measure=arpu
 - RIGHT: subject=profit,    measure=gross_profit      | WRONG: subject=margin,  measure=gross_margin
 - RIGHT: include dimension channel/status when words like online/email/active appear | WRONG: missing dimension
 - RIGHT: "How many active customers" → dimension={{"status":"active"}}
 - RIGHT: "online sales" → dimension={{"channel":"online"}}
 - RIGHT: "year to date" → time={{"window":"ytd","granularity":"month"}}
 - RIGHT: "last 6 months" → time={{"window":"l6m","granularity":"month"}}
 - RIGHT: "over last 8 quarters" → time={{"window":"l8q","granularity":"quarter"}}
 - RIGHT: "correlate conversion rate with ad spend" → intent=correlation, dimension={{"related_metric":"ad_spend"}}
 - RIGHT: "compare by product line" → intent=breakdown, dimension may include breakdown fields but JSON stays in the fixed schema

ALWAYS include ALL keys below (even if dimension/time are empty). Return ONLY this JSON structure (no prose):
{{
  "intent": "<one>",
  "subject": "<entity>",
  "measure": "<metric>",
  "dimension": {{}} ,
  "time": {{}} ,
  "confidence": {{
     "overall": 0.9,
     "components": {{"intent": 0.9, "subject": 0.9, "measure": 0.9, "time": 0.8, "dimension": 0.8}}
  }},
  "refused": false,
  "refusal_reason": null
}}"""

    def _build_repair_prompt(self, question: str, current: Dict[str, Any], issues: List[str]) -> str:
        """Build repair prompt for Ollama (mirrors Bedrock)."""
        return (
            "You produced the following JSON classification, but it has issues to fix.\n"
            "Fix ONLY the JSON to satisfy the constraints and detected issues. Do not add prose.\n\n"
            f"Question: {question}\n\n"
            f"Current JSON: {json.dumps(current, ensure_ascii=False)}\n\n"
            "Constraints (must all be satisfied):\n"
            "- subject must be a business entity (not a metric) from: [revenue, margin, profit, customers, orders, sales, marketing, products, regions, segments, reps, productLines, timePeriods].\n"
            "- If measure in customers set [customer_count, churn_rate, ltv, nps, cac, arpu], subject MUST be customers.\n"
            "- If measure in orders set [order_count, aov, return_rate], subject MUST be orders.\n"
            "- Map adjectives to dimensions: active/inactive -> {\"status\":\"active|inactive\"}; online/offline/email/web/mobile -> {\"channel\":\"online|offline|email|web|mobile\"}.\n"
            "- If phrase 'year to date' or 'ytd' appears, time.window MUST be 'ytd' with granularity 'month'.\n"
            "- Time tokens must be canonical as defined previously.\n\n"
            f"Detected issues: {json.dumps(issues, ensure_ascii=False)}\n\n"
            "Return ONLY the corrected JSON object."
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
        """Build narrative generation prompt."""
        data_str = json.dumps(data_references, indent=2)
        return f"""Generate a clear, concise business narrative based on this data.

Classification: {json.dumps(classification, indent=2)}

Data: {data_str}

Requirements:

Return only the narrative text, nothing else."""
    
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
