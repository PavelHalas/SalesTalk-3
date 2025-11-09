# SalesTalk Data Platform - Quick Start Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for LocalStack)
- boto3 and pytest installed

### Installation

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Or with specific packages
pip install boto3 pytest pytest-cov
```

### Running Contract Tests

```bash
# Run all contract tests
pytest backend/tests/contracts/test_contracts.py -v

# Run with coverage
pytest backend/tests/contracts/test_contracts.py --cov=backend/src --cov-report=html

# Run only unit tests (skip integration)
pytest backend/tests/contracts/test_contracts.py -m "not skip" -v
```

Expected output: **16 passed, 4 skipped**

### Seeding LocalStack (when available)

```bash
# Start LocalStack
docker-compose up -d

# Run seed script
python backend/scripts/seed_localstack.py

# Or with custom endpoint
python backend/scripts/seed_localstack.py --endpoint-url http://localhost:4566
```

This will create:
- `tenants-metadata` table
- `tenant-acme-corp-001-messages` table
- `tenant-acme-corp-001-metrics` table
- `tenant-techstart-inc-002-messages` table
- `tenant-techstart-inc-002-metrics` table

And seed them with sample data.

## 📁 Project Structure

```
SalesTalk-3/
├── README.md
├── docs/
│   ├── DATA_CONTRACTS.md        # Data contract specifications
│   ├── PHASE2_CHECKLIST.md      # Phase 2 completion checklist
│   ├── QUICKSTART.md            # Quick start guide
│   └── ...
│
├── backend/
│   ├── requirements.txt         # Python dependencies
│   ├── pyproject.toml          # pytest configuration
│   ├── src/
│   │   └── ingestion/
│   │       ├── __init__.py
│   │       └── idempotent_ingestion.py  # Ingestion stubs
│   ├── tests/
│   │   └── contracts/
│   │       ├── __init__.py
│   │       └── test_contracts.py   # Contract validation tests
│   ├── scripts/
│   │   └── seed_localstack.py     # LocalStack seeding script
│   └── seed_data/               # Test tenant data
│       ├── README.md
│       ├── tenant_acme_corp.json
│       ├── tenant_techstart_inc.json
│       ├── acme_corp_metrics.json
│       ├── acme_corp_messages.json
│       ├── techstart_inc_metrics.json
│       └── techstart_inc_messages.json
│
└── infra/
    └── terraform/
        ├── dynamodb.tf        # DynamoDB table definitions
        └── variables.tf       # Terraform variables
```

## 🗄️ DynamoDB Schema Summary

### Global: tenants-metadata

**Primary Key**: `tenantId` (HASH)

**GSIs**:
- `OwnerEmailIndex`: Query tenants by owner email
- `StatusIndex`: Query tenants by status (active, suspended, deleted)

### Per-Tenant: tenant-{tenantId}-messages

**Primary Key**: `pk` (HASH), `sk` (RANGE)

**PK/SK Pattern**:
- `pk`: `MSG#{messageId}`
- `sk`: ISO timestamp

**GSIs**:
- `SessionIndex`: Query messages by session
- `SenderIndex`: Query messages by sender type

### Per-Tenant: tenant-{tenantId}-metrics

**Primary Key**: `pk` (HASH), `sk` (RANGE)

**PK/SK Pattern**:
- `pk`: `METRIC#{subject}`
- `sk`: Period (e.g., `2025-Q3`, `2025-11`)

**GSIs**:
- `MetricTypeIndex`: Time-series queries for a metric
- `DimensionIndex`: Query metrics by dimension

## 🧪 Data Contracts

### Key Constraints

1. **Confidence Scores**: MUST be in range [0.0, 1.0]
   ```python
   assert 0.0 <= confidence <= 1.0
   ```

2. **Data References**: MUST include source traceability
   ```json
   {
     "metric": "revenue",
     "period": "2025-Q3",
     "value": 2500000,
     "unit": "USD",
     "source": {
       "table": "tenant-acme-corp-001-metrics",
       "pk": "METRIC#revenue",
       "sk": "2025-Q3"
     }
   }
   ```

3. **Timestamps**: MUST be valid Unix timestamps (seconds)

4. **Tenant Isolation**: All data scoped to tenant tables

## 🔄 Idempotency

### Message Ingestion

Idempotency Key: `messageId` (UUID)

```python
# Duplicate messages are detected and handled gracefully
result = ingestion.ingest_message(tenant_id, message)
# Returns: {'status': 'created'} or {'status': 'already_exists'}
```

### Metric Ingestion

Idempotency Key: `{tenantId}:{subject}:{period}`

```python
# Same metric for same period = update, not duplicate
result = ingestion.ingest_metric(tenant_id, metric)
```

### Retry Strategy

- **Network errors**: 5 retries, exponential backoff
- **Throttling**: 10 retries, exponential backoff with jitter
- **Validation errors**: Fail fast (no retry)
- **Already exists**: No retry (success)

## 📊 Sample Data

### Test Tenants

1. **ACME Corporation** (`acme-corp-001`)
   - Industry: Manufacturing
   - Region: North America
   - Plan: Standard
   - Metrics: Revenue, Margin, Customers, Renewal Rate

2. **TechStart Inc** (`techstart-inc-002`)
   - Industry: Technology
   - Region: Europe
   - Plan: Enterprise
   - Metrics: Revenue (EUR), ARR, Churn, Margin

### Sample Queries

```python
import boto3

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:4566',
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)

# Get ACME Corp Q3 revenue
table = dynamodb.Table('tenant-acme-corp-001-metrics')
response = table.get_item(Key={'pk': 'METRIC#revenue', 'sk': '2025-Q3'})
print(f"Revenue: ${response['Item']['value']:,}")  # $2,500,000

# Get all messages in a session
table = dynamodb.Table('tenant-acme-corp-001-messages')
response = table.query(
    IndexName='SessionIndex',
    KeyConditionExpression='sessionId = :sid',
    ExpressionAttributeValues={':sid': 'session-acme-001'}
)
for msg in response['Items']:
    print(f"{msg['sender']}: {msg['text']}")
```

## 🔍 Validation

### Running Validations

```bash
# Validate seed data structure
python -c "
from backend.scripts.seed_localstack import LocalStackSeeder
from pathlib import Path

seeder = LocalStackSeeder()
tenant_data = seeder.load_json_file(Path('backend/seed_data/tenant_acme_corp.json'))
print(f'✓ Tenant: {tenant_data[\"tenantId\"]}')
"

# Validate contract compliance
pytest backend/tests/contracts/test_contracts.py::TestConfidenceValidation -v
pytest backend/tests/contracts/test_contracts.py::TestReferenceFormat -v
```

## 📖 Documentation

- **docs/DATA_CONTRACTS.md**: Complete data contract specifications
- **backend/seed_data/README.md**: Seed data documentation
- **docs/PHASE2_CHECKLIST.md**: Phase 2 completion status
- **docs/contracts/EVENTS.md**: Event schemas
- **docs/architecture/ARCHITECTURE_OVERVIEW.md**: System architecture

## 🐛 Troubleshooting

### Import Errors

```bash
# Ensure you're in the project root
cd /path/to/SalesTalk-3

# Install dependencies
pip install -r backend/requirements.txt
```

### LocalStack Connection Issues

```bash
# Check LocalStack is running
docker ps | grep localstack

# Verify endpoint
curl http://localhost:4566/_localstack/health
```

### Test Failures

```bash
# Run with verbose output
pytest backend/tests/contracts/test_contracts.py -vv

# Run specific test
pytest backend/tests/contracts/test_contracts.py::TestConfidenceValidation::test_valid_confidence_scores -v
```

## 🚀 Next Steps

Phase 2 is complete! Next phases:

1. **Phase 3**: Implement Lambda functions and actual ingestion
2. Deploy to LocalStack for integration testing
3. Implement event-driven workflows
4. Add monitoring and observability

---

**Need Help?** See docs/DATA_CONTRACTS.md for detailed specifications.
