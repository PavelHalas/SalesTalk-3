"""Active Learning Event Emitter

Emits low-confidence or unmatched Czech queries to an event queue for review.
Safe no-op when AWS is unavailable (local dev with LocalStack).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency on boto3
_sqs_client = None


def _get_sqs_client():
    global _sqs_client
    if _sqs_client is not None:
        return _sqs_client
    try:
        import boto3
        endpoint = os.getenv("AWS_SQS_ENDPOINT_URL")
        if endpoint:
            _sqs_client = boto3.client("sqs", endpoint_url=endpoint)
        else:
            _sqs_client = boto3.client("sqs")
        return _sqs_client
    except Exception as e:
        logger.warning(f"SQS client unavailable: {e}")
        return None


def emit_learning_event(
    tenant_id: str,
    original_query: str,
    language: str,
    confidence: float,
    normalization_coverage: float,
    pattern_matched: Optional[list] = None,
    fuzzy_score: Optional[float] = None,
    exemplar_matches: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Emit a learning event for queries that need manual review or alias addition.
    
    Args:
        tenant_id: Tenant identifier
        original_query: User's original query text
        language: Detected language code
        confidence: Overall classification confidence
        normalization_coverage: Fraction of words normalized
        pattern_matched: Patterns that matched (if any)
        fuzzy_score: Fuzzy match score (if any)
        exemplar_matches: Exemplar retrieval results
        metadata: Additional context
    
    Returns:
        True if event was emitted successfully, False otherwise
    """
    queue_url = os.getenv("LEARNING_QUEUE_URL")
    if not queue_url:
        logger.debug("No learning queue configured; skipping event emission")
        return False
    
    client = _get_sqs_client()
    if not client:
        logger.debug("SQS unavailable; skipping learning event")
        return False
    
    event = {
        "tenantId": tenant_id,
        "originalQuery": original_query,
        "language": language,
        "confidence": confidence,
        "normalizationCoverage": normalization_coverage,
        "patternMatched": pattern_matched or [],
        "fuzzyScore": fuzzy_score,
        "exemplarMatches": exemplar_matches or [],
        "metadata": metadata or {},
    }
    
    try:
        client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(event),
            MessageAttributes={
                "tenantId": {"StringValue": tenant_id, "DataType": "String"},
                "language": {"StringValue": language, "DataType": "String"},
            },
        )
        logger.info(f"Emitted learning event for tenant {tenant_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to emit learning event: {e}")
        return False
