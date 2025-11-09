# SalesTalk Seed Data

This directory contains sample tenant data for local development and testing.

## Files

### Tenant Metadata
- `tenant_acme_corp.json` - ACME Corporation tenant metadata
- `tenant_techstart_inc.json` - TechStart Inc tenant metadata

### Business Metrics
- `acme_corp_metrics.json` - Q2-Q4 2025 sales metrics for ACME Corp
  - Revenue, Margin, Customers, Products, Renewal Rate
  - Focuses on North America Enterprise segment
  
- `techstart_inc_metrics.json` - Q3-Q4 2025 sales metrics for TechStart Inc
  - Revenue (EUR), Margin, Customers, ARR, Churn Rate
  - Focuses on Europe SMB segment

### Conversation Messages
- `acme_corp_messages.json` - Sample conversation for ACME Corp
  - Questions about Q3 revenue and margin
  - Includes classification and AI-generated responses
  
- `techstart_inc_messages.json` - Sample conversation for TechStart Inc
  - Questions about ARR growth and churn improvement
  - Includes classification and AI-generated responses

## Data Structure

### Tenants

**ACME Corporation (`acme-corp-001`)**
- Industry: Manufacturing
- Plan: Standard
- Region: North America
- Employees: 500

**TechStart Inc (`techstart-inc-002`)**
- Industry: Technology
- Plan: Enterprise
- Region: Europe
- Employees: 150

## Using Seed Data

The seed data is loaded into LocalStack DynamoDB using the `seed_localstack.py` script:

```bash
# Start LocalStack
docker-compose up -d

# Run seed script
python scripts/seed_localstack.py

# Or with custom endpoint
python scripts/seed_localstack.py --endpoint-url http://localhost:4566
```

## Sample Queries

Once seeded, you can query the data:

```python
import boto3

# Connect to LocalStack
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:4566',
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)

# Get ACME Corp revenue for Q3
table = dynamodb.Table('tenant-acme-corp-001-metrics')
response = table.get_item(
    Key={
        'pk': 'METRIC#revenue',
        'sk': '2025-Q3'
    }
)
print(response['Item'])  # $2.5M

# Get all messages in ACME Corp session
table = dynamodb.Table('tenant-acme-corp-001-messages')
response = table.query(
    IndexName='SessionIndex',
    KeyConditionExpression='sessionId = :sid',
    ExpressionAttributeValues={
        ':sid': 'session-acme-001'
    }
)
for message in response['Items']:
    print(f"{message['sender']}: {message['text']}")
```

## Data Quality

All seed data conforms to the contracts defined in `DATA_CONTRACTS.md`:

- ✅ Confidence scores in range [0.0, 1.0]
- ✅ Data references include source traceability
- ✅ Timestamps are valid Unix timestamps
- ✅ Tenant isolation enforced (separate tables)
- ✅ Idempotency keys present (messageId, metricId)

## Extending Seed Data

To add more test data:

1. Create a new JSON file following the existing structure
2. Update `seed_localstack.py` to load the new file
3. Ensure data conforms to `DATA_CONTRACTS.md` specifications
4. Run contract tests: `pytest tests/contracts/test_contracts.py`

## Notes

- All timestamps use Unix timestamp format (seconds since epoch)
- Currency values use appropriate units (USD, EUR)
- Dimensions enable multi-dimensional analysis (region, product, segment)
- Confidence scores demonstrate realistic classification quality
