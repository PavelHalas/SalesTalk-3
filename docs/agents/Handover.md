# 🔄 SalesTalk Agent Handover & Master TODO

This document defines the phased sequence of work across all agents, clarifies who starts when, the gating artifacts per phase, and the inter-agent handoffs. Use it as the canonical execution playbook.

## Phase Overview
| Phase | Goal | Primary Driver | Support Agents | Gate to Next |
|-------|------|----------------|----------------|--------------|
| 0. Vision Inception | Clarify product vision & KPIs | Product Owner | Architect, Data Science, UX | Vision brief + KPI baseline |
| 1. Domain & Architecture Foundation | Establish architecture principles & data/event contracts | Architect | Product Owner, Data Engineer, Developer | Architecture overview + initial contracts approved |
| 2. Data Platform Bootstrapping | Tenant-safe storage + ingestion seeds | Data Engineer | Architect, Tester | Seeded LocalStack + data contracts + quality checklist |
| 3. Semantic Layer & Evaluation | Ontology + classification/narrative evaluation harness | Data Science | Data Engineer, Tester, Product Owner | Gold set + evaluator + baseline metrics |
| 4. UX Conversation Flows | Prototype first-conversation journey & streaming states | UX | Product Owner, Data Science, Architect | Usability-tested prototype + a11y checklist pass |
| 5. Feature Implementation | Working backend & frontend feature slices | Developer | Architect, Data Science, Data Engineer | All feature slice tests passing (non-gap) |
| 6. Quality Hardening | Edge cases, failure modes, performance & security | Tester | Architect, Developer, Data Engineer | CI gating green (only known-gap failures) + perf/SLO report |
| 7. Release Readiness | Deployment, observability, rollback & docs | Architect + Developer | Tester, Product Owner | Release checklist signed; rollback plan validated |
| 8. Post-Release Monitoring | Track KPIs, model & data drift | Product Owner + Data Science | Data Engineer, Tester | KPI dashboard live + drift alerts configured |

## Detailed Handover Steps

### Phase 0: Vision Inception
- Product Owner
  - Draft vision narrative & problem statement
  - Define initial KPIs (time-to-insight, satisfaction, accuracy confidence)
  - Provide 10–15 exemplar user questions (incl. ambiguous & negative examples)
- Output Artifacts: `VISION_BRIEF.md`, `KPI_BASELINE.md`
- Gate: Stakeholder review acceptance

### Phase 1: Domain & Architecture Foundation
- Architect
  - Produce system diagram (Mermaid) & deployment outline
  - Define event names & initial schemas (classification.performed.v1, narrative.generated.v1)
  - Specify multi-tenant isolation approach (DynamoDB table strategy, S3 prefixes)
  - Draft non-functional requirements (latency, cost envelope, security boundaries)
- Product Owner: Clarify priority flows to shape architecture decisions
- Data Engineer: Early feedback on data feasibility
- Output Artifacts: `/docs/architecture/ARCHITECTURE_OVERVIEW.md`, `/docs/contracts/EVENTS.md`
- Gate: Architecture review signed; events versioned & published

### Phase 2: Data Platform Bootstrapping
- Data Engineer
  - Design DynamoDB PK/SK & GSI patterns; add LocalStack seed script
  - Implement ingestion stubs & idempotency strategy (outline only if delayed)
  - Provide seeded test tenants (at least 2) with sales snapshot data
  - Add data contract tests (confidence fields ranges, reference formats)
- Tester: Contract test harness skeleton
- Output Artifacts: `/infra/terraform/dynamodb.tf` (draft), `seed_data/`, `DATA_CONTRACTS.md`
- Gate: Local dev environment produces consistent seeded data; quality checklist passes

### Phase 3: Semantic Layer & Evaluation
- Data Science
  - Draft ontology: intent, subject, measure, dimension, time enumerations
  - Build gold question set (≥50) + adversarial set (≥30)
  - Implement classification evaluator (component accuracy + calibration)
  - Define narrative factuality rules (reference coverage, hallucination detection)
- Tester: Integrate evaluator into CI (deterministic mode)
- Output Artifacts: `ontology/ONTOLOGY_v0.md`, `evaluation/gold.json`, `evaluation/adversarial.json`, `scripts/evaluate_classification.py`
- Gate: Baseline metrics collected; hallucination rate < provisional threshold (e.g. <10%)

### Phase 4: UX Conversation Flows
- UX
  - Map "first conversation" journey including clarification/repair flows
  - Prototype streaming UI (loading, partial, final states + uncertainty badges)
  - Define component tokens (color, spacing, typography, dark mode basics)
  - A11y pass: keyboard nav, focus order, ARIA labels, color contrast
- Product Owner: Validate that flows address exemplar questions
- Output Artifacts: `ux/flows/first_conversation.md`, `ux/prototypes/`, `ux/tokens.json`, `ux/a11y_report.md`
- Gate: Usability test (≥5 users) success rate ≥80%; a11y checklist fully green

### Phase 5: Feature Implementation
- Developer
  - Implement classification Lambda + adapter interface + logging (tenant & requestId)
  - Implement chat endpoint + streaming response scaffolding
  - Integrate UX component library (design tokens) into frontend skeleton
  - Add tests: unit (core logic), integration (end-to-end classification → narrative stub)
- Data Engineer: Ensure data access helpers used correctly
- Data Science: Provide prompt template revisions
- Output Artifacts: `lambda/classify.py`, `lambda/chat.py`, `frontend/components/`, `tests/`
- Gate: All slice tests pass (excluding tagged known-gap); coverage ≥80% new logic

### Phase 6: Quality Hardening
- Tester
  - Introduce adversarial fuzz tests (typos, mixed locales, ambiguous time phrases)
  - Performance tests (p95 latency baseline) & isolation tests (no cross-tenant leakage)
  - Security/robustness checks: malformed JWT, missing tenant claim, truncated payloads
  - Tag known gaps with rationale & ETA
- Architect: Observability pattern review
- Output Artifacts: `tests/adversarial/`, `tests/performance/`, `ci/reports/quality.md`
- Gate: False-green risk addressed; flake rate <1%; no high-severity leaks

### Phase 7: Release Readiness
- Architect + Developer
  - Finalize Terraform modules, environment variables, secrets handling
  - Create rollback plan (prompt/model versions, infra changes)
  - Observability dashboards (logs, metrics, traces by tenant)
- Product Owner: Final go/no-go checklist
- Tester: Final regression green (known gaps only)
- Output Artifacts: `RELEASE_CHECKLIST.md`, `ROLLBACK_PLAN.md`, `observability/dashboards/`
- Gate: Checklist signed; rollback drill completed successfully

### Phase 8: Post-Release Monitoring
- Product Owner + Data Science
  - Monitor KPIs vs targets; narrative factuality spot checks
  - Drift detection on classification accuracy & confidence calibration
  - Gather user feedback; prioritize iteration backlog
- Data Engineer: Freshness/completeness alerts configured
- Tester: Ongoing regression + new edge cases
- Output Artifacts: `kpi/DASHBOARD.md`, `evaluation/drift_report.md`, `backlog/iteration_plan.md`
- Gate: Drift alerts functional; first iteration backlog approved

## Master Checklist (Condensed)

### Product Owner
- [ ] Vision brief
- [ ] KPI baseline
- [ ] Exemplar & adversarial user questions
- [ ] Go/no-go release checklist sign-off

### Architect
- [ ] System diagram
- [ ] Event & API contracts
- [ ] Data model patterns
- [ ] Non-functional requirements
- [ ] Terraform modules & rollback plan
- [ ] Observability dashboards

### Data Engineer
- [ ] PK/SK/GSI design
- [ ] Seed scripts & multi-tenant fixtures
- [ ] Ingestion stubs & idempotency outline
- [ ] Data contracts & tests
- [ ] Quality dashboard

### Data Science
- [ ] Ontology v0
- [ ] Gold + adversarial dataset
- [ ] Classification evaluator & metrics
- [ ] Narrative factuality rules
- [ ] Prompt templates & versioning policy
- [ ] Calibration report

### UX
- [ ] First conversation flow map
- [ ] Streaming prototype
- [ ] Design tokens & component specs
- [ ] Accessibility checklist pass
- [ ] Usability test findings

### Developer
- [ ] Classification Lambda
- [ ] Chat/streaming endpoint
- [ ] Frontend component integration
- [ ] Observability (logs/metrics/traces)
- [ ] Unit + integration tests (≥80% coverage)
- [ ] Docs/runbooks

### Tester
- [ ] Contract tests
- [ ] Adversarial + fuzz suite
- [ ] Performance & isolation tests
- [ ] CI gating rules implemented
- [ ] Known-gap tagging & tracking

### Cross-Cutting Gates
- [ ] Tenant isolation verified
- [ ] Hallucination < target threshold
- [ ] Latency p95 within SLO
- [ ] No untagged failing tests
- [ ] Rollback drill success
- [ ] Drift alerts configured

## Parallelization Notes
- Phases 2 & 3 can overlap after initial contracts: Data Engineer builds seeds while Data Science drafts ontology.
- UX (Phase 4) can begin mid Phase 3 once ontology stabilizes for classification labels.
- Developer can start slice work once minimal data seeds + provisional ontology exist (early in Phase 4).
- Tester begins contract scaffold during late Phase 2; adversarial sets emerge in Phase 3/4.

## Escalation Triggers & Owners
| Trigger | Owner | Action |
|---------|-------|--------|
| Data freshness breach | Data Engineer | Quarantine pipeline; notify Architect & Product Owner |
| Accuracy regression > tolerance | Data Science | Rollback prompt/model; open improvement ticket |
| Tenant isolation failure | Architect | Immediate incident protocol; Tester expands isolation suite |
| Latency p95 drift | Developer | Profiling & optimization; Architect reviews design |
| Hallucination spike | Data Science | Tighten guardrails; add references or refusal policy updates |
| Flake rate >1% | Tester | Quarantine tests; root cause analysis |

## Versioning & Change Management
- Contracts: Semantic version (e.g., classification.performed.v1 → v2 only with additive or documented breaking change).
- Prompts/models: Tag with `prompt-vX.Y` + store rollback set.
- Terraform: Module versions pinned; upgrades require two-agent (Architect + Developer) approval.
- Datasets: Gold set changes trigger recalibration run.

## Handover Summary Flow (Narrative)
1. Product Owner frames the problem and KPIs.
2. Architect translates into system & contract blueprint.
3. Data Engineer instantiates tenant-safe data surface.
4. Data Science builds semantic intelligence & evaluation harness.
5. UX shapes human conversation interfaces.
6. Developer implements feature slices informed by contracts & flows.
7. Tester pushes edge cases and gates quality.
8. Architect & Developer finalize release infra; Product Owner signs off.
9. Post-release, Data Science & Product Owner watch drift; all respond to signals.

Keep this file synchronized; adjustments to phases should include reason + date.

*Last updated: November 2025*
