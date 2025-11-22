"""Tests for active_learning event emitter."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add lambda directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda"))

from normalization.active_learning import emit_learning_event


@pytest.fixture
def mock_sqs_client():
    """Mock SQS client."""
    client = MagicMock()
    client.send_message = MagicMock()
    return client


def test_emit_learning_event_no_queue_url():
    """Should return False when LEARNING_QUEUE_URL is not set."""
    with patch.dict(os.environ, {}, clear=True):
        result = emit_learning_event(
            tenant_id="tenant-123",
            original_query="proc klesaji trzby",
            language="cs",
            confidence=0.45,
            normalization_coverage=0.67,
        )
        assert result is False


def test_emit_learning_event_sqs_unavailable():
    """Should return False when SQS client is unavailable."""
    with patch.dict(os.environ, {"LEARNING_QUEUE_URL": "http://localhost:4566/queue/learning"}):
        with patch("normalization.active_learning._get_sqs_client", return_value=None):
            result = emit_learning_event(
                tenant_id="tenant-123",
                original_query="proc klesaji trzby",
                language="cs",
                confidence=0.45,
                normalization_coverage=0.67,
            )
            assert result is False


def test_emit_learning_event_success(mock_sqs_client):
    """Should emit event successfully when queue URL and client are available."""
    queue_url = "http://localhost:4566/queue/learning"
    
    with patch.dict(os.environ, {"LEARNING_QUEUE_URL": queue_url}):
        with patch("normalization.active_learning._get_sqs_client", return_value=mock_sqs_client):
            result = emit_learning_event(
                tenant_id="tenant-123",
                original_query="proc klesaji trzby",
                language="cs",
                confidence=0.45,
                normalization_coverage=0.67,
                pattern_matched=["downward_trend_reason"],
                fuzzy_score=0.82,
                exemplar_matches=[{"cz": "proc klesly prijmy", "score": 0.75}],
                metadata={"session_id": "sess-456"},
            )
            
            assert result is True
            assert mock_sqs_client.send_message.call_count == 1
            
            call_kwargs = mock_sqs_client.send_message.call_args.kwargs
            assert call_kwargs["QueueUrl"] == queue_url
            
            body = json.loads(call_kwargs["MessageBody"])
            assert body["tenantId"] == "tenant-123"
            assert body["originalQuery"] == "proc klesaji trzby"
            assert body["language"] == "cs"
            assert body["confidence"] == 0.45
            assert body["normalizationCoverage"] == 0.67
            assert body["patternMatched"] == ["downward_trend_reason"]
            assert body["fuzzyScore"] == 0.82
            assert len(body["exemplarMatches"]) == 1
            assert body["metadata"]["session_id"] == "sess-456"
            
            attrs = call_kwargs["MessageAttributes"]
            assert attrs["tenantId"]["StringValue"] == "tenant-123"
            assert attrs["language"]["StringValue"] == "cs"


def test_emit_learning_event_send_failure(mock_sqs_client):
    """Should return False and log warning when send_message fails."""
    mock_sqs_client.send_message.side_effect = Exception("Network error")
    
    with patch.dict(os.environ, {"LEARNING_QUEUE_URL": "http://localhost:4566/queue/learning"}):
        with patch("normalization.active_learning._get_sqs_client", return_value=mock_sqs_client):
            result = emit_learning_event(
                tenant_id="tenant-123",
                original_query="proc klesaji trzby",
                language="cs",
                confidence=0.45,
                normalization_coverage=0.67,
            )
            
            assert result is False
