# SalesTalk Radical Classification Improvement Plan

Last Updated: 2025-11-15
Owner: Developer Agent
Status: Draft (Phase 0 pending)

## 1. Vision
Achieve near-production, multilingual (EN/CZ) business-intelligence question classification with >95–98% accuracy across intent, subject, measure, time, and dimension while reducing latency (<400ms p50) and cost per request (<25% of current) by layering deterministic taxonomy logic, retrieval, and a tiny recursive/specialized model.

## 2. Current Baseline (llama3.2, self-repair enabled)
| Component  | Accuracy | Target End-State |
|-----------|----------|------------------|
| Intent     | 79%      | ≥97% |
| Subject    | ~52%     | ≥98% |
| Measure    | ~52%     | ≥96% |
| Dimension* | Low (<10% when expected) | ≥92% |
| Time*      | Low (<15% when expected) | ≥95% |
| Structural Validity | ~100% (JSON shape) | ≥99.5% |
| Latency p95 | ~>8s (LLM only) | <800ms overall / <400ms p50 |
*When expectations non-empty.

## 3. Phase Overview
| Phase | Name | Goal | Success Criteria (SC) |
|-------|------|------|-----------------------|
|0|Baseline Hardening|Eliminate trivial errors|Subject/measure leaks <5%; time token coverage >90% common periods|
|1|Taxonomy Multi-Pass|Reduce hallucination via staged classification|Subject ≥95%; Measure ≥92% pre-repair|
|2|Retrieval Exemplars|Improve nuanced intents & measures|Intent misclass (rank/breakdown/correlation) <2%; Measure ≥95%|
|3|Synthetic + Active Learning|Broad generalization & edge coverage|Adversarial accuracy ≥90%; dataset ≥1200 high-quality items|
|4|Specialized Tiny Model|Lower cost & latency|Latency p95 <400ms first pass; Subject ≥95% tiny model|
|5|Multilingual Integration|Czech parity with English|CZ metrics within 3% of EN; cross-language confusion <2%|
|6|Reliability & CI|Prevent regressions|CI gate rejects >1% drop; prompt hash traceability 100%|
|7|Repair Optimization|Minimize iterative overhead|Avg repair steps <0.2; residual error <2%|

## 4. Tasks Mapping
Each task has a short code used in metrics & dashboards.

| ID | Code | Task | Phase | SC Impact |
|----|------|------|-------|-----------|
|1|TAXO|Dynamic taxonomy loader|1|Subject accuracy|
|4|HIER|Hierarchical passes|1|Subject/measure accuracy|
|5|SCHEMA_PROMPT|Prompt guardrails w/ schema|1|Structural reliability|
|14|JSON_STRICT|Constrained JSON decoding|0/7|Reduce malformed outputs & repair count|
|15|RULES|Subject-metric rule engine|0|Reduce metric-as-subject leaks|
|23|TIME_EXT|Time normalization expansion|0|Time accuracy|
|24|DIM_EXT|Dimension extraction enrichment|0|Dimension accuracy|
|9|RETRIEVE|Vector exemplar retrieval|2|Intent/measure uplift|
|16|AUG|Synthetic data augmentation|3|Generalization|
|18|ACTIVE|Active learning loop|3|Continuous improvement|
|19|TINY|Tiny specialized classifier|4|Latency & base accuracy|
|2|LANG_DETECT|Language detection|5|Multilingual routing|
|3|CZ_NORM|Czech normalization pipeline|5|Czech accuracy|
|7|CZ_TESTS|Czech contract tests|5|Coverage|
|25|CALIB|Confidence calibration|4/7|Reliable thresholds|
|26|FALLBACK|Fallback strategy matrix|4/7|Reliability & refusal quality|
|28|REG_GATE|Automated regression gating|6|Quality stability|
|29|PROMPT_VER|Prompt versioning & diff|6|Traceability|
|30|SCHEMA_ENF|Schema contract enforcement|1/7|Structural validity|
|17|ERR_DASH|Error taxonomy dashboard|3/6|Visibility|
|21|RANK_INTENT|Ranking intent precision|2|Rank intent accuracy|
|22|CORR_INTENT|Correlation disambiguation|2|Correlation intent accuracy|
|20|RAG_EXEMPLAR|Retrieval-augmented prompting|2|Measure intent synergy|
|10|MULTI_CONF|Multi-language confidence scoring|5|Cross-language quality|
|8|CACHE|Config caching strategy|6|Latency|

## 5. Phase 0 Detailed Plan (Immediate)
Objectives:
- Fix frequent, deterministic misclassifications before deeper changes.
Steps:
1. Implement RULES: mapping known metrics (mrr, arr, pipeline_value, nps, cac, churn_rate, aov, order_count, return_rate, arpu) back to correct subject families.
2. Implement JSON_STRICT: streaming brace balancer; if parsing fails, auto re-prompt with minimal diff.
3. Extend time tokens TIME_EXT: add next_month, l8q, l30d, holiday_YYYY, eoy_YYYY; heuristics map phrases.
4. DIM_EXT baseline: regex for `top\s+(\d+)`, `bottom\s+(\d+)`, region names (EMEA, APAC, NA), segments (SMB, Enterprise), product line patterns.
5. Instrument metrics: Add classification metadata fields: `corrections_applied`, `parse_attempts`.
6. Run e2e; produce delta JSON `baseline_hardening_report.json` diff vs prior run.
Acceptance:
- Leak rate (metric-as-subject) <5%
- Time token presence when expected >70% (intermediate), >90% final for common tokens.
- Dimension extraction (rank limit/channel/status/region/segment) >40% interim.

## 6. Hierarchical Multi-Pass (Phase 1)
Design:
- Pass 1 (Subject + Intent): restrict output to taxonomy subject list.
- Pass 2 (Measure): allowed list = measures of chosen subject.
- Pass 3 (Dimension + Time): restricted candidate sets; incorporate canonical mapping.
Implementation Notes:
- Each pass returns JSON fragment; compose into final.
- Fail fast if pass confidence < threshold; escalate to fallback or refusal.
Metrics:
- Compare subject/measure mismatch vs baseline (target 30–40% relative reduction initial).

## 7. Retrieval & Exemplars (Phase 2)
- Build embeddings for each curated gold question + classification.
- Retrieve k examples per subject/intent; deduplicate overlapping metrics.
- Insert exemplars in prompt boundaries clearly labeled.
Evaluation:
- Track accuracy improvement after adding retrieval (A/B without retrieval for 100-sample subset).

## 8. Synthetic Data + Active Learning (Phase 3)
Augmentation Types:
- Paraphrase (LLM rewriting).
- Adversarial: inserted extra clauses, ambiguous time phrases.
- Noise injection: punctuation variance, numeric variations.
Active Learning Queue:
- Criteria: low confidence (<0.6), disagreement between tiny model and LLM, new patterns.
Human Review:
- Simple web form writing labeled JSON; autopush to gold set.

## 9. Specialized Tiny Model (Phase 4)
Model Options:
- Distilled small transformer (≤50M params) or TRM variant.
Features:
- Multi-head classification (intent, subject, measure index vectors).
Training Data:
- Gold + high-confidence synthetic.
Evaluation:
- Confusion matrices per component; calibration using logistic on validation.
Fallback Strategy:
- If tiny model confidence below thresholds, escalate to large LLM multi-pass + repair.

## 10. Multilingual (Phase 5)
Czech Pipeline:
- Detect (LANG_DETECT) → Normalize (CZ_NORM) → Translate ambiguous synonyms to canonical English tokens.
Exemplars:
- Bilingual; retrieval prioritizes same language, fallback to English.
Confidence:
- MULTI_CONF penalizes mismatched diacritics or unnormalized tokens.

## 11. Reliability & CI (Phase 6)
Regression Gating:
- After each merge to main, run full suite; compare metrics vs baseline JSON stored under `metrics/baselines/latest.json`.
- Block if any core metric drops >1% absolute or structural invalid increases.
Prompt Versioning:
- Hash prompt string; embed `prompt_hash` in classification metadata.
Dashboard:
- ERR_DASH: HTML + charts (Sparkline of weekly metrics).

## 12. Repair Optimization (Phase 7)
Enhancements:
- Expand detection heuristics; only trigger repair when deterministic rules insufficient.
- Repair attempts logged; measure distribution.
Goal: average repair attempts <0.2 across 1k sample.

## 13. Metrics & Telemetry
Data Fields per Classification:
- latency_ms, model_name, prompt_hash, corrections_applied[], parse_attempts, repair_steps, tiny_model_used(bool), tiny_confidence, llm_confidence.
Rollups:
- Daily aggregates & trend lines; error taxonomy counts (by tag).

## 14. Risk Mitigation
| Risk | Mitigation |
|------|------------|
| Overfitting synthetic | Use embedding distance filtering; holdout adversarial set |
| Latency growth (multi-pass) | Benchmark each pass; merge passes if >100ms p95 |
| Repair loop runaway | Cap steps (env variable), monitor repair frequency alarm |
| Schema drift | Schema contract enforcement + CI diff |
| Multilingual ambiguity | Explicit language detection; separate normalization path |

## 15. Acceptance Criteria (Final End-State)
- All core accuracy targets met on stable 1k dataset.
- Tiny model handles ≥85% of requests without fallback.
- Cost & latency targets met.
- CI gate active; zero silent regressions in 30-day window.
- Multilingual parity achieved (CZ vs EN delta <3%).

## 16. Timeline (Aggressive 8 Weeks)
Week 1: Phase 0 tasks (RULES, JSON_STRICT, TIME_EXT, DIM_EXT) + baseline diff.
Week 2: TAXO + HIER + SCHEMA_PROMPT + SCHEMA_ENF.
Week 3: RETRIEVE + RAG_EXEMPLAR + RANK_INTENT + CORR_INTENT.
Week 4: AUG + ERR_DASH + ACTIVE.
Week 5: TINY + CALIB + FALLBACK.
Week 6: LANG_DETECT + CZ_NORM + CZ_TESTS + MULTI_CONF.
Week 7: REG_GATE + PROMPT_VER + CACHE.
Week 8: Optimization of repair + final calibration + acceptance metrics publication.

## 17. Implementation Priorities (Immediate Backlog)
1. RULES (subject-metric corrections)
2. JSON_STRICT (stream parser & re-prompt)
3. TIME_EXT (extended time tokens)
4. DIM_EXT (rank + region + segment)
5. Metrics instrumentation (metadata fields)

## 18. Reference Environment Variables (to add incrementally)
| Env Var | Purpose | Default |
|---------|---------|---------|
| USE_SELF_REPAIR | Enable repair loop | false |
| SELF_REPAIR_STEPS | Max repair iterations | 1 |
| USE_HIER_PASSES | Enable multi-pass taxonomy classification | false |
| USE_TINY_MODEL | Enable tiny classifier first pass | false |
| PROMPT_VERSION | Manual prompt version tag | unset |
| ENABLE_JSON_STRICT | Use strict streaming JSON parser | false |

## 19. Open Questions
- Do we handle partial commissions & derived metrics (e.g., seasonality) or force canonical only? (Recommendation: canonical only until Phase 3.)
- Should dimension ranking default limit be 10 when unspecified? (Recommendation: only if explicit top/bottom cue without number.)

## 20. Next Action Checklist (Developer Agent)
- [ ] Implement RULES
- [ ] Implement JSON_STRICT
- [ ] Extend time tokens TIME_EXT
- [ ] Add DIM_EXT regex + mapping
- [ ] Add metadata instrumentation & delta report

---
This plan file will evolve—update `Last Updated` and commit deltas with prompt hash changes.
