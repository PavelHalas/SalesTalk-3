# 🏗️ SalesTalk Architecture Documentation

**Phase 1: Domain & Architecture Foundation**

---

## 📚 Documentation Overview

This directory contains the technical architecture and contracts for the SalesTalk conversational intelligence platform.

### Core Documents

| Document | Purpose | Status |
|----------|---------|--------|
| **[ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)** | Complete system architecture, components, and deployment | ✅ Complete |
| **[../contracts/EVENTS.md](../contracts/EVENTS.md)** | Event schemas and versioning strategy | ✅ Complete |
| **DATA_MODEL.md** | Detailed database schemas and indexes | 🔲 Phase 2 |
| **LOCAL_DEV_GUIDE.md** | Step-by-step local development setup | 🔲 Phase 2 |

---

## 🎯 Quick Navigation

### I want to understand...

- **The overall system architecture** → [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)
- **Multi-tenant isolation strategy** → [ARCHITECTURE_OVERVIEW.md#multi-tenant-isolation-strategy](./ARCHITECTURE_OVERVIEW.md#multi-tenant-isolation-strategy)
- **Event-driven patterns** → [../contracts/EVENTS.md](../contracts/EVENTS.md)
- **Non-functional requirements** → [ARCHITECTURE_OVERVIEW.md#non-functional-requirements](./ARCHITECTURE_OVERVIEW.md#non-functional-requirements)
- **Data model and schemas** → [ARCHITECTURE_OVERVIEW.md#data-model](./ARCHITECTURE_OVERVIEW.md#data-model)
- **AWS component interactions** → [ARCHITECTURE_OVERVIEW.md#system-architecture](./ARCHITECTURE_OVERVIEW.md#system-architecture)
- **LocalStack + Ollama setup** → [ARCHITECTURE_OVERVIEW.md#local-development-setup](./ARCHITECTURE_OVERVIEW.md#local-development-setup)

### I want to implement...

- **A new Lambda function** → See [Component Responsibilities](./ARCHITECTURE_OVERVIEW.md#component-responsibilities)
- **A new event type** → See [Event Naming Convention](../contracts/EVENTS.md#event-naming-convention)
- **Terraform modules** → See [Infrastructure as Code](./ARCHITECTURE_OVERVIEW.md#infrastructure-as-code)
- **A new tenant** → See [Tenant Provisioning Flow](./ARCHITECTURE_OVERVIEW.md#data-flow-examples)

---

## 🏛️ Architecture Principles

1. **Serverless-First** - AWS Lambda + API Gateway for operational simplicity
2. **Per-Tenant Isolation** - Dedicated DynamoDB tables for security and compliance  
3. **Event-Driven** - Asynchronous processing via EventBridge/SQS
4. **AI-Context Separation** - Tenant-aware reasoning with strict boundaries
5. **Infrastructure Parity** - LocalStack mirrors AWS for seamless development
6. **Cost-Aware** - Optimized for <100 tenants MVP, scaling to 1K+

---

## 📊 Key Architectural Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Per-tenant DynamoDB tables** | Hard isolation, compliance-ready, performance isolation | More tables to manage |
| **Lambda over ECS** | Lower ops cost for <1K QPS workloads | Cold start latency |
| **Bedrock over self-hosted LLM** | Managed service, lower ops burden | Higher cost, less control |
| **EventBridge for events** | Native AWS integration, powerful routing | Cost at scale |

See [Decision Log](./ARCHITECTURE_OVERVIEW.md#decision-log) for full history.

---

## 🔍 Event Architecture

SalesTalk uses event-driven architecture for decoupled, scalable services.

### Core Events (Phase 1)

| Event Type | Emitted By | Description |
|------------|------------|-------------|
| `classification.performed.v1` | chat-handler | User intent classified |
| `narrative.generated.v1` | chat-handler | AI response generated |
| `conversation.completed.v1` | chat-handler | Session ended |
| `metrics.ingested.v1` | metrics-handler | Business data imported |
| `tenant.provisioned.v1` | tenant-onboard | New tenant created |

→ See [EVENTS.md](../contracts/EVENTS.md) for complete schemas

---

## 🎯 Non-Functional Requirements Summary

| Dimension | Target | Rationale |
|-----------|--------|-----------|
| **Response Time (P95)** | < 2s | Conversational UX requires immediacy |
| **Availability** | > 99.9% | Business-critical insights platform |
| **Cost per Tenant (idle)** | < $1/month | Enable low-tier free plans |
| **Data Isolation** | 100% | Compliance and security requirement |
| **Event Processing Latency** | < 5s | Near real-time insights |

→ See [Non-Functional Requirements](./ARCHITECTURE_OVERVIEW.md#non-functional-requirements) for detailed targets

---

## 🚀 Getting Started

### For Architects
1. Read [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)
2. Review [Multi-Tenant Isolation Strategy](./ARCHITECTURE_OVERVIEW.md#multi-tenant-isolation-strategy)
3. Understand [Non-Functional Requirements](./ARCHITECTURE_OVERVIEW.md#non-functional-requirements)

### For Developers
1. Review [Component Responsibilities](./ARCHITECTURE_OVERVIEW.md#component-responsibilities)
2. Set up [Local Development](./ARCHITECTURE_OVERVIEW.md#local-development-setup)
3. Understand [Event Schemas](../contracts/EVENTS.md)

### For Data Engineers
1. Study [Data Model](./ARCHITECTURE_OVERVIEW.md#data-model)
2. Review per-tenant table structure
3. Understand event-driven data flows

### For Product Managers
1. Review [Architecture Goals](./ARCHITECTURE_OVERVIEW.md#architecture-goals)
2. Understand [Cost Envelope](./ARCHITECTURE_OVERVIEW.md#cost-envelope)
3. Check [Scalability Requirements](./ARCHITECTURE_OVERVIEW.md#scalability-requirements)

---

## 📖 Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| **Vision Brief** | [../VISION_BRIEF.md](../VISION_BRIEF.md) | Product vision and user personas |
| **MVP Spec** | [../MVP_spec.md](../MVP_spec.md) | MVP scope and features |
| **KPI Baseline** | [../KPI_BASELINE.md](../KPI_BASELINE.md) | Success metrics and measurement |
| **Event Contracts** | [../contracts/EVENTS.md](../contracts/EVENTS.md) | Event schemas and versioning |

---

## ✅ Phase 1 Completion Checklist

- [x] System architecture diagram with Mermaid
- [x] Multi-tenant isolation strategy defined
- [x] Event naming conventions established
- [x] Event schemas versioned (v1)
- [x] Non-functional requirements specified
- [x] Deployment topology documented
- [x] Local development approach outlined
- [x] Cost envelope estimated
- [ ] Architecture review signed off _(Pending)_

---

## 🔄 Next Phases

### Phase 2: Data & Ontology Foundation
- Detailed DATA_MODEL.md with indexes and access patterns
- LOCAL_DEV_GUIDE.md with step-by-step setup
- Data seed scripts for development
- Classification ontology definitions

### Phase 3: Implementation
- Terraform modules for all components
- Lambda function implementations
- EventBridge routing rules
- CI/CD pipelines

---

## 📝 Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-09 | Initial architecture foundation | Architect Agent |

---

## 🤝 Contributing

When updating architecture documentation:

1. **Maintain Consistency** - Ensure changes align across all docs
2. **Version Events** - Always version breaking changes to event schemas
3. **Update Decision Log** - Record significant architectural decisions
4. **Cross-reference** - Link related sections across documents
5. **Review Non-Functionals** - Validate changes against NFRs

---

**Architecture Steward:** Architect Agent  
**Last Review:** 2025-11-09  
**Status:** Phase 1 Complete ✅
