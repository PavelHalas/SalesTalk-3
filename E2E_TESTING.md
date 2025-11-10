# Running E2E Tests Locally

This guide helps you run end-to-end tests for SalesTalk using LocalStack.

## Quick Start

The fastest way to run E2E tests:

```bash
# From the repository root
cd backend/tests/e2e
./setup_and_run.sh
```

This script will:
1. ✅ Check for Docker and Python
2. ✅ Install Python dependencies
3. ✅ Start LocalStack (if not running)
4. ✅ Seed DynamoDB with test data
5. ✅ Run all E2E tests

## Manual Setup

### 1. Start LocalStack

**Option A: Using Docker Compose (Recommended)**

```bash
# From repository root
docker-compose -f docker-compose.localstack.yml up -d
```

**Option B: Using Docker directly**

```bash
docker run -d \
  --name salestalk-localstack \
  -p 4566:4566 \
  -e SERVICES=dynamodb \
  localstack/localstack:latest
```

### 2. Verify LocalStack is Running

```bash
# Check health
curl http://localhost:4566/_localstack/health

# List DynamoDB tables (should be empty initially)
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

### 3. Seed Test Data

```bash
cd backend
python scripts/seed_localstack.py
```

This creates and populates:
- `tenants-metadata` - Global tenant registry
- `tenant-acme-corp-001-messages` - Messages for ACME Corp
- `tenant-acme-corp-001-metrics` - Metrics for ACME Corp
- `tenant-techstart-inc-002-messages` - Messages for TechStart
- `tenant-techstart-inc-002-metrics` - Metrics for TechStart

### 4. Run E2E Tests

```bash
cd backend
pytest tests/e2e/ -v
```

## Test Coverage

The E2E test suite includes **28 comprehensive test cases**:

### Intent Types (11 tests)
- ✅ **what** - "What is Q3 revenue?"
- ✅ **compare** - "How does EMEA compare to APAC?"
- ✅ **why** - "Why did churn increase?"
- ✅ **trend** - "Show me revenue trending over 12 months"
- ✅ **rank** - "Top 5 products by revenue"

### Validation Coverage
- ✅ Intent classification
- ✅ Subject identification (revenue, margin, customers, etc.)
- ✅ Measure extraction (revenue, gm_pct, churn_rate, etc.)
- ✅ Dimension parsing (region, segment, product line)
- ✅ Time handling (Q3, last_month, ytd, l12m)
- ✅ Confidence scores (overall + components)
- ✅ Multi-tenant isolation
- ✅ Data provenance (table/pk/sk references)
- ✅ Error handling (400, 502 status codes)

### Test Categories

1. **Basic What Questions** (3 tests)
2. **Comparative Questions** (2 tests)
3. **Causal Why Questions** (2 tests)
4. **Trend Analysis** (2 tests)
5. **Ranking Questions** (2 tests)
6. **Multi-Dimensional Queries** (2 tests)
7. **Edge Cases & Ambiguity** (3 tests)
8. **Multi-Tenant Isolation** (3 tests)
9. **End-to-End Chat Flow** (2 tests)
10. **Confidence & Quality** (3 tests)
11. **Error Handling** (4 tests)

## Running Specific Tests

### Run by marker
```bash
pytest -m e2e -v
```

### Run by test class
```bash
pytest tests/e2e/test_localstack_e2e.py::TestBasicWhatQuestions -v
```

### Run single test
```bash
pytest tests/e2e/test_localstack_e2e.py::TestBasicWhatQuestions::test_what_is_q3_revenue -v
```

### Skip E2E tests (useful in CI without LocalStack)
```bash
pytest -m "not e2e" -v
```

## Troubleshooting

### LocalStack Not Starting

**Symptom:** Tests skip with "LocalStack not available"

**Solution:**
```bash
# Check if LocalStack is running
docker ps | grep localstack

# View LocalStack logs
docker logs salestalk-localstack

# Restart LocalStack
docker stop salestalk-localstack
docker rm salestalk-localstack
docker run -d -p 4566:4566 --name salestalk-localstack localstack/localstack
```

### Tables Not Seeded

**Symptom:** Tests skip with "Required tables not seeded"

**Solution:**
```bash
# Re-run seed script
cd backend
python scripts/seed_localstack.py

# Verify tables created
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

### Port 4566 Already in Use

**Symptom:** LocalStack fails to start with port conflict

**Solution:**
```bash
# Find what's using the port
lsof -i :4566

# Stop the process or use a different port
export LOCALSTACK_ENDPOINT=http://localhost:4567
docker run -d -p 4567:4566 --name salestalk-localstack localstack/localstack
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    services:
      localstack:
        image: localstack/localstack:latest
        ports:
          - 4566:4566
        env:
          SERVICES: dynamodb
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Seed LocalStack
        run: |
          cd backend
          python scripts/seed_localstack.py
      
      - name: Run E2E tests
        run: |
          cd backend
          pytest tests/e2e/ -v --junitxml=test-results/e2e.xml
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: backend/test-results/
```

## Test Data

### Tenants
- **acme-corp-001** - ACME Corporation (Manufacturing, 500 employees)
- **techstart-inc-002** - TechStart Inc (SaaS startup)

### Metrics Available
- Revenue (Q3, Q4)
- Margin (Q3, Q4)
- Customer count
- Churn rate
- Multiple dimensions: region, segment, product line

## Cleanup

### Stop LocalStack
```bash
docker stop salestalk-localstack
```

### Remove LocalStack container
```bash
docker rm salestalk-localstack
```

### Remove LocalStack data
```bash
rm -rf backend/.localstack
```

## Next Steps

- Run tests before committing changes
- Add new test cases for new features
- Keep test data realistic and comprehensive
- Update README when adding new test scenarios

## Resources

- [E2E Test Documentation](backend/tests/e2e/README.md)
- [Seed Data README](backend/seed_data/README.md)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Architecture Overview](docs/architecture/ARCHITECTURE_OVERVIEW.md)
