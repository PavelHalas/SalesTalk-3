# 📡 SalesTalk Event Contracts

**Event-Driven Architecture Documentation**

---

## 📚 Overview

This directory contains the event contracts and schemas for SalesTalk's event-driven architecture.

### Documents

| Document | Purpose | Status |
|----------|---------|--------|
| **[EVENTS.md](./EVENTS.md)** | Event schemas, versioning, and routing patterns | ✅ Phase 1 Complete |
| **API_CONTRACTS.md** | REST API contracts and OpenAPI specs | 🔲 Phase 2 |
| **DATA_CONTRACTS.md** | DynamoDB and S3 data contracts | 🔲 Phase 2 |

---

## 🎯 Quick Reference

### Event Types (v1)

| Event Type | Source | Purpose |
|------------|--------|---------|
| `classification.performed.v1` | chat-handler | User message classified |
| `narrative.generated.v1` | chat-handler | AI narrative generated |
| `conversation.completed.v1` | chat-handler | Conversation session ended |
| `metrics.ingested.v1` | metrics-handler | Business metrics imported |
| `tenant.provisioned.v1` | tenant-onboard | New tenant created |

→ See [EVENTS.md](./EVENTS.md) for complete schemas

---

## 📛 Naming Convention

Events follow the pattern: **`{domain}.{action}.{version}`**

**Examples:**
- `classification.performed.v1` - Classification domain, performed action, version 1
- `narrative.generated.v2` - Narrative domain, generated action, version 2

**Rules:**
- Domain: lowercase, singular noun
- Action: past tense verb
- Version: `v{number}` (semantic versioning at event type level)

---

## 🔄 Versioning Strategy

### Backward-Compatible Changes (Same Version)
✅ Add optional fields  
✅ Add new enum values  
✅ Deprecate fields (with 6-month notice)

### Breaking Changes (New Version)
🚫 Remove required fields → Requires new version  
🚫 Change field types → Requires new version  
🚫 Rename fields → Requires new version

**Version Support Policy:**
- **Current (v1):** Fully supported
- **Previous (if exists):** 6 months after new version
- **Deprecated:** 3 months notice before removal

---

## 📦 Common Event Envelope

All events share this structure:

```json
{
  "eventId": "uuid",
  "eventType": "domain.action.version",
  "eventVersion": "1.0",
  "source": "service-name",
  "timestamp": "ISO 8601",
  "tenantId": "tenant-xxx",
  "userId": "user-yyy",
  "sessionId": "session-zzz",
  "metadata": {
    "correlationId": "uuid",
    "causationId": "parent-event-uuid",
    "traceId": "x-ray-trace-id"
  },
  "data": {
    // Event-specific payload
  }
}
```

---

## 🔀 Event Flow Examples

### Example 1: Chat Flow

```
User Message
    ↓
classification.performed.v1 emitted
    ↓
[insights-queue processes classification]
    ↓
narrative.generated.v1 emitted
    ↓
[analytics-stream monitors quality]
    ↓
conversation.completed.v1 emitted
```

### Example 2: Metrics Ingestion

```
CSV Upload
    ↓
metrics.ingested.v1 emitted
    ↓
[aggregation-queue pre-computes summaries]
    ↓
[validation-queue checks data quality]
```

---

## 🧪 Testing Events

### Generate Test Event

```python
import uuid
from datetime import datetime

def create_test_event(event_type: str, tenant_id: str, data: dict):
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "eventVersion": "1.0",
        "source": "test-harness",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tenantId": tenant_id,
        "metadata": {
            "correlationId": str(uuid.uuid4())
        },
        "data": data
    }
```

### Validate Schema

All events must pass JSON Schema validation before publishing.

→ See [Schema Validation](./EVENTS.md#schema-validation) in EVENTS.md

---

## 📊 Event Monitoring

### Key Metrics

- **Event Publish Success Rate:** > 99.9%
- **Event Processing Latency (P95):** < 5s
- **DLQ Depth:** 0 (alert > 10)
- **Consumer Error Rate:** < 0.1%

### CloudWatch Dashboards

- Event volume by type
- Processing latency per consumer
- Error rates and DLQ depths
- Cost per event type

---

## 🚀 Adding a New Event

1. **Define Schema** in [EVENTS.md](./EVENTS.md)
2. **Follow Naming Convention:** `{domain}.{action}.v1`
3. **Include All Required Envelope Fields**
4. **Document Consumer Use Cases**
5. **Add Routing Rules** to EventBridge
6. **Create Unit Tests** for event generation
7. **Update This README** with new event type

---

## 🔗 Related Documentation

- **[Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md)** - System architecture
- **[Vision Brief](../VISION_BRIEF.md)** - Product vision
- **[KPI Baseline](../KPI_BASELINE.md)** - Measurement framework

---

## 📝 Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-09 | Initial event contracts (v1) | Architect Agent |

---

**Contract Owner:** Architect Agent  
**Last Review:** 2025-11-09  
**Status:** Phase 1 Complete ✅
