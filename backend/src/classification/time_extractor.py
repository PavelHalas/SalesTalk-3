"""
Phase 0: Extended Time Token Extraction (TIME_EXT)

Expands time token recognition to include additional canonical tokens
and maps common phrases to structured time objects.
"""

import re
from typing import Dict, Any, Optional, List

# Extended canonical time period tokens
CANONICAL_PERIODS = {
    "today", "yesterday",
    "this_week", "last_week",
    "this_month", "last_month",
    "this_quarter", "last_quarter", "next_quarter",
    "this_year", "last_year", "next_year",
    "Q1", "Q2", "Q3", "Q4",
    # Phase 0 additions
    "next_month",
}

# Window tokens (rolling/cumulative periods)
CANONICAL_WINDOWS = {
    "ytd": "ytd",  # year-to-date
    "qtd": "qtd",  # quarter-to-date
    "mtd": "mtd",  # month-to-date
    "l3m": "l3m",  # last 3 months
    "l6m": "l6m",  # last 6 months
    "l12m": "l12m",  # last 12 months
    # Phase 0 additions
    "l8q": "l8q",  # last 8 quarters
    "l30d": "l30d",  # last 30 days
    "l90d": "l90d",  # last 90 days
}

# Granularity options
CANONICAL_GRANULARITY = {"day", "week", "month", "quarter", "year"}

# Phrase-to-token mappings
TIME_PHRASE_PATTERNS = [
    # Year-to-date variations
    (re.compile(r'\b(year[\s-]?to[\s-]?date|ytd)\b', re.I), {"window": "ytd", "granularity": "month"}),
    (re.compile(r'\b(quarter[\s-]?to[\s-]?date|qtd)\b', re.I), {"window": "qtd", "granularity": "month"}),
    (re.compile(r'\b(month[\s-]?to[\s-]?date|mtd)\b', re.I), {"window": "mtd", "granularity": "day"}),
    
    # Last N months/quarters
    (re.compile(r'\blast\s+3\s+months?\b', re.I), {"window": "l3m", "granularity": "month"}),
    (re.compile(r'\blast\s+6\s+months?\b', re.I), {"window": "l6m", "granularity": "month"}),
    (re.compile(r'\blast\s+12\s+months?\b', re.I), {"window": "l12m", "granularity": "month"}),
    (re.compile(r'\blast\s+8\s+quarters?\b', re.I), {"window": "l8q", "granularity": "quarter"}),
    (re.compile(r'\blast\s+30\s+days?\b', re.I), {"window": "l30d", "granularity": "day"}),
    (re.compile(r'\blast\s+90\s+days?\b', re.I), {"window": "l90d", "granularity": "day"}),
    
    # Quarter references
    (re.compile(r'\bQ1\b', re.I), {"period": "Q1", "granularity": "quarter"}),
    (re.compile(r'\bQ2\b', re.I), {"period": "Q2", "granularity": "quarter"}),
    (re.compile(r'\bQ3\b', re.I), {"period": "Q3", "granularity": "quarter"}),
    (re.compile(r'\bQ4\b', re.I), {"period": "Q4", "granularity": "quarter"}),
    
    # Period references
    (re.compile(r'\bthis\s+quarter\b', re.I), {"period": "this_quarter", "granularity": "quarter"}),
    (re.compile(r'\blast\s+quarter\b', re.I), {"period": "last_quarter", "granularity": "quarter"}),
    (re.compile(r'\bnext\s+quarter\b', re.I), {"period": "next_quarter", "granularity": "quarter"}),
    (re.compile(r'\bthis\s+month\b', re.I), {"period": "this_month", "granularity": "month"}),
    (re.compile(r'\blast\s+month\b', re.I), {"period": "last_month", "granularity": "month"}),
    (re.compile(r'\bnext\s+month\b', re.I), {"period": "next_month", "granularity": "month"}),
    (re.compile(r'\bthis\s+year\b', re.I), {"period": "this_year", "granularity": "year"}),
    (re.compile(r'\blast\s+year\b', re.I), {"period": "last_year", "granularity": "year"}),
    
    # Holiday patterns (Phase 0 addition)
    (re.compile(r'\bholiday[\s_]?(?:season[\s_]?)?(\d{4})\b', re.I), lambda m: {"period": f"holiday_{m.group(1)}", "granularity": "month"}),
    (re.compile(r'\bend[\s_]?of[\s_]?year[\s_]?(\d{4})\b', re.I), lambda m: {"period": f"eoy_{m.group(1)}", "granularity": "quarter"}),
]


def extract_time_tokens(question: str, existing_time: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract and normalize time tokens from a question.
    
    Args:
        question: User question string
        existing_time: Existing time dict from LLM (may be incomplete)
        
    Returns:
        Enhanced time dict with canonical tokens
    """
    # Start with existing time if provided
    time_obj = dict(existing_time) if existing_time else {}
    
    q = question.lower()

    # Detect candidates without early stopping to allow precedence logic
    detected: Dict[str, Any] = {}
    for pattern in TIME_PHRASE_PATTERNS:
        if isinstance(pattern, tuple) and len(pattern) == 2:
            regex, time_dict = pattern
            match = regex.search(q)
            if match:
                curr = time_dict(match) if callable(time_dict) else dict(time_dict)
                # Prefer most specific (windows override periods later)
                # Accumulate latest detection; last match wins for same key
                for k, v in curr.items():
                    detected[k] = v

    # Precedence: window > period when both present or when existing has period but query conveys a window
    window = detected.get("window")
    period = detected.get("period")
    gran = detected.get("granularity")

    # If query indicates a window and existing has only period, switch to window
    if window:
        time_obj["window"] = window
        # Drop period to avoid conflicts
        if "period" in time_obj:
            time_obj.pop("period", None)
        # Ensure granularity present
        if gran:
            time_obj["granularity"] = gran
        elif not time_obj.get("granularity"):
            # Default granularities for windows
            if window in {"l30d", "l90d"}:
                time_obj["granularity"] = "day"
            elif window in {"l8q"}:
                time_obj["granularity"] = "quarter"
            else:
                time_obj["granularity"] = "month"
        return time_obj

    # If no window, consider period detection and fill missing pieces
    if period and not time_obj.get("period"):
        time_obj["period"] = period
    # Override granularity if detected pattern has explicit granularity
    # (patterns like "last quarter" know the correct granularity is "quarter")
    if gran:
        time_obj["granularity"] = gran

    return time_obj


def validate_time_tokens(time_obj: Dict[str, Any]) -> List[str]:
    """
    Validate time tokens and return list of issues.
    
    Args:
        time_obj: Time dictionary
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    if not time_obj:
        return issues
    
    period = time_obj.get("period")
    window = time_obj.get("window")
    granularity = time_obj.get("granularity")
    
    # Check that we have either period or window (not both)
    if period and window:
        issues.append("time_has_both_period_and_window")
    
    # Check canonical values
    if period and period not in CANONICAL_PERIODS and not period.startswith("holiday_") and not period.startswith("eoy_"):
        issues.append(f"non_canonical_period:{period}")
    
    if window and window not in CANONICAL_WINDOWS:
        issues.append(f"non_canonical_window:{window}")
    
    if granularity and granularity not in CANONICAL_GRANULARITY:
        issues.append(f"non_canonical_granularity:{granularity}")
    
    # If we have period/window but no granularity, that's an issue
    if (period or window) and not granularity:
        issues.append("missing_granularity_with_period_or_window")
    
    return issues
