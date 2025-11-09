ARCHITECTURE.md

SalesTalk — Architecture (Lambda-based, per-tenant DynamoDB)
Version: 1.0
Owner: Architect Copilot
Date: November 2025

⸻

Overview — high-level intent

This document describes the serverless architecture for SalesTalk optimized for multi-tenant isolation (1 DynamoDB table per tenant), cost-efficiency (AWS Lambda + API Gateway), and developer experience (LocalStack + Ollama locally, Bedrock in production). It includes component diagrams, Terraform module structure, IAM guidance, deployment flow, and local development notes.

⸻

System components (summary)
	•	Frontend: Steamlit app hosted on S3 + CloudFront. Talks to API Gateway.
	•	Auth: Amazon Cognito (or custom JWT) — tenantId contained in token claims.
	•	API Gateway: HTTP API (low latency) -> Lambda integration.
	•	Lambdas:
	•	tenant-onboard — creates tenant metadata & Dynamo table.
	•	chat-handler — main chat endpoint: classify → fetch data → call model → persist.
	•	metrics-handler — ingestion & simple aggregations.
	•	insights-worker — async enrichment, batch jobs.
	•	AI:
	•	Local: Ollama (dev)
	•	Prod: AWS Bedrock (Claude/Titan) or TRM container as needed
	•	Data:
	•	Per-tenant DynamoDB table(s): tenant-<id>-messages, tenant-<id>-metrics
	•	Global metadata table: tenants-metadata
	•	Storage: S3 for archived conversations & exports
	•	Observability: CloudWatch Logs, X-Ray, OpenTelemetry collector (optional)
	•	IaC & CI: Terraform modules + GitHub Actions

⸻

Architecture diagram

Mermaid flow (can be rendered in README viewers that support it):

flowchart LR
  subgraph User
    A[Browser / Streamlit Frontend]
  end

  A -->|HTTPS JWT| APIGW[API Gateway]
  APIGW --> LambdaChat[Lambda: chat-handler]
  APIGW --> LambdaTenant[Lambda: tenant-onboard]
  LambdaChat -->|Query| TenantTable[(DynamoDB per-tenant)]
  LambdaChat -->|Invoke| Bedrock[Bedrock / Ollama]
  LambdaChat -->|Store| TenantTable
  LambdaChat -->|Write| S3Archived[(S3)]
  LambdaTenant -->|Create Table| DynamoAdmin[(Terraform / CloudFormation)]
  Bedrock -->|Response| LambdaChat
  S3Archived -->|CloudFront| A
  APIGW -->|AuthN| Cognito[(Cognito)]
  style TenantTable fill:#fef4e6,stroke:#f5b041


⸻

Key design decisions (why)
	•	Per-tenant DynamoDB tables provide strong storage segregation and allow different throughput/retention policies per customer (enterprise vs standard).
	•	Lambda-first architecture minimizes operational overhead and reduces idle cost for low to moderate QPS.
	•	API Gateway HTTP APIs give straightforward routing and native authorizers for Cognito/JWT.
	•	Bedrock (prod) / Ollama (local) split enables low-friction local development and secure scale in production.
	•	Terraform standardizes both localstack and AWS deployments via workspaces.

⸻

DynamoDB per-tenant table schema (recommended)

Table name: tenant-<TENANT_ID>-messages

Primary Key:
	•	pk (STRING) — e.g., MSG#<uuid> or METRIC#<subject>#<yyyy-mm>
	•	sk (STRING) — timestamp or sort key (e.g., 2025-11-09T12:00:00Z)

Attributes:
	•	tenantId (STRING) — denormalized (for admin queries)
	•	messageId (STRING)
	•	timestamp (NUMBER)
	•	sender (STRING) — user / assistant / system
	•	text (STRING)
	•	context (MAP) — classification JSON
	•	metadata (MAP) — sessionId, source, tags, cost, modelVersion

GSI (optional): GSI1 for sessionId –> query message history quickly.

For metrics tables (if separate): pk=METRIC#<subject> and sk=YYYY-Q# or YYYY-MM.

⸻

Tenant provisioning flow (detailed)
	1.	Admin hits /tenants (or onboarding UI) → API Gateway → tenant-onboard Lambda.
	2.	tenant-onboard validates request (owner email, plan), registers tenant in tenants-metadata global table.
	3.	tenant-onboard triggers Terraform (or CloudFormation) to create per-tenant DynamoDB tables and S3 prefixes and optionally a dedicated IAM role for advanced enterprise isolation.
	•	Implementation choices:
	•	Option A: Lambda calls a management service (an API) that triggers Terraform Cloud workspace for tenant table creation.
	•	Option B: Use AWS SDK in Lambda to create DynamoDB table directly (fast, simpler).
	4.	Return provisioning result and credentials; add tenantId claim to Cognito group or issue initial admin invite.

Note: For MVP prefer Option B (Lambda uses AWS SDK to create table) because it’s fast and simple to implement. For enterprise-grade, use Terraform Cloud or a control plane to create infra as code for auditability.

⸻

Authorization & tenant enforcement
	•	Every request must include JWT with tenantId claim (Cognito custom claim or your own).
	•	API Gateway authorizer verifies token and sets principalId + tenantId in context.
	•	Each Lambda must:
	•	Read tenantId from request context, not from body.
	•	Use tenant-specific table name (or lookup from tenants-metadata).
	•	Validate access (owner, admin) on sensitive operations.
	•	IAM model:
	•	Management account has permission to create tables.
	•	Runtime Lambdas use least privilege for the tenant resources they access. For per-tenant IAM roles (advanced), grant Lambda role only the table name corresponding to that tenant.

⸻

Lambda responsibilities & patterns
	•	chat-handler:
	•	Validate JWT & tenantId
	•	Run TRM classifier (local container or separate Lambda / container)
	•	Query DynamoDB per-tenant metrics/messages
	•	Build context for model call
	•	Call Ollama (local) or Bedrock (prod) with chosen model
	•	Persist assistant message to tenant table
	•	Return response and cost metadata
	•	tenant-onboard:
	•	Create per-tenant table(s)
	•	Seed example data & indexes if requested
	•	Create S3 prefix and optionally KMS key
	•	Register tenant metadata row
	•	metrics-handler:
	•	Accept CSV / API push from admin
	•	Normalize & store metrics into tenant-<id>-metrics table
	•	Trigger aggregation lambdas or stream to S3 for batch jobs
	•	insights-worker (async):
	•	Triggered by DynamoDB Streams or SQS for heavy tasks (batch narratives, scheduled jobs)

⸻

AI integration (Ollama local, Bedrock prod)

Local (dev):
	•	Run Ollama as a container. chat-handler calls http://ollama:11434 or local host.
	•	TRM classifier runs either embedded or on a small local container.

Prod:
	•	chat-handler calls Bedrock via AWS SDK:
	•	Build prompt using classification and small context window from DynamoDB
	•	Call Bedrock text generation
	•	Consider response post-processing and hallucination guard (check facts vs cached metrics)

Cost & latency notes:
	•	Keep prompt size minimal: include only classification JSON, essential metrics, and one-paragraph system instruction.
	•	Cache frequent results in per-tenant S3 or Dynamo (TTL) where possible.

⸻

Terraform module structure (recommended)

infra/
├── modules/
│   ├── tenant_table/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── lambda/
│   │   ├── main.tf
│   │   └── ...
│   ├── apigateway/
│   └── bedrock_integration/
├── envs/
│   ├── local/
│   │   └── backend.tfvars
│   └── prod/
│       └── backend.tfvars
├── main.tf
└── versions.tf

Example modules/tenant_table/main.tf (sketch)

variable "tenant_id" { type = string }

resource "aws_dynamodb_table" "tenant_table" {
  name           = "tenant-${var.tenant_id}-messages"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }

  tags = {
    Tenant = var.tenant_id
    Project = "SalesTalk"
  }
}

Use a root tenant-onboard mechanism to call this module with tenant_id variable.

⸻

Local development (Localstack + Ollama)
	•	docker-compose.yml run services:
	•	localstack (API Gateway, DynamoDB, S3, Cognito)
	•	ollama
	•	a small mock auth server (optional)
	•	Use Terraform workspace local to deploy infra to Localstack (use AWS CLI env vars pointing to localstack endpoints).
	•	Lambdas: run via sam local or test via unit tests invoking handler functions.
	•	Example: awslocal dynamodb create-table ... and curl to local API endpoint to simulate frontend.

⸻

Observability & tracing
	•	Logging: Lambdas push to CloudWatch Logs (tag logs with tenantId).
	•	Tracing: Enable X-Ray for Lambdas. Include tenantId as annotation.
	•	Metrics: Custom CloudWatch metrics for per-tenant usage (invocations, cost).
	•	Cost tracking: Log Bedrock call tokens and store per-tenant summary in tenants-metadata for billing estimation.

⸻

Security considerations
	•	Encryption: Enable server-side encryption (SSE) on DynamoDB if required (use KMS keys per tenant for enterprise).
	•	IAM least privilege: Grant Lambdas minimal permissions; consider per-tenant IAM role if required.
	•	Audit: Record table creation, updates in an audit S3 bucket and CloudTrail.
	•	Secrets: Store model keys or third-party credentials in AWS Secrets Manager.

⸻

Deployment & CI/CD (GitHub Actions sketch)
	•	Build & publish Lambda artifacts to ECR (or zip packages to S3).
	•	Terraform steps:
	•	terraform plan (workspace: staging/prod)
	•	terraform apply
	•	Deploy static frontend to S3 + CloudFront invalidation.

Example pipeline stages:
	1.	Test (unit + integration)
	2.	Build (backend & frontend)
	3.	Push (ECR / S3)
	4.	Terraform apply (infra changes)
	5.	Deploy Lambdas & invalidate CloudFront

⸻

Operational notes & scaling
	•	Table-per-tenant scaling: Each per-tenant table auto-scales with PAY_PER_REQUEST; for very large tenants consider provisioned capacity or a dedicated table with autoscaling rules.
	•	Cold starts: Use provisioned concurrency for latency-sensitive functions (enterprise customers).
	•	Cost: Per-tenant table approach increases number of tables, which slightly increases meta-cost and management overhead — account for this in the pricing model.
	•	Backups: Use on-demand backups or point-in-time recovery per table; store backups in tenant-specific S3 prefixes.

⸻

Example Lambda handler (Node.js pseudo)

// chat-handler.js
exports.handler = async (event) => {
  const tenantId = event.requestContext.authorizer.claims.tenantId;
  // Validate tenant
  const tableName = await lookupTenantTable(tenantId);
  // classify
  const classification = await callTRMClassifier(event.body.text);
  // fetch context data
  const metrics = await queryTenantMetrics(tableName, classification);
  // build prompt and call model (bedrock or ollama)
  const modelResp = await callModel(classification, metrics, tenantId);
  // persist assistant message
  await saveMessage(tableName, { sender: 'assistant', text: modelResp.text, context: classification });
  // return
  return { statusCode: 200, body: JSON.stringify({ text: modelResp.text }) };
};


⸻

Checklist for Tech Lead (next steps)
	•	Implement tenant-onboard Lambda (AWS SDK createTable + metadata store).
	•	Implement chat-handler with pluggable model adapter (Ollama & Bedrock).
	•	Build Terraform modules/tenant_table and a simple provisioner CLI for on-boarding.
	•	Add API Gateway authorizer with Cognito mapping for tenantId.
	•	Implement local dev docker-compose for Localstack + Ollama + mock frontend.
	•	Create GitHub Actions pipeline for infra + app deploy.

⸻

Appendix — recommendations & trade-offs
	•	Per-tenant tables:
	•		•	Hard isolation, easier compliance
	•		•	More tables to manage; slightly more complex IAM/backup management
	•	Lambda vs long-running containers:
	•	Lambda = lower ops cost and pay-per-use; use provisioned concurrency for low-latency enterprise endpoints
	•	Bedrock vs TRM vs Ollama:
	•	Use Ollama for cheap, fast local testing; Bedrock for production-grade models and compliance; TRM for deterministic smaller classifiers close to data
