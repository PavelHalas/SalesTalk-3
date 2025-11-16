"""Phase 0: Dimension Extraction Enhancement (DIM_EXT).

# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false

Extracts dimensions (filters/breakdowns) from questions using regex patterns for
common cues like rank limits, regions, segments, channels, and status. All
vocabularies are sourced from the shared classification configuration to avoid
hardcoded taxonomies.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional, List, Tuple, cast, Match, Callable

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


DIM_CONFIG: Dict[str, Any] = get_dimensions_config()
SYNONYMS: Dict[str, List[str]] = cast(Dict[str, List[str]], DIM_CONFIG.get("synonyms", {})) if isinstance(DIM_CONFIG.get("synonyms", {}), dict) else {}

def _upper(val: str) -> str:
    return val.upper()

def _lower(val: str) -> str:
    return val.lower()

def _id(val: str) -> str:
    return val

REGION_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("regions", [])), _upper)
SEGMENT_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("segments", [])), _id)
CHANNEL_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("channels", [])), _lower)
STATUS_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("status", [])), _lower)
TIME_OF_WEEK_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("timeOfWeek", [])), _lower)
PRODUCT_LINE_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("productLines", [])), _id)
RELATED_METRIC_LOOKUP = _build_lookup(cast(List[str], DIM_CONFIG.get("related_metrics", [])), _id)

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

# Synonym vocab from taxonomy (no hardcoded tokens)
RANK_TOP_TRIGGERS = [str(x) for x in SYNONYMS.get("rank_top_triggers", [])]
RANK_BOTTOM_TRIGGERS = [str(x) for x in SYNONYMS.get("rank_bottom_triggers", [])]
REGION_PREPOSITIONS = [str(x) for x in SYNONYMS.get("region_prepositions", [])]
CHANNEL_PREPOSITIONS = [str(x) for x in SYNONYMS.get("channel_prepositions", [])]
CHANNEL_NOUN_TARGETS = [str(x) for x in SYNONYMS.get("channel_noun_targets", [])]
STATUS_NOUNS = [str(x) for x in SYNONYMS.get("status_nouns", [])]
PRODUCT_LINE_PHRASES = [str(x) for x in SYNONYMS.get("product_line_phrases", [])]
CORRELATION_VERBS = [str(x) for x in SYNONYMS.get("correlation_verbs", [])]
CORRELATION_CONNECTORS = [str(x) for x in SYNONYMS.get("correlation_connectors", [])]

RANK_TOP_PATTERN = _choice_pattern(RANK_TOP_TRIGGERS) if RANK_TOP_TRIGGERS else r""
RANK_BOTTOM_PATTERN = _choice_pattern(RANK_BOTTOM_TRIGGERS) if RANK_BOTTOM_TRIGGERS else r""
REGION_PREP_PATTERN = _choice_pattern(REGION_PREPOSITIONS) if REGION_PREPOSITIONS else r""
CHANNEL_PREP_PATTERN = _choice_pattern(CHANNEL_PREPOSITIONS) if CHANNEL_PREPOSITIONS else r""
CHANNEL_NOUNS_PATTERN = _choice_pattern(CHANNEL_NOUN_TARGETS) if CHANNEL_NOUN_TARGETS else r""
STATUS_NOUNS_PATTERN = _choice_pattern(STATUS_NOUNS) if STATUS_NOUNS else r""
PRODUCT_LINE_PHRASES_PATTERN = _choice_pattern(PRODUCT_LINE_PHRASES) if PRODUCT_LINE_PHRASES else r""
CORRELATION_VERBS_PATTERN = _choice_pattern(CORRELATION_VERBS) if CORRELATION_VERBS else r""
CORRELATION_CONNECTORS_PATTERN = _choice_pattern(CORRELATION_CONNECTORS) if CORRELATION_CONNECTORS else r""

MAX_RANK_LIMIT = int(DIM_CONFIG.get("rank", {}).get("max_limit", 1000))

Extractor = Callable[[Match[str]], Dict[str, Any]]
DIMENSION_PATTERNS: List[Tuple[re.Pattern[str], Extractor]] = []

# Rank patterns from taxonomy triggers
if RANK_TOP_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({RANK_TOP_PATTERN})\s+(\d+)\b", re.I),
            lambda m: {"limit": int(m.group(2)), "direction": "top"},
        )
    )
if RANK_BOTTOM_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({RANK_BOTTOM_PATTERN})\s+(\d+)\b", re.I),
            lambda m: {"limit": int(m.group(2)), "direction": "bottom"},
        )
    )

# Region patterns from configured prepositions and values
if REGION_PREP_PATTERN and REGION_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({REGION_PREP_PATTERN})\s+({REGION_PATTERN})\b", re.I),
            lambda m: {"region": REGION_LOOKUP[m.group(2).lower()]},
        )
    )
if REGION_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({REGION_PATTERN})\b", re.I),
            lambda m: {"region": REGION_LOOKUP[m.group(1).lower()]},
        )
    )

# Segment patterns
if SEGMENT_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({SEGMENT_PATTERN})\b", re.I),
            lambda m: {"segment": SEGMENT_LOOKUP[m.group(1).lower()]},
        )
    )

# Channel patterns from configured nouns and prepositions
if CHANNEL_PATTERN and CHANNEL_NOUNS_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({CHANNEL_PATTERN})\s+({CHANNEL_NOUNS_PATTERN})\b", re.I),
            lambda m: {"channel": CHANNEL_LOOKUP[m.group(1).lower()]},
        )
    )
if CHANNEL_PREP_PATTERN and CHANNEL_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({CHANNEL_PREP_PATTERN})\s+({CHANNEL_PATTERN})\b", re.I),
            lambda m: {"channel": CHANNEL_LOOKUP[m.group(2).lower()]},
        )
    )

# Status patterns from configured nouns
if STATUS_PATTERN and STATUS_NOUNS_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({STATUS_PATTERN})\s+({STATUS_NOUNS_PATTERN})\b", re.I),
            lambda m: {"status": STATUS_LOOKUP[m.group(1).lower()]},
        )
    )
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({STATUS_NOUNS_PATTERN})\s+(who\s+are\s+)?({STATUS_PATTERN})\b", re.I),
            lambda m: {"status": STATUS_LOOKUP[m.group(3).lower()]},
        )
    )

# Time-of-week patterns from configured tokens
if TIME_OF_WEEK_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({TIME_OF_WEEK_PATTERN})\b", re.I),
            lambda m: {"timeOfWeek": TIME_OF_WEEK_LOOKUP.get(m.group(1).lower(), m.group(1).lower())},
        )
    )

# Product line patterns from configured phrases and values
if PRODUCT_LINE_PHRASES_PATTERN and PRODUCT_LINE_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({PRODUCT_LINE_PHRASES_PATTERN})\s+(?:of\s+)?({PRODUCT_LINE_PATTERN})\b", re.I),
            lambda m: {"productLine": PRODUCT_LINE_LOOKUP[m.group(2).lower()]},
        )
    )
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({PRODUCT_LINE_PATTERN})\b\s+(?:{PRODUCT_LINE_PHRASES_PATTERN})\b", re.I),
            lambda m: {"productLine": PRODUCT_LINE_LOOKUP[m.group(1).lower()]},
        )
    )

# Related metric correlation phrasing from configured verbs/connectors
if RELATED_METRIC_PATTERN and CORRELATION_VERBS_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({CORRELATION_VERBS_PATTERN})\b.*?\b({RELATED_METRIC_PATTERN})\b", re.I),
            lambda m: {"related_metric": RELATED_METRIC_LOOKUP[m.group(2).lower()]},
        )
    )
if RELATED_METRIC_PATTERN and CORRELATION_CONNECTORS_PATTERN:
    DIMENSION_PATTERNS.append(
        (
            re.compile(rf"\b({RELATED_METRIC_PATTERN})\b\s+(?:{CORRELATION_CONNECTORS_PATTERN})\b", re.I),
            lambda m: {"related_metric": RELATED_METRIC_LOOKUP[m.group(1).lower()]},
        )
    )

# Additional related metric heuristics from taxonomy regex patterns
for entry in DIM_CONFIG.get("related_metric_patterns", []) or []:
    try:
        rx = str(entry.get("regex", ""))
        val = str(entry.get("value", ""))
        if not rx or not val:
            continue
        pattern = re.compile(rx, re.I)
        DIMENSION_PATTERNS.append((pattern, lambda m, v=val: {"related_metric": v}))
    except Exception:
        continue


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

    # Check for bare status words with configured status nouns
    if not dimension.get("status") and STATUS_NOUNS:
        nouns_alt = _choice_pattern(STATUS_NOUNS)
        for status_word in STATUS_LOOKUP.keys():
            if re.search(rf'\b{re.escape(status_word)}\s+({nouns_alt})\b', q_lower):
                canonical = STATUS_LOOKUP[status_word]
                dimension["status"] = canonical
                extractions.append(f"dimension_status_extracted_heuristic:{canonical}")
                break

    # Check for bare channel words
    if not dimension.get("channel") and CHANNEL_NOUN_TARGETS:
        nouns_alt = _choice_pattern(CHANNEL_NOUN_TARGETS)
        for channel_word in CHANNEL_LOOKUP.keys():
            if re.search(rf'\b{re.escape(channel_word)}\s+({nouns_alt})\b', q_lower):
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
