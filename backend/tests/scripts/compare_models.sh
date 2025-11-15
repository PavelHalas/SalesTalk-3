#!/bin/bash
# Compare classification accuracy across different Ollama models
# Usage: ./compare_models.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$BACKEND_DIR/tests/logs"
TIMESTAMP=$(date +%s)

cd "$BACKEND_DIR"

# Models to test (from available models, ordered by expected performance)
MODELS=(
    "llama3:latest"           # Current baseline (8B): Intent 83%, Subject 30%
    "llama3.1:8b"             # Improved llama3 (8B): Expected slight improvement
    "deepseek-r1:8b"          # DeepSeek reasoning (8B): Good at structured tasks
    "gpt-oss:20b"             # Largest model (20B): Best expected accuracy
    "dolphin-mistral:latest"  # Mistral variant (7B): Good instruction following
    "sqlcoder:7b"             # SQL-focused (7B): Might help with structured extraction
)

echo "================================================================================"
echo "MODEL COMPARISON: Classification Accuracy"
echo "================================================================================"
echo "Testing ${#MODELS[@]} models against 100 Product Owner questions"
echo "Started: $(date)"
echo ""

# Create comparison results file
COMPARISON_FILE="$LOG_DIR/model_comparison_${TIMESTAMP}.txt"
echo "Model Comparison Results - $(date)" > "$COMPARISON_FILE"
echo "================================================================================" >> "$COMPARISON_FILE"
echo "" >> "$COMPARISON_FILE"

for MODEL in "${MODELS[@]}"; do
    echo "--------------------------------------------------------------------------------"
    echo "Testing model: $MODEL"
    echo "--------------------------------------------------------------------------------"
    
    # Check if model is available
    if ! ollama list | grep -q "^${MODEL%%:*}"; then
        echo "⚠️  Model $MODEL not found. Pulling..."
        ollama pull "$MODEL" || {
            echo "❌ Failed to pull $MODEL. Skipping."
            echo "$MODEL: SKIPPED (pull failed)" >> "$COMPARISON_FILE"
            continue
        }
    fi
    
    # Run test suite with this model
    START_TIME=$(date +%s)
    
    if STRICT_E2E=false \
       OLLAMA_MODEL="$MODEL" \
       ./.venv/bin/python -m pytest tests/e2e/test_product_owner_questions.py::TestProductOwnerQuestionSuite::test_summary_report \
       -v --tb=line 2>&1 | tee "$LOG_DIR/model_${MODEL//[:\/]/_}_${TIMESTAMP}.log"; then
        RESULT="PASSED"
    else
        RESULT="FAILED (below thresholds)"
    fi
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # Extract accuracy from aggregate file (most recent)
    AGG_FILE="$LOG_DIR/product_owner_aggregate.json"
    if [ -f "$AGG_FILE" ]; then
        INTENT_ACC=$(python3 -c "import json; print(f\"{json.load(open('$AGG_FILE'))['rates']['intent']*100:.1f}%\")" 2>/dev/null || echo "N/A")
        SUBJECT_ACC=$(python3 -c "import json; print(f\"{json.load(open('$AGG_FILE'))['rates']['subject']*100:.1f}%\")" 2>/dev/null || echo "N/A")
        MEASURE_ACC=$(python3 -c "import json; print(f\"{json.load(open('$AGG_FILE'))['rates']['measure']*100:.1f}%\")" 2>/dev/null || echo "N/A")
        
        echo ""
        echo "✓ $MODEL completed in ${DURATION}s"
        echo "  Intent: $INTENT_ACC | Subject: $SUBJECT_ACC | Measure: $MEASURE_ACC"
        echo ""
        
        echo "$MODEL ($RESULT - ${DURATION}s):" >> "$COMPARISON_FILE"
        echo "  Intent:   $INTENT_ACC" >> "$COMPARISON_FILE"
        echo "  Subject:  $SUBJECT_ACC" >> "$COMPARISON_FILE"
        echo "  Measure:  $MEASURE_ACC" >> "$COMPARISON_FILE"
        echo "" >> "$COMPARISON_FILE"
        
        # Archive the aggregate file
        cp "$AGG_FILE" "$LOG_DIR/aggregate_${MODEL//[:\/]/_}_${TIMESTAMP}.json"
    else
        echo "⚠️  No aggregate file found for $MODEL"
        echo "$MODEL: NO RESULTS" >> "$COMPARISON_FILE"
        echo "" >> "$COMPARISON_FILE"
    fi
done

echo "================================================================================"
echo "Comparison complete!"
echo "Results summary: $COMPARISON_FILE"
echo "Detailed logs: $LOG_DIR/model_*_${TIMESTAMP}.log"
echo "================================================================================"

cat "$COMPARISON_FILE"
