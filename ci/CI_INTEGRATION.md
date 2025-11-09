# CI Integration Guide - Quality Hardening Tests

## Overview

Phase 6 Quality Hardening has introduced comprehensive test suites for adversarial scenarios, performance baselines, and security validation. This guide explains how to integrate these tests into CI/CD pipelines.

## Test Suites

### 1. Adversarial Tests (`tests/adversarial/`)

**Purpose:** Falsify assumptions and find edge cases  
**Count:** 32 tests  
**Run Time:** ~20 seconds

```bash
pytest tests/adversarial/ -v
```

**When to Run:**
- Every PR (pre-merge)
- Release candidates
- Nightly builds

### 2. Performance Tests (`tests/performance/`)

**Purpose:** Validate latency baselines and resource usage  
**Count:** 18 tests  
**Run Time:** ~60 seconds (includes intentional delays)

```bash
pytest tests/performance/ -v -m performance
```

**When to Run:**
- Nightly builds (full suite)
- On-demand for performance analysis
- Before releases

### 3. Security Tests (`tests/security/`)

**Purpose:** Verify tenant isolation and prevent attacks  
**Count:** 27 tests  
**Run Time:** ~15 seconds

```bash
pytest tests/security/ -v
```

**When to Run:**
- Every PR (pre-merge) - **MANDATORY**
- Release candidates
- Weekly security scans

## CI/CD Pipeline Integration

### GitHub Actions Example

```yaml
name: Quality Hardening Tests

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM UTC

jobs:
  security-tests:
    name: Security & Isolation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run security tests
        run: |
          cd backend
          pytest tests/security/ -v --junitxml=test-results/security.xml
      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-test-results
          path: backend/test-results/

  adversarial-tests:
    name: Adversarial & Fuzz
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run adversarial tests
        run: |
          cd backend
          pytest tests/adversarial/ -v --junitxml=test-results/adversarial.xml
      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: adversarial-test-results
          path: backend/test-results/

  performance-tests:
    name: Performance Baselines
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run performance tests
        run: |
          cd backend
          pytest tests/performance/ -v -m performance --junitxml=test-results/performance.xml
      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: performance-test-results
          path: backend/test-results/
```

## Quality Gates

### PR Merge Requirements

All of the following must pass:

✅ **Security Tests:** 100% pass rate (excluding skipped)  
✅ **Adversarial Tests:** 100% pass rate (excluding skipped/xfail)  
✅ **Existing Unit Tests:** No regressions  
✅ **No New XFails:** Without documented rationale  
✅ **No High-Severity Findings:** From security tests

### Release Requirements

Additional gates for releases:

✅ **Performance Tests:** P95 latency within SLO  
✅ **Known Gaps:** All documented with ETAs  
✅ **Security Review:** Manual review of skipped tests  
✅ **Test Coverage:** No decrease in coverage  

## Test Execution Strategies

### Development (Local)

```bash
# Fast feedback - skip slow tests
pytest tests/ -v -m "not performance" --tb=short

# Quick security check
pytest tests/security/ -v --tb=line

# Full suite
pytest tests/ -v
```

### CI - Pull Request

```bash
# Security (mandatory)
pytest tests/security/ -v --strict-markers

# Adversarial (mandatory)
pytest tests/adversarial/ -v --strict-markers

# Existing tests (mandatory)
pytest tests/contracts/ tests/integration/ tests/lambda/ -v
```

### CI - Nightly

```bash
# Full suite including performance
pytest tests/ -v --strict-markers --junitxml=results.xml

# Generate coverage report
pytest tests/ --cov=lambda --cov-report=html --cov-report=term
```

### CI - Release Candidate

```bash
# All tests with coverage
pytest tests/ -v --cov=lambda --cov-report=xml --junitxml=results.xml

# No xfail without strict=False
pytest tests/ --runxfail
```

## Handling Test Results

### Expected Results

```
Total: 161 tests
Passed: 139 (86%)
Skipped: 20 (12%) - Infrastructure dependencies
XFailed: 1 (0.6%) - Known gaps
XPassed: 1 (0.6%) - Review needed
Failed: 0 (0%)
```

### Interpreting Failures

| Result | Action |
|--------|--------|
| **Failed** | ❌ Block merge, investigate immediately |
| **XFailed** | ✅ Expected, verify reason documented |
| **XPassed** | ⚠️ Review - may indicate unexpected fix |
| **Skipped** | ✅ Expected for infrastructure tests |

### XPassed Tests

When a test marked `xfail` unexpectedly passes:

1. Verify the fix is intentional
2. Remove `xfail` marker
3. Update documentation
4. Close related tracking issue

## Metrics to Track

### Test Health

- **Pass Rate:** (Passed / (Total - Skipped - XFail)) × 100
  - Target: 100%
  - Current: 100%

- **Flake Rate:** (Flaky Runs / Total Runs) × 100
  - Target: < 1%
  - Current: 0%

- **Known Gaps:** Count of XFail tests
  - Target: Decreasing over time
  - Current: 1

### Performance Metrics

- **P95 Latency:** 95th percentile response time
  - Target: < 2000ms
  - Current: ~500ms (mocked)

- **Test Duration:** Time to run full suite
  - Target: < 5 minutes
  - Current: ~60 seconds

## Troubleshooting

### Common Issues

**Issue:** Security tests fail with "Tenant ID not found"
- **Cause:** Missing authorizer in test event
- **Fix:** Add `requestContext.authorizer.claims` to event

**Issue:** Performance tests timeout
- **Cause:** Mock not configured properly
- **Fix:** Verify `@patch('classify.get_adapter')` in test

**Issue:** Skipped tests increase
- **Cause:** Missing LocalStack or infrastructure
- **Fix:** Acceptable if documented; track separately

## Reporting

### Quality Report

Generate quality report:

```bash
# Run tests with JSON report
pytest tests/ --json-report --json-report-file=report.json

# Or use built-in quality.md
cat ci/reports/quality.md
```

### Coverage Report

```bash
# Generate HTML coverage
pytest tests/ --cov=lambda --cov-report=html

# View in browser
open htmlcov/index.html
```

## Maintenance

### Weekly

- Review XPassed tests
- Check for new known gaps
- Verify flake rate remains 0%

### Monthly

- Update known gap ETAs
- Review performance trends
- Security test coverage audit

### Quarterly

- Full security review
- Performance baseline refresh
- Test suite optimization

## Contact

For issues with CI integration:
- **Tester Copilot** - Test infrastructure
- **Architect Copilot** - Observability patterns
- **Developer Copilot** - Test failures

---

**Last Updated:** 2025-11-09  
**Maintainer:** Tester Copilot
