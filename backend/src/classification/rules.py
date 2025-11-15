"""
Phase 0: Subject-Metric Rules Engine (RULES)

Deterministic corrections for known metric-to-subject family mappings.
Eliminates trivial leaks where metrics appear as subjects.
"""

from typing import Dict, Any, List, Tuple

from .config_loader import ClassificationConfigError, get_metrics_config

_METRIC_CONFIG = get_metrics_config()
METRIC_SUBJECT_MAP = _METRIC_CONFIG.get("subject_map", {})
METRIC_ALIASES = _METRIC_CONFIG.get("aliases", {})

if not METRIC_SUBJECT_MAP:
    raise ClassificationConfigError("Metric subject map is empty; taxonomy misconfigured")


def apply_subject_metric_rules(classification: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Apply deterministic subject-metric correction rules.
    
    Args:
        classification: Initial classification dict
        
    Returns:
        Tuple of (corrected_classification, list of corrections applied)
    """
    corrections = []
    result = dict(classification)
    
    subject = result.get("subject", "").lower()
    measure = result.get("measure", "").lower()
    
    # Rule 1: Normalize metric aliases to canonical names
    if measure in METRIC_ALIASES:
        canonical = METRIC_ALIASES[measure]
        corrections.append(f"metric_alias_normalized:{measure}→{canonical}")
        result["measure"] = canonical
        measure = canonical
    
    # Rule 2: Fix metric-as-subject leak (most common error)
    if subject in METRIC_SUBJECT_MAP:
        # Subject is actually a metric name
        correct_subject = METRIC_SUBJECT_MAP[subject]
        original_subject = subject  # Save original before correction
        corrections.append(f"metric_leak_fixed:subject={subject}→{correct_subject}")
        result["subject"] = correct_subject
        subject = correct_subject
        
        # If measure is empty or generic, use the leaked subject (which was the metric) as the measure
        if not measure or measure in {"value", "total", "amount"}:
            # Normalize the measure in case it's an alias
            normalized_measure = METRIC_ALIASES.get(original_subject, original_subject)
            corrections.append(f"measure_inferred:{original_subject}")
            if normalized_measure != original_subject:
                corrections.append(f"metric_alias_normalized:{original_subject}→{normalized_measure}")
            result["measure"] = normalized_measure
            measure = normalized_measure
    
    # Rule 3: Enforce metric-subject family constraints
    if measure in METRIC_SUBJECT_MAP:
        required_subject = METRIC_SUBJECT_MAP[measure]
        if subject != required_subject:
            corrections.append(
                f"subject_family_corrected:measure={measure} requires subject={required_subject} (was {subject})"
            )
            result["subject"] = required_subject
    
    return result, corrections


def normalize_measure(measure: str) -> str:
    """
    Normalize a measure name to its canonical form.
    
    Args:
        measure: Raw measure string
        
    Returns:
        Canonical measure name
    """
    measure = measure.lower().strip()
    return METRIC_ALIASES.get(measure, measure)


def get_subject_for_measure(measure: str) -> str:
    """
    Get the canonical subject for a given measure.
    
    Args:
        measure: Measure name
        
    Returns:
        Subject name or empty string if not found
    """
    measure = normalize_measure(measure)
    return METRIC_SUBJECT_MAP.get(measure, "")
