# 📋 SalesTalk Data Contracts

**Version:** 1.0  
**Author:** Data Engineer Agent  
**Date:** November 2025  
**Status:** Phase 2 - Data Platform Bootstrapping

---

## 📋 Overview

This document defines the **data contracts** for SalesTalk's multi-tenant architecture, including:

1. **DynamoDB Table Schemas** with PK/SK patterns and GSI strategies
2. **Data Quality Constraints** and validation rules
3. **Idempotency Strategy** for ingestion and processing
4. **Event Data Contracts** and field specifications
5. **Storage Patterns** and access patterns

---

## 🗄️ DynamoDB Table Schemas

### 1. Global Tenants Metadata Table

**Table Name:** `tenants-metadata`

**Purpose:** Central registry for all tenants in the system

**Access Pattern:** Single-item lookups by tenantId, queries by owner email or status

#### Primary Key Design

| Attribute | Type | Key Type | Description |
|-----------|------|----------|-------------|
| `tenantId` | String | HASH (PK) | Unique tenant identifier (e.g., `acme-corp-001`) |

#### Attributes

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `tenantId` | String | Yes | Unique tenant identifier | Pattern: `[a-z0-9-]+`, Max length: 64 |
| `name` | String | Yes | Organization display name | Max length: 256 |
| `ownerEmail` | String | Yes | Primary contact email | Valid email format |
| `plan` | String | Yes | Subscription tier | Enum: `free`, `standard`, `enterprise` |
| `messagesTableName` | String | Yes | DynamoDB messages table | Format: `tenant-{tenantId}-messages` |
| `metricsTableName` | String | Yes | DynamoDB metrics table | Format: `tenant-{tenantId}-metrics` |
| `s3Prefix` | String | Yes | S3 artifact path | Format: `tenant-{tenantId}/` |
| `createdAt` | Number | Yes | Unix timestamp (seconds) | > 0 |
| `updatedAt` | Number | Yes | Unix timestamp (seconds) | >= createdAt |
| `status` | String | Yes | Tenant status | Enum: `active`, `suspended`, `deleted` |
| `metadata` | Map | No | Additional tenant configuration | Max size: 10KB |

#### Global Secondary Indexes

1. **OwnerEmailIndex**
   - Hash Key: `ownerEmail`
   - Projection: ALL
   - Use Case: Lookup tenant by admin email

2. **StatusIndex**
   - Hash Key: `status`
   - Projection: ALL
   - Use Case: Query active/suspended tenants

#### Example Item

```json
{
  "tenantId": "acme-corp-001",
  "name": "ACME Corporation",
  "ownerEmail": "admin@acme.com",
  "plan": "standard",
  "messagesTableName": "tenant-acme-corp-001-messages",
  "metricsTableName": "tenant-acme-corp-001-metrics",
  "s3Prefix": "tenant-acme-corp-001/",
  "createdAt": 1699545600,
  "updatedAt": 1699545600,
  "status": "active",
  "metadata": {
    "industry": "Manufacturing",
    "employees": 500,
    "region": "North America"
  }
}
```

---

### 2. Per-Tenant Messages Table

**Table Name:** `tenant-{tenantId}-messages`

**Purpose:** Store conversation messages and classification results per tenant

**Access Patterns:**
- Retrieve message by messageId
- Query all messages in a session (chronologically)
- Query messages by sender type (user, assistant, system)

#### Primary Key Design

| Attribute | Type | Key Type | Description |
|-----------|------|----------|-------------|
| `pk` | String | HASH (PK) | Partition key: `MSG#{messageId}` or `SESSION#{sessionId}` |
| `sk` | String | RANGE (SK) | Sort key: ISO timestamp `2025-11-09T12:34:56.789Z` |

**PK/SK Pattern:**

```
# Single message access
pk = "MSG#550e8400-e29b-41d4-a716-446655440000"
sk = "2025-11-09T12:34:56.789Z"

# Session rollup (metadata)
pk = "SESSION#session-uuid-001"
sk = "METADATA"

# Messages in session (via GSI)
sessionId = "session-uuid-001"
timestamp = 1699545600
```

#### Attributes

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `pk` | String | Yes | Partition key | Format: `MSG#{uuid}` or `SESSION#{uuid}` |
| `sk` | String | Yes | Sort key | ISO 8601 timestamp or `METADATA` |
| `tenantId` | String | Yes | Tenant identifier (denormalized) | Matches table name |
| `messageId` | String | Yes | Unique message UUID | UUID v4 format |
| `sessionId` | String | Yes | Conversation session UUID | UUID v4 format |
| `sender` | String | Yes | Message sender type | Enum: `user`, `assistant`, `system` |
| `text` | String | Yes | Message content | Max length: 10,000 chars |
| `classification` | Map | No | Intent classification result | See classification schema |
| `metadata` | Map | No | Additional message data | Max size: 50KB |
| `timestamp` | Number | Yes | Unix timestamp (seconds) | > 0 |
| `ttl` | Number | No | TTL for expiration (optional) | Unix timestamp |

#### Classification Schema (Nested Map)

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `intent` | String | Yes | Classified intent | Enum: see EVENTS.md |
| `subject` | String | Yes | Business subject | Enum: see EVENTS.md |
| `measure` | String | Yes | Measure type | Enum: see EVENTS.md |
| `timeRange` | Map | No | Time period specification | See timeRange schema |
| `filters` | List | No | Dimensional filters | List of {key, value} maps |
| `confidence` | Number | Yes | Overall confidence score | **Range: [0.0, 1.0]** |
| `components` | Map | No | Per-component confidence | Each value: **Range: [0.0, 1.0]** |

**Confidence Field Constraints (Contract Test Required):**
- `confidence`: MUST be between 0.0 and 1.0 (inclusive)
- `components.*`: Each component confidence MUST be between 0.0 and 1.0 (inclusive)
- Invalid values MUST be rejected during ingestion

#### Global Secondary Indexes

1. **SessionIndex**
   - Hash Key: `sessionId`
   - Range Key: `timestamp`
   - Projection: ALL
   - Use Case: Retrieve all messages in a conversation (chronologically)

2. **SenderIndex**
   - Hash Key: `sender`
   - Range Key: `timestamp`
   - Projection: ALL
   - Use Case: Analytics on user vs assistant messages

#### Example Item

```json
{
  "pk": "MSG#550e8400-e29b-41d4-a716-446655440000",
  "sk": "2025-11-09T12:34:56.789Z",
  "tenantId": "acme-corp-001",
  "messageId": "550e8400-e29b-41d4-a716-446655440000",
  "sessionId": "session-uuid-001",
  "sender": "user",
  "text": "What was revenue in Q3?",
  "classification": {
    "intent": "fact_retrieval",
    "subject": "revenue",
    "measure": "total",
    "timeRange": {
      "period": "quarter",
      "value": "Q3",
      "year": 2025
    },
    "filters": [],
    "confidence": 0.92,
    "components": {
      "intent_confidence": 0.95,
      "subject_confidence": 0.91,
      "measure_confidence": 0.90,
      "time_confidence": 0.93
    }
  },
  "metadata": {
    "classifierModel": "trm-classifier-v1.2",
    "processingTimeMs": 87
  },
  "timestamp": 1699545696
}
```

---

### 3. Per-Tenant Metrics Table

**Table Name:** `tenant-{tenantId}-metrics`

**Purpose:** Store business performance metrics per tenant

**Access Patterns:**
- Retrieve specific metric for a time period
- Query all periods for a metric type (time-series)
- Query metrics by dimension (e.g., all North America revenue)

#### Primary Key Design

| Attribute | Type | Key Type | Description |
|-----------|------|----------|-------------|
| `pk` | String | HASH (PK) | Partition key: `METRIC#{subject}` (e.g., `METRIC#revenue`) |
| `sk` | String | RANGE (SK) | Sort key: Time period (e.g., `2025-Q3`, `2025-11`, `2025-11-09`) |

**PK/SK Pattern:**

```
# Quarterly metric
pk = "METRIC#revenue"
sk = "2025-Q3"

# Monthly metric
pk = "METRIC#margin"
sk = "2025-11"

# Daily metric
pk = "METRIC#customers"
sk = "2025-11-09"

# With dimensions (via dimensionKey GSI)
dimensionKey = "region:North America"
timestamp = 1699545600
```

#### Attributes

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `pk` | String | Yes | Partition key | Format: `METRIC#{subject}` |
| `sk` | String | Yes | Sort key | Format: `YYYY-QN`, `YYYY-MM`, or `YYYY-MM-DD` |
| `tenantId` | String | Yes | Tenant identifier (denormalized) | Matches table name |
| `metricId` | String | Yes | Unique metric UUID | UUID v4 format |
| `metricType` | String | Yes | Subject (denormalized from pk) | Same as subject in pk |
| `subject` | String | Yes | Business subject | Enum: `revenue`, `margin`, `customers`, `products`, etc. |
| `value` | Number | Yes | Metric value | Can be positive, negative, or zero |
| `unit` | String | Yes | Unit of measure | Enum: `USD`, `EUR`, `count`, `percentage`, etc. |
| `dimensions` | Map | No | Dimensional attributes | Key-value pairs (region, product, etc.) |
| `dimensionKey` | String | No | Composite dimension key | Format: `{dimName}:{dimValue}` |
| `timestamp` | Number | Yes | Unix timestamp (seconds) | > 0 |
| `metadata` | Map | No | Additional metric metadata | Max size: 10KB |

#### Reference Format (Contract Test Required)

For data references in narratives, metrics MUST be formatted as:

```json
{
  "metric": "revenue",
  "period": "2025-Q3",
  "value": 2500000,
  "unit": "USD",
  "dimensions": {
    "region": "North America"
  },
  "source": {
    "table": "tenant-acme-corp-001-metrics",
    "pk": "METRIC#revenue",
    "sk": "2025-Q3"
  }
}
```

**Reference Format Constraints:**
- `metric`: MUST match subject from source
- `period`: MUST match sk from source
- `value`: MUST match value from source
- `unit`: MUST be present and non-empty
- `source`: MUST include table, pk, and sk for traceability

#### Global Secondary Indexes

1. **MetricTypeIndex**
   - Hash Key: `metricType`
   - Range Key: `timestamp`
   - Projection: ALL
   - Use Case: Time-series queries for a specific metric

2. **DimensionIndex**
   - Hash Key: `dimensionKey`
   - Range Key: `timestamp`
   - Projection: ALL
   - Use Case: Query metrics by dimension (e.g., all North America metrics)

#### Example Item

```json
{
  "pk": "METRIC#revenue",
  "sk": "2025-Q3",
  "tenantId": "acme-corp-001",
  "metricId": "metric-uuid-001",
  "metricType": "revenue",
  "subject": "revenue",
  "value": 2500000,
  "unit": "USD",
  "dimensions": {
    "region": "North America",
    "productLine": "Enterprise",
    "segment": "New Business"
  },
  "dimensionKey": "region:North America",
  "timestamp": 1699545600,
  "metadata": {
    "source": "csv_upload",
    "uploadedBy": "admin@acme.com",
    "batchId": "batch-uuid-001"
  }
}
```

---

## 🔒 Idempotency Strategy

### Overview

SalesTalk implements **idempotent ingestion** to ensure data consistency and prevent duplicate processing, even in the face of retries, network failures, or concurrent operations.

### Idempotency Keys

| Operation | Idempotency Key | Storage | TTL |
|-----------|----------------|---------|-----|
| **Message Ingestion** | `messageId` (UUID) | DynamoDB `pk` field | N/A (permanent) |
| **Event Processing** | `eventId` (UUID) | DynamoDB conditional writes | N/A |
| **Metrics Ingestion** | `{tenantId}:{subject}:{period}` | DynamoDB primary key | N/A |
| **Batch Upload** | `batchId` (UUID) | Metadata field | 30 days |

### Ingestion Flow (Idempotent)

```python
# Pseudo-code for idempotent message ingestion
def ingest_message(message: dict) -> dict:
    """
    Idempotent message ingestion using messageId as idempotency key.
    
    Prevents duplicate messages even if function is invoked multiple times.
    """
    message_id = message['messageId']
    tenant_id = message['tenantId']
    
    # Step 1: Attempt conditional write
    try:
        dynamodb.put_item(
            TableName=f'tenant-{tenant_id}-messages',
            Item={
                'pk': f'MSG#{message_id}',
                'sk': message['timestamp'],
                # ... other fields
            },
            ConditionExpression='attribute_not_exists(pk)'  # Fail if already exists
        )
        return {'status': 'created', 'messageId': message_id}
    
    except ConditionalCheckFailedException:
        # Message already exists - this is idempotent, so return success
        return {'status': 'already_exists', 'messageId': message_id}
```

### Retry Strategy

| Scenario | Strategy | Backoff | Max Retries |
|----------|----------|---------|-------------|
| **Network Timeout** | Exponential backoff | 100ms, 200ms, 400ms, ... | 5 |
| **Throttling (ProvisionedThroughputExceeded)** | Exponential backoff with jitter | 100ms, 200ms, 400ms, ... | 10 |
| **Validation Error** | No retry (fail fast) | N/A | 0 |
| **Conditional Check Failed** | No retry (already exists) | N/A | 0 |

### Duplicate Detection

1. **At Ingestion:** Use `ConditionExpression='attribute_not_exists(pk)'`
2. **At Processing:** Check `eventId` in processing metadata before handling event
3. **At API Level:** Generate `requestId` (UUID) and store in DynamoDB for 24 hours

---

## ✅ Data Quality Constraints

### Validation Rules

#### 1. Confidence Fields (Critical)

**Rule:** All confidence scores MUST be in the range [0.0, 1.0] (inclusive)

**Fields:**
- `classification.confidence`
- `classification.components.intent_confidence`
- `classification.components.subject_confidence`
- `classification.components.measure_confidence`
- `classification.components.time_confidence`

**Enforcement:**
- Schema validation before DynamoDB write
- Contract tests in test suite
- API gateway input validation

**Test Cases:**
```python
# Valid
assert 0.0 <= confidence <= 1.0

# Invalid (must reject)
confidence = -0.1  # Too low
confidence = 1.5   # Too high
confidence = None  # Missing
```

#### 2. Reference Format Validation

**Rule:** Data references in narratives MUST include source traceability

**Required Fields:**
- `metric` (string, non-empty)
- `period` (string, valid period format)
- `value` (number)
- `unit` (string, non-empty)
- `source.table` (string, matches tenant table)
- `source.pk` (string, non-empty)
- `source.sk` (string, non-empty)

**Validation:**
```python
def validate_reference(ref: dict) -> bool:
    required_fields = ['metric', 'period', 'value', 'unit']
    source_fields = ['table', 'pk', 'sk']
    
    # Check top-level fields
    if not all(field in ref for field in required_fields):
        return False
    
    # Check source traceability
    if 'source' not in ref:
        return False
    if not all(field in ref['source'] for field in source_fields):
        return False
    
    # Validate value types
    if not isinstance(ref['value'], (int, float)):
        return False
    if not isinstance(ref['metric'], str) or not ref['metric']:
        return False
    
    return True
```

#### 3. Timestamp Validation

**Rule:** All timestamps MUST be valid Unix timestamps in seconds

**Constraints:**
- Must be positive integer
- Must be >= system epoch (1970-01-01)
- Should be <= current time + 1 hour (allow for clock skew)

#### 4. Tenant Isolation

**Rule:** All operations MUST be scoped to the correct tenant

**Enforcement:**
- Extract `tenantId` from JWT at API Gateway
- Validate table name matches `tenant-{tenantId}-*` pattern
- Deny cross-tenant reads/writes with IAM policies

---

## 📊 Event Data Contracts

### Event Confidence Requirements

All `classification.performed.v1` events MUST include:

```json
{
  "data": {
    "classification": {
      "confidence": 0.92,  // MUST be [0.0, 1.0]
      "components": {
        "intent_confidence": 0.95,    // MUST be [0.0, 1.0]
        "subject_confidence": 0.91,   // MUST be [0.0, 1.0]
        "measure_confidence": 0.90,   // MUST be [0.0, 1.0]
        "time_confidence": 0.93       // MUST be [0.0, 1.0]
      }
    }
  }
}
```

### Narrative Generation Requirements

All `narrative.generated.v1` events MUST include:

```json
{
  "data": {
    "dataReferences": [
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
    ],
    "qualityMetrics": {
      "confidenceScore": 0.94  // MUST be [0.0, 1.0]
    }
  }
}
```

---

## 🧪 Contract Test Harness

### Test Categories

1. **Schema Compliance Tests**
   - Validate all required fields present
   - Validate field types match specification
   - Validate nested structures (classification, metadata)

2. **Constraint Tests**
   - Confidence ranges: [0.0, 1.0]
   - Timestamp validity: positive, reasonable range
   - Enum values: valid set membership

3. **Reference Format Tests**
   - Source traceability present
   - Metric/period/value consistency
   - Unit non-empty

4. **Idempotency Tests**
   - Duplicate messageId rejection
   - Duplicate eventId handling
   - Concurrent write scenarios

5. **Tenant Isolation Tests**
   - Cross-tenant access denial
   - Table name validation
   - JWT claim enforcement

### Example Test (pytest)

```python
import pytest
from decimal import Decimal

def test_confidence_range_validation():
    """Test that confidence scores are validated to be in [0.0, 1.0]"""
    
    # Valid confidence scores
    valid_confidences = [0.0, 0.5, 1.0, 0.92, 0.01, 0.99]
    for conf in valid_confidences:
        assert validate_confidence(conf) is True
    
    # Invalid confidence scores
    invalid_confidences = [-0.1, 1.1, 1.5, -1.0, 2.0, None, "0.5"]
    for conf in invalid_confidences:
        assert validate_confidence(conf) is False

def test_reference_format_validation():
    """Test that data references include required traceability"""
    
    valid_ref = {
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
    assert validate_reference(valid_ref) is True
    
    # Missing source
    invalid_ref = {
        "metric": "revenue",
        "period": "2025-Q3",
        "value": 2500000,
        "unit": "USD"
    }
    assert validate_reference(invalid_ref) is False
```

---

## 📖 Related Documents

- **[EVENTS.md](./docs/contracts/EVENTS.md)** - Event schemas and versioning
- **[ARCHITECTURE_OVERVIEW.md](./docs/architecture/ARCHITECTURE_OVERVIEW.md)** - System architecture
- **[dynamodb.tf](../infra/terraform/dynamodb.tf)** - Terraform table definitions

---

**Version History:**

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-09 | Initial data contracts and schemas | Data Engineer Agent |

---

*Data contracts are the foundation of data quality. Design them carefully, test them thoroughly.*
