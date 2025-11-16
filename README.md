# 🎯 SalesTalk - Conversational Intelligence Platform

**Turn data into conversation. Turn conversation into understanding. Turn understanding into better decisions.**

---

## 🌟 Overview

SalesTalk is a conversational intelligence platform that transforms how teams understand and act on their business performance. Instead of navigating complex dashboards, users simply talk about what matters—revenue, margin, customers, products—and receive clear, context-aware insights.

**Status:** Phase 1 - Architecture Foundation Complete ✅

---

## 📚 Documentation

### Core Documents

| Document | Purpose |
|----------|---------|
| **[Vision Brief](./docs/VISION_BRIEF.md)** | Product vision, user personas, and exemplar questions |
| **[MVP Specification](./docs/MVP_spec.md)** | MVP scope, features, and technical stack |
| **[KPI Baseline](./docs/KPI_BASELINE.md)** | Success metrics and measurement framework |

### Architecture & Contracts

| Document | Purpose |
|----------|---------|
| **[Architecture Overview](./docs/architecture/ARCHITECTURE_OVERVIEW.md)** | System architecture, components, and deployment |
| **[Event Contracts](./docs/contracts/EVENTS.md)** | Event schemas and versioning strategy |
| **[Architecture README](./docs/architecture/README.md)** | Navigation guide for architecture docs |

---

## 🏗️ Architecture Highlights

- **Serverless-First:** AWS Lambda + API Gateway + DynamoDB
- **Multi-Tenant Isolation:** Dedicated DynamoDB tables per tenant
- **Event-Driven:** EventBridge + SQS for async processing
- **AI Integration:** AWS Bedrock (production) + Ollama (local development)
- **Infrastructure as Code:** Terraform for all AWS resources
- **Local Development:** LocalStack + Ollama for full parity

→ See [Architecture Overview](./docs/architecture/ARCHITECTURE_OVERVIEW.md) for details

---

## 🎯 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Streamlit (MVP), React + Vite (future) |
| **API** | AWS API Gateway (HTTP API) |
| **Compute** | AWS Lambda (Python) |
| **Data** | DynamoDB (per-tenant tables), S3 |
| **AI** | AWS Bedrock (Claude), Ollama (local) |
| **Events** | EventBridge, SQS |
| **Auth** | Cognito (JWT + tenant claim) |
| **IaC** | Terraform |
| **CI/CD** | GitHub Actions |
| **Local Dev** | LocalStack + Ollama |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Terraform >= 1.5
- AWS CLI (for production deployment)
- Python 3.11+ (for Lambda development)

### Local Development Setup

```bash
# Start LocalStack + Ollama
docker-compose up -d

# Deploy infrastructure to LocalStack
terraform workspace select local
terraform init
terraform apply

# Run frontend
cd frontend
streamlit run app.py
```

→ See [Local Development Guide](./docs/architecture/ARCHITECTURE_OVERVIEW.md#local-development-setup) for full setup

### E2E Tests (Streaming Progress)

Run the product owner question suite with per-question ticks/crosses:

```bash
./run_e2e.sh                # defaults to llama3.2:latest
./run_e2e.sh dolphin-mistral:latest
```

Each question prints expected vs actual classification components. Disable streaming with `VERBOSE_E2E=false`.

---

## 📊 Key Features (MVP)

✅ **Conversational Q&A** - Natural language queries about business metrics  
✅ **Intent Classification** - TRM-based understanding of user questions  
✅ **Narrative Generation** - AI-powered explanations with context  
✅ **Multi-Tenant Isolation** - Per-tenant data security  
✅ **Event-Driven Processing** - Async workflows for insights  
✅ **Local Development** - Full AWS simulation locally  

---

## 🎭 Example Interactions

**User:** "What was revenue in Q3?"

**SalesTalk:** "Revenue in Q3 2025 was $2.5M, representing a 15% increase from Q2 2025 ($2.17M). The growth was primarily driven by new enterprise deals in North America (+$180K) and strong renewal rates (95%, up from 89% last quarter)."

---

**User:** "Why is margin down?"

**SalesTalk:** "I'd be happy to help you understand margin performance. Which time period would you like to analyze? This month, this quarter, or a custom range?"

---

## 🏛️ Architecture Principles

1. **Serverless-First** - Leverage AWS Lambda for low operational overhead
2. **Per-Tenant Isolation** - Each tenant owns separate DynamoDB tables
3. **Event-Driven** - Async processing via EventBridge/SQS
4. **AI-Context Separation** - Tenant-aware reasoning with strict boundaries
5. **Infrastructure Parity** - LocalStack mirrors production AWS
6. **Cost-Aware** - Optimized for <100 tenants MVP, scaling to 1K+

---

## 📈 Non-Functional Requirements

| Metric | Target |
|--------|--------|
| **Response Time (P95)** | < 2s |
| **Availability** | > 99.9% |
| **Cost per Tenant (idle)** | < $1/month |
| **Data Isolation** | 100% table-level |

→ See [Non-Functional Requirements](./docs/architecture/ARCHITECTURE_OVERVIEW.md#non-functional-requirements) for complete targets

---

## 🔄 Development Workflow

### Phase 1: Architecture Foundation ✅
- [x] System architecture diagram
- [x] Multi-tenant isolation strategy
- [x] Event schemas (v1)
- [x] Non-functional requirements
- [ ] Architecture review sign-off _(Pending)_

### Phase 2: Data & Ontology Foundation (Next)
- [ ] Data model documentation
- [ ] Classification ontology
- [ ] Data seed scripts
- [ ] Local development guide

### Phase 3: Implementation
- [ ] Terraform modules
- [ ] Lambda functions
- [ ] Frontend UI
- [ ] CI/CD pipelines

---

## 📡 Event-Driven Architecture

SalesTalk uses events for asynchronous, decoupled processing:

- `classification.performed.v1` - User intent classified
- `narrative.generated.v1` - AI response generated
- `conversation.completed.v1` - Session ended
- `metrics.ingested.v1` - Business data imported
- `tenant.provisioned.v1` - New tenant created

→ See [Event Contracts](./docs/contracts/EVENTS.md) for schemas

---

## 🤝 Contributing

This is an AI-agent-driven project. Contributions are coordinated by specialized agents:

- **Architect Agent** - System design and non-functional requirements
- **Product Owner Agent** - Vision, scope, and priorities
- **Developer Agent** - Implementation and code quality
- **Data Engineer Agent** - Data pipelines and storage
- **Data Science Agent** - AI/ML models and evaluation
- **UX Agent** - User experience and conversation flows
- **Tester Agent** - Quality assurance and testing

→ See [Agent Responsibilities](./docs/agents/Responsibilities.md)

---

## 📝 Project Status

**Current Phase:** Phase 1 - Architecture Foundation  
**Status:** ✅ Complete (pending review sign-off)  
**Next Phase:** Phase 2 - Data & Ontology Foundation  
**Target Launch:** Q1 2026

---

## 📖 Additional Resources

- [Vision Brief](./docs/VISION_BRIEF.md) - Product strategy and user personas
- [MVP Spec](./docs/MVP_spec.md) - Features and scope
- [KPI Baseline](./docs/KPI_BASELINE.md) - Success metrics
- [Architecture Overview](./docs/architecture/ARCHITECTURE_OVERVIEW.md) - Technical architecture
- [Event Contracts](./docs/contracts/EVENTS.md) - Event schemas

---

## 🔐 Security & Compliance

- ✅ **Tenant Isolation:** Per-tenant DynamoDB tables
- ✅ **Data Encryption:** SSE for DynamoDB and S3
- ✅ **Authentication:** JWT via Cognito with tenant claims
- ✅ **Authorization:** IAM policies per tenant
- ✅ **Audit Logging:** CloudWatch Logs + X-Ray tracing

---

## 📞 Contact

**Project:** SalesTalk Conversational Intelligence  
**Repository:** github.com/PavelHalas/SalesTalk-3  
**Documentation:** [docs/](./docs/)

---

*This project is in active development. Documentation evolves with implementation.*