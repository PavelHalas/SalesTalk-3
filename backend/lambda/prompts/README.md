# Prompt Templates

This directory contains externalized prompt templates for AI model interactions.

## Directory Structure

```
prompts/
├── classification/
│   ├── bedrock_classification.txt    # Bedrock (Claude) classification prompt
│   ├── ollama_classification.txt     # Ollama (local) classification prompt
│   └── repair_prompt.txt              # Self-repair prompt for both providers
└── narrative/
    └── narrative_generation.txt       # Narrative generation prompt
```

## Template Format

Templates use Python `.format()` syntax with named placeholders:

### Classification Templates
- `{question}` - The user's natural language question

### Repair Template
- `{question}` - The user's original question
- `{current_json}` - Current classification JSON (as string)
- `{issues}` - List of detected issues (as JSON array string)

### Narrative Template
- `{classification}` - Classification result (as JSON string)
- `{data_references}` - Data points with provenance (as JSON string)

## Editing Prompts

To modify classification behavior:

1. **Update the appropriate template file** (not the Python code)
2. **Test with E2E suite**: `pytest backend/tests/e2e/test_product_owner_questions.py -q`
3. **Review accuracy metrics** before committing changes

## Key Disambiguation Rules

### Margin Metrics
- `"margin"` (without "gross") → `margin_pct`
- `"gross margin"` or `"gm"` → `gm` (absolute value)
- `"gross margin %"` or `"gm%"` → `gm_pct` (percentage)
- `"operating margin"` → `op_margin_pct`

### Subject vs Measure
- Subject must be a **business entity**: revenue, margin, customers, orders, sales, etc.
- Measure must be a **specific metric**: mrr, churn_rate, pipeline_value, etc.
- Never use a metric name as a subject

### Intent Classification
- `"Why did X increase?"` → `why` (causal explanation)
- `"X is increasing"` → `trend` (pattern description)
- `"Which products..."` → `rank` (dimensional ranking)

## Version Control

All prompt changes are tracked in git. Review diffs carefully as prompt engineering directly affects classification accuracy.

## Architecture Alignment

These templates support the **No-Hardcoding Policy** defined in:
- `backend/src/classification/README.md`
- `docs/architecture/ARCHITECTURE_OVERVIEW.md`

All classification patterns and rules should be in taxonomy JSON files or these prompt templates - never hardcoded in Python.
