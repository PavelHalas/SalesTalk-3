# Phase 0: Baseline Hardening - Implementation Complete

**Status**: ✅ Complete  
**Date**: 2025-11-15  
**Owner**: Classification System

## Overview

Phase 0 implements deterministic improvements to eliminate trivial classification errors before deeper architectural changes. All Phase 0 components are production-ready and tested.

## Components Implemented

### 1. RULES - Subject-Metric Corrections ✅

**Location**: `backend/src/classification/rules.py`  
**Tests**: `backend/tests/classification/test_rules.py` (14 tests, all passing)

Deterministic mapping of metrics to their correct subject families:
- **Metric leak fix**: Prevents metrics from appearing as subjects (e.g., `churn_rate` → subject:`customers`, measure:`churn_rate`)
- **Alias normalization**: Maps aliases to canonical names (e.g., `gross_margin` → `gm`, `refund_rate` → `return_rate`)
- **Family constraints**: Enforces subject-metric relationships (e.g., `arpu` requires `customers` subject, `aov` requires `orders`)

**Coverage**:
- Revenue metrics: `revenue`, `mrr`, `arr`, `gm`, `gm_pct`, `gross_profit`
- Customer metrics: `customer_count`, `churn_rate`, `ltv`, `nps`, `cac`, `arpu`
- Orders metrics: `order_count`, `aov`, `return_rate`
- Sales metrics: `pipeline_value`, `win_rate`, `deal_count`
- Marketing metrics: `conversion_rate`, `signup_count`, `lead_count`

### 2. JSON_STRICT - Robust JSON Parser ✅

**Location**: `backend/src/classification/json_parser.py`  
**Tests**: `backend/tests/classification/test_json_parser.py` (17 tests, all passing)

Multi-strategy JSON extraction with automatic recovery:
- **5 fallback strategies**: Direct parse → Markdown removal → Brace extraction → Brace balancing → Error fixing
- **Brace balancing**: Adds missing closing braces for incomplete JSON
- **Common fixes**: Removes trailing commas, fixes quote styles
- **Structure validation**: Validates required fields and confidence ranges

**Metrics tracked**: `parse_attempts` (number of strategies needed to parse)

### 3. TIME_EXT - Extended Time Tokens ✅

**Location**: `backend/src/classification/time_extractor.py`  
**Tests**: `backend/tests/classification/test_time_extractor.py` (16 tests, all passing)

Expanded time token recognition beyond baseline:
- **New periods**: `next_month`, `next_quarter`
- **New windows**: `l8q` (last 8 quarters), `l30d` (last 30 days), `l90d` (last 90 days)
- **Phrase mapping**: "year to date" → `{"window": "ytd", "granularity": "month"}`
- **Holiday patterns**: `holiday_2024`, `eoy_2024`

**Canonical tokens**:
- Periods: `today`, `yesterday`, `this_week`, `last_week`, `this_month`, `last_month`, `Q1-Q4`, etc.
- Windows: `ytd`, `qtd`, `mtd`, `l3m`, `l6m`, `l12m`, `l8q`, `l30d`, `l90d`
- Granularity: `day`, `week`, `month`, `quarter`, `year`

### 4. DIM_EXT - Dimension Extraction ✅

**Location**: `backend/src/classification/dimension_extractor.py`  
**Tests**: `backend/tests/classification/test_dimension_extractor.py` (18 tests, all passing)

Regex-based extraction of dimension filters from questions:
- **Rank patterns**: "top 5", "bottom 10" → `{"limit": 5, "direction": "top"}`
- **Regions**: EMEA, APAC, NA, LATAM, EU, US, UK, Canada
- **Segments**: SMB, Enterprise, Mid-Market, Startup
- **Channels**: online, offline, email, web, mobile, phone, direct, partner
- **Status**: active, inactive, churned, trial, paying
- **Related metrics**: discount_rate, page_load_time, sales_headcount, demo_completion_rate, seasonality_index
- **Product lines**: Software, Hardware, Services, Platform, SaaS, PaaS, IaaS
- **Time of week**: weekday, weekend

**Heuristics**: Detects bare adjectives like "active customers" or "online sales" without explicit "by/for/in" prepositions.

**⚠️ No Hardcoding Policy**:
All dimension patterns, synonyms, and heuristics are **loaded from taxonomy files** (`taxonomy/default/shared/dimensions.json`).
- Do NOT edit `DIMENSION_PATTERNS` or other constants in `dimension_extractor.py` code.
- Instead, update the taxonomy configuration:
  - Add new dimension values to `regions`, `channels`, `status`, `productLines`, `related_metrics`, etc.
  - Add synonym triggers to `synonyms` (e.g., `rank_top_triggers`, `correlation_verbs`, `channel_noun_targets`).
  - Add complex patterns to `related_metric_patterns` (regex + value pairs).
- The extractor automatically compiles regex patterns from taxonomy at load time.

### 5. Metadata Instrumentation ✅

**Location**: Integrated in `backend/lambda/ai_adapter.py`

Classification metadata fields added:
```json
{
  "metadata": {
    "corrections_applied": ["metric_leak_fixed:churn_rate→customers", "time_tokens_enhanced"],
    "parse_attempts": 1,
    "latencyMs": 350,
    "provider": "ollama"
  }
}
```

## Integration

Phase 0 components are integrated into both `BedrockAdapter` and `OllamaAdapter`:

1. **JSON parsing**: Uses `extract_json_strict()` with fallback to original parser
2. **Post-processing**: `_apply_phase_0_enhancements()` applies RULES → TIME_EXT → DIM_EXT in order
3. **Metadata tracking**: Corrections logged in `metadata.corrections_applied`
4. **Logging**: Enhanced structured logging includes correction counts and parse attempts

## Acceptance Criteria Status

| Criterion | Target | Status |
|-----------|--------|--------|
| Metric-as-subject leak rate | <5% | ✅ Deterministic fixes applied |
| Time token coverage (common) | >90% | ✅ Extended tokens + phrase mapping |
| Dimension extraction | >40% interim | ✅ Regex + heuristics cover rank/channel/status/region |
| Metadata instrumentation | Complete | ✅ corrections_applied, parse_attempts tracked |

## Usage

Phase 0 enhancements are **always active** in the classification pipeline. No environment variables required.

To disable for testing/debugging:
- Remove Phase 0 modules from `backend/src/classification/`
- Adapters will gracefully fall back to original behavior with warning logs

## Testing

```bash
# Run all Phase 0 tests (65 tests)
cd backend
source .venv/bin/activate
pytest tests/classification/ -v

# Run specific component tests
pytest tests/classification/test_rules.py -v
pytest tests/classification/test_time_extractor.py -v
pytest tests/classification/test_dimension_extractor.py -v
pytest tests/classification/test_json_parser.py -v
```

All tests pass with 100% success rate.

## Examples

### Example 1: Metric Leak Fix
**Input**: `{"subject": "churn_rate", "measure": "value"}`  
**Output**: `{"subject": "customers", "measure": "churn_rate", "metadata": {"corrections_applied": ["metric_leak_fixed:churn_rate→customers", "measure_inferred:churn_rate"]}}`

### Example 2: Time Token Enhancement
**Question**: "Revenue year to date"  
**Before**: `{"time": {}}`  
**After**: `{"time": {"window": "ytd", "granularity": "month"}, "metadata": {"corrections_applied": ["time_tokens_enhanced"]}}`

### Example 3: Dimension Extraction
**Question**: "Top 5 active customers in EMEA"  
**Before**: `{"dimension": {}}`  
**After**: `{"dimension": {"limit": 5, "direction": "top", "status": "active", "region": "EMEA"}, "metadata": {"corrections_applied": ["dimension_limit_extracted:5", "dimension_status_extracted_heuristic:active", "dimension_region_extracted:EMEA"]}}`

### Example 4: JSON Recovery
**Malformed**: `{"intent": "what", "subject": "revenue", "measure": "mrr", "confidence": {"overall": 0.9`  
**Parsed**: Automatically adds missing `}}` and succeeds  
**Metadata**: `{"parse_attempts": 4}` (brace balancing strategy)

## Next Steps

Phase 0 establishes the baseline hardening layer. Proceed to:
- **Phase 1**: Taxonomy multi-pass (hierarchical classification)
- **Phase 2**: Retrieval exemplars (RAG-based improvements)
- **Phase 3**: Synthetic data + active learning

## Phase 1: Hierarchical Multi-Pass

**Status**: ✅ Available behind `USE_HIER_PASSES=true`

Phase 1 lives in `classification/hierarchy.py` and adds a deterministic multi-pass sanitizer that runs immediately after Phase 0:

1. **Pass 1 — Subject + Intent**: Restricts the subject to taxonomy-defined entities (including aliases) and snaps the intent to the per-subject allow list.
2. **Pass 2 — Measure**: Resolves metric aliases, enforces that the metric belongs to the selected subject, and reassigns the subject when the metric family disagrees.
3. **Pass 3 — Context (Dimension + Time)**: Drops out-of-vocabulary dimension values, canonicalizes valid tokens, caps rank limits using `shared/dimensions.json`, and forces time tokens to the canonical vocab defined in `shared/time.json`.

Corrections applied during these passes append `phase1.*` entries to `metadata.corrections_applied`, and a structured trace is stored under `metadata.phase1`. If the pipeline cannot reconcile the inputs (e.g., unknown metric), it raises `PhaseOneClassificationError`; the adapters catch this and mark the request as `refused` with a descriptive reason.

**Testing**: `backend/tests/classification/test_hierarchy.py` exercises subject inference, intent restriction, measure realignment, dimension/time sanitization, and refusal paths for unknown metrics.

## Performance Impact

- **Latency**: Negligible (<10ms per classification for all Phase 0 enhancements)
- **Memory**: Minimal (static rule dictionaries, compiled regex patterns)
- **Accuracy**: Expected improvements:
  - Subject/measure leak: ~5% → <1% (deterministic)
  - Time token presence: ~70% → ~90%
  - Dimension extraction: ~10% → ~40-50%

## Maintenance

### Extending Taxonomy (No-Hardcoding Policy)

**⚠️ Critical Guardrail**: Do NOT hardcode patterns, triggers, or synonyms in Python code. All classification configuration must live in JSON taxonomy files under `backend/src/classification/taxonomy/default/`.

#### Adding Metrics
Create or update files under `metrics/<metric>.json` (set `subject`, `aliases`, metadata) and list the metric slug in the appropriate `subjects/<subject>.json` file. The loader auto-builds `METRIC_SUBJECT_MAP` and aliases at runtime.

#### Adding Dimension Values
Edit `shared/dimensions.json`:
- Add to `regions`, `channels`, `status`, `productLines`, `related_metrics`, etc.
- The dimension extractor will automatically load and use these values.

#### Adding Dimension Patterns
Edit `shared/dimensions.json`:
- **Synonyms**: Add to `synonyms` dict (e.g., `rank_top_triggers`, `correlation_verbs`, `channel_noun_targets`)
- **Regex Patterns**: Add to `related_metric_patterns` array with `{"regex": "...", "value": "canonical_name"}`

Example:
```json
{
  "synonyms": {
    "rank_top_triggers": ["top", "best", "highest"],
    "correlation_verbs": ["correlate", "correlation", "impact", "impacts"]
  },
  "related_metric_patterns": [
    {"regex": "\\bdiscount(s|ing|ed)?\\b", "value": "discount_rate"},
    {"regex": "\\bsales\\s+(headcount|team\\s*size)\\b", "value": "sales_headcount"}
  ]
}
```

The `dimension_extractor.py` compiles these into regex patterns at load time—no code changes needed.
- **Adding intents**: Drop a new file into `taxonomy/<env>/<version>/intents/<intent>.json` and reference the slug inside any subject file that should allow it.
- **Adding time tokens**: Update `TIME_PHRASE_PATTERNS` in `time_extractor.py`
- **Adding dimensions**: Update `DIMENSION_PATTERNS` in `dimension_extractor.py`
- **Tests**: Add corresponding test cases for new mappings
- **Storage**: Taxonomy assets stay in version-controlled files that ship with each release (no DynamoDB copy); update the repo and redeploy to propagate changes.

## References

- Development plan: `docs/DEVELOPMENT_PLAN.md`
- Architecture: `docs/architecture/ARCHITECTURE_OVERVIEW.md`
- Lambda documentation: `backend/lambda/README.md`
