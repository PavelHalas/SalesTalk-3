# 🧪 SalesTalk Evaluation Framework

**Version:** 1.0  
**Author:** Data Science Copilot  
**Date:** November 2025

---

## 📋 Overview

This directory contains the evaluation framework for SalesTalk's classification system. It includes:

- **Gold dataset** (`gold.json`): 55 carefully labeled business questions for accuracy measurement
- **Adversarial dataset** (`adversarial.json`): 35 edge cases and ambiguous queries for robustness testing
- **Evaluation script** (`../scripts/evaluate_classification.py`): Automated evaluation with accuracy, calibration, and hallucination metrics

---

## 🎯 Purpose

The evaluation framework measures:

1. **Classification Accuracy**: How well the system classifies user questions
   - Component-level accuracy (intent, subject, measure, dimension, time)
   - Overall accuracy (all components correct)

2. **Calibration**: How well confidence scores match actual accuracy
   - Expected Calibration Error (ECE)
   - Reliability diagrams by confidence bucket

3. **Safety & Hallucination**: How often the system makes mistakes or refuses appropriately
   - Hallucination rate (incorrect responses)
   - Refusal accuracy (correctly refusing ambiguous questions)
   - Reference coverage (facts backed by data)

---

## 📊 Datasets

### Gold Dataset (`gold.json`)

**Purpose:** Baseline accuracy measurement with high-quality labeled questions

**Contents:**
- 55 business questions covering all major intents and subjects
- Difficulty levels: easy (40%), medium (45%), hard (15%)
- Tags: basic queries, comparisons, trends, rankings, drill-downs, etc.

**Coverage:**
- Intents: `what` (20), `compare` (12), `trend` (5), `rank` (5), `drill` (6), `why` (2), `forecast` (2), `target` (2), `anomaly` (1), `correlation` (1)
- Subjects: revenue, margin, customers, products, sales, orders, operations, finance, people
- Time periods: quarters, months, weeks, days, YTD, MTD, rolling windows, YoY/QoQ/MoM comparisons

**Example:**
```json
{
  "id": "gold_001",
  "question": "What is our Q3 revenue?",
  "expected": {
    "intent": "what",
    "subject": "revenue",
    "measure": "revenue",
    "dimension": {},
    "time": {"period": "Q3", "granularity": "quarter"}
  },
  "difficulty": "easy",
  "tags": ["basic", "single_metric", "quarterly"]
}
```

### Adversarial Dataset (`adversarial.json`)

**Purpose:** Robustness testing with challenging, ambiguous, and edge-case queries

**Contents:**
- 35 adversarial test cases
- Categories: vague, incomplete, typos, multi-question, non-English, nonsense, etc.

**Categories:**
- **Vague/Ambiguous** (5): "How are we doing?", "Are we winning?"
- **Syntax Issues** (8): Typos, fragments, all-caps, repetitive keywords
- **Multi-Question** (4): Compound queries with multiple intents
- **Out-of-Scope** (6): Non-English, weather questions, hypotheticals
- **Refusal Cases** (10): Should trigger refusal (low confidence or nonsense)
- **Security** (2): SQL injection attempts

**Example:**
```json
{
  "id": "adv_001",
  "question": "How are we doing?",
  "expected": {
    "intent": "what",
    "subject": "unknown",
    "measure": "unknown",
    "should_refuse": true,
    "refusal_reason": "Ambiguous - no clear metric specified"
  },
  "difficulty": "hard",
  "category": "vague",
  "tags": ["ambiguous", "underspecified", "refusal_case"]
}
```

---

## 🚀 Usage

### Basic Evaluation

```bash
# Evaluate gold dataset only
cd /path/to/SalesTalk-3
python3 scripts/evaluate_classification.py --dataset evaluation/gold.json --mode gold

# Evaluate adversarial dataset only
python3 scripts/evaluate_classification.py --dataset evaluation/adversarial.json --mode adversarial

# Evaluate all datasets
python3 scripts/evaluate_classification.py --all
```

### Save Results

```bash
# Save detailed results to JSON
python3 scripts/evaluate_classification.py --all --output evaluation/results.json

# Results are saved as:
# - evaluation/results_gold.json
# - evaluation/results_adversarial.json
```

### Example Output

```
======================================================================
EVALUATION SUMMARY - GOLD MODE
======================================================================

Overall Accuracy: 85.5% ✓ PASS
  Target: ≥80% for gold set, ≥70% for adversarial

Component Accuracy:
  Component    Accuracy   Count    Target     Status
  ------------------------------------------------------------
  intent         92.7%    55       ≥90%       ✓
  subject        89.1%    55       ≥85%       ✓
  measure        87.3%    55       ≥85%       ✓
  dimension      81.8%    55       ≥75%       ✓
  time           85.5%    55       ≥80%       ✓

Calibration (ECE - Expected Calibration Error):
  ECE: 0.065 ✓ PASS
  Target: <0.08

Hallucination & Safety Metrics:
  Hallucination Rate: 3.6% ✓ PASS
  Target: <10% (MVP), <5% (production)
```

---

## 📏 Evaluation Metrics

### Component Accuracy

Measures how often each classification component is correct:

| Component | Target (Gold) | Target (Adversarial) |
|-----------|---------------|---------------------|
| **Intent** | ≥90% | ≥85% |
| **Subject** | ≥85% | ≥80% |
| **Measure** | ≥85% | ≥80% |
| **Dimension** | ≥75% | ≥70% |
| **Time** | ≥80% | ≥75% |

### Overall Accuracy

Percentage of questions where **all components** are classified correctly.

- **Gold Target:** ≥80%
- **Adversarial Target:** ≥70%

### Calibration (ECE)

Expected Calibration Error measures how well confidence scores match actual accuracy.

- **Formula:** `ECE = Σ (weight × |accuracy - confidence|)` across confidence buckets
- **Target:** <0.08
- **Interpretation:** Lower is better. ECE < 0.08 means confidence is well-calibrated.

**Confidence Buckets:**
- 0.9-1.0: Very high confidence
- 0.8-0.9: High confidence
- 0.7-0.8: Medium-high confidence
- 0.6-0.7: Medium confidence
- 0.0-0.6: Low confidence

### Hallucination Rate

Percentage of questions where the system provides an incorrect or unsupported answer.

- **MVP Target:** <10%
- **Production Target:** <5%
- **Critical:** <2%

**Counted as hallucination:**
- Incorrect refusal (refusing a valid question)
- Fabricated data values
- Unsupported claims in narrative

### Refusal Accuracy

Percentage of ambiguous/invalid questions that are correctly refused.

- **Target:** ≥85%
- **Correct refusal:** System declines to answer when confidence < threshold
- **Incorrect refusal:** System declines a valid, clear question

---

## 🎯 Gate Criteria (MVP Launch)

For MVP launch approval, the following must be met:

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| **Overall Accuracy (Gold)** | ≥75% | Required |
| **Hallucination Rate** | <10% | Required |
| **Calibration (ECE)** | <0.08 | Required |
| **Component Accuracy** | See table above | Recommended |

**Pass Criteria:**
- All three required criteria must pass
- At least 3 out of 5 component accuracies meet targets

---

## 🔧 Integration with CI

### GitHub Actions Workflow

Add to `.github/workflows/evaluate.yml`:

```yaml
name: Classification Evaluation

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run evaluation
        run: |
          python3 scripts/evaluate_classification.py --all --output evaluation/ci_results.json
      
      - name: Check gate criteria
        run: |
          python3 -c "
          import json
          import sys
          
          with open('evaluation/ci_results_gold.json') as f:
              results = json.load(f)
          
          overall_acc = results['overall_accuracy']
          hall_rate = results['hallucination']['hallucination_rate']
          ece = results['calibration']['ece']
          
          passed = overall_acc >= 0.75 and hall_rate < 0.10 and ece < 0.08
          
          print(f'Overall Accuracy: {overall_acc:.1%}')
          print(f'Hallucination Rate: {hall_rate:.1%}')
          print(f'ECE: {ece:.3f}')
          
          if not passed:
              print('GATE CRITERIA NOT MET')
              sys.exit(1)
          else:
              print('GATE CRITERIA PASSED')
          "
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: evaluation-results
          path: evaluation/ci_results_*.json
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run evaluation before commit (optional - may be slow)

python3 scripts/evaluate_classification.py --dataset evaluation/gold.json --mode gold

if [ $? -ne 0 ]; then
    echo "Evaluation failed. Commit aborted."
    exit 1
fi
```

---

## 📈 Monitoring & Continuous Improvement

### Weekly Evaluation

Run evaluation weekly on production data samples:

```bash
# Extract sample of real user questions
python3 scripts/sample_production_questions.py --output evaluation/prod_sample.json

# Manually label
# (Use labeling tool or human review)

# Evaluate
python3 scripts/evaluate_classification.py --dataset evaluation/prod_sample.json --mode gold
```

### Drift Detection

Monitor for accuracy drift over time:

1. Store weekly evaluation results
2. Compare to baseline
3. Alert if accuracy drops >5% from baseline

### Expansion

Add new questions to datasets when:
- Users report classification errors
- New intents/subjects are added to ontology
- Edge cases are discovered in production

---

## 🔄 Dataset Maintenance

### Adding Questions to Gold Set

1. Write the business question
2. Manually label expected classification
3. Test with actual classifier
4. Add difficulty level and tags
5. Validate with peer review

**Template:**
```json
{
  "id": "gold_XXX",
  "question": "Your question here",
  "expected": {
    "intent": "...",
    "subject": "...",
    "measure": "...",
    "dimension": {},
    "time": {}
  },
  "difficulty": "easy|medium|hard",
  "tags": ["tag1", "tag2"]
}
```

### Adding Adversarial Cases

1. Identify edge case or failure mode
2. Document expected behavior (refuse, partial, or attempt)
3. Add category and rationale
4. Test for correct refusal or degradation

**Template:**
```json
{
  "id": "adv_XXX",
  "question": "Edge case question",
  "expected": {
    "should_refuse": true,
    "refusal_reason": "Why it should refuse"
  },
  "difficulty": "hard",
  "category": "vague|typo|nonsense|...",
  "tags": ["edge_case_type"]
}
```

---

## 📚 References

- **ONTOLOGY_v0.md**: Classification schema and component definitions
- **KPI_BASELINE.md**: Success metrics and targets
- **Architecture.md**: System design and data model

---

## ✅ Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-09 | Initial release with 55 gold + 35 adversarial questions |

---

*This evaluation framework is designed to grow with the product. Expect regular updates as new intents, subjects, and edge cases are discovered.*
