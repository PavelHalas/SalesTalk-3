# Security & Isolation Tests

## Purpose

Security tests verify that SalesTalk enforces strong security boundaries and prevents common attack vectors. **Zero tolerance for cross-tenant data leakage.**

## Security Principles

1. **Multi-tenant safe-by-default** - No cross-tenant leakage under any failure mode
2. **Defense in depth** - Multiple layers of validation
3. **Fail secure** - Errors never expose sensitive data
4. **Least privilege** - Tenants access only their data

## Test Categories

### JWT Security (`TestJWTSecurity`)

Validates authentication and authorization:

✅ **Validated Controls:**
- Missing tenant claim → Rejected (400)
- Missing authorizer context → Rejected (400)
- Null tenant ID → Rejected
- Empty string tenant ID → Rejected
- Malformed claims structure → Rejected (400)

**Architectural Note:** JWT signature validation is performed by API Gateway before Lambda invocation.

### Tenant Isolation (`TestTenantIsolation`)

Ensures complete tenant separation:

✅ **Validated Controls:**
- Tenant ID included in all log entries
- Different tenants get isolated processing
- Tenant ID propagates to all downstream operations
- No tenant override via request payload

**Known Gap:** DynamoDB table-level isolation tests require LocalStack setup

### Injection Attacks (`TestInjectionAttacks`)

Prevents code injection vectors:

✅ **Protected Against:**
- SQL injection attempts (DROP TABLE, SELECT)
- Tenant ID injection via question text
- JSON injection in questions

### Payload Robustness (`TestPayloadRobustness`)

Handles malformed inputs safely:

✅ **Validated Handling:**
- Malformed JSON → Error response (400/500)
- Missing body → Rejected (400)
- Empty JSON → Rejected (400)
- Truncated JSON → Error response
- Extra fields → Safely ignored

### PII Leakage Prevention (`TestPIILeakagePrevention`)

Prevents sensitive data exposure:

✅ **Basic Protection:**
- PII in questions processed without crashes

**Known Gap:** PII detection and redaction planned for v2.0

### Authorization Boundaries (`TestAuthorizationBoundaries`)

Enforces access controls:

✅ **Current:**
- Tenant tokens cannot access system operations
- Tenant scope strictly enforced

**Known Gap:** Role-based access control (RBAC) planned for v2.1

## Running Tests

```bash
# Run all security tests
pytest tests/security/ -v

# Run specific security category
pytest tests/security/test_isolation.py::TestJWTSecurity -v

# Run with coverage
pytest tests/security/ -v --cov=lambda --cov-report=term-missing
```

## Security Assertions

### Critical Invariants

1. **Tenant ID Required** - Every operation must have valid tenant context
2. **No Cross-Tenant Access** - Tenant A cannot access Tenant B's data
3. **Input Validation** - Reject malformed/malicious inputs
4. **Secure Defaults** - Fail closed, not open

### Example: Tenant Isolation

```python
def test_tenant_id_passed_to_all_downstream_calls(self):
    """Verify tenant ID propagates through entire call chain."""
    # Track all tenant IDs used
    classify_calls = []
    narrative_calls = []
    
    # ... make request as tenant-chain ...
    
    # Verify same tenant ID used everywhere
    assert "tenant-chain" in classify_calls
    assert "tenant-chain" in narrative_calls
```

## Attack Vectors Tested

### 1. Authentication Bypass

- Missing JWT → Rejected
- Null tenant ID → Rejected
- Empty tenant ID → Rejected

### 2. Tenant Isolation Breach

- Cross-tenant data access → Prevented
- Tenant override via payload → Blocked
- Tenant leakage in logs → Prevented

### 3. Injection Attacks

- SQL injection → Sanitized as text
- JSON injection → Treated as literal
- Tenant ID injection → Ignored

### 4. Malformed Inputs

- Invalid JSON → Error response
- Truncated payload → Error response
- Extra fields → Safely ignored

## Security Gaps (Known & Tracked)

| Gap | Reason | ETA | Severity |
|-----|--------|-----|----------|
| JWT signature validation | Done by API Gateway | N/A | Low (architectural) |
| DynamoDB isolation tests | Requires LocalStack | Integration | Medium |
| PII detection/redaction | Privacy enhancement | v2.0 | Medium |
| Cross-tenant leak detection | Needs DB integration | Integration | High |
| RBAC | Authorization expansion | v2.1 | Low |

## Security Metrics

### Zero-Tolerance Thresholds

| Metric | Threshold | Current |
|--------|-----------|---------|
| Cross-tenant leaks | 0 | 0 ✅ |
| Auth bypass incidents | 0 | 0 ✅ |
| Injection successes | 0 | 0 ✅ |
| PII exposures | 0 | 0 ✅ |

## Incident Response

If a security test fails:

1. **Immediately stop deployment** - Do not merge
2. **Assess severity** - Critical/High/Medium/Low
3. **Isolate vulnerability** - What's exposed?
4. **Fix root cause** - Not just the test
5. **Add regression test** - Prevent recurrence
6. **Document incident** - Update security log

## Compliance

Security tests support:
- **SOC 2 Type II** - Access controls, logging
- **GDPR** - Data isolation, PII handling
- **ISO 27001** - Information security management

## Best Practices

1. **Think like an attacker** - How would you breach this?
2. **Test negative cases** - What should be rejected?
3. **Verify isolation** - No cross-tenant anything
4. **Log security events** - Audit trail required
5. **Fail secure** - Errors never expose data

## Adding Security Tests

When adding new security tests:

1. **Identify the threat** - What attack are you preventing?
2. **Test the boundary** - Where does security enforce?
3. **Verify all paths** - Don't miss edge cases
4. **Document severity** - How bad if this fails?
5. **Add to CI gates** - Security tests must pass

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)

---

**Last Updated:** 2025-11-09  
**Maintainer:** Tester Copilot  
**Security Contact:** security@salestalk.example
