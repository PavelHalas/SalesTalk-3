# 🧭 SalesTalk Agent Responsibilities Overview

This document wires all agents together with clear inputs/outputs and dependencies. Use it as the single source of truth for handoffs and accountability.

## Matrix (Provides → Depends On)

| Agent | Provides | Depends On |
|------|----------|------------|
| Product Owner | Vision, roadmap, KPIs, user stories with acceptance/negative cases | Architect, UX, Data Science, Developer, Data Engineer, Tester |
| Architect | Principles, API/event contracts, data model patterns, IaC guardrails | Product Owner, UX, Developer, Data Engineer, Data Science, Tester |
| UX | Flows, prototypes, component specs, a11y/content guidelines | Product Owner, Architect, Developer, Data Science, Data Engineer, Tester |
| Developer | Features (BE/FE), adapters, tests, observability, docs | Product Owner, Architect, UX, Data Science, Data Engineer, Tester |
| Tester | Regression harness, adversarial/edge suites, CI gates, telemetry | Product Owner, Architect, Developer, Data Engineer, Data Science, UX |
| Data Engineer | Ingestion, data contracts, seeds, lineage/quality dashboards | Product Owner, Architect, Developer, Data Science, Tester, UX |
| Data Science | Ontology, prompts/models, evaluation sets, metrics, guardrails | Product Owner, Architect, Developer, Data Engineer, Tester, UX |

## RACI Hints
- PO: Accountable for “what/why”; Consulted on quality gates.
- Architect: Accountable for cross-cutting constraints; Reviews all contracts.
- Developer: Responsible for feature delivery; Accountable for code quality.
- Tester: Accountable for gating; Responsible for surfacing useful failures.
- Data Engineer: Accountable for data quality/freshness; Responsible for contracts.
- Data Science: Accountable for accuracy/calibration; Responsible for eval suites.
- UX: Accountable for usability & accessibility; Responsible for specs.

## Handoff Artifacts
- Contracts: API/event/data schemas versioned with changelogs.
- Evaluation: Gold/adversarial sets; calibration reports.
- Seeds: LocalStack datasets; reproducible seeds for tests.
- Observability: Standard log/metric/trace fields including tenant & request IDs.

Keep this doc synchronized with each agent’s “Responsibility Handshake” section.
