"""Fuzzy Czech Pattern Matcher

Lightweight fuzzy matching for colloquial Czech phrases on diacritic-free text.
No external dependencies: uses difflib and token overlap heuristics.

Returns shape compatible with PatternMatcher.apply:
{ "matched": [names], "rewrite": str|None, "tags": [..], "score": float }
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .pattern_matcher import PatternRule

DEFAULT_PATTERN_PATH = Path(__file__).parent / "patterns_cz.json"


def _load_rules() -> List[PatternRule]:
    try:
        data = json.loads(DEFAULT_PATTERN_PATH.read_text(encoding="utf-8"))
        rules: List[PatternRule] = []
        for p in data.get("patterns", []):
            regex_val = p.get("regex", "")
            if not regex_val:
                continue
            rules.append(
                PatternRule(
                    name=p.get("name", "unknown"),
                    regex=regex_val,
                    replacement_en=p.get("replacement_en", ""),
                    tags=list(p.get("tags", [])),
                )
            )
        return rules
    except Exception:
        return []


def _anchors_from_regex(regex: str) -> List[str]:
    # Heuristically extract literal alternates from a simple regex with \b anchors
    # Remove word boundaries and escapes
    s = regex
    s = s.replace("\\b", " ")
    s = s.replace("\\", "")
    # Remove simple optional groups like (me)?
    s = re.sub(r"\([^)]*\)\?", "", s)
    # Split alternations
    parts = [p.strip() for p in s.split("|") if p.strip()]
    # Normalize whitespace
    anchors = [re.sub(r"\s+", " ", p) for p in parts]
    return anchors


def _token_overlap(a: str, b: str) -> float:
    at = a.split()
    bt = b.split()
    if not at:
        return 0.0
    inter = len(set(at) & set(bt))
    return inter / float(len(set(at)))


def _seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def apply_fuzzy_czech_patterns(normalized_text: str, min_ratio: float = 0.85, min_token_overlap: float = 0.8) -> Dict[str, Any]:
    rules = _load_rules()
    best: Tuple[float, Optional[PatternRule], Optional[str]] = (0.0, None, None)
    matched_names: List[str] = []
    tags: List[str] = []

    for rule in rules:
        anchors = _anchors_from_regex(rule.regex_raw)
        for anchor in anchors:
            # lowercased text expected; caller should strip diacritics
            r1 = _seq_ratio(anchor, normalized_text)
            r2 = _token_overlap(anchor, normalized_text)
            score = max(r1, r2)
            if score >= min(min_ratio, 1.0):
                matched_names.append(rule.name)
                tags.extend(rule.tags)
                if score > best[0]:
                    best = (score, rule, anchor)

    rewrite: Optional[str] = best[1].replacement_en if best[1] is not None else None
    return {
        "matched": list(dict.fromkeys(matched_names)),  # unique preserve order
        "rewrite": rewrite,
        "tags": list(dict.fromkeys(tags)),
        "score": best[0],
    }
