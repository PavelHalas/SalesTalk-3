"""
Additional tests for chat handler to increase coverage.
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from chat import stream_chat_response


class TestStreamingScaffolding:
    """Tests for streaming response scaffolding."""
    
    @patch("chat.get_adapter")
    def test_stream_chat_response(self, mock_get_adapter):
        """Test streaming response generator."""
        # Setup mock adapter
        mock_adapter = Mock()
        mock_adapter.classify.return_value = {
            "intent": "what",
            "subject": "revenue",
            "measure": "revenue",
            "time": {"period": "Q3"},
            "confidence": {"overall": 0.92},
            "refused": False
        }
        mock_adapter.generate_narrative.return_value = {
            "text": "Q3 revenue was $2.5M.",
            "metadata": {"model": "test"}
        }
        mock_get_adapter.return_value = mock_adapter
        
        # Generate stream
        events = list(stream_chat_response(
            message="What is Q3 revenue?",
            tenant_id="test-tenant",
            session_id="session-123",
            request_id="request-123"
        ))
        
        # Verify events
        assert len(events) > 0
        
        # Parse first event
        first_event = json.loads(events[0].strip())
        assert first_event["type"] == "classification_start"
        
        # Find completion event
        completion_events = [json.loads(e.strip()) for e in events if "complete" in e]
        assert len(completion_events) > 0
    
    @patch("chat.get_adapter")
    def test_stream_chat_response_error(self, mock_get_adapter):
        """Test streaming response with error."""
        # Setup mock adapter to raise error
        mock_adapter = Mock()
        mock_adapter.classify.side_effect = Exception("AI error")
        mock_get_adapter.return_value = mock_adapter
        
        # Generate stream
        events = list(stream_chat_response(
            message="What is Q3 revenue?",
            tenant_id="test-tenant",
            session_id="session-123",
            request_id="request-123"
        ))
        
        # Should have error event
        error_events = [json.loads(e.strip()) for e in events if "error" in e]
        assert len(error_events) > 0
        assert error_events[0]["type"] == "error"
