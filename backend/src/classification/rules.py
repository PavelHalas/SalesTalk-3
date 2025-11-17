"""
Phase 0: Subject-Metric Rules Engine (RULES)

Deterministic corrections for known metric-to-subject family mappings.
Eliminates trivial leaks where metrics appear as subjects.

Design goal: keep logic generic and taxonomy-driven. Avoid hardcoded
metric-specific keywords; rely on taxonomy aliases for detection.
"""

from typing import Dict, Any, List, Tuple
import re

from .config_loader import ClassificationConfigError, get_metrics_config, get_intent_patterns_config

_METRIC_CONFIG = get_metrics_config()
METRIC_SUBJECT_MAP = _METRIC_CONFIG.get("subject_map", {})
METRIC_ALIASES = _METRIC_CONFIG.get("aliases", {})

_INTENT_PATTERNS = get_intent_patterns_config()

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
        
        # Only apply correction if subject is wrong
        if subject != correct_subject:
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
    
    # Rule 3: Enforce metric-subject family constraints (avoid duplicate corrections)
    if measure in METRIC_SUBJECT_MAP:
        required_subject = METRIC_SUBJECT_MAP[measure]
        if subject != required_subject:
            tag = f"subject_family_corrected:measure={measure} requires subject={required_subject} (was {subject})"
            if tag not in corrections:
                corrections.append(tag)
            result["subject"] = required_subject

    # Dedupe any repeated corrections (preserve order)
    if corrections:
        corrections = list(dict.fromkeys(corrections))
    
    return result, corrections


def apply_intent_rules(question: str, classification: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Lightweight intent corrections based on taxonomy-driven cues and extracted dimensions.

    - If question contains 'why' style cues -> intent='why'
    - If dimension includes rank limit+direction -> intent='rank'
    - If dimension includes breakdown_by -> intent='breakdown'
    - If comparison cues like ' vs ' / 'compare' -> intent='compare'
    
    All cue lists are loaded from taxonomy/default/shared/intent_patterns.json.
    """
    ql = (question or "").lower()
    result = dict(classification)
    corrections: List[str] = []
    intent = str(result.get("intent", "")).lower()
    dim = result.get("dimension") if isinstance(result.get("dimension"), dict) else {}

    # Why-cues override
    why_cues = _INTENT_PATTERNS.get("why_cues", [])
    if any(cue in ql for cue in why_cues) and intent != "why":
        result["intent"] = "why"
        corrections.append("intent_corrected:why_cue")
        intent = "why"

    # Rank based on limit+direction
    if isinstance(dim, dict) and ("limit" in dim and "direction" in dim) and intent != "rank":
        result["intent"] = "rank"
        corrections.append("intent_corrected:rank_from_limit_direction")
        intent = "rank"

    # Breakdown based on breakdown_by
    if isinstance(dim, dict) and dim.get("breakdown_by") and intent != "breakdown":
        result["intent"] = "breakdown"
        corrections.append("intent_corrected:breakdown_from_dimensions")
        intent = "breakdown"

    # Compare cues
    compare_cues = _INTENT_PATTERNS.get("compare_cues", [])
    if any(cue in f" {ql} " for cue in compare_cues) and intent != "compare":
        result["intent"] = "compare"
        corrections.append("intent_corrected:compare_cue")

    return result, corrections


def apply_measure_text_corrections(question: str, classification: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Correct measure using taxonomy-driven alias detection (no hardcoding).

    Generic approach:
    - Scan the question for any taxonomy alias (including underscore-to-space variants)
      with word-boundary matching.
    - If exactly one canonical measure is referenced, and it differs from the current
      predicted measure, set the measure to that canonical value.
    - If zero or multiple measures are referenced, do nothing (ambiguous or none).
    """
    ql = (question or "").lower()
    result = dict(classification)
    corrections: List[str] = []

    current_measure = str(result.get("measure", "")).lower()

    # Build an alias->canonical map for scanning, including canonical names themselves.
    alias_to_canonical = dict(METRIC_ALIASES)  # aliases are already lowercased by loader
    # Include canonical measure names as self-aliases to catch direct mentions
    for canonical in METRIC_SUBJECT_MAP.keys():
        if canonical not in alias_to_canonical:
            alias_to_canonical[canonical] = canonical

    # Scan for aliases present in the question using word-boundary regex
    referenced: List[str] = []
    for alias, canonical in alias_to_canonical.items():
        # Consider both the alias as-is and underscore-to-space variant for matching natural text
        variants = {alias}
        if "_" in alias:
            variants.add(alias.replace("_", " "))
        for variant in variants:
            if not variant:
                continue
            pattern = rf"\b{re.escape(variant)}\b"
            if re.search(pattern, ql):
                referenced.append(canonical)
                break  # avoid duplicate entries per alias due to multiple variants

    # Deduplicate and decide
    referenced_unique = list(dict.fromkeys(referenced))
    if len(referenced_unique) == 1:
        target = referenced_unique[0]
        if target and target != current_measure:
            result["measure"] = target
            corrections.append(f"measure_corrected:alias_cue:{current_measure}->{target}")

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
