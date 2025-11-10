# Copilot Instructions for SalesTalk

Use these repo-specific guardrails to be productive immediately.

## Architecture snapshot
- Serverless-first backend on AWS: Lambda + API Gateway + DynamoDB. Local dev uses LocalStack for AWS and Ollama for AI.
- Multi-tenant data model: one global table `tenants-metadata`; per-tenant tables `tenant-<tenantId>-messages` and `tenant-<tenantId>-metrics` (see `infra/terraform/dynamodb.tf`).
- Chat flow: classify → fetch metrics → generate narrative. Lambda entrypoints: `backend/lambda/classify.py` and `backend/lambda/chat.py`. AI abstraction in `backend/lambda/ai_adapter.py` supports `AI_PROVIDER=bedrock|ollama`.
- Ingestion layer is scaffolded in `backend/src/ingestion/` with idempotent patterns (conditional writes, retries) but some functions are stubs pending later phases.

## Daily workflows
- Use venv to manage Python dependencies.
- Local AWS services: `docker compose -f docker-compose.localstack.yml up -d` then verify `curl http://localhost:4566/_localstack/health` shows DynamoDB running.
- Python deps: `pip install -r backend/requirements.txt`.
- Seed data: `python backend/scripts/seed_localstack.py` creates the metadata table plus per-tenant messages/metrics tables with sample rows.
- E2E tests (mock AI default): from `backend`, run `pytest tests/e2e/ -v`.
- E2E tests (real AI): ensure Ollama is running, then `USE_REAL_AI=true AI_PROVIDER=ollama pytest tests/e2e/ -v`. Optionally set `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.

## Conventions & patterns
- Table naming: `tenant-<tenantId>-messages` and `tenant-<tenantId>-metrics` with `pk`/`sk` keys and GSIs like `SessionIndex`, `SenderIndex`, `MetricTypeIndex`, `DimensionIndex`.
- Tenant isolation: derive tenant from JWT claims (`custom:tenant_id`) and always scope queries by tenant. Tests enforce isolation (`backend/tests/security`, `backend/tests/e2e`).
- Contracts & validation: schemas and contract tests live in `backend/tests/contracts/` and are referenced by handlers; confidence scores must be in [0.0, 1.0].
- AI integration: prefer `ai_adapter.py` for all model calls; never import provider SDKs directly in handlers. Switch using env vars.
- Error handling: handlers return API Gateway-style responses (statusCode, headers, body). Map validation errors to 400, provider failures to 502; see `backend/lambda/README.md` and tests under `backend/tests/lambda/`.
- Deterministic tests: default to mock AI; real AI mode is opt-in via `USE_REAL_AI=true`.

## Where to look first
- Top-level overview: `README.md` and `docs/architecture/ARCHITECTURE_OVERVIEW.md`.
- Lambdas and adapters: `backend/lambda/` (read the README there for inputs/outputs and envs).
- E2E flows and setup: `E2E_TESTING.md` and `backend/tests/e2e/README.md`.
- Data model and seed: `infra/terraform/dynamodb.tf`, `backend/scripts/seed_localstack.py`, `backend/seed_data/`.
- Agent roles & handover: `.github/agents/*.md`, `docs/agents/`.

## Examples from this repo
- Calling classify: see `backend/tests/lambda/test_classify.py` and the input/output shapes in `backend/lambda/README.md`.
- Full chat path: `backend/tests/lambda/test_chat.py` and E2E cases in `backend/tests/e2e/test_localstack_e2e.py`.
- Seeding and querying: seed script in `backend/scripts/seed_localstack.py` and per-tenant table names created there.

## PR expectations
- Add or update tests alongside changes: unit under `backend/tests/lambda/`, contracts under `backend/tests/contracts/`, and E2E when touching cross-cutting behavior.
- Keep local parity: ensure changes work with LocalStack and Ollama; document any new env vars in `backend/lambda/README.md`.

If anything here is unclear or you find drift from the code/tests, tell us which section needs refinement and propose an update.
