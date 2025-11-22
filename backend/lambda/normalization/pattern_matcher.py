"""Czech Pattern Matcher

Applies colloquial Czech phrase patterns AFTER diacritic stripping & normalization
(to diacritic-free lowercase text) to produce canonical English rewrites that
improve downstream AI classification consistency.
"""
import json
import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

PATTERN_FILE_ENV = "CZ_PATTERN_FILE_PATH"
DEFAULT_PATTERN_PATH = Path(__file__).parent / "patterns_cz.json"

class PatternRule:
    def __init__(self, name: str, regex: str, replacement_en: str, tags: List[str]):
        self.name: str = name
        self.regex_raw: str = regex
        self.pattern: re.Pattern[str] = re.compile(regex, re.IGNORECASE)
        self.replacement_en: str = replacement_en
        self.tags: List[str] = tags

    def match(self, text: str) -> bool:
        return bool(self.pattern.search(text))


class PatternMatcher:
    _cache: Optional[List[PatternRule]] = None

    @classmethod
    def _load_patterns(cls) -> List[PatternRule]:
        if cls._cache is not None:
            return cls._cache
        path: Path = DEFAULT_PATTERN_PATH
        override = os.getenv(PATTERN_FILE_ENV)
        if override and Path(override).exists():
            path = Path(override)
        try:
            raw = path.read_text(encoding="utf-8")
            data: Dict[str, Any] = json.loads(raw)
            patterns: List[PatternRule] = []
            for p in data.get("patterns", []):
                regex_val = p.get("regex", "")
                if not regex_val:
                    continue
                patterns.append(PatternRule(
                    name=p.get("name", "unknown"),
                    regex=regex_val,
                    replacement_en=p.get("replacement_en", ""),
                    tags=list(p.get("tags", []))
                ))
            cls._cache = patterns
            return patterns
        except Exception:
            cls._cache = []
            return cls._cache

    @classmethod
    def apply(cls, normalized_text: str) -> Dict[str, Any]:
        """Apply patterns to normalized (diacritic-free) Czech text.

        Returns dict with optional rewrite and matched patterns.
        { "matched": [names], "rewrite": str|None, "tags": [..] }
        """
        patterns = cls._load_patterns()
        matched: List[str] = []
        tags: List[str] = []
        rewrite: Optional[str] = None
        for rule in patterns:
            if rule.match(normalized_text):
                matched.append(rule.name)
                if rule.tags:
                    tags.extend(rule.tags)
                if rewrite is None and rule.replacement_en:
                    rewrite = rule.replacement_en
        result: Dict[str, Any] = {
            "matched": matched,
            "rewrite": rewrite,
            "tags": tags
        }
        return result


def apply_czech_patterns(normalized_text: str) -> Dict[str, Any]:
    return PatternMatcher.apply(normalized_text)
