# End-to-End Tests with LocalStack

Comprehensive E2E test suite for local development using LocalStack and DynamoDB.

## Overview

This test suite validates the complete question-processing pipeline:
- Classification of user questions
- Intent, subject, measure, dimension, and time extraction
- Multi-tenant data isolation
- Narrative generation
- Data provenance and references
- Error handling and robustness
- **Supports both mock and real AI providers** (Ollama, Bedrock)

## Test Modes

### Mock AI Mode (Default - Fast & Deterministic)

By default, tests use mock AI adapters for fast, deterministic results:

```bash
cd backend
pytest tests/e2e/ -v
```

**Benefits:**
- ✅ Fast execution (no real AI calls)
- ✅ Deterministic results
- ✅ No external dependencies
- ✅ Ideal for CI/CD pipelines

### Real AI Mode (Integration Testing)

Test with real AI providers (Ollama or Bedrock) for true end-to-end validation:

```bash
# With Ollama (requires Ollama running locally)
USE_REAL_AI=true AI_PROVIDER=ollama pytest tests/e2e/ -v

# With Bedrock (requires AWS credentials)
USE_REAL_AI=true AI_PROVIDER=bedrock pytest tests/e2e/ -v
```

**Benefits:**
- ✅ True end-to-end validation
- ✅ Real AI model testing
- ✅ Actual response quality validation
- ✅ Model behavior verification

**Prerequisites for Real AI Mode:**
- **Ollama**: Start Ollama locally (`ollama serve` on port 11434)
- **Bedrock**: Configure AWS credentials with Bedrock access

## Prerequisites

### 1. LocalStack

Start LocalStack to simulate DynamoDB locally:

```bash
# Using Docker
docker run -d \
  --name salestalk-localstack \
  -p 4566:4566 \
  -e SERVICES=dynamodb \
  localstack/localstack

# Or using Docker Compose (if available)
docker-compose up -d localstack
```

Verify LocalStack is running:

```bash
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

### 2. Seed Test Data

Seed LocalStack DynamoDB with test tenant data:

```bash
cd backend
python scripts/seed_localstack.py
```

This creates:
- `tenants-metadata` table
- `tenant-acme-corp-001-messages` table
- `tenant-acme-corp-001-metrics` table
- `tenant-techstart-inc-002-messages` table  
- `tenant-techstart-inc-002-metrics` table

And populates them with sample data for two test tenants.

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. (Optional) Setup Real AI Provider

#### For Ollama:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Start Ollama server
ollama serve
```

#### For Bedrock:
```bash
# Configure AWS credentials
aws configure

# Ensure you have Bedrock access in your AWS account
```

## Running Tests

### Mock AI Mode (Default)

```bash
cd backend
pytest tests/e2e/ -v
```

### Real AI Mode

```bash
# With Ollama
USE_REAL_AI=true AI_PROVIDER=ollama pytest tests/e2e/ -v

# With Ollama on custom URL
USE_REAL_AI=true AI_PROVIDER=ollama OLLAMA_BASE_URL=http://localhost:11434 pytest tests/e2e/ -v

# With Bedrock
USE_REAL_AI=true AI_PROVIDER=bedrock pytest tests/e2e/ -v
```

### Run with E2E Marker

```bash
pytest -m e2e -v
```

### Run Specific Test Class

```bash
pytest tests/e2e/test_localstack_e2e.py::TestBasicWhatQuestions -v
```

### Run Single Test

```bash
pytest tests/e2e/test_localstack_e2e.py::TestBasicWhatQuestions::test_what_is_q3_revenue -v
```

### Skip E2E Tests (if LocalStack not available)

```bash
pytest -m "not e2e" -v
```

## Test Coverage

### Intent Types Tested

- ✅ **what** - Basic "what is" questions (revenue, margin, customers)
- ✅ **compare** - Comparative questions (EMEA vs APAC, Q3 vs Q4)
- ✅ **why** - Causal questions (why did churn increase?)
- ✅ **trend** - Trend analysis (12-month revenue trend)
- ✅ **rank** - Ranking questions (top 5 products)
- ✅ **breakdown** - Multi-dimensional breakdowns

### Validation Checks

Each test validates:
- ✅ **Intent** classification (what, compare, why, trend, rank, etc.)
- ✅ **Subject** extraction (revenue, margin, customers, products, etc.)
- ✅ **Measure** identification (revenue, gm_pct, churn_rate, etc.)
- ✅ **Dimensions** parsing (region, segment, product line, etc.)
- ✅ **Time** handling (Q3, last_month, ytd, l12m, etc.)
- ✅ **Confidence scores** (overall + components, all in [0, 1])
- ✅ **Tenant isolation** (correct tenant ID, table names)
- ✅ **Data references** (provenance with source table/pk/sk)
- ✅ **Error handling** (400 for invalid input, 502 for AI errors)

### Test Scenarios

1. **Basic What Questions** (3 tests)
   - Q3 revenue
   - Gross margin this quarter
   - Active customer count

2. **Comparative Questions** (2 tests)
   - EMEA vs APAC revenue
   - Q3 vs Q4 margin

3. **Causal Why Questions** (2 tests)
   - Why did churn increase?
   - Why is margin down in EMEA?

4. **Trend Analysis** (2 tests)
   - Revenue trend over 12 months
   - Quarterly margin trend YTD

5. **Ranking Questions** (2 tests)
   - Top 5 products by revenue
   - Worst performing regions

6. **Multi-Dimensional Queries** (2 tests)
   - Enterprise revenue in North America Q3
   - Margin by product line and region

7. **Edge Cases and Ambiguity** (3 tests)
   - Ambiguous time reference ("last quarter")
   - Missing time period
   - Ambiguous subject ("growth")

8. **Multi-Tenant Isolation** (3 tests)
   - Tenant 1 classification
   - Tenant 2 classification
   - Data references include tenant table

9. **End-to-End Chat Flow** (2 tests)
   - Complete flow with narrative
   - Session continuity across requests

10. **Confidence and Quality** (3 tests)
    - All confidence components present
    - High confidence for clear questions
    - Lower confidence for ambiguous questions

11. **Error Handling** (4 tests)
    - Missing tenant ID → 400
    - Empty question → 400
    - Overly long question → 400
    - AI provider error → 502

**Total: 30+ comprehensive E2E test cases**

## Test Structure

```
tests/e2e/
├── __init__.py
├── test_localstack_e2e.py    # Main E2E test suite
└── README.md                  # This file
```

## Configuration

### Environment Variables

- `LOCALSTACK_ENDPOINT` - LocalStack URL (default: `http://localhost:4566`)
- `AWS_REGION` - AWS region (default: `us-east-1`)

### Test Tenants

- `acme-corp-001` - ACME Corporation (Manufacturing)
- `techstart-inc-002` - TechStart Inc (SaaS)

## Fixtures

### Module-Scoped Fixtures

- `dynamodb_client` - boto3 DynamoDB client for LocalStack
- `dynamodb_resource` - boto3 DynamoDB resource for LocalStack
- `verify_localstack` - Skips tests if LocalStack not running
- `verify_tables_seeded` - Skips tests if tables not seeded

### Function-Scoped Fixtures

- `mock_ai_adapter` - Mock AI adapter for deterministic testing

### Helper Functions

- `create_api_event()` - Creates API Gateway event for testing

## Troubleshooting

### LocalStack Not Running

If you see: `LocalStack not available: <error>`

**Solution:**
```bash
# Check if LocalStack is running
docker ps | grep localstack

# Start LocalStack if not running
docker run -d -p 4566:4566 localstack/localstack
```

### Tables Not Seeded

If you see: `Required tables not seeded. Missing: <tables>`

**Solution:**
```bash
# Run seed script
cd backend
python scripts/seed_localstack.py
```

### Tests Skipped

If all E2E tests are skipped, check:

1. LocalStack is running: `curl http://localhost:4566/_localstack/health`
2. Tables are seeded: `aws --endpoint-url=http://localhost:4566 dynamodb list-tables`
3. boto3 is installed: `pip install boto3`

## Continuous Integration

### CI Configuration Example

```yaml
# .github/workflows/test.yml
jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    services:
      localstack:
        image: localstack/localstack
        ports:
          - 4566:4566
        env:
          SERVICES: dynamodb
    steps:
      - uses: actions/checkout@v2
      - name: Seed LocalStack
        run: |
          cd backend
          python scripts/seed_localstack.py
      - name: Run E2E Tests
        run: |
          cd backend
          pytest tests/e2e/ -v --junit-xml=test-results/e2e.xml
```

## Best Practices

1. **Isolation** - Each test is independent and can run in any order
2. **Deterministic** - Uses mocks for AI responses to ensure reproducibility
3. **Comprehensive** - Covers happy paths, edge cases, and error scenarios
4. **Fast** - Uses mocks instead of real AI calls for speed
5. **Documented** - Each test has clear docstring explaining scenario
6. **Realistic** - Uses actual tenant data structure from seed files

## Next Steps

- [ ] Add tests for actual DynamoDB queries (without mocks)
- [ ] Add tests for AI adapter integration with Ollama
- [ ] Add performance/latency benchmarks
- [ ] Add chaos testing (network failures, timeouts)
- [ ] Add tests for concurrent requests across tenants
- [ ] Add tests for rate limiting and throttling

## Related Documentation

- [Seed Data README](../../seed_data/README.md)
- [Lambda Functions](../../lambda/README.md)
- [Architecture Overview](../../../docs/architecture/ARCHITECTURE_OVERVIEW.md)
- [Data Contracts](../../../docs/contracts/DATA_CONTRACTS.md)
