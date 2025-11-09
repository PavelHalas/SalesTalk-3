# 📡 SalesTalk Event Contracts

**Version:** 1.0  
**Author:** Architect Agent  
**Date:** November 2025  
**Status:** Phase 1 - Foundation

---

## 📋 Overview

SalesTalk uses an **event-driven architecture** to decouple services and enable asynchronous processing. This document defines:

1. **Event naming conventions**
2. **Event schema versioning strategy**
3. **Core event schemas** (classification.performed.v1, narrative.generated.v1, etc.)
4. **Event lifecycle and routing patterns**

---

## 🎯 Event Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Events are Immutable** | Once published, events cannot be changed |
| **Schema Evolution** | Backward-compatible changes only; breaking changes require new version |
| **Tenant Isolation** | Every event includes `tenantId` for routing and filtering |
| **Idempotent Processing** | Consumers must handle duplicate events gracefully |
| **Versioned Schemas** | Explicit version in event type (e.g., `.v1`, `.v2`) |

---

## 📛 Event Naming Convention

### Pattern

```
{domain}.{action}.{version}
```

**Components:**
- **domain:** Business domain (e.g., `classification`, `conversation`, `metrics`)
- **action:** Past-tense verb describing what happened (e.g., `performed`, `generated`, `ingested`)
- **version:** Schema version (e.g., `v1`, `v2`)

### Examples

| Event Type | Domain | Action | Version |
|------------|--------|--------|---------|
| `classification.performed.v1` | classification | performed | v1 |
| `narrative.generated.v1` | narrative | generated | v1 |
| `conversation.completed.v1` | conversation | completed | v1 |
| `metrics.ingested.v1` | metrics | ingested | v1 |
| `tenant.provisioned.v1` | tenant | provisioned | v1 |

---

## 🔄 Event Versioning Strategy

### Version Evolution Rules

1. **Backward-Compatible Changes (Same Version):**
   - Adding optional fields
   - Adding new enum values
   - Deprecating fields (keep for 6 months)

2. **Breaking Changes (New Version):**
   - Removing required fields
   - Changing field types
   - Renaming fields
   - Changing field semantics

### Version Support Policy

- **Current Version (v1):** Fully supported, recommended for new integrations
- **Previous Version (if exists):** Supported for 6 months after new version release
- **Deprecated Version:** 3 months notice before removal

### Schema Registry

All event schemas are versioned in this document. Future implementation may use:
- AWS EventBridge Schema Registry
- JSON Schema definitions in `/docs/contracts/schemas/`

---

## 📦 Common Event Envelope

All events share a common envelope structure:

```json
{
  "eventId": "uuid-v4",
  "eventType": "domain.action.version",
  "eventVersion": "1.0",
  "source": "service-name",
  "timestamp": "2025-11-09T12:34:56.789Z",
  "tenantId": "tenant-abc123",
  "userId": "user-xyz789",
  "sessionId": "session-uuid",
  "metadata": {
    "correlationId": "uuid-v4",
    "causationId": "parent-event-uuid",
    "traceId": "x-ray-trace-id"
  },
  "data": {
    // Event-specific payload
  }
}
```

### Envelope Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | string (UUID) | Yes | Unique event identifier |
| `eventType` | string | Yes | Event type following naming convention |
| `eventVersion` | string | Yes | Envelope version (currently "1.0") |
| `source` | string | Yes | Service that emitted the event |
| `timestamp` | string (ISO 8601) | Yes | Event creation time (UTC) |
| `tenantId` | string | Yes | Tenant identifier for isolation |
| `userId` | string | No | User who triggered the event (if applicable) |
| `sessionId` | string | No | Conversation session ID (if applicable) |
| `metadata.correlationId` | string (UUID) | Yes | Request correlation ID |
| `metadata.causationId` | string (UUID) | No | Parent event ID (if this event was caused by another) |
| `metadata.traceId` | string | No | AWS X-Ray trace ID for distributed tracing |
| `data` | object | Yes | Event-specific payload |

---

## 🔍 Event Schema Definitions

### 1. classification.performed.v1

**Description:** Emitted when user message classification is completed.

**Source:** `chat-handler` Lambda

**Consumers:** 
- `insights-worker` (for pattern analysis)
- Analytics pipeline (for user intent tracking)

**Schema:**

```json
{
  "eventId": "550e8400-e29b-41d4-a716-446655440000",
  "eventType": "classification.performed.v1",
  "eventVersion": "1.0",
  "source": "chat-handler",
  "timestamp": "2025-11-09T12:34:56.789Z",
  "tenantId": "tenant-abc123",
  "userId": "user-xyz789",
  "sessionId": "session-uuid-001",
  "metadata": {
    "correlationId": "corr-uuid-001",
    "traceId": "1-5e1c6b3d-a9c8b7d6e5f4a3b2c1d0e1f0"
  },
  "data": {
    "messageId": "msg-uuid-001",
    "originalText": "What was revenue in Q3?",
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
      "confidence": 0.92
    },
    "classifierModel": "trm-classifier-v1.2",
    "processingTimeMs": 87
  }
}
```

**Field Definitions (data object):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messageId` | string (UUID) | Yes | Unique message identifier |
| `originalText` | string | Yes | User's original input |
| `classification.intent` | string (enum) | Yes | Classified intent type |
| `classification.subject` | string (enum) | Yes | Business subject (revenue, margin, customers, etc.) |
| `classification.measure` | string (enum) | Yes | Measure type (total, average, count, growth, etc.) |
| `classification.timeRange` | object | No | Time period specification |
| `classification.filters` | array | Yes | Additional filters (region, product, etc.) |
| `classification.confidence` | number (0-1) | Yes | Classification confidence score |
| `classifierModel` | string | Yes | Model version used |
| `processingTimeMs` | number | Yes | Classification latency |

**Intent Enum Values:**

- `fact_retrieval` - User asks for specific data point
- `comparison` - User compares two periods/entities
- `trend_analysis` - User asks about changes over time
- `root_cause` - User asks "why" something happened
- `prediction` - User asks for forecast (post-MVP)
- `list` - User asks for list of entities
- `unknown` - Unable to classify

**Subject Enum Values:**

- `revenue` - Sales revenue
- `margin` - Profit margin
- `customers` - Customer metrics
- `products` - Product performance
- `pipeline` - Sales pipeline
- `deals` - Individual deals
- `unknown` - Unable to classify

**Measure Enum Values:**

- `total` - Sum/total value
- `average` - Mean value
- `count` - Number of entities
- `growth` - Percentage or absolute change
- `ratio` - Proportion or percentage
- `rate` - Velocity or frequency

---

### 2. narrative.generated.v1

**Description:** Emitted when AI narrative is successfully generated.

**Source:** `chat-handler` Lambda

**Consumers:**
- Analytics pipeline (for quality monitoring)
- Caching service (for response caching)
- Audit log (for compliance)

**Schema:**

```json
{
  "eventId": "660e8400-e29b-41d4-a716-446655440001",
  "eventType": "narrative.generated.v1",
  "eventVersion": "1.0",
  "source": "chat-handler",
  "timestamp": "2025-11-09T12:35:02.456Z",
  "tenantId": "tenant-abc123",
  "userId": "user-xyz789",
  "sessionId": "session-uuid-001",
  "metadata": {
    "correlationId": "corr-uuid-001",
    "causationId": "550e8400-e29b-41d4-a716-446655440000",
    "traceId": "1-5e1c6b3d-a9c8b7d6e5f4a3b2c1d0e1f0"
  },
  "data": {
    "messageId": "msg-uuid-002",
    "conversationId": "session-uuid-001",
    "userMessageId": "msg-uuid-001",
    "narrativeText": "Revenue in Q3 2025 was $2.5M, representing a 15% increase from Q2 2025 ($2.17M). The growth was primarily driven by new enterprise deals in North America (+$180K) and strong renewal rates (95%, up from 89% last quarter).",
    "classification": {
      "intent": "fact_retrieval",
      "subject": "revenue",
      "measure": "total"
    },
    "dataReferences": [
      {
        "metric": "revenue",
        "period": "2025-Q3",
        "value": 2500000,
        "unit": "USD"
      },
      {
        "metric": "revenue",
        "period": "2025-Q2",
        "value": 2170000,
        "unit": "USD"
      },
      {
        "metric": "renewal_rate",
        "period": "2025-Q3",
        "value": 0.95,
        "unit": "percentage"
      }
    ],
    "aiModel": {
      "provider": "bedrock",
      "modelId": "anthropic.claude-v2",
      "temperature": 0.3,
      "maxTokens": 500
    },
    "performance": {
      "totalTimeMs": 1834,
      "classificationMs": 87,
      "dataRetrievalMs": 143,
      "aiGenerationMs": 1542,
      "validationMs": 62
    },
    "tokenUsage": {
      "promptTokens": 387,
      "completionTokens": 156,
      "totalTokens": 543
    },
    "cost": {
      "amountUSD": 0.0217,
      "currency": "USD"
    },
    "qualityMetrics": {
      "hallucinationDetected": false,
      "factsVerified": 3,
      "factsTotal": 3,
      "confidenceScore": 0.94
    }
  }
}
```

**Field Definitions (data object):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messageId` | string (UUID) | Yes | Assistant message ID |
| `conversationId` | string (UUID) | Yes | Session/conversation ID |
| `userMessageId` | string (UUID) | Yes | Reference to user's message |
| `narrativeText` | string | Yes | Generated narrative response |
| `classification` | object | Yes | Simplified classification context |
| `dataReferences` | array | Yes | All data points referenced in narrative |
| `aiModel.provider` | string (enum) | Yes | AI provider: `bedrock`, `ollama` |
| `aiModel.modelId` | string | Yes | Specific model identifier |
| `aiModel.temperature` | number (0-1) | Yes | Model temperature setting |
| `aiModel.maxTokens` | number | Yes | Max tokens allowed |
| `performance` | object | Yes | Timing breakdown |
| `tokenUsage` | object | Yes | Token consumption |
| `cost.amountUSD` | number | Yes | Estimated cost in USD |
| `qualityMetrics` | object | Yes | Quality and validation metrics |

---

### 3. conversation.completed.v1

**Description:** Emitted when a user conversation session ends (timeout or explicit end).

**Source:** `chat-handler` Lambda or session-manager

**Consumers:**
- Analytics pipeline (for engagement metrics)
- Billing service (for usage tracking)
- Archival service (for conversation archival)

**Schema:**

```json
{
  "eventId": "770e8400-e29b-41d4-a716-446655440002",
  "eventType": "conversation.completed.v1",
  "eventVersion": "1.0",
  "source": "chat-handler",
  "timestamp": "2025-11-09T12:45:00.000Z",
  "tenantId": "tenant-abc123",
  "userId": "user-xyz789",
  "sessionId": "session-uuid-001",
  "metadata": {
    "correlationId": "corr-uuid-002",
    "traceId": "1-5e1c6b3d-a9c8b7d6e5f4a3b2c1d0e1f1"
  },
  "data": {
    "conversationId": "session-uuid-001",
    "startTime": "2025-11-09T12:34:00.000Z",
    "endTime": "2025-11-09T12:45:00.000Z",
    "durationSeconds": 660,
    "messageCount": 8,
    "userMessageCount": 4,
    "assistantMessageCount": 4,
    "subjects": ["revenue", "margin"],
    "intents": ["fact_retrieval", "comparison"],
    "actionsTaken": {
      "insightSaved": true,
      "insightShared": false,
      "dataExported": false,
      "followUpCreated": true
    },
    "satisfactionRating": 5,
    "totalCostUSD": 0.087,
    "averageResponseTimeMs": 1923
  }
}
```

**Field Definitions (data object):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversationId` | string (UUID) | Yes | Session identifier |
| `startTime` | string (ISO 8601) | Yes | Conversation start timestamp |
| `endTime` | string (ISO 8601) | Yes | Conversation end timestamp |
| `durationSeconds` | number | Yes | Total duration |
| `messageCount` | number | Yes | Total messages (user + assistant) |
| `userMessageCount` | number | Yes | User messages |
| `assistantMessageCount` | number | Yes | Assistant messages |
| `subjects` | array[string] | Yes | Unique subjects discussed |
| `intents` | array[string] | Yes | Unique intents identified |
| `actionsTaken` | object | Yes | Boolean flags for actions |
| `satisfactionRating` | number (1-5) | No | User satisfaction rating |
| `totalCostUSD` | number | Yes | Total AI cost for conversation |
| `averageResponseTimeMs` | number | Yes | Average assistant response time |

---

### 4. metrics.ingested.v1

**Description:** Emitted when business metrics data is successfully ingested.

**Source:** `metrics-handler` Lambda

**Consumers:**
- Aggregation worker (for pre-computation)
- Validation service (for data quality checks)
- Audit log (for compliance)

**Schema:**

```json
{
  "eventId": "880e8400-e29b-41d4-a716-446655440003",
  "eventType": "metrics.ingested.v1",
  "eventVersion": "1.0",
  "source": "metrics-handler",
  "timestamp": "2025-11-09T08:00:15.234Z",
  "tenantId": "tenant-abc123",
  "userId": "admin-user-001",
  "metadata": {
    "correlationId": "corr-uuid-003",
    "traceId": "1-5e1c6b3d-a9c8b7d6e5f4a3b2c1d0e1f2"
  },
  "data": {
    "batchId": "batch-uuid-001",
    "source": "csv_upload",
    "fileName": "Q3_revenue_2025.csv",
    "recordCount": 247,
    "metricsIngested": [
      {
        "subject": "revenue",
        "period": "2025-Q3",
        "value": 2500000,
        "unit": "USD",
        "dimensions": {
          "region": "North America",
          "productLine": "Enterprise"
        }
      }
    ],
    "validationResults": {
      "valid": 247,
      "invalid": 0,
      "warnings": 3
    },
    "processingTimeMs": 1234
  }
}
```

**Field Definitions (data object):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `batchId` | string (UUID) | Yes | Unique batch identifier |
| `source` | string (enum) | Yes | Ingestion source: `csv_upload`, `api`, `integration` |
| `fileName` | string | No | File name if uploaded via file |
| `recordCount` | number | Yes | Total records in batch |
| `metricsIngested` | array | Yes | Sample of ingested metrics |
| `validationResults` | object | Yes | Validation summary |
| `processingTimeMs` | number | Yes | Processing time |

---

### 5. tenant.provisioned.v1

**Description:** Emitted when a new tenant is successfully onboarded.

**Source:** `tenant-onboard` Lambda

**Consumers:**
- Billing service (for account creation)
- Email service (for welcome email)
- Analytics (for tenant tracking)

**Schema:**

```json
{
  "eventId": "990e8400-e29b-41d4-a716-446655440004",
  "eventType": "tenant.provisioned.v1",
  "eventVersion": "1.0",
  "source": "tenant-onboard",
  "timestamp": "2025-11-09T10:00:00.000Z",
  "tenantId": "tenant-abc123",
  "userId": "admin-user-001",
  "metadata": {
    "correlationId": "corr-uuid-004",
    "traceId": "1-5e1c6b3d-a9c8b7d6e5f4a3b2c1d0e1f3"
  },
  "data": {
    "tenantId": "tenant-abc123",
    "organizationName": "Acme Corporation",
    "ownerEmail": "admin@acme.com",
    "plan": "standard",
    "region": "us-east-1",
    "resources": {
      "messagesTableName": "tenant-abc123-messages",
      "metricsTableName": "tenant-abc123-metrics",
      "s3Prefix": "tenant-abc123/"
    },
    "provisioningTimeMs": 3456,
    "sampleDataSeeded": true
  }
}
```

---

## 🔀 Event Routing Patterns

### EventBridge Rules

Events are routed based on event type and tenant context:

```json
{
  "source": ["chat-handler"],
  "detail-type": ["classification.performed.v1"],
  "detail": {
    "tenantId": ["tenant-abc123"]
  }
}
```

### Routing Table

| Event Type | Target | Description |
|------------|--------|-------------|
| `classification.performed.v1` | `insights-queue` | For pattern analysis |
| `narrative.generated.v1` | `analytics-stream` | For quality monitoring |
| `conversation.completed.v1` | `archival-queue`, `billing-queue` | For archival and billing |
| `metrics.ingested.v1` | `aggregation-queue` | For pre-computation |
| `tenant.provisioned.v1` | `welcome-email-queue`, `billing-queue` | For onboarding |

### Dead Letter Queue (DLQ)

All event consumers have DLQ for failed processing:
- **Retention:** 14 days
- **Retry Strategy:** Exponential backoff (3 attempts)
- **Alerting:** CloudWatch alarm on DLQ depth > 10

---

## 🧪 Event Testing Strategy

### Test Event Generator

```python
# Example test event generation
def create_classification_event(tenant_id: str, message: str) -> dict:
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": "classification.performed.v1",
        "eventVersion": "1.0",
        "source": "test-harness",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tenantId": tenant_id,
        "data": {
            "messageId": str(uuid.uuid4()),
            "originalText": message,
            # ... rest of schema
        }
    }
```

### Consumer Testing

Each event consumer must have:
1. **Unit tests** with mock events
2. **Integration tests** with LocalStack EventBridge
3. **Contract tests** validating schema compliance
4. **Idempotency tests** ensuring duplicate handling

---

## 📊 Event Monitoring

### Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Event Publish Success Rate** | > 99.9% | < 99.0% |
| **Event Processing Latency (P95)** | < 5s | > 30s |
| **DLQ Depth** | 0 | > 10 messages |
| **Consumer Error Rate** | < 0.1% | > 1% |

### CloudWatch Dashboards

- Event volume by type (24h, 7d, 30d)
- Processing latency per consumer
- Error rates and DLQ depths
- Cost per event type

---

## 🔄 Event Replay

For debugging or data recovery, events can be replayed:

1. **Query CloudWatch Logs:** Filter by `eventId` or `tenantId`
2. **Extract Event:** Copy event JSON from logs
3. **Publish to EventBridge:** Use `PutEvents` API
4. **Monitor Processing:** Track via `correlationId`

**Replay SLA:** Events retained for 14 days (DLQ) or 90 days (S3 archive)

---

## 📝 Schema Validation

All events must pass JSON Schema validation before publishing:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["eventId", "eventType", "eventVersion", "source", "timestamp", "tenantId", "data"],
  "properties": {
    "eventId": {"type": "string", "format": "uuid"},
    "eventType": {"type": "string", "pattern": "^[a-z]+\\.[a-z]+\\.v[0-9]+$"},
    "eventVersion": {"type": "string"},
    "source": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "tenantId": {"type": "string"},
    "data": {"type": "object"}
  }
}
```

---

## 🚀 Roadmap

### Phase 1 (Current)
- [x] Core event schemas defined
- [x] Versioning strategy established
- [ ] EventBridge integration
- [ ] Schema validation implementation

### Phase 2
- [ ] AWS EventBridge Schema Registry integration
- [ ] Automated schema evolution testing
- [ ] Event replay UI/tooling
- [ ] Consumer SLA monitoring

### Phase 3
- [ ] Cross-region event replication
- [ ] Event sourcing for audit trail
- [ ] Real-time event streaming dashboard

---

## 📚 Related Documents

- **[ARCHITECTURE_OVERVIEW.md](../architecture/ARCHITECTURE_OVERVIEW.md)** - System architecture
- **[../VISION_BRIEF.md](../VISION_BRIEF.md)** - Product vision
- **[../KPI_BASELINE.md](../KPI_BASELINE.md)** - Measurement framework

---

**Version History:**

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-09 | Initial event schemas and versioning strategy | Architect Agent |

---

**Review & Approval:**

- [ ] Architect Agent: _____________________ Date: ___________
- [ ] Data Engineer: _____________________ Date: ___________
- [ ] Developer Lead: _____________________ Date: ___________

---

*Events are the nervous system of SalesTalk. Design them carefully.*
