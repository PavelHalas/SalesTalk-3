# 🛠️ SalesTalk Scripts

This directory contains utility scripts for SalesTalk development, testing, and evaluation.

---

## 📁 Scripts

### `evaluate_classification.py`

**Purpose:** Evaluate classification accuracy, calibration, and safety metrics for SalesTalk's semantic layer.

**Features:**
- Component-level accuracy (intent, subject, measure, dimension, time)
- Overall classification accuracy
- Expected Calibration Error (ECE) measurement
- Hallucination detection and tracking
- Refusal accuracy for ambiguous questions
- Gate criteria validation for MVP launch

**Usage:**
```bash
# Evaluate gold dataset
python3 backend/src/evaluate_classification.py --dataset evaluation/gold.json --mode gold

# Evaluate adversarial dataset
python3 backend/src/evaluate_classification.py --dataset backend/evaluation/adversarial.json --mode adversarial

# Evaluate all datasets
python3 backend/src/evaluate_classification.py --all

# Save detailed results
python3 backend/src/evaluate_classification.py --all --output evaluation/results.json
```

**Options:**
- `--dataset PATH`: Path to evaluation dataset JSON file
- `--mode {gold,adversarial}`: Evaluation mode (default: gold)
- `--output PATH`: Save detailed results to JSON file
- `--all`: Evaluate both gold and adversarial datasets
- `--help`: Show help message

**Output:**
- Console summary with component accuracy, calibration, and hallucination metrics
- Optional JSON output with detailed per-question results
- Pass/fail status for MVP gate criteria

**Dependencies:**
- Python 3.8+ (uses only standard library)
- No external packages required for basic functionality

**Integration Points:**
In production, the classifier function should be passed to `evaluate_dataset()`:

```python
from my_classifier import classify_question

evaluator = ClassificationEvaluator("evaluation/gold.json", mode="gold")
results = evaluator.evaluate_dataset(classifier_func=classify_question)
```

---

## 🔮 Future Scripts (Planned)

### `sample_production_questions.py`
Extract and anonymize production user questions for evaluation dataset expansion.

### `generate_calibration_plot.py`
Create visual reliability diagrams from evaluation results.

### `benchmark_latency.py`
Measure P50/P95/P99 latency for classification and narrative generation.

### `validate_ontology.py`
Check ontology consistency and coverage against production data.

### `analyze_failures.py`
Deep-dive analysis of classification failures and error patterns.

---

## 📚 Documentation

For detailed information on evaluation:
- See `evaluation/README.md` for dataset documentation
- See `backend/ontology/ONTOLOGY_v0.md` for classification schema
- See `docs/KPI_BASELINE.md` for success criteria

---

## 🤝 Contributing

When adding new scripts:

1. **Follow naming convention:** `verb_noun.py` (e.g., `evaluate_classification.py`)
2. **Add docstring:** Module-level docstring with purpose and usage
3. **Add to this README:** Document the script with examples
4. **Make executable:** `chmod +x scripts/your_script.py`
5. **Add shebang:** `#!/usr/bin/env python3` at top of file
6. **Use argparse:** Consistent CLI interface with `--help`
7. **Error handling:** Graceful failures with informative messages

---

*Last updated: November 2025*
