"""
Performance and latency baseline tests.

Tests:
- P95 latency measurements for classification and chat endpoints
- Timeout handling and propagation
- Backoff and retry behavior
- Performance budgets validation
"""

import pytest
import json
import time
import sys
import os
from typing import List, Dict, Any
from statistics import median, quantiles
from unittest.mock import Mock, patch

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))

from classify import lambda_handler as classify_handler
from chat import lambda_handler as chat_handler


# ============================================================================
# Latency Baseline Tests
# ============================================================================

class TestLatencyBaseline:
    """Tests for establishing p95 latency baselines."""
    
    # SLO target: P95 < 2000ms end-to-end
    P95_TARGET_MS = 2000
    
    @pytest.fixture
    def mock_ai_adapter(self):
        """Mock AI adapter with controlled latency."""
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            # Simulate realistic AI response time (300-500ms)
            def classify_with_delay(*args, **kwargs):
                time.sleep(0.35)  # 350ms simulated AI call
                return {
                    "intent": "what",
                    "subject": "revenue",
                    "measure": "revenue",
                    "dimension": {},
                    "time": {"period": "Q3", "granularity": "quarter"},
                    "confidence": {
                        "overall": 0.85,
                        "components": {
                            "intent": 0.9,
                            "subject": 0.85,
                            "measure": 0.85,
                            "time": 0.8
                        }
                    }
                }
            
            adapter.classify.side_effect = classify_with_delay
            mock.return_value = adapter
            yield adapter
    
    def test_classification_latency_single_request(self, mock_ai_adapter):
        """Test single request latency for classification."""
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "perf-test-1",
                "authorizer": {
                    "claims": {"custom:tenant_id": "perf-tenant"}
                }
            }
        }
        
        start_time = time.time()
        result = classify_handler(event, None)
        latency_ms = (time.time() - start_time) * 1000
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "metadata" in body
        assert "latencyMs" in body["metadata"]
        
        # Latency should be reasonable for a single request
        assert latency_ms < 1000  # Should be well under 1 second for mock
    
    @pytest.mark.performance
    def test_classification_p95_latency(self, mock_ai_adapter):
        """Test p95 latency over multiple requests."""
        latencies = []
        num_requests = 20  # Small sample for unit test
        
        for i in range(num_requests):
            event = {
                "body": json.dumps({"question": f"What is Q{(i % 4) + 1} revenue?"}),
                "requestContext": {
                    "requestId": f"perf-test-{i}",
                    "authorizer": {
                        "claims": {"custom:tenant_id": "perf-tenant"}
                    }
                }
            }
            
            start_time = time.time()
            result = classify_handler(event, None)
            latency_ms = (time.time() - start_time) * 1000
            
            assert result["statusCode"] == 200
            latencies.append(latency_ms)
        
        # Calculate p95
        if len(latencies) >= 20:
            p95 = quantiles(latencies, n=20)[18]  # 95th percentile
        else:
            p95 = max(latencies)  # Use max for small samples
        
        p50 = median(latencies)
        
        # Log metrics for tracking
        print(f"\nLatency metrics (n={num_requests}):")
        print(f"  P50: {p50:.1f}ms")
        print(f"  P95: {p95:.1f}ms")
        print(f"  Min: {min(latencies):.1f}ms")
        print(f"  Max: {max(latencies):.1f}ms")
        
        # P95 should be under target (allowing for mock overhead)
        assert p95 < 1000, f"P95 latency {p95:.1f}ms exceeds threshold"
    
    @pytest.mark.performance
    def test_latency_metadata_accuracy(self, mock_ai_adapter):
        """Test that reported latency in metadata is accurate."""
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "perf-meta-test",
                "authorizer": {
                    "claims": {"custom:tenant_id": "perf-tenant"}
                }
            }
        }
        
        start_time = time.time()
        result = classify_handler(event, None)
        actual_latency_ms = (time.time() - start_time) * 1000
        
        body = json.loads(result["body"])
        reported_latency_ms = body["metadata"]["latencyMs"]
        
        # Reported latency should be within 10% of actual
        tolerance = actual_latency_ms * 0.1
        assert abs(reported_latency_ms - actual_latency_ms) < tolerance


# ============================================================================
# Timeout Handling Tests
# ============================================================================

class TestTimeoutBehavior:
    """Tests for timeout handling and propagation."""
    
    def test_slow_ai_provider_timeout(self):
        """Test handling of slow AI provider responses."""
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            
            # Simulate extremely slow AI response (beyond acceptable)
            def slow_classify(*args, **kwargs):
                time.sleep(5)  # 5 seconds - way too slow
                return {"intent": "what", "subject": "revenue"}
            
            adapter.classify.side_effect = slow_classify
            mock.return_value = adapter
            
            event = {
                "body": json.dumps({"question": "What is revenue?"}),
                "requestContext": {
                    "requestId": "timeout-test",
                    "authorizer": {
                        "claims": {"custom:tenant_id": "test-tenant"}
                    }
                }
            }
            
            # In production, API Gateway would timeout at 30s
            # For this test, we verify the function can handle long waits
            # without crashing (actual timeout enforcement is at API GW level)
            start = time.time()
            result = classify_handler(event, None)
            duration = time.time() - start
            
            # Should complete (even if slow) without errors
            assert result["statusCode"] in [200, 502]
            assert duration >= 5  # Confirms it waited
    
    @pytest.mark.xfail(
        reason="Client-side timeout not implemented - planned for v1.1",
        strict=False
    )
    def test_ai_adapter_timeout_configuration(self):
        """Test that AI adapters respect timeout configuration."""
        # Known gap: No client-side timeout enforcement yet
        # AWS Lambda timeout is the only limit currently
        pytest.skip("Client-side timeout configuration is a known gap for v1.1")


# ============================================================================
# Backoff and Retry Tests
# ============================================================================

class TestBackoffBehavior:
    """Tests for backoff and retry mechanisms."""
    
    @pytest.mark.xfail(
        reason="Retry logic not implemented - planned for v1.2",
        strict=False
    )
    def test_exponential_backoff_on_provider_error(self):
        """Test exponential backoff for AI provider errors."""
        # Known gap: No retry logic implemented yet
        pytest.skip("Retry with exponential backoff is a known gap for v1.2")
    
    @pytest.mark.xfail(
        reason="Rate limiting not implemented - planned for v1.2",
        strict=False
    )
    def test_rate_limit_backoff(self):
        """Test backoff behavior when rate limited."""
        # Known gap: No rate limiting or backoff implemented
        pytest.skip("Rate limit handling is a known gap for v1.2")


# ============================================================================
# Load Testing Scenarios
# ============================================================================

class TestLoadBehavior:
    """Tests for behavior under concurrent load."""
    
    @pytest.mark.performance
    def test_concurrent_requests_different_tenants(self):
        """Test handling of concurrent requests from different tenants."""
        # This is a smoke test - full load testing requires k6 or similar
        import concurrent.futures
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            adapter.classify.return_value = {
                "intent": "what",
                "subject": "revenue",
                "measure": "revenue",
                "dimension": {},
                "time": {"period": "Q3"},
                "confidence": {"overall": 0.85, "components": {
                    "intent": 0.9, "subject": 0.85, "measure": 0.85, "time": 0.8
                }}
            }
            mock.return_value = adapter
            
            def make_request(tenant_id):
                event = {
                    "body": json.dumps({"question": "What is revenue?"}),
                    "requestContext": {
                        "requestId": f"load-{tenant_id}",
                        "authorizer": {
                            "claims": {"custom:tenant_id": tenant_id}
                        }
                    }
                }
                return classify_handler(event, None)
            
            # Simulate 5 concurrent tenants
            tenants = [f"tenant-{i}" for i in range(5)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, t) for t in tenants]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            # All requests should succeed
            assert len(results) == 5
            assert all(r["statusCode"] == 200 for r in results)
    
    @pytest.mark.xfail(
        reason="Load testing with k6 not integrated - planned for v1.3",
        strict=False
    )
    def test_sustained_load_p95_within_slo(self):
        """Test that p95 remains within SLO under sustained load."""
        # Known gap: Full load testing requires external tools
        pytest.skip("K6 load testing integration is a known gap for v1.3")


# ============================================================================
# Performance Budget Validation
# ============================================================================

class TestPerformanceBudgets:
    """Tests for validating performance budgets."""
    
    def test_classification_memory_footprint(self):
        """Test that classification doesn't consume excessive memory."""
        # Basic smoke test - comprehensive profiling requires tooling
        event = {
            "body": json.dumps({"question": "What is Q3 revenue?"}),
            "requestContext": {
                "requestId": "mem-test",
                "authorizer": {
                    "claims": {"custom:tenant_id": "test-tenant"}
                }
            }
        }
        
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            adapter.classify.return_value = {
                "intent": "what",
                "subject": "revenue",
                "confidence": {"overall": 0.85, "components": {}}
            }
            mock.return_value = adapter
            
            # Should complete without memory errors
            result = classify_handler(event, None)
            assert result["statusCode"] == 200
    
    @pytest.mark.xfail(
        reason="Memory profiling not integrated - planned for v1.4",
        strict=False
    )
    def test_memory_usage_under_load(self):
        """Test memory usage under concurrent load."""
        # Known gap: Memory profiling requires instrumentation
        pytest.skip("Memory profiling integration is a known gap for v1.4")


# ============================================================================
# Performance Regression Detection
# ============================================================================

class TestPerformanceRegression:
    """Tests for detecting performance regressions.
    
    These tests establish baselines and should be tracked over time.
    """
    
    @pytest.mark.performance
    def test_baseline_classification_time(self):
        """Establish baseline for classification time."""
        with patch('classify.get_adapter') as mock:
            adapter = Mock()
            # Simulate typical AI response time
            def classify_realistic(*args, **kwargs):
                time.sleep(0.01)  # Minimal delay for mock
                return {
                    "intent": "what",
                    "subject": "revenue",
                    "confidence": {"overall": 0.85, "components": {
                        "intent": 0.9, "subject": 0.85, "measure": 0.85, "time": 0.8
                    }}
                }
            
            adapter.classify.side_effect = classify_realistic
            mock.return_value = adapter
            
            event = {
                "body": json.dumps({"question": "What is Q3 revenue?"}),
                "requestContext": {
                    "requestId": "baseline-test",
                    "authorizer": {
                        "claims": {"custom:tenant_id": "test-tenant"}
                    }
                }
            }
            
            start = time.time()
            result = classify_handler(event, None)
            duration_ms = (time.time() - start) * 1000
            
            print(f"\nBaseline classification time: {duration_ms:.1f}ms")
            
            # Baseline should be fast with mock
            assert duration_ms < 100  # Generous threshold for mock
            assert result["statusCode"] == 200
