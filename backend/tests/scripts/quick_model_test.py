#!/usr/bin/env python3
"""
Quick model test: Test 10 representative questions on a single model
Usage: python quick_model_test.py [model_name]
Example: python quick_model_test.py dolphin-mistral:latest
"""
import os
import sys
import json
import time
from pathlib import Path

# Add lambda to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambda"))

from ai_adapter import get_adapter, AIProvider

# 10 representative questions covering the problem areas
TEST_QUESTIONS = [
    ("What is our Q3 revenue?", {"intent": "what", "subject": "revenue", "measure": "revenue"}),
    ("How many orders last month?", {"intent": "what", "subject": "orders", "measure": "order_count"}),
    ("What's customer churn rate?", {"intent": "what", "subject": "customers", "measure": "churn_rate"}),
    ("Show sales pipeline value", {"intent": "what", "subject": "sales", "measure": "pipeline_value"}),
    ("What's conversion rate for marketing?", {"intent": "what", "subject": "marketing", "measure": "conversion_rate"}),
    ("Compare Q3 vs Q4 revenue", {"intent": "compare", "subject": "revenue", "measure": "revenue"}),
    ("Top 5 customers by LTV", {"intent": "rank", "subject": "customers", "measure": "ltv"}),
    ("Revenue by region", {"intent": "breakdown", "subject": "revenue", "measure": "revenue"}),
    ("Are we on track for Q4 target?", {"intent": "target", "subject": "revenue", "measure": "revenue"}),
    ("What's gross margin for Enterprise segment?", {"intent": "what", "subject": "margin", "measure": "gm"}),
]

# Get model from command line arg or env var
MODEL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OLLAMA_MODEL", "dolphin-mistral:latest")

def test_model(model_name: str):
    """Test a model against the 10 questions"""
    print(f"\n{'='*80}")
    print(f"Testing: {model_name}")
    print(f"{'='*80}")
    
    try:
        adapter = get_adapter(
            AIProvider.OLLAMA,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=model_name
        )
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return None
    
    results = {
        "model": model_name,
        "intent_correct": 0,
        "subject_correct": 0,
        "measure_correct": 0,
        "total": len(TEST_QUESTIONS),
        "avg_confidence": 0.0,
        "total_time": 0.0,
        "timeouts": 0,
        "errors": 0,
    }
    
    confidences = []
    
    for i, (question, expected) in enumerate(TEST_QUESTIONS, 1):
        try:
            start = time.time()
            classification = adapter.classify(question, "test-tenant", f"test-{i}")
            elapsed = time.time() - start
            results["total_time"] += elapsed
            
            # Check correctness
            if classification.get("intent") == expected["intent"]:
                results["intent_correct"] += 1
            if classification.get("subject") == expected["subject"]:
                results["subject_correct"] += 1
            if classification.get("measure") == expected["measure"]:
                results["measure_correct"] += 1
            
            conf = classification.get("confidence", {}).get("overall", 0.0)
            confidences.append(conf)
            
            # Print result
            intent_ok = "✓" if classification.get("intent") == expected["intent"] else "✗"
            subject_ok = "✓" if classification.get("subject") == expected["subject"] else "✗"
            measure_ok = "✓" if classification.get("measure") == expected["measure"] else "✗"
            
            print(f"{i:2}. [{intent_ok}{subject_ok}{measure_ok}] {question[:50]:<50} ({elapsed:.1f}s)")
            if subject_ok == "✗":
                print(f"     Subject: expected={expected['subject']}, got={classification.get('subject')}")
            
        except Exception as e:
            results["errors"] += 1
            print(f"{i:2}. [ERR] {question[:50]:<50} Error: {str(e)[:40]}")
    
    if confidences:
        results["avg_confidence"] = sum(confidences) / len(confidences)
    
    # Calculate percentages
    intent_pct = (results["intent_correct"] / results["total"]) * 100
    subject_pct = (results["subject_correct"] / results["total"]) * 100
    measure_pct = (results["measure_correct"] / results["total"]) * 100
    avg_time = results["total_time"] / results["total"]
    
    print(f"\n{'─'*80}")
    print(f"Results for {model_name}:")
    print(f"  Intent:     {results['intent_correct']}/{results['total']} ({intent_pct:.0f}%)")
    print(f"  Subject:    {results['subject_correct']}/{results['total']} ({subject_pct:.0f}%) {'🎯' if subject_pct >= 70 else '❌'}")
    print(f"  Measure:    {results['measure_correct']}/{results['total']} ({measure_pct:.0f}%)")
    print(f"  Avg Conf:   {results['avg_confidence']:.2f}")
    print(f"  Avg Time:   {avg_time:.1f}s/question")
    print(f"  Total Time: {results['total_time']:.1f}s")
    if results["errors"]:
        print(f"  Errors:     {results['errors']}")
    
    return results

if __name__ == "__main__":
    print("="*80)
    print(f"QUICK MODEL TEST: {MODEL}")
    print("="*80)
    print("Testing 10 representative questions")
    print()
    
    result = test_model(MODEL)
    
    if result:
        print(f"\n{'='*80}")
        print(f"RESULT FOR {MODEL}")
        print(f"{'='*80}")
        subj_pct = (result['subject_correct'] / result['total']) * 100
        int_pct = (result['intent_correct'] / result['total']) * 100
        meas_pct = (result['measure_correct'] / result['total']) * 100
        avg_time = result['total_time'] / result['total'] if result['total'] > 0 else 0
        
        print(f"Intent:  {int_pct:>5.1f}% ({result['intent_correct']}/{result['total']})")
        print(f"Subject: {subj_pct:>5.1f}% ({result['subject_correct']}/{result['total']}) {'✅ PASS' if subj_pct >= 70 else '❌ FAIL'}")
        print(f"Measure: {meas_pct:>5.1f}% ({result['measure_correct']}/{result['total']})")
        print(f"Avg Time: {avg_time:.1f}s/question")
        print(f"Errors: {result['errors']}")
        print("="*80)

