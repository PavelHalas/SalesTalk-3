"""
Chat Lambda Handler

AWS Lambda function that handles chat interactions with streaming responses.

Features:
- Tenant isolation via JWT claims
- Streaming response scaffolding
- Integration with classification and narrative generation
- Structured logging with tenant + requestId
- Session management
- Error handling
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, Generator, Optional
import time

from ai_adapter import get_adapter, AIProvider, AIProviderError, ValidationError

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_tenant_id(event: Dict[str, Any]) -> str:
    """
    Extract tenant ID from JWT claims in API Gateway event.
    
    Args:
        event: API Gateway event dict
        
    Returns:
        Tenant ID string
        
    Raises:
        ValueError: If tenant ID cannot be extracted
    """
    try:
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        claims = authorizer.get("claims", {})
        tenant_id = claims.get("custom:tenant_id") or claims.get("tenantId")
        
        if not tenant_id:
            raise ValueError("Tenant ID not found in JWT claims")
        
        return tenant_id
    except Exception as e:
        logger.error("Failed to extract tenant ID", exc_info=True)
        raise ValueError(f"Invalid authentication: {e}")


def validate_request(body: Dict[str, Any]) -> None:
    """
    Validate chat request body.
    
    Args:
        body: Request body dict
        
    Raises:
        ValueError: If validation fails
    """
    if not body:
        raise ValueError("Request body is required")
    
    message = body.get("message")
    if not message:
        raise ValueError("message field is required")
    
    if not isinstance(message, str):
        raise ValueError("message must be a string")
    
    if len(message) > 10000:
        raise ValueError("message exceeds maximum length of 10,000 characters")
    
    if not message.strip():
        raise ValueError("message cannot be empty")
    
    # Validate optional sessionId
    session_id = body.get("sessionId")
    if session_id and not isinstance(session_id, str):
        raise ValueError("sessionId must be a string")


def fetch_data_stub(
    classification: Dict[str, Any],
    tenant_id: str
) -> list:
    """
    Stub function for data retrieval.
    
    In production, this would query DynamoDB for actual metrics.
    For Phase 5, returns mock data for testing.
    
    Args:
        classification: Structured classification
        tenant_id: Tenant identifier
        
    Returns:
        List of data references with provenance
    """
    # Mock data reference
    return [
        {
            "metric": classification.get("measure", "revenue"),
            "period": classification.get("time", {}).get("period", "Q3"),
            "value": 2500000,
            "unit": "USD",
            "source": {
                "table": f"tenant-{tenant_id}-metrics",
                "pk": f"METRIC#{classification.get('measure', 'revenue')}",
                "sk": classification.get("time", {}).get("period", "Q3")
            }
        }
    ]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for chat endpoint.
    
    Expected input (API Gateway):
    {
        "body": "{\"message\": \"What is Q3 revenue?\", \"sessionId\": \"uuid\"}",
        "requestContext": {
            "requestId": "uuid",
            "authorizer": {
                "claims": {
                    "custom:tenant_id": "acme-corp-001"
                }
            }
        }
    }
    
    Response:
    {
        "statusCode": 200,
        "body": "{\"response\": \"...\", \"sessionId\": \"uuid\", \"requestId\": \"uuid\"}"
    }
    
    Note: For true streaming, this would use API Gateway WebSocket or
    Lambda response streaming (invoke-with-response-stream).
    """
    # Generate request ID for tracing
    request_id = event.get("requestContext", {}).get("requestId") or str(uuid.uuid4())
    
    # Start time for latency tracking
    start_time = time.time()
    
    try:
        # Extract tenant ID from JWT
        tenant_id = extract_tenant_id(event)
        
        logger.info(
            "Chat request received",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "event_source": "api_gateway"
            }
        )
        
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        
        # Validate request
        validate_request(body)
        
        message = body["message"]
        session_id = body.get("sessionId") or str(uuid.uuid4())
        
        # Get AI adapter
        provider_name = os.environ.get("AI_PROVIDER", "bedrock").lower()
        
        if provider_name == "ollama":
            provider = AIProvider.OLLAMA
            adapter_config = {
                "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                "model": os.environ.get("OLLAMA_MODEL", "llama2")
            }
        else:
            provider = AIProvider.BEDROCK
            adapter_config = {
                "model_id": os.environ.get(
                    "BEDROCK_MODEL_ID",
                    "anthropic.claude-3-sonnet-20240229-v1:0"
                ),
                "region": os.environ.get("AWS_REGION", "us-east-1")
            }
        
        adapter = get_adapter(provider, **adapter_config)
        
        # Step 1: Classify the message
        logger.info(
            "Classifying message",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "session_id": session_id
            }
        )
        
        classification = adapter.classify(
            question=message,
            tenant_id=tenant_id,
            request_id=request_id
        )
        
        # Check if classification was refused
        if classification.get("refused", False):
            logger.info(
                "Classification refused",
                extra={
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "refusal_reason": classification.get("refusal_reason")
                }
            )
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "X-Request-Id": request_id,
                    "X-Session-Id": session_id
                },
                "body": json.dumps({
                    "response": classification.get(
                        "refusal_reason",
                        "I'm not confident I understood your question. Could you rephrase?"
                    ),
                    "sessionId": session_id,
                    "requestId": request_id,
                    "metadata": {
                        "refused": True,
                        "latencyMs": int((time.time() - start_time) * 1000)
                    }
                })
            }
        
        # Step 2: Fetch relevant data (stub for Phase 5)
        logger.info(
            "Fetching data",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "intent": classification.get("intent"),
                "subject": classification.get("subject")
            }
        )
        
        data_references = fetch_data_stub(classification, tenant_id)
        
        # Step 3: Generate narrative
        logger.info(
            "Generating narrative",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "data_points": len(data_references)
            }
        )
        
        narrative = adapter.generate_narrative(
            classification=classification,
            data_references=data_references,
            tenant_id=tenant_id,
            request_id=request_id
        )
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Chat interaction completed successfully",
            extra={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "session_id": session_id,
                "latency_ms": latency_ms,
                "confidence": classification.get("confidence", {}).get("overall", 0)
            }
        )
        
        # Build response
        response = {
            "response": narrative["text"],
            "sessionId": session_id,
            "requestId": request_id,
            "classification": classification,
            "dataReferences": data_references,
            "metadata": {
                "latencyMs": latency_ms,
                "provider": provider_name,
                "confidence": classification.get("confidence", {}).get("overall", 0)
            }
        }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id,
                "X-Session-Id": session_id
            },
            "body": json.dumps(response)
        }
        
    except ValueError as e:
        # Validation or authentication errors (400)
        logger.warning(
            "Chat validation error",
            extra={
                "request_id": request_id,
                "error": str(e)
            }
        )
        
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id
            },
            "body": json.dumps({
                "error": "ValidationError",
                "message": str(e),
                "requestId": request_id
            })
        }
    
    except AIProviderError as e:
        # AI provider errors (502)
        logger.error(
            "AI provider error",
            extra={
                "request_id": request_id,
                "error": str(e)
            },
            exc_info=True
        )
        
        return {
            "statusCode": 502,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id
            },
            "body": json.dumps({
                "error": "AIProviderError",
                "message": "Chat service temporarily unavailable",
                "requestId": request_id
            })
        }
    
    except Exception as e:
        # Unexpected errors (500)
        logger.error(
            "Unexpected error in chat handler",
            extra={
                "request_id": request_id,
                "error": str(e)
            },
            exc_info=True
        )
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id
            },
            "body": json.dumps({
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "requestId": request_id
            })
        }


# ============================================================================
# Streaming Response Scaffolding
# ============================================================================

def stream_chat_response(
    message: str,
    tenant_id: str,
    session_id: str,
    request_id: str
) -> Generator[str, None, None]:
    """
    Streaming response generator (scaffolding for future implementation).
    
    This function demonstrates how streaming would work with
    Lambda response streaming or WebSocket API.
    
    Args:
        message: User message
        tenant_id: Tenant identifier
        session_id: Session identifier
        request_id: Request identifier
        
    Yields:
        JSON-encoded chunks for streaming
        
    Note:
        Requires Lambda response streaming or API Gateway WebSocket.
        Current implementation returns full response in lambda_handler.
    """
    try:
        # Get adapter
        provider_name = os.environ.get("AI_PROVIDER", "bedrock").lower()
        
        if provider_name == "ollama":
            provider = AIProvider.OLLAMA
            adapter_config = {
                "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                "model": os.environ.get("OLLAMA_MODEL", "llama2")
            }
        else:
            provider = AIProvider.BEDROCK
            adapter_config = {
                "model_id": os.environ.get(
                    "BEDROCK_MODEL_ID",
                    "anthropic.claude-3-sonnet-20240229-v1:0"
                ),
                "region": os.environ.get("AWS_REGION", "us-east-1")
            }
        
        adapter = get_adapter(provider, **adapter_config)
        
        # Yield classification start event
        yield json.dumps({
            "type": "classification_start",
            "requestId": request_id,
            "sessionId": session_id
        }) + "\n"
        
        # Classify
        classification = adapter.classify(
            question=message,
            tenant_id=tenant_id,
            request_id=request_id
        )
        
        # Yield classification result
        yield json.dumps({
            "type": "classification_complete",
            "classification": classification,
            "requestId": request_id
        }) + "\n"
        
        # Yield data retrieval start event
        yield json.dumps({
            "type": "data_retrieval_start",
            "requestId": request_id
        }) + "\n"
        
        # Fetch data
        data_references = fetch_data_stub(classification, tenant_id)
        
        # Yield data retrieval complete
        yield json.dumps({
            "type": "data_retrieval_complete",
            "dataPoints": len(data_references),
            "requestId": request_id
        }) + "\n"
        
        # Yield narrative generation start
        yield json.dumps({
            "type": "narrative_start",
            "requestId": request_id
        }) + "\n"
        
        # Generate narrative
        narrative = adapter.generate_narrative(
            classification=classification,
            data_references=data_references,
            tenant_id=tenant_id,
            request_id=request_id
        )
        
        # Yield narrative (could be streamed token-by-token in future)
        yield json.dumps({
            "type": "narrative_chunk",
            "text": narrative["text"],
            "requestId": request_id
        }) + "\n"
        
        # Yield completion event
        yield json.dumps({
            "type": "complete",
            "requestId": request_id,
            "sessionId": session_id
        }) + "\n"
        
    except Exception as e:
        # Yield error event
        yield json.dumps({
            "type": "error",
            "error": str(e),
            "requestId": request_id
        }) + "\n"
