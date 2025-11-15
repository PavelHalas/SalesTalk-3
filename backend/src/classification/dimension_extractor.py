"""Phase 0: Dimension Extraction Enhancement (DIM_EXT).

Extracts dimensions (filters/breakdowns) from questions using regex patterns for
common cues like rank limits, regions, segments, channels, and status. All
vocabularies are sourced from the shared classification configuration to avoid
hardcoded taxonomies.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional, List, Tuple

from .config_loader import ClassificationConfigError, get_dimensions_config


def _choice_pattern(values: List[str]) -> str:
    """Create a regex alternation pattern for the provided values."""
    if not values:
        raise ClassificationConfigError("Dimension configuration values cannot be empty")
    sorted_vals = sorted({value.lower() for value in values}, key=len, reverse=True)
    return "|".join(re.escape(val) for val in sorted_vals)


def _build_lookup(values: List[str], transform=None) -> Dict[str, str]:
    """Build a lowercase lookup map for canonical values with optional transformations."""
    lookup: Dict[str, str] = {}
    for value in values:
        canonical = transform(value) if transform else value
        lookup[value.lower()] = canonical
        # Allow space vs hyphen variants automatically
        if "-" in value:
            variant = value.replace("-", " ").lower()
            lookup.setdefault(variant, canonical)
        # Allow underscore vs space variants automatically
        if "_" in value:
            variant2 = value.replace("_", " ").lower()
            lookup.setdefault(variant2, canonical)
    return lookup


DIM_CONFIG = get_dimensions_config()

REGION_LOOKUP = _build_lookup(DIM_CONFIG.get("regions", []), lambda val: val.upper())
SEGMENT_LOOKUP = _build_lookup(DIM_CONFIG.get("segments", []))
CHANNEL_LOOKUP = _build_lookup(DIM_CONFIG.get("channels", []), lambda val: val.lower())
STATUS_LOOKUP = _build_lookup(DIM_CONFIG.get("status", []), lambda val: val.lower())
TIME_OF_WEEK_LOOKUP = _build_lookup(DIM_CONFIG.get("timeOfWeek", []), lambda val: val.lower())
PRODUCT_LINE_LOOKUP = _build_lookup(DIM_CONFIG.get("productLines", []), lambda val: val)
RELATED_METRIC_LOOKUP = _build_lookup(DIM_CONFIG.get("related_metrics", []), lambda val: val)

REGION_CANONICAL_VALUES = set(REGION_LOOKUP.values())
SEGMENT_CANONICAL_VALUES = set(SEGMENT_LOOKUP.values())
CHANNEL_CANONICAL_VALUES = set(CHANNEL_LOOKUP.values())
STATUS_CANONICAL_VALUES = set(STATUS_LOOKUP.values())
TIME_OF_WEEK_CANONICAL_VALUES = set(TIME_OF_WEEK_LOOKUP.values())
PRODUCT_LINE_CANONICAL_VALUES = set(PRODUCT_LINE_LOOKUP.values())
RELATED_METRIC_CANONICAL_VALUES = set(RELATED_METRIC_LOOKUP.values())

# Backwards-compatible exports consumed by existing tests
KNOWN_REGIONS = sorted(REGION_CANONICAL_VALUES)
KNOWN_CHANNELS = sorted(CHANNEL_CANONICAL_VALUES)
KNOWN_STATUS = sorted(STATUS_CANONICAL_VALUES)

if not REGION_LOOKUP or not SEGMENT_LOOKUP or not CHANNEL_LOOKUP or not STATUS_LOOKUP:
    raise ClassificationConfigError("Incomplete dimension configuration; ensure regions, segments, channels, and status are defined")

REGION_PATTERN = _choice_pattern(list(REGION_LOOKUP.keys()))
SEGMENT_PATTERN = _choice_pattern(list(SEGMENT_LOOKUP.keys()))
CHANNEL_PATTERN = _choice_pattern(list(CHANNEL_LOOKUP.keys()))
STATUS_PATTERN = _choice_pattern(list(STATUS_LOOKUP.keys()))
TIME_OF_WEEK_PATTERN = _choice_pattern(list(TIME_OF_WEEK_LOOKUP.keys())) if TIME_OF_WEEK_LOOKUP else r""
PRODUCT_LINE_PATTERN = _choice_pattern(list(PRODUCT_LINE_LOOKUP.keys())) if PRODUCT_LINE_LOOKUP else r""
RELATED_METRIC_PATTERN = _choice_pattern(list(RELATED_METRIC_LOOKUP.keys())) if RELATED_METRIC_LOOKUP else r""

MAX_RANK_LIMIT = int(DIM_CONFIG.get("rank", {}).get("max_limit", 1000))

# Dimension extraction patterns
DIMENSION_PATTERNS = [
    # Rank patterns: "top 5", "bottom 10", "top N", "best 3"
    (re.compile(r'\b(top|best|highest)\s+(\d+)\b', re.I), lambda m: {"limit": int(m.group(2)), "direction": "top"}),
    (re.compile(r'\b(bottom|worst|lowest)\s+(\d+)\b', re.I), lambda m: {"limit": int(m.group(2)), "direction": "bottom"}),

    # Region patterns (preposition + region, or standalone region word)
    (re.compile(rf'\b(in|for|from)\s+({REGION_PATTERN})\b', re.I),
     lambda m: {"region": REGION_LOOKUP[m.group(2).lower()]}),
    (re.compile(rf'\b({REGION_PATTERN})\b', re.I),
     lambda m: {"region": REGION_LOOKUP[m.group(1).lower()]}),

    # Segment patterns
    (re.compile(rf'\b({SEGMENT_PATTERN})\b', re.I),
     lambda m: {"segment": SEGMENT_LOOKUP[m.group(1).lower()]}),

    # Channel patterns: adjectives like "online", "email"
    (re.compile(rf'\b({CHANNEL_PATTERN})\s+(sales|orders|customers|revenue|signups?)\b', re.I),
     lambda m: {"channel": CHANNEL_LOOKUP[m.group(1).lower()]}),
    (re.compile(rf'\b(through|via|from)\s+({CHANNEL_PATTERN})\b', re.I),
     lambda m: {"channel": CHANNEL_LOOKUP[m.group(2).lower()]}),

    # Status patterns: "active customers", "inactive users", "churned"
    (re.compile(rf'\b({STATUS_PATTERN})\s+(customers?|users?|accounts?)\b', re.I),
     lambda m: {"status": STATUS_LOOKUP[m.group(1).lower()]}),
    (re.compile(rf'\b(customers?|users?|accounts?)\s+(who\s+are\s+)?({STATUS_PATTERN})\b', re.I),
     lambda m: {"status": STATUS_LOOKUP[m.group(3).lower()]}),

    # Time-of-week patterns (weekday/weekend, allow optional plural "s")
    (
        re.compile(r"\b(weekday|weekend)s?\b", re.I),
        lambda m: {"timeOfWeek": TIME_OF_WEEK_LOOKUP.get(m.group(1).lower(), m.group(1).lower())},
    ),

    # Product line patterns — prefer taxonomy-backed canonicalization
    *([] if not PRODUCT_LINE_PATTERN else [
        (re.compile(rf'\b(product\s+line|product\s+lines?)\s+(?:of\s+)?({PRODUCT_LINE_PATTERN})\b', re.I),
         lambda m: {"productLine": PRODUCT_LINE_LOOKUP[m.group(2).lower()]}),
        (re.compile(rf'\b({PRODUCT_LINE_PATTERN})\b\s+(?:product|product\s+line)', re.I),
         lambda m: {"productLine": PRODUCT_LINE_LOOKUP[m.group(1).lower()]}),
    ]),

    # Related metric correlation phrasing
    *([] if not RELATED_METRIC_PATTERN else [
        (re.compile(rf'\bcorrelat(?:e|ion)\b.*?\b({RELATED_METRIC_PATTERN})\b', re.I),
         lambda m: {"related_metric": RELATED_METRIC_LOOKUP[m.group(1).lower()]}),
        (re.compile(rf'\bimpact(?:s)?\b.*?\b({RELATED_METRIC_PATTERN})\b', re.I),
         lambda m: {"related_metric": RELATED_METRIC_LOOKUP[m.group(1).lower()]}),
        (re.compile(rf'\b({RELATED_METRIC_PATTERN})\b\s+(?:vs|and|with)\b', re.I),
         lambda m: {"related_metric": RELATED_METRIC_LOOKUP[m.group(1).lower()]}),
    ]),
]


def extract_dimensions(question: str, existing_dimension: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
    """
    Extract dimension filters from a question.
    
    Args:
        question: User question string
        existing_dimension: Existing dimension dict from LLM
        
    Returns:
        Tuple of (enhanced dimension dict, list of extractions made)
    """
    # Start with existing dimension if provided
    dimension = dict(existing_dimension) if existing_dimension else {}
    extractions = []
    
    q = question
    
    # Apply each pattern
    for pattern, extractor in DIMENSION_PATTERNS:
        match = pattern.search(q)
        if match:
            extracted = extractor(match)
            for key, value in extracted.items():
                # Only add if not already present
                if key not in dimension or not dimension[key]:
                    dimension[key] = value
                    extractions.append(f"dimension_{key}_extracted:{value}")
    
    # Additional heuristic: if question contains common adjectives without explicit "by/for/in",
    # still extract as dimension
    q_lower = question.lower()

    # Check for bare status words at start or with "how many"
    if not dimension.get("status"):
        for status_word in STATUS_LOOKUP.keys():
            if re.search(rf'\b{re.escape(status_word)}\s+(customers?|users?|accounts?)\b', q_lower):
                canonical = STATUS_LOOKUP[status_word]
                dimension["status"] = canonical
                extractions.append(f"dimension_status_extracted_heuristic:{canonical}")
                break

    # Check for bare channel words
    if not dimension.get("channel"):
        for channel_word in CHANNEL_LOOKUP.keys():
            if re.search(rf'\b{re.escape(channel_word)}\s+(revenue|sales|orders|signups?|customers?)\b', q_lower):
                canonical = CHANNEL_LOOKUP[channel_word]
                dimension["channel"] = canonical
                extractions.append(f"dimension_channel_extracted_heuristic:{canonical}")
                break

    # Heuristic for simple related metric mentions
    if not dimension.get("related_metric") and RELATED_METRIC_LOOKUP:
        for rm_word in RELATED_METRIC_LOOKUP.keys():
            if re.search(rf'\b{re.escape(rm_word)}\b', q_lower):
                canonical = RELATED_METRIC_LOOKUP[rm_word]
                dimension["related_metric"] = canonical
                extractions.append(f"dimension_related_metric_extracted_heuristic:{canonical}")
                break

    # Heuristic for product line single-token mentions
    if not dimension.get("productLine") and PRODUCT_LINE_LOOKUP:
        for pl_word in PRODUCT_LINE_LOOKUP.keys():
            if re.search(rf'\b{re.escape(pl_word)}\b', q_lower):
                canonical = PRODUCT_LINE_LOOKUP[pl_word]
                dimension["productLine"] = canonical
                extractions.append(f"dimension_productLine_extracted_heuristic:{canonical}")
                break
    
    return dimension, extractions


def validate_dimensions(dimension: Dict[str, Any]) -> List[str]:
    """
    Validate dimension values.
    
    Args:
        dimension: Dimension dictionary
        
    Returns:
        List of validation issues
    """
    issues = []
    
    if not dimension:
        return issues
    
    # Validate limit is positive integer
    if "limit" in dimension:
        limit = dimension.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            issues.append(f"invalid_limit:{limit}")
        if limit and MAX_RANK_LIMIT and limit > MAX_RANK_LIMIT:
            issues.append(f"limit_too_large:{limit}")
    
    # Validate direction
    if "direction" in dimension:
        direction = dimension.get("direction")
        if direction not in {"top", "bottom"}:
            issues.append(f"invalid_direction:{direction}")
    
    # Validate limit and direction come together
    if ("limit" in dimension) != ("direction" in dimension):
        issues.append("limit_direction_mismatch")
    
    # Validate known values
    if "region" in dimension:
        region_value = str(dimension.get("region", "")).upper()
        if region_value not in REGION_CANONICAL_VALUES:
            issues.append(f"unknown_region:{region_value}")

    if "segment" in dimension:
        segment_value = str(dimension.get("segment", ""))
        if segment_value not in SEGMENT_CANONICAL_VALUES:
            issues.append(f"unknown_segment:{segment_value}")

    if "channel" in dimension:
        channel_value = str(dimension.get("channel", "")).lower()
        if channel_value not in CHANNEL_CANONICAL_VALUES:
            issues.append(f"unknown_channel:{channel_value}")

    if "status" in dimension:
        status_value = str(dimension.get("status", "")).lower()
        if status_value not in STATUS_CANONICAL_VALUES:
            issues.append(f"unknown_status:{status_value}")

    if "timeOfWeek" in dimension:
        tow_value = str(dimension.get("timeOfWeek", "")).lower()
        if tow_value not in TIME_OF_WEEK_CANONICAL_VALUES:
            issues.append(f"unknown_timeOfWeek:{tow_value}")

    if "productLine" in dimension:
        pl_value = str(dimension.get("productLine", ""))
        if pl_value not in PRODUCT_LINE_CANONICAL_VALUES:
            issues.append(f"unknown_productLine:{pl_value}")

    if "related_metric" in dimension:
        rm_value = str(dimension.get("related_metric", ""))
        if rm_value not in RELATED_METRIC_CANONICAL_VALUES:
            issues.append(f"unknown_related_metric:{rm_value}")
    
    return issues
