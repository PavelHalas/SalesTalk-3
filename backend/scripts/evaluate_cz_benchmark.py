#!/usr/bin/env python3
"""Czech Benchmark Evaluation

Evaluates classification pipeline coverage and accuracy against the Czech benchmark corpus.
Reports layer-by-layer recall and identifies gaps.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lambda"))

from normalization.diacritic_utils import strip_diacritics
from normalization.cz_normalizer import normalize_czech_query
from normalization.pattern_matcher import apply_czech_patterns
from normalization.fuzzy_matcher import apply_fuzzy_czech_patterns
from normalization.exemplar_store import retrieve_similar_cz

CORPUS_PATH = Path(__file__).parent.parent / "tests" / "data" / "czech_benchmark_corpus.jsonl"


def load_corpus() -> List[Dict[str, Any]]:
    """Load benchmark corpus from JSONL."""
    queries = []
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                queries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return queries


def evaluate_query(query: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single query through the pipeline.
    
    Returns:
        Result dict with detected layer, success, and details
    """
    cz_text = query["cz"]
    expected_layer = query["layer"]
    
    # Normalize (strip diacritics)
    normalized = strip_diacritics(cz_text.lower())
    
    # Layer 1: Lexical normalization
    norm_result = normalize_czech_query(normalized)
    if norm_result.normalized != normalized:
        # Some normalization occurred
        return {
            "layer": "lexical",
            "success": expected_layer == "lexical",
            "output": norm_result.normalized,
            "coverage": norm_result.coverage,
        }
    
    # Layer 2: Pattern matching
    pattern_result = apply_czech_patterns(normalized)
    if pattern_result.get("rewrite"):
        return {
            "layer": "pattern",
            "success": expected_layer == "pattern",
            "output": pattern_result["rewrite"],
            "patterns": pattern_result.get("matched", []),
        }
    
    # Layer 3: Fuzzy matching
    fuzzy_result = apply_fuzzy_czech_patterns(normalized)
    if fuzzy_result.get("rewrite") and fuzzy_result.get("score", 0) >= 0.75:
        return {
            "layer": "fuzzy",
            "success": expected_layer == "fuzzy",
            "output": fuzzy_result["rewrite"],
            "score": fuzzy_result["score"],
        }
    
    # Layer 4: Exemplar retrieval
    exemplars = retrieve_similar_cz(normalized, top_k=1)
    if exemplars and exemplars[0]["score"] >= 0.85:
        return {
            "layer": "exemplar",
            "success": expected_layer == "exemplar",
            "output": exemplars[0]["en"],
            "score": exemplars[0]["score"],
        }
    
    # No layer matched
    return {
        "layer": "none",
        "success": expected_layer == "manual",
        "output": normalized,
    }


def main():
    """Run benchmark evaluation."""
    print("🧪 Czech Benchmark Evaluation\n")
    
    corpus = load_corpus()
    print(f"Loaded {len(corpus)} queries from corpus\n")
    
    # Track results by layer
    layer_stats = {
        "lexical": {"total": 0, "correct": 0},
        "pattern": {"total": 0, "correct": 0},
        "fuzzy": {"total": 0, "correct": 0},
        "exemplar": {"total": 0, "correct": 0},
        "manual": {"total": 0, "correct": 0},
        "none": {"total": 0, "correct": 0},
    }
    
    failures = []
    
    for query in corpus:
        result = evaluate_query(query)
        expected_layer = query["layer"]
        detected_layer = result["layer"]
        
        # Update stats
        layer_stats[expected_layer]["total"] += 1
        if result["success"]:
            layer_stats[expected_layer]["correct"] += 1
        else:
            failures.append({
                "query": query["cz"],
                "expected_layer": expected_layer,
                "detected_layer": detected_layer,
                "expected_en": query["en"],
                "actual_output": result.get("output", ""),
            })
    
    # Print layer-by-layer recall
    print("📊 Layer-by-Layer Recall:\n")
    total_queries = len(corpus)
    total_correct = 0
    
    for layer, stats in layer_stats.items():
        if stats["total"] > 0:
            recall = stats["correct"] / stats["total"]
            total_correct += stats["correct"]
            print(f"  {layer:12s}: {stats['correct']:2d}/{stats['total']:2d} ({recall:6.1%})")
    
    overall_recall = total_correct / total_queries if total_queries > 0 else 0
    print(f"\n  {'Overall':12s}: {total_correct:2d}/{total_queries:2d} ({overall_recall:6.1%})")
    
    # Print failures
    if failures:
        print(f"\n❌ {len(failures)} Mismatches:\n")
        for i, fail in enumerate(failures[:10], 1):  # Show first 10
            print(f"{i}. \"{fail['query']}\"")
            print(f"   Expected: {fail['expected_layer']} → \"{fail['expected_en']}\"")
            print(f"   Detected: {fail['detected_layer']} → \"{fail['actual_output']}\"")
            print()
        
        if len(failures) > 10:
            print(f"   ... and {len(failures) - 10} more mismatches")
    
    print("\n" + "=" * 60)
    
    if overall_recall >= 0.85:
        print(f"✅ PASS: Overall recall {overall_recall:.1%} >= 85%")
        sys.exit(0)
    else:
        print(f"⚠️  WARN: Overall recall {overall_recall:.1%} < 85%")
        print("   Consider expanding lexicons, patterns, or exemplars")
        sys.exit(1)


if __name__ == "__main__":
    main()
