# 🧩 SalesTalk MVP Specification

**Version:** 1.1  
**Author:** Product Owner Agent  
**Date:** November 2025

---

## 🎯 Vision

SalesTalk helps teams **talk about their business** in a natural, friendly, AI-assisted way — connecting performance data (revenue, margin, customers, products, etc.) with human context.  
It’s a conversational layer over your company’s commercial heartbeat: sales, strategy, and product success.

Users should feel like they’re **talking to a smart colleague** — not querying a database.

---

🎯 Goal

Deliver a conversational analytics assistant that can:
	1.	Understand user questions about key business metrics.
	2.	Classify them into a structured understanding (intent → subject → measure → time → filter).
	3.	Retrieve and generate human-friendly narrative insights from a simple metric dataset.
	4.	Allow sharing or commenting on those insights within a conversation.

---

## 🧱 MVP Scope

### Core Goals
- Enable users to have natural-language conversations about **their company’s performance data**.
- Provide **per-tenant isolation** for data storage and reasoning.
- Support **AI summarization and insights** via AWS Bedrock (cloud) or Ollama (local).
- Provide a **simple web UI** for chat and quick visual summaries.

### What’s Included
✅ Multi-tenant backend (AWS Lambda + API Gateway + DynamoDB per tenant)  
✅ Chat interface (Streamlit frontend)  
✅ Message history storage  
✅ Simple metric summary & sentiment analysis  
✅ Bedrock integration for reasoning  
✅ Localstack + Ollama for offline dev  
✅ Terraform IaC  
✅ GitHub CI/CD pipeline  

### What’s Not Included (Post-MVP)
🚫 Custom dashboards  
🚫 Deep data integrations (CRM, ERP, etc.)  
🚫 User roles/permissions beyond owner  
🚫 Billing & tenant provisioning UI  
🚫 Multi-language support  

---

## 🧩 System Architecture

### High-Level Overview

+—————————–+
|         Frontend            |
| Steamlit for MVP, later React (Vite) + Tailwind UI  |
+———––+—————+
|
v
+———––+—————+
|  API Gateway (per region)   |
|  Auth via Cognito or JWT    |
+———––+—————+
|
v
+———––+—————+
|   AWS Lambda Functions      |
|   - /chat                   |
|   - /metrics                |
|   - /tenants                |
|   - /insights               |
+———––+—————+
|
v
+———––+—————+
|  DynamoDB Tables (1 per tenant)  |
|  Schema: message history, metrics|
+———––+—————+
|
v
+———––+—————+
|     AWS Bedrock / TRM AI     |
|  (Production reasoning layer) |
+———––+—————+
|
v
+———––+—————+
|   S3 + CloudFront (Static Web) |
+––––––––––––––––+

---

## 🧮 Data Model

Each tenant has its own **DynamoDB table**, e.g.:

tenant-1234-messages
tenant-5678-messages
…

### Table Structure
| Field | Type | Description |
|--------|------|-------------|
| `id` | string (PK) | UUID of message |
| `timestamp` | number | Message time (epoch) |
| `sender` | string | "user" or "assistant" |
| `text` | string | Message text |
| `context` | map | Optional — e.g. metric references |
| `metadata` | map | e.g. sessionId, tags |

### Tenant Metadata Table (global)
| Field | Type | Description |
|--------|------|-------------|
| `tenantId` | string (PK) | Unique tenant key |
| `name` | string | Tenant name |
| `ownerEmail` | string | Owner or admin email |
| `tableName` | string | Reference to the per-tenant table |
| `createdAt` | number | Timestamp |

---

## 🧠 AI Layer Integration

| Environment | Model Provider | Description |
|--------------|----------------|--------------|
| **Local Dev** | Ollama | Fast iteration using local LLM (e.g., `mistral`, `llama3`) |
| **Production** | AWS Bedrock | Secure, managed inference via Claude or Titan models |
| **Future** | TRM | Lightweight embedded models for specialized reasoning |

Each chat Lambda can:
1. Retrieve context (e.g. sales data, metrics)
2. Invoke model via Bedrock or Ollama
3. Store conversation to DynamoDB

---

## ⚙️ Local Development

### Using Localstack + Ollama
```bash
docker-compose up

Local endpoints
	•	API Gateway mock: http://localhost:4566/restapis/salestalk/...
	•	DynamoDB: http://localhost:4566
	•	Ollama: http://localhost:11434

Terraform supports two workspaces:
	•	local → deploys to Localstack
	•	aws → deploys to AWS

Example:

terraform workspace select local
terraform apply


⸻

🧰 Tech Stack

Layer	Technology
Frontend	Streamlit, later React + Vite + Tailwind
API	AWS API Gateway
Functions	AWS Lambda (Python or Node)
Data	DynamoDB (per-tenant tables)
Auth	Cognito or JWT authorizer
AI	AWS Bedrock (Claude), Ollama (local), TRM (future)
IaC	Terraform
CI/CD	GitHub Actions
Local	Localstack + Ollama
Monitoring	CloudWatch Logs


⸻

🚀 Deployment Flow
	1.	Create tenant (owner onboarding)
	•	New tenant metadata entry in global table
	•	Terraform Lambda creates per-tenant table automatically
	2.	Frontend login
	•	User authenticates → JWT with tenantId
	3.	Chat session
	•	Requests routed via API Gateway → Lambda → DynamoDB
	4.	AI response
	•	Lambda calls Bedrock → stores result
	5.	Logs + metrics
	•	Exported to CloudWatch / S3 for analysis

⸻

📈 Success Criteria

Metric	Target
First tenant setup time	< 5 minutes
Chat response latency	< 2s average
Local dev startup	< 30s
Cost per tenant (idle)	<$1/month
Clear data isolation	✅ verified per table
Seamless AI switch (local/cloud)	✅ via config


⸻

🧭 Next Steps
	•	Implement tenant onboarding Lambda (table creation + metadata)
	•	Define chat Lambda with Bedrock & Ollama adapters
	•	Deploy Streamlit / React UI to S3 + CloudFront
	•	Add CI/CD GitHub workflow for auto-deploy
	•	Implement basic metric summary endpoint

⸻

🔒 Security & Data Isolation
	•	Each tenant has its own DynamoDB table — physical separation at storage layer.
	•	API Gateway authorizer enforces JWT-based tenant identity.
	•	Tenant ID is embedded in JWT claims and validated before any table access.
	•	CloudWatch logs are tagged with tenantId for traceability.
	•	Optionally, future enterprise plan: separate S3 bucket and Lambda IAM role per tenant.

⸻

🧩 Future Expansion

Area	Description
Integrations	Import sales data from CRM, ERP, or BI tools
Visualization	Metric charts and executive summaries
Multi-agent reasoning	TRM-based tree reasoning per company domain
Multi-language support	Localized chat for EMEA customers
Tenant analytics dashboard	Usage, engagement, and AI insight tracking


⸻

✅ MVP Ready for Implementation

This spec defines a serverless, per-tenant architecture ready to scale from prototype to production.
Next step: hand off to Tech Lead Agent to define the ARCHITECTURE.md and Terraform module layout.
