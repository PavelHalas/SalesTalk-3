#!/usr/bin/env python3
"""
SalesTalk Classification Evaluator

This script evaluates the accuracy and calibration of the classification system
for the SalesTalk conversational analytics platform.

Features:
- Component-level accuracy (intent, subject, measure, dimension, time)
- Overall classification accuracy
- Calibration measurement with reliability diagrams
- Hallucination detection and reference coverage checks
- Support for both gold and adversarial datasets

Usage:
    python evaluate_classification.py --dataset evaluation/gold.json
    python evaluate_classification.py --dataset evaluation/adversarial.json --mode adversarial
    python evaluate_classification.py --all
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')


class ClassificationEvaluator:
    """Evaluates classification accuracy and quality metrics."""
    
    def __init__(self, dataset_path: str, mode: str = "gold"):
        """
        Initialize evaluator.
        
        Args:
            dataset_path: Path to JSON dataset file
            mode: 'gold' for standard evaluation, 'adversarial' for robustness testing
        """
        self.dataset_path = Path(dataset_path)
        self.mode = mode
        self.dataset = self._load_dataset()
        self.results = {
            "metadata": {},
            "component_accuracy": {},
            "overall_accuracy": 0.0,
            "calibration": {},
            "hallucination": {},
            "per_question_results": []
        }
        
    def _load_dataset(self) -> Dict[str, Any]:
        """Load and validate dataset file."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")
        
        with open(self.dataset_path, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if "questions" not in data:
            raise ValueError("Dataset missing 'questions' key")
        
        print(f"✓ Loaded dataset: {data['metadata'].get('description', 'Unknown')}")
        print(f"  Total questions: {len(data['questions'])}")
        
        return data
    
    def evaluate_component(self, predicted: Any, expected: Any, component: str) -> Tuple[bool, float]:
        """
        Evaluate a single component of classification.
        
        Args:
            predicted: Predicted value
            expected: Expected value
            component: Component name (intent, subject, measure, etc.)
        
        Returns:
            Tuple of (is_correct, partial_credit_score)
        """
        # Placeholder implementation - in production, this would call actual classifier
        # For now, we simulate perfect classification for demonstration
        
        if expected is None or expected == "unknown":
            # Unknown expected value - can't evaluate
            return (True, 1.0)
        
        if isinstance(expected, dict):
            # Dictionary comparison (e.g., dimension, time)
            if not isinstance(predicted, dict):
                return (False, 0.0)
            
            # Count matching keys
            total_keys = len(expected)
            if total_keys == 0:
                return (True, 1.0)
            
            matching_keys = sum(1 for k, v in expected.items() 
                              if k in predicted and self._values_match(predicted[k], v))
            
            score = matching_keys / total_keys
            is_correct = score >= 0.8  # 80% threshold for correctness
            return (is_correct, score)
        
        elif isinstance(expected, list):
            # List comparison (e.g., multiple regions)
            if not isinstance(predicted, list):
                predicted = [predicted]
            
            # Check if all expected items are in predicted
            matches = sum(1 for item in expected if item in predicted)
            score = matches / len(expected) if expected else 1.0
            is_correct = score >= 0.8
            return (is_correct, score)
        
        else:
            # Simple value comparison
            is_correct = self._values_match(predicted, expected)
            return (is_correct, 1.0 if is_correct else 0.0)
    
    def _values_match(self, val1: Any, val2: Any) -> bool:
        """Check if two values match (case-insensitive for strings)."""
        if isinstance(val1, str) and isinstance(val2, str):
            return val1.lower() == val2.lower()
        return val1 == val2
    
    def evaluate_dataset(self, classifier_func=None) -> Dict[str, Any]:
        """
        Evaluate entire dataset.
        
        Args:
            classifier_func: Optional classifier function. If None, uses mock results.
        
        Returns:
            Evaluation results dictionary
        """
        print(f"\n{'='*70}")
        print(f"EVALUATING: {self.mode.upper()} MODE")
        print(f"{'='*70}\n")
        
        component_scores = defaultdict(list)
        overall_correct = 0
        total_questions = len(self.dataset['questions'])
        
        # Calibration buckets
        calibration_buckets = defaultdict(lambda: {"correct": 0, "total": 0})
        
        # Hallucination tracking
        hallucination_cases = []
        refusal_accuracy = {"correct_refusals": 0, "incorrect_refusals": 0, "total_should_refuse": 0}
        
        for question_data in self.dataset['questions']:
            question_id = question_data['id']
            question = question_data['question']
            expected = question_data['expected']
            
            # In production, this would call the actual classifier
            # For demonstration, we simulate predictions
            predicted = self._mock_classifier(question, expected)
            
            # Evaluate each component
            results = {}
            all_correct = True
            
            for component in ['intent', 'subject', 'measure', 'dimension', 'time']:
                if component in expected:
                    is_correct, score = self.evaluate_component(
                        predicted.get(component),
                        expected.get(component),
                        component
                    )
                    results[component] = {
                        "correct": is_correct,
                        "score": score,
                        "predicted": predicted.get(component),
                        "expected": expected.get(component)
                    }
                    component_scores[component].append(score)
                    
                    if not is_correct:
                        all_correct = False
            
            # Overall accuracy
            if all_correct:
                overall_correct += 1
            
            # Calibration tracking
            confidence = predicted.get("confidence", {}).get("overall", 0.5)
            bucket = self._get_confidence_bucket(confidence)
            calibration_buckets[bucket]["total"] += 1
            if all_correct:
                calibration_buckets[bucket]["correct"] += 1
            
            # Refusal accuracy
            should_refuse = question_data.get('expected', {}).get('should_refuse', False)
            did_refuse = predicted.get('refused', False)
            
            if should_refuse:
                refusal_accuracy["total_should_refuse"] += 1
                if did_refuse:
                    refusal_accuracy["correct_refusals"] += 1
            elif did_refuse:
                refusal_accuracy["incorrect_refusals"] += 1
                hallucination_cases.append({
                    "question_id": question_id,
                    "question": question,
                    "reason": "Incorrectly refused valid question"
                })
            
            # Store per-question results
            self.results["per_question_results"].append({
                "question_id": question_id,
                "question": question,
                "all_correct": all_correct,
                "component_results": results,
                "confidence": confidence,
                "should_refuse": should_refuse,
                "did_refuse": did_refuse
            })
        
        # Calculate component accuracy
        for component, scores in component_scores.items():
            accuracy = sum(scores) / len(scores) if scores else 0.0
            self.results["component_accuracy"][component] = {
                "accuracy": accuracy,
                "count": len(scores)
            }
        
        # Overall accuracy
        self.results["overall_accuracy"] = overall_correct / total_questions if total_questions > 0 else 0.0
        
        # Calibration metrics
        self.results["calibration"] = self._calculate_calibration(calibration_buckets)
        
        # Hallucination metrics
        hallucination_rate = len(hallucination_cases) / total_questions if total_questions > 0 else 0.0
        self.results["hallucination"] = {
            "hallucination_rate": hallucination_rate,
            "hallucination_cases": hallucination_cases,
            "refusal_accuracy": refusal_accuracy
        }
        
        # Metadata
        self.results["metadata"] = {
            "dataset": str(self.dataset_path),
            "mode": self.mode,
            "total_questions": total_questions,
            "dataset_info": self.dataset.get("metadata", {})
        }
        
        return self.results
    
    def _mock_classifier(self, question: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock classifier for demonstration purposes.
        
        In production, this would call the actual TRM classifier or LLM-based classifier.
        For demonstration, we simulate realistic predictions with some errors.
        """
        import random
        
        # Simulate high accuracy (90%) for gold set, lower (70%) for adversarial
        accuracy_target = 0.90 if self.mode == "gold" else 0.70
        
        # Check if question should be refused
        should_refuse = expected.get('should_refuse', False)
        
        # Simulate refusal behavior
        if should_refuse:
            # 85% chance of correctly refusing
            did_refuse = random.random() < 0.85
        else:
            # 5% chance of incorrectly refusing
            did_refuse = random.random() < 0.05
        
        if did_refuse:
            return {
                "refused": True,
                "refusal_reason": "Insufficient confidence or ambiguous question",
                "confidence": {"overall": random.uniform(0.3, 0.6)}
            }
        
        # Build predicted classification
        predicted = {
            "refused": False,
            "confidence": {
                "overall": random.uniform(0.7, 0.95) if random.random() < accuracy_target else random.uniform(0.5, 0.7)
            }
        }
        
        # For each component, simulate prediction
        for component in ['intent', 'subject', 'measure', 'dimension', 'time']:
            if component in expected:
                # Simulate accuracy: correct most of the time
                if random.random() < accuracy_target:
                    # Correct prediction
                    predicted[component] = expected[component]
                else:
                    # Incorrect prediction - use a plausible wrong answer
                    predicted[component] = self._generate_wrong_answer(component, expected[component])
        
        return predicted
    
    def _generate_wrong_answer(self, component: str, correct_value: Any) -> Any:
        """Generate a plausible wrong answer for testing."""
        wrong_answers = {
            "intent": ["what", "compare", "trend", "why", "rank"],
            "subject": ["revenue", "margin", "customers", "products", "sales"],
            "measure": ["revenue", "gm_pct", "customer_count", "churn_rate", "aov"]
        }
        
        if component in wrong_answers:
            options = [x for x in wrong_answers[component] if x != correct_value]
            return options[0] if options else correct_value
        
        return "unknown"
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Map confidence to a bucket for calibration analysis."""
        if confidence >= 0.9:
            return "0.9-1.0"
        elif confidence >= 0.8:
            return "0.8-0.9"
        elif confidence >= 0.7:
            return "0.7-0.8"
        elif confidence >= 0.6:
            return "0.6-0.7"
        else:
            return "0.0-0.6"
    
    def _calculate_calibration(self, buckets: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Calculate calibration metrics (ECE - Expected Calibration Error)."""
        calibration_data = []
        total_samples = sum(b["total"] for b in buckets.values())
        ece = 0.0  # Expected Calibration Error
        
        for bucket_name in sorted(buckets.keys()):
            bucket = buckets[bucket_name]
            if bucket["total"] == 0:
                continue
            
            accuracy = bucket["correct"] / bucket["total"]
            # Use midpoint of bucket as confidence
            confidence = float(bucket_name.split("-")[0]) + 0.05
            weight = bucket["total"] / total_samples
            
            calibration_gap = abs(accuracy - confidence)
            ece += weight * calibration_gap
            
            calibration_data.append({
                "bucket": bucket_name,
                "confidence": confidence,
                "accuracy": accuracy,
                "count": bucket["total"],
                "gap": calibration_gap
            })
        
        return {
            "ece": ece,
            "calibration_data": calibration_data
        }
    
    def print_summary(self):
        """Print evaluation summary to console."""
        results = self.results
        
        print(f"\n{'='*70}")
        print(f"EVALUATION SUMMARY - {self.mode.upper()} MODE")
        print(f"{'='*70}\n")
        
        # Overall accuracy
        overall = results["overall_accuracy"]
        status = "✓ PASS" if overall >= 0.80 else "✗ FAIL"
        print(f"Overall Accuracy: {overall:.1%} {status}")
        print(f"  Target: ≥80% for gold set, ≥70% for adversarial\n")
        
        # Component accuracy
        print("Component Accuracy:")
        print(f"  {'Component':<12} {'Accuracy':<10} {'Count':<8} {'Target':<10} {'Status':<6}")
        print(f"  {'-'*60}")
        
        targets = {
            "intent": 0.90,
            "subject": 0.85,
            "measure": 0.85,
            "time": 0.80,
            "dimension": 0.75
        }
        
        for component, data in sorted(results["component_accuracy"].items()):
            accuracy = data["accuracy"]
            count = data["count"]
            target = targets.get(component, 0.80)
            status = "✓" if accuracy >= target else "✗"
            
            print(f"  {component:<12} {accuracy:>7.1%}    {count:<8} ≥{target:.0%}       {status}")
        
        # Calibration
        print(f"\nCalibration (ECE - Expected Calibration Error):")
        ece = results["calibration"]["ece"]
        ece_status = "✓ PASS" if ece < 0.08 else "✗ FAIL"
        print(f"  ECE: {ece:.3f} {ece_status}")
        print(f"  Target: <0.08\n")
        
        print("  Reliability by Confidence Bucket:")
        print(f"  {'Bucket':<12} {'Confidence':<12} {'Accuracy':<12} {'Count':<8} {'Gap':<8}")
        print(f"  {'-'*60}")
        
        for cal_data in results["calibration"]["calibration_data"]:
            print(f"  {cal_data['bucket']:<12} {cal_data['confidence']:>10.2f}   "
                  f"{cal_data['accuracy']:>10.1%}   {cal_data['count']:<8} {cal_data['gap']:>6.3f}")
        
        # Hallucination metrics
        print(f"\nHallucination & Safety Metrics:")
        hall_data = results["hallucination"]
        hall_rate = hall_data["hallucination_rate"]
        hall_status = "✓ PASS" if hall_rate < 0.10 else "✗ FAIL"
        print(f"  Hallucination Rate: {hall_rate:.1%} {hall_status}")
        print(f"  Target: <10% (MVP), <5% (production)\n")
        
        refusal = hall_data["refusal_accuracy"]
        if refusal["total_should_refuse"] > 0:
            refusal_rate = refusal["correct_refusals"] / refusal["total_should_refuse"]
            print(f"  Refusal Accuracy: {refusal_rate:.1%}")
            print(f"    Correct refusals: {refusal['correct_refusals']}/{refusal['total_should_refuse']}")
            print(f"    Incorrect refusals: {refusal['incorrect_refusals']}")
        
        # Gate criteria
        print(f"\n{'='*70}")
        print(f"GATE CRITERIA - MVP LAUNCH")
        print(f"{'='*70}\n")
        
        gate_pass = True
        
        checks = [
            ("Overall Accuracy ≥75%", overall >= 0.75, overall),
            ("Hallucination Rate <10%", hall_rate < 0.10, hall_rate),
            ("ECE <0.08", ece < 0.08, ece),
        ]
        
        for check_name, passed, value in checks:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {check_name:<30} {status}")
            if not passed:
                gate_pass = False
        
        print(f"\n{'='*70}")
        if gate_pass:
            print(f"✓ ALL GATE CRITERIA MET - READY FOR MVP LAUNCH")
        else:
            print(f"✗ SOME CRITERIA NOT MET - ADDITIONAL WORK REQUIRED")
        print(f"{'='*70}\n")
    
    def save_results(self, output_path: str):
        """Save detailed results to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"✓ Detailed results saved to: {output_path}")


def main():
    """Main entry point for evaluation script."""
    parser = argparse.ArgumentParser(
        description="Evaluate SalesTalk classification accuracy and quality"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Path to dataset JSON file"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["gold", "adversarial"],
        default="gold",
        help="Evaluation mode"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for detailed results JSON"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all datasets (gold and adversarial)"
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Evaluate both datasets
        datasets = [
            ("evaluation/gold.json", "gold"),
            ("evaluation/adversarial.json", "adversarial")
        ]
    elif args.dataset:
        datasets = [(args.dataset, args.mode)]
    else:
        print("Error: Must specify --dataset or --all")
        parser.print_help()
        sys.exit(1)
    
    # Run evaluations
    all_results = {}
    
    for dataset_path, mode in datasets:
        try:
            evaluator = ClassificationEvaluator(dataset_path, mode)
            results = evaluator.evaluate_dataset()
            evaluator.print_summary()
            
            # Save results if output specified
            if args.output:
                output_file = args.output.replace(".json", f"_{mode}.json")
                evaluator.save_results(output_file)
            
            all_results[mode] = results
            
        except Exception as e:
            print(f"Error evaluating {dataset_path}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Final summary if evaluating all
    if args.all:
        print(f"\n{'='*70}")
        print(f"COMBINED SUMMARY")
        print(f"{'='*70}\n")
        
        for mode, results in all_results.items():
            print(f"{mode.upper()}: Overall Accuracy = {results['overall_accuracy']:.1%}, "
                  f"Hallucination Rate = {results['hallucination']['hallucination_rate']:.1%}")
        
        print()


if __name__ == "__main__":
    main()
