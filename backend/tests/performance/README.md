# Performance Tests

## Purpose

Performance tests establish baselines and validate that SalesTalk meets its performance budgets under various conditions.

## SLO Targets

| Metric | Target |
|--------|--------|
| **P95 Latency** | < 2000ms |
| **P50 Latency** | < 1000ms |
| **Availability** | > 99.9% |
| **Flake Rate** | < 1% |

## Test Categories

### Latency Baselines (`TestLatencyBaseline`)

Establishes and validates latency baselines:
- **Single Request Latency** - Individual request performance
- **P95 Latency** - 95th percentile across multiple requests
- **Metadata Accuracy** - Reported latency matches actual

**Current Baselines (with mocked AI):**
- P95: ~500ms
- P50: ~350ms
- Single: ~350ms

**Note:** Production baselines will be higher with real AI providers.

### Timeout Behavior (`TestTimeoutBehavior`)

Tests timeout handling:
- Slow AI provider responses (5s)
- Timeout propagation
- **Known Gap:** Client-side timeout configuration (v1.1)

### Backoff Behavior (`TestBackoffBehavior`)

Tests retry and backoff mechanisms:
- **Known Gap:** Exponential backoff not implemented (v1.2)
- **Known Gap:** Rate limit handling not implemented (v1.2)

### Load Behavior (`TestLoadBehavior`)

Tests behavior under concurrent load:
- Concurrent requests from different tenants
- Tenant isolation under load
- **Known Gap:** K6 load testing integration (v1.3)

### Performance Budgets (`TestPerformanceBudgets`)

Validates resource constraints:
- Memory footprint during classification
- **Known Gap:** Memory profiling instrumentation (v1.4)

### Performance Regression (`TestPerformanceRegression`)

Tracks baselines over time:
- Classification time baseline
- Narrative generation baseline

## Running Tests

```bash
# Run all performance tests
pytest tests/performance/ -v -m performance

# Run specific test class
pytest tests/performance/test_latency.py::TestLatencyBaseline -v

# Run with timing output
pytest tests/performance/ -v --durations=10
```

## Performance Markers

Performance tests are marked with `@pytest.mark.performance` to allow selective execution:

```bash
# Run only performance-marked tests
pytest -m performance

# Exclude performance tests (for fast feedback)
pytest -m "not performance"
```

## Interpreting Results

### Latency Metrics

```python
# Example output from test_classification_p95_latency:
Latency metrics (n=20):
  P50: 345.2ms
  P95: 498.7ms
  Min: 321.1ms
  Max: 512.3ms
```

- **P50 (Median):** Half of requests are faster
- **P95:** 95% of requests are faster (SLO critical)
- **Min/Max:** Range of observed latencies

### Performance Budgets

Tests validate:
- Memory doesn't grow unbounded
- Response times remain within SLO
- No resource leaks under load

## Known Gaps

| Gap | Rationale | ETA | Impact |
|-----|-----------|-----|--------|
| Client-side timeouts | API GW handles this | v1.1 | Low |
| Retry with backoff | Need failure patterns | v1.2 | Medium |
| Rate limiting | Need usage data | v1.2 | Medium |
| K6 load testing | CI integration effort | v1.3 | Medium |
| Memory profiling | Requires instrumentation | v1.4 | Low |

## Load Testing

### Current Approach

- **Unit-level:** Concurrent request tests (5 tenants)
- **Integration-level:** Not yet implemented
- **Load testing:** Planned with k6 (v1.3)

### Future: K6 Integration

```javascript
// Future k6 scenario
export default function() {
  let response = http.post('https://api/classify', {
    question: 'What is Q3 revenue?'
  });
  check(response, {
    'status is 200': (r) => r.status === 200,
    'latency < 2s': (r) => r.timings.duration < 2000,
  });
}
```

## Monitoring

Track these metrics:
- P95 latency trend over time
- Regression detection on changes
- Flake rate (should be 0%)
- Resource utilization

## Best Practices

1. **Use mocks for consistency** - AI providers add variability
2. **Test realistic scenarios** - Not just happy paths
3. **Measure everything** - Latency, memory, concurrency
4. **Set thresholds** - Fail fast on regressions
5. **Track baselines** - Know when things get slower

---

**Last Updated:** 2025-11-09  
**Maintainer:** Tester Copilot
