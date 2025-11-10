"""
End-to-End Tests with LocalStack and DynamoDB

Comprehensive E2E test suite for local development that:
- Uses LocalStack for DynamoDB simulation
- Seeds test data for multi-tenant scenarios
- Tests complete question-processing pipeline
- Validates classification, narrative, and data retrieval
- Covers edge cases, ambiguity, and multi-dimensional queries
- Supports both mock and real AI providers (Ollama, Bedrock)

Requirements:
    - LocalStack running on localhost:4566
    - DynamoDB tables created and seeded
    - Optional: AI_PROVIDER set to 'ollama' or 'bedrock' for real AI testing

Usage:
    # With mock AI (fast, deterministic)
    pytest tests/e2e/test_localstack_e2e.py -v
    
    # With real AI provider (requires Ollama or Bedrock)
    USE_REAL_AI=true AI_PROVIDER=ollama pytest tests/e2e/test_localstack_e2e.py -v
    
    # Start LocalStack
    docker run -d -p 4566:4566 localstack/localstack
    
    # Seed data
    python scripts/seed_localstack.py
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from classify import lambda_handler as classify_handler
from chat import lambda_handler as chat_handler


# ============================================================================
# Test Configuration
# ============================================================================

LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
AWS_REGION = "us-east-1"
TEST_TENANT_1 = "acme-corp-001"
TEST_TENANT_2 = "techstart-inc-002"

# Control whether to use real AI provider or mocks
# Set USE_REAL_AI=true to test with real Ollama/Bedrock
USE_REAL_AI = os.environ.get("USE_REAL_AI", "false").lower() in ("true", "1", "yes")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def dynamodb_client():
    """Create DynamoDB client for LocalStack."""
    return boto3.client(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture(scope="module")
def dynamodb_resource():
    """Create DynamoDB resource for LocalStack."""
    return boto3.resource(
        "dynamodb",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture(scope="module")
def verify_localstack(dynamodb_client):
    """Verify LocalStack is running and accessible."""
    try:
        dynamodb_client.list_tables()
        return True
    except Exception as e:
        pytest.skip(f"LocalStack not available: {e}")


@pytest.fixture(scope="module")
def verify_tables_seeded(dynamodb_client, verify_localstack):
    """Verify that test tables are seeded with data."""
    required_tables = [
        f"tenant-{TEST_TENANT_1}-metrics",
        f"tenant-{TEST_TENANT_1}-messages",
        f"tenant-{TEST_TENANT_2}-metrics",
        f"tenant-{TEST_TENANT_2}-messages",
    ]
    
    try:
        response = dynamodb_client.list_tables()
        existing_tables = response.get("TableNames", [])
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        if missing_tables:
            pytest.skip(
                f"Required tables not seeded. Missing: {missing_tables}. "
                f"Run: python scripts/seed_localstack.py"
            )
        
        return True
    except Exception as e:
        pytest.skip(f"Failed to verify tables: {e}")


@pytest.fixture(scope="module")
def use_real_ai():
    """
    Determine if tests should use real AI provider or mocks.
    
    Returns:
        bool: True if USE_REAL_AI env var is set, False otherwise
    """
    if USE_REAL_AI:
        # Verify AI provider is configured
        ai_provider = os.environ.get("AI_PROVIDER", "ollama").lower()
        if ai_provider == "ollama":
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            print(f"\n✓ Using real AI: Ollama at {ollama_url}")
        else:
            print(f"\n✓ Using real AI: {ai_provider}")
    else:
        print("\n✓ Using mock AI for fast, deterministic tests")
    
    return USE_REAL_AI


@pytest.fixture
def mock_ai_adapter():
    """Create a mock AI adapter for deterministic testing."""
    def create_classification(
        intent: str,
        subject: str,
        measure: str,
        dimension: Dict = None,
        time: Dict = None,
        confidence_overall: float = 0.90,
        refused: bool = False,
        refusal_reason: str = None
    ) -> Dict[str, Any]:
        """Helper to create classification response."""
        return {
            "intent": intent,
            "subject": subject,
            "measure": measure,
            "dimension": dimension or {},
            "time": time or {},
            "confidence": {
                "overall": confidence_overall,
                "components": {
                    "intent": min(0.95, confidence_overall + 0.05),
                    "subject": confidence_overall,
                    "measure": confidence_overall - 0.02,
                    "time": confidence_overall + 0.02,
                    "dimension": confidence_overall - 0.05
                }
            },
            "refused": refused,
            "refusal_reason": refusal_reason
        }
    
    def create_narrative(
        text: str,
        data_references: List[Dict] = None,
        model: str = "test-model"
    ) -> Dict[str, Any]:
        """Helper to create narrative response."""
        return {
            "text": text,
            "dataReferences": data_references or [],
            "metadata": {
                "model": model,
                "provider": "test"
            }
        }
    
    return {
        "create_classification": create_classification,
        "create_narrative": create_narrative,
    }


def create_api_event(
    question_or_message: str,
    tenant_id: str,
    endpoint: str = "classify",
    session_id: str = None
) -> Dict[str, Any]:
    """
    Create API Gateway event for testing.
    
    Args:
        question_or_message: The question or message text
        tenant_id: Tenant ID for JWT claims
        endpoint: 'classify' or 'chat'
        session_id: Optional session ID for chat
        
    Returns:
        API Gateway event dict
    """
    body_key = "question" if endpoint == "classify" else "message"
    body = {body_key: question_or_message}
    
    if session_id and endpoint == "chat":
        body["sessionId"] = session_id
    
    return {
        "body": json.dumps(body),
        "requestContext": {
            "requestId": f"test-request-{int(time.time() * 1000)}",
            "authorizer": {
                "claims": {
                    "custom:tenant_id": tenant_id
                }
            }
        }
    }


def setup_mock_if_needed(use_real_ai: bool, mock_get_adapter, mock_ai_adapter, 
                        expected_response: Dict[str, Any], endpoint: str = "classify"):
    """
    Setup mock adapter if not using real AI.
    
    Args:
        use_real_ai: Whether to use real AI provider
        mock_get_adapter: Mock for get_adapter function
        mock_ai_adapter: Mock AI adapter fixture
        expected_response: Expected classification or narrative response
        endpoint: 'classify' or 'chat'
        
    Returns:
        Mock adapter if mocking is needed, None otherwise
    """
    if use_real_ai:
        # Don't mock - let real AI provider be used
        mock_get_adapter.stop()
        return None
    
    # Setup mock adapter
    mock_adapter = Mock()
    if endpoint == "classify":
        mock_adapter.classify.return_value = expected_response
    else:  # chat endpoint uses both classify and generate_narrative
        if "intent" in expected_response:
            mock_adapter.classify.return_value = expected_response
        if "text" in expected_response:
            mock_adapter.generate_narrative.return_value = expected_response
    
    mock_get_adapter.return_value = mock_adapter
    return mock_adapter


def validate_classification_response(
    classification: Dict[str, Any],
    expected_intent: Optional[str] = None,
    expected_subject: Optional[str] = None,
    expected_measure: Optional[str] = None,
    check_confidence: bool = True
):
    """
    Validate classification response with flexible assertions.
    
    Works with both mock and real AI responses.
    Real AI responses may vary, so we validate structure and ranges
    rather than exact values when expected values are not provided.
    
    Args:
        classification: Classification response to validate
        expected_intent: Expected intent (optional for real AI)
        expected_subject: Expected subject (optional for real AI)
        expected_measure: Expected measure (optional for real AI)
        check_confidence: Whether to validate confidence scores
    """
    # Required fields must be present
    assert "intent" in classification, "Missing 'intent' field"
    assert "subject" in classification, "Missing 'subject' field"
    assert "measure" in classification, "Missing 'measure' field"
    assert "confidence" in classification, "Missing 'confidence' field"
    
    # Validate against expected values if provided (for mock tests)
    if expected_intent:
        assert classification["intent"] == expected_intent, \
            f"Intent mismatch: expected '{expected_intent}', got '{classification['intent']}'"
    
    if expected_subject:
        assert classification["subject"] == expected_subject, \
            f"Subject mismatch: expected '{expected_subject}', got '{classification['subject']}'"
    
    if expected_measure:
        assert classification["measure"] == expected_measure, \
            f"Measure mismatch: expected '{expected_measure}', got '{classification['measure']}'"
    
    # Validate confidence scores
    if check_confidence:
        confidence = classification["confidence"]
        assert "overall" in confidence, "Missing overall confidence"
        assert 0.0 <= confidence["overall"] <= 1.0, \
            f"Overall confidence out of range: {confidence['overall']}"
        
        if "components" in confidence:
            for component, value in confidence["components"].items():
                assert 0.0 <= value <= 1.0, \
                    f"Component {component} confidence out of range: {value}"


# ============================================================================
# Test Suite: Basic "What" Questions
# ============================================================================

@pytest.mark.e2e
class TestBasicWhatQuestions:
    """Test basic 'what' intent questions with single metrics."""
    
    @patch("classify.get_adapter")
    def test_what_is_q3_revenue(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        use_real_ai,
        verify_tables_seeded
    ):
        """Test: What is our Q3 revenue?"""
        # Setup mock only if not using real AI
        if not use_real_ai:
            expected = mock_ai_adapter["create_classification"](
                intent="what",
                subject="revenue",
                measure="revenue",
                time={"period": "Q3", "granularity": "quarter"}
            )
            setup_mock_if_needed(use_real_ai, mock_get_adapter, mock_ai_adapter, 
                                expected, endpoint="classify")
        
        # Execute
        event = create_api_event("What is our Q3 revenue?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        # Validate classification with flexible assertions
        classification = body["classification"]
        if not use_real_ai:
            # Strict validation for mock responses
            validate_classification_response(
                classification,
                expected_intent="what",
                expected_subject="revenue",
                expected_measure="revenue"
            )
            assert classification["time"]["period"] == "Q3"
            assert classification["time"]["granularity"] == "quarter"
        else:
            # Flexible validation for real AI responses
            validate_classification_response(classification)
            # Just verify it recognized revenue-related intent
            assert classification["subject"] in ["revenue", "sales", "income"]
        
        assert body["tenantId"] == TEST_TENANT_1
    
    @patch("classify.get_adapter")
    def test_what_is_gross_margin_this_quarter(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        use_real_ai,
        verify_tables_seeded
    ):
        """Test: What's our gross margin percentage this quarter?"""
        if not use_real_ai:
            expected = mock_ai_adapter["create_classification"](
                intent="what",
                subject="margin",
                measure="gm_pct",
                time={"period": "this_quarter", "granularity": "quarter"}
            )
            setup_mock_if_needed(use_real_ai, mock_get_adapter, mock_ai_adapter,
                                expected, endpoint="classify")
        
        event = create_api_event("What's our gross margin percentage this quarter?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        if not use_real_ai:
            validate_classification_response(
                classification,
                expected_intent="what",
                expected_subject="margin",
                expected_measure="gm_pct"
            )
        else:
            validate_classification_response(classification)
            assert classification["subject"] in ["margin", "profitability", "profit"]
    
    @patch("classify.get_adapter")
    def test_what_is_customer_count(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        use_real_ai,
        verify_tables_seeded
    ):
        """Test: How many active customers do we have?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="customers",
            measure="customer_count",
            dimension={"status": "active"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("How many active customers do we have?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "what"
        assert classification["subject"] == "customers"
        assert classification["measure"] == "customer_count"


# ============================================================================
# Test Suite: Comparative Questions
# ============================================================================

@pytest.mark.e2e
class TestComparativeQuestions:
    """Test comparative 'compare' intent questions."""
    
    @patch("classify.get_adapter")
    def test_compare_emea_vs_apac_revenue(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: How does EMEA revenue compare to APAC?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="compare",
            subject="revenue",
            measure="revenue",
            dimension={"region": ["EMEA", "APAC"]},
            time={"period": "current", "granularity": "quarter"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("How does EMEA revenue compare to APAC?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "compare"
        assert classification["subject"] == "revenue"
        assert "region" in classification["dimension"]
        assert "EMEA" in classification["dimension"]["region"]
        assert "APAC" in classification["dimension"]["region"]
    
    @patch("classify.get_adapter")
    def test_compare_q3_vs_q4_margin(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Compare Q3 margin to Q4 margin"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="compare",
            subject="margin",
            measure="margin",
            time={
                "periods": ["Q3", "Q4"],
                "granularity": "quarter",
                "comparison": "sequential"
            }
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Compare Q3 margin to Q4 margin", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "compare"
        assert classification["subject"] == "margin"


# ============================================================================
# Test Suite: Causal "Why" Questions
# ============================================================================

@pytest.mark.e2e
class TestCausalWhyQuestions:
    """Test causal 'why' intent questions."""
    
    @patch("classify.get_adapter")
    def test_why_did_churn_increase(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Why did customer churn increase last month?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="why",
            subject="customers",
            measure="churn_rate",
            time={
                "period": "last_month",
                "comparison": "mom",
                "granularity": "month"
            }
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Why did customer churn increase last month?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "why"
        assert classification["subject"] == "customers"
        assert classification["measure"] == "churn_rate"
        assert "last_month" in classification["time"]["period"]
    
    @patch("classify.get_adapter")
    def test_why_is_margin_down_in_emea(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Why is margin down in EMEA?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="why",
            subject="margin",
            measure="margin",
            dimension={"region": "EMEA"},
            time={"period": "current", "granularity": "quarter"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Why is margin down in EMEA?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "why"
        assert classification["subject"] == "margin"
        assert classification["dimension"]["region"] == "EMEA"


# ============================================================================
# Test Suite: Trend Analysis Questions
# ============================================================================

@pytest.mark.e2e
class TestTrendAnalysisQuestions:
    """Test trend analysis intent questions."""
    
    @patch("classify.get_adapter")
    def test_revenue_trend_last_12_months(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Show me revenue trending over the last 12 months"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="trend",
            subject="revenue",
            measure="revenue",
            time={"window": "l12m", "granularity": "month"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Show me revenue trending over the last 12 months", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "trend"
        assert classification["subject"] == "revenue"
        assert "l12m" in classification["time"]["window"]
    
    @patch("classify.get_adapter")
    def test_margin_trend_quarterly(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: What is the quarterly margin trend this year?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="trend",
            subject="margin",
            measure="margin",
            time={"window": "ytd", "granularity": "quarter"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is the quarterly margin trend this year?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "trend"
        assert classification["subject"] == "margin"


# ============================================================================
# Test Suite: Ranking Questions
# ============================================================================

@pytest.mark.e2e
class TestRankingQuestions:
    """Test ranking intent questions."""
    
    @patch("classify.get_adapter")
    def test_top_5_products_by_revenue(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Top 5 products by revenue"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="rank",
            subject="products",
            measure="revenue",
            dimension={"limit": 5, "direction": "top"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Top 5 products by revenue", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "rank"
        assert classification["subject"] == "products"
        assert classification["measure"] == "revenue"
        assert classification["dimension"]["limit"] == 5
    
    @patch("classify.get_adapter")
    def test_worst_performing_regions(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Which regions are performing worst?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="rank",
            subject="regions",
            measure="performance",
            dimension={"direction": "bottom"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Which regions are performing worst?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "rank"
        assert classification["subject"] == "regions"


# ============================================================================
# Test Suite: Multi-Dimensional Queries
# ============================================================================

@pytest.mark.e2e
class TestMultiDimensionalQueries:
    """Test queries with multiple dimensions."""
    
    @patch("classify.get_adapter")
    def test_enterprise_revenue_north_america_q3(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: What is enterprise revenue in North America for Q3?"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            dimension={
                "segment": "Enterprise",
                "region": "North America"
            },
            time={"period": "Q3", "granularity": "quarter"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event(
            "What is enterprise revenue in North America for Q3?",
            TEST_TENANT_1
        )
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "what"
        assert classification["dimension"]["segment"] == "Enterprise"
        assert classification["dimension"]["region"] == "North America"
        assert classification["time"]["period"] == "Q3"
    
    @patch("classify.get_adapter")
    def test_product_line_margin_by_region(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: Show me margin by product line and region"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="breakdown",
            subject="margin",
            measure="margin",
            dimension={
                "breakdown_by": ["productLine", "region"]
            }
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("Show me margin by product line and region", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert "breakdown_by" in classification["dimension"]
        assert "productLine" in classification["dimension"]["breakdown_by"]
        assert "region" in classification["dimension"]["breakdown_by"]


# ============================================================================
# Test Suite: Edge Cases and Ambiguity
# ============================================================================

@pytest.mark.e2e
class TestEdgeCasesAndAmbiguity:
    """Test edge cases and ambiguous queries."""
    
    @patch("classify.get_adapter")
    def test_ambiguous_time_last_quarter(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: What was revenue last quarter? (ambiguous time reference)"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={
                "period": "last_quarter",
                "relative": True,
                "granularity": "quarter"
            },
            confidence_overall=0.75  # Lower confidence for ambiguous time
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What was revenue last quarter?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "what"
        assert "last_quarter" in classification["time"]["period"]
        # Should have lower confidence for ambiguous time
        assert classification["confidence"]["overall"] < 0.85
    
    @patch("classify.get_adapter")
    def test_incomplete_question_missing_time(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: What is our revenue? (missing time period)"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={},  # Empty time
            confidence_overall=0.70  # Lower confidence for missing time
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is our revenue?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        assert classification["intent"] == "what"
        assert classification["subject"] == "revenue"
        # Should indicate missing time information
        assert classification["time"] == {} or "period" not in classification["time"]
    
    @patch("classify.get_adapter")
    def test_ambiguous_subject_growth(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test: What is our growth? (ambiguous - revenue? margin? customers?)"""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="growth",  # Ambiguous
            measure="growth_rate",
            time={"period": "current"},
            confidence_overall=0.65  # Low confidence for ambiguous subject
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is our growth?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        classification = body["classification"]
        # Should have low confidence for ambiguous subject
        assert classification["confidence"]["overall"] < 0.75


# ============================================================================
# Test Suite: Multi-Tenant Isolation
# ============================================================================

@pytest.mark.e2e
class TestMultiTenantIsolation:
    """Test tenant isolation and data segregation."""
    
    @patch("classify.get_adapter")
    def test_tenant_1_classification(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test classification for tenant 1."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is Q3 revenue?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["tenantId"] == TEST_TENANT_1
    
    @patch("classify.get_adapter")
    def test_tenant_2_classification(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test classification for tenant 2."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is Q3 revenue?", TEST_TENANT_2)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["tenantId"] == TEST_TENANT_2
        assert body["tenantId"] != TEST_TENANT_1
    
    @patch("chat.get_adapter")
    def test_data_references_include_tenant_table(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test that data references include tenant-specific table names."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3"}
        )
        mock_adapter.generate_narrative.return_value = mock_ai_adapter["create_narrative"](
            text="Q3 revenue was $2.5M.",
            data_references=[
                {
                    "metric": "revenue",
                    "period": "Q3",
                    "value": 2500000,
                    "unit": "USD",
                    "source": {
                        "table": f"tenant-{TEST_TENANT_1}-metrics",
                        "pk": "METRIC#revenue",
                        "sk": "Q3"
                    }
                }
            ]
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is Q3 revenue?", TEST_TENANT_1, endpoint="chat")
        response = chat_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        # Verify data references include tenant-specific table
        assert len(body["dataReferences"]) > 0
        ref = body["dataReferences"][0]
        assert TEST_TENANT_1 in ref["source"]["table"]


# ============================================================================
# Test Suite: End-to-End Chat Flow
# ============================================================================

@pytest.mark.e2e
class TestEndToEndChatFlow:
    """Test complete chat flow from question to narrative."""
    
    @patch("chat.get_adapter")
    def test_complete_chat_flow_with_narrative(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test complete flow: question -> classification -> data -> narrative."""
        mock_adapter = Mock()
        
        # Mock classification
        classification = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3", "granularity": "quarter"}
        )
        mock_adapter.classify.return_value = classification
        
        # Mock narrative
        narrative = mock_ai_adapter["create_narrative"](
            text="Q3 2025 revenue was $2.5M, up 15% from Q2 2025 ($2.17M). "
                 "Growth driven by Enterprise segment in North America.",
            data_references=[
                {
                    "metric": "revenue",
                    "period": "Q3",
                    "value": 2500000,
                    "unit": "USD",
                    "source": {
                        "table": f"tenant-{TEST_TENANT_1}-metrics",
                        "pk": "METRIC#revenue",
                        "sk": "Q3"
                    }
                }
            ]
        )
        mock_adapter.generate_narrative.return_value = narrative
        mock_get_adapter.return_value = mock_adapter
        
        # Execute
        event = create_api_event("What is our Q3 revenue?", TEST_TENANT_1, endpoint="chat")
        response = chat_handler(event, None)
        
        # Assert response structure
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        # Verify all required fields
        assert "response" in body
        assert "classification" in body
        assert "dataReferences" in body
        assert "sessionId" in body
        assert "requestId" in body
        assert "metadata" in body
        
        # Verify classification
        assert body["classification"]["intent"] == "what"
        assert body["classification"]["subject"] == "revenue"
        
        # Verify narrative
        assert "$2.5M" in body["response"]
        assert "15%" in body["response"]
        
        # Verify data references
        assert len(body["dataReferences"]) > 0
        ref = body["dataReferences"][0]
        assert ref["metric"] == "revenue"
        assert ref["value"] == 2500000
        assert "source" in ref
        assert TEST_TENANT_1 in ref["source"]["table"]
        
        # Verify metadata
        assert "latencyMs" in body["metadata"]
        assert body["metadata"]["latencyMs"] >= 0
    
    @patch("chat.get_adapter")
    def test_chat_with_session_continuity(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test chat maintains session continuity across requests."""
        session_id = "test-session-123"
        
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3"}
        )
        mock_adapter.generate_narrative.return_value = mock_ai_adapter["create_narrative"](
            text="Q3 revenue was $2.5M."
        )
        mock_get_adapter.return_value = mock_adapter
        
        # First request with session ID
        event1 = create_api_event(
            "What is Q3 revenue?",
            TEST_TENANT_1,
            endpoint="chat",
            session_id=session_id
        )
        response1 = chat_handler(event1, None)
        body1 = json.loads(response1["body"])
        
        assert body1["sessionId"] == session_id
        
        # Second request with same session ID
        event2 = create_api_event(
            "What about Q4?",
            TEST_TENANT_1,
            endpoint="chat",
            session_id=session_id
        )
        response2 = chat_handler(event2, None)
        body2 = json.loads(response2["body"])
        
        # Session ID should be maintained
        assert body2["sessionId"] == session_id
        assert body2["sessionId"] == body1["sessionId"]


# ============================================================================
# Test Suite: Confidence and Quality Metrics
# ============================================================================

@pytest.mark.e2e
class TestConfidenceAndQuality:
    """Test confidence scores and quality metrics."""
    
    @patch("classify.get_adapter")
    def test_confidence_components_all_present(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test that all confidence components are present and valid."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3"}
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is Q3 revenue?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        body = json.loads(response["body"])
        confidence = body["classification"]["confidence"]
        
        # Verify overall confidence
        assert "overall" in confidence
        assert 0.0 <= confidence["overall"] <= 1.0
        
        # Verify component confidences
        assert "components" in confidence
        required_components = ["intent", "subject", "measure", "time", "dimension"]
        
        for component in required_components:
            assert component in confidence["components"]
            value = confidence["components"][component]
            assert 0.0 <= value <= 1.0, f"Component {component} out of range: {value}"
    
    @patch("classify.get_adapter")
    def test_high_confidence_for_clear_question(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test high confidence for clear, unambiguous questions."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="revenue",
            measure="revenue",
            time={"period": "Q3", "granularity": "quarter"},
            confidence_overall=0.95
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is our Q3 2025 revenue?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        body = json.loads(response["body"])
        assert body["classification"]["confidence"]["overall"] >= 0.90
    
    @patch("classify.get_adapter")
    def test_lower_confidence_for_ambiguous_question(
        self,
        mock_get_adapter,
        mock_ai_adapter,
        verify_tables_seeded
    ):
        """Test lower confidence for ambiguous questions."""
        mock_adapter = Mock()
        mock_adapter.classify.return_value = mock_ai_adapter["create_classification"](
            intent="what",
            subject="performance",  # Ambiguous
            measure="performance",
            time={},  # Missing time
            confidence_overall=0.60
        )
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("How are we doing?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        body = json.loads(response["body"])
        # Ambiguous questions should have lower confidence
        assert body["classification"]["confidence"]["overall"] < 0.75


# ============================================================================
# Test Suite: Error Handling and Robustness
# ============================================================================

@pytest.mark.e2e
class TestErrorHandlingAndRobustness:
    """Test error handling and system robustness."""
    
    def test_missing_tenant_id_returns_400(self):
        """Test that missing tenant ID returns 400 error."""
        event = {
            "body": json.dumps({"question": "What is revenue?"}),
            "requestContext": {
                "requestId": "test-request",
                "authorizer": {
                    "claims": {}  # Missing tenant_id
                }
            }
        }
        
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "Validation" in body["error"] or "Invalid" in body.get("message", "")
    
    def test_empty_question_returns_400(self):
        """Test that empty question returns 400 error."""
        event = create_api_event("", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
    
    def test_extremely_long_question_returns_400(self):
        """Test that overly long question returns 400 error."""
        long_question = "A" * 10001  # Exceeds 10,000 char limit
        event = create_api_event(long_question, TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
    
    @patch("classify.get_adapter")
    def test_ai_provider_error_returns_502(self, mock_get_adapter):
        """Test that AI provider errors return 502."""
        from ai_adapter import AIProviderError
        
        mock_adapter = Mock()
        mock_adapter.classify.side_effect = AIProviderError("AI service unavailable")
        mock_get_adapter.return_value = mock_adapter
        
        event = create_api_event("What is revenue?", TEST_TENANT_1)
        response = classify_handler(event, None)
        
        assert response["statusCode"] == 502
        body = json.loads(response["body"])
        assert "error" in body
