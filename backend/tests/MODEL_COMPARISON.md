# Model Comparison Guide

## Quick Test: Single Model

Test with a specific model:

```bash
cd backend

# Test with default llama3
OLLAMA_MODEL=llama3 STRICT_E2E=false \
  ./.venv/bin/python -m pytest tests/e2e/test_product_owner_questions.py -v

# Test with larger model (if available)
OLLAMA_MODEL=qwen2.5:32b STRICT_E2E=false \
  ./.venv/bin/python -m pytest tests/e2e/test_product_owner_questions.py -v

# Test with Mixtral
OLLAMA_MODEL=mixtral:8x7b STRICT_E2E=false \
  ./.venv/bin/python -m pytest tests/e2e/test_product_owner_questions.py -v
```

## Full Model Comparison

Run systematic comparison across multiple models:

```bash
cd backend
./tests/scripts/compare_models.sh
```

This will:
1. Test each model listed in the script
2. Pull models automatically if not available
3. Run the 100-question suite for each
4. Generate comparison report with accuracy stats
5. Save individual logs and aggregate JSONs per model

## Recommended Models to Try

### Small (Fast, Lower Accuracy)
- `llama3` (8B) — Current baseline: Intent 83%, Subject 30%, Measure 74%
- `llama3.1` (8B) — Improved version of llama3
- `phi3:medium` (14B) — Microsoft's efficient model

### Medium (Balanced)
- `qwen2.5:14b` — Good instruction following
- `mistral:7b-instruct` — Strong reasoning
- `deepseek-coder-v2:16b` — Code/structured output focused

### Large (Slower, Highest Accuracy)
- `qwen2.5:32b` — Excellent instruction following and accuracy
- `mixtral:8x7b` — Mixture of experts, very capable
- `llama3.1:70b` — Largest llama variant (requires significant RAM)

## Expected Improvements

Based on the classification failures (subject: 30%, dimension/time: <10%):

| Model Size | Expected Subject Accuracy | Expected Dimension/Time |
|------------|---------------------------|-------------------------|
| 8B (llama3) | 30-40% | <10% |
| 14-16B | 50-65% | 15-25% |
| 32B | 70-85% | 30-50% |
| 70B+ | 85-95% | 50-70% |

**Key improvement areas for larger models:**
1. Better entity vs metric distinction (subject field)
2. More consistent structured field extraction (dimension/time)
3. Reduced hallucination/defaulting to "revenue"
4. Better few-shot learning from prompt examples

## Installing Models

```bash
# List available models
ollama list

# Pull a specific model
ollama pull qwen2.5:32b

# Pull multiple models for comparison
ollama pull llama3.1
ollama pull qwen2.5:14b
ollama pull mixtral:8x7b
```

## Viewing Results

After running comparison:

```bash
# View summary
cat backend/tests/logs/model_comparison_*.txt

# View detailed mismatches for a specific model
cat backend/tests/logs/aggregate_qwen2.5_32b_*.json

# Compare top subject mismatches across models
grep -A 10 "top_subject_mismatches" backend/tests/logs/aggregate_*.json
```

## Quick Single-Model Test (5 questions)

To quickly test a model without running all 100 questions:

```bash
cd backend

# Create a small test
OLLAMA_MODEL=qwen2.5:32b python3 << 'EOF'
import os
import sys
sys.path.insert(0, "lambda")
from ai_adapter import get_adapter, AIProvider

adapter = get_adapter(
    AIProvider.OLLAMA,
    base_url="http://localhost:11434",
    model=os.environ["OLLAMA_MODEL"]
)

test_questions = [
    "What is our Q3 revenue?",
    "How many orders last month?",
    "What's customer churn rate?",
    "Show sales pipeline value",
    "What's conversion rate for marketing?",
]

for q in test_questions:
    result = adapter.classify(q, "test-tenant", "test-req")
    print(f"\nQ: {q}")
    print(f"  Intent: {result['intent']}, Subject: {result['subject']}, Measure: {result['measure']}")
    print(f"  Confidence: {result['confidence']['overall']:.2f}")
EOF
```

## Adjusting for Model Speed/Accuracy Tradeoff

Edit `backend/tests/scripts/compare_models.sh` to test only specific models:

```bash
# Replace the MODELS array with your selection:
MODELS=(
    "llama3.1"          # Baseline improved
    "qwen2.5:32b"       # Best candidate for accuracy
)
```

Then run: `./tests/scripts/compare_models.sh`

## Next Steps After Finding Best Model

1. Update default in test suite:
   ```bash
   # In backend/tests/e2e/test_product_owner_questions.py
   os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:32b")  # or your winner
   ```

2. Update production environment variables:
   ```bash
   # In your deployment/infra config
   OLLAMA_MODEL=qwen2.5:32b
   ```

3. Document model choice and rationale in architecture docs

4. If still below thresholds, iterate on prompt engineering with the better model
