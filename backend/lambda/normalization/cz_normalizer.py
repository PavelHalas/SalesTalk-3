"""
Czech Normalizer

Converts Czech business query text to canonical English tokens using
deterministic phrase mapping with longest-match-first strategy.

Designed to handle both diacritic and diacritic-free Czech text robustly.

Flow:
1. Strip diacritics from input
2. Apply longest-match-first phrase replacement
3. Return normalized text with English tokens

Performance Target: <50ms p95
Coverage Target: ≥90% common Czech business phrases
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import sibling modules
import sys
lambda_dir = Path(__file__).parent.parent
if str(lambda_dir) not in sys.path:
    sys.path.insert(0, str(lambda_dir))

from normalization.diacritic_utils import strip_diacritics, normalize_czech_text
from normalization.lexicon_loader import load_lexicons

logger = logging.getLogger(__name__)


# Cache for compiled mapping (loaded once per Lambda container)
_mapping_cache: Optional[Dict[str, Dict[str, str]]] = None
_compiled_patterns: Optional[Dict[str, List[Tuple[re.Pattern[str], str]]]] = None


def _load_mapping() -> Dict[str, Dict[str, str]]:
    """
    Load Czech→English mapping from JSON file.
    
    Returns:
        Nested dict with categories → phrase → canonical token
    """
    global _MAPPING_CACHE
    global _mapping_cache
    if _mapping_cache is not None:
        return _mapping_cache
    
    # Start with lexicon-based mapping if lexicon dir exists
    base_dir = Path(__file__).parent
    lex_dir = base_dir / 'lexicons'
    combined: Dict[str, Dict[str, str]] = {}
    if lex_dir.exists():
        try:
            lex_map = load_lexicons(lex_dir)
            combined.update(lex_map)
            logger.info(f"Loaded Czech lexicons from {lex_dir}")
        except Exception as e:
            logger.warning(f"Failed to load lexicons: {e}")

    # Also load legacy flat mapping if present and merge (lexicons take precedence)
    legacy_path = os.getenv('CZ_NORMALIZATION_MAP_PATH', str(base_dir / 'cz_mapping.json'))
    if Path(legacy_path).exists():
        try:
            legacy = json.loads(Path(legacy_path).read_text(encoding='utf-8'))
            for category, phrases in legacy.items():
                cat_map = combined.setdefault(category, {})
                for cz_phrase, token in phrases.items():
                    key = strip_diacritics(cz_phrase.lower()).strip()
                    if key not in cat_map:
                        cat_map[key] = token
            logger.info(f"Merged legacy mapping from {legacy_path}")
        except Exception as e:
            logger.warning(f"Failed to load legacy mapping: {e}")

    # Deduplicate and cache
    _mapping_cache = combined
    total_phrases = sum(len(v) for v in _mapping_cache.values())
    logger.info(
        f"Czech normalization mapping ready with {total_phrases} deduplicated phrases"
    )
    return _mapping_cache


def _compile_patterns() -> Dict[str, List[Tuple[re.Pattern[str], str]]]:
    """
    Compile regex patterns for phrase matching, sorted by length (longest first).
    
    Returns:
        Dict of category → [(pattern, replacement)] sorted by phrase length descending
    """
    global _compiled_patterns
    if _compiled_patterns is not None:
        return _compiled_patterns
    
    mapping = _load_mapping()
    compiled: Dict[str, List[Tuple[re.Pattern[str], str]]] = {}
    
    for category, phrases in mapping.items():
        # Sort phrases by length (longest first) for greedy matching
        sorted_phrases = sorted(phrases.items(), key=lambda x: len(x[0]), reverse=True)
        
        patterns: List[Tuple[re.Pattern[str], str]] = []
        for czech_phrase, english_token in sorted_phrases:
            # Create word boundary regex pattern (case-insensitive)
            # Escape special regex chars in the phrase
            escaped_phrase = re.escape(czech_phrase)
            pattern: re.Pattern[str] = re.compile(r'\b' + escaped_phrase + r'\b', re.IGNORECASE)
            replacement: str = str(english_token)
            patterns.append((pattern, replacement))
        
        compiled[category] = patterns
    
    _compiled_patterns = compiled
    logger.debug(f"Compiled {sum(len(v) for v in compiled.values())} regex patterns")
    return _compiled_patterns


@dataclass
class NormalizationResult:
    """Result of Czech text normalization."""
    original_text: str
    normalized_text: str
    coverage: float  # Fraction of words successfully normalized (0.0 to 1.0)
    replacements: Dict[str, str]  # Czech phrase → English token
    categories_used: List[str]  # Which mapping categories were used


def normalize_czech_query(text: str) -> NormalizationResult:
    """
    Normalize Czech business query to English canonical tokens.
    
    Uses longest-match-first strategy across all mapping categories:
    - Subjects (tržby → revenue)
    - Metrics (MRR, churn rate, etc.)
    - Intents (co → what, proč → why)
    - Time periods (minulý měsíc → last_month)
    - Time windows (ytd, l3m, etc.)
    - Dimensions (aktivní → active, SMB, EMEA)
    - Granularity (den → day, měsíc → month)
    
    Args:
        text: Input Czech query (with or without diacritics)
        
    Returns:
        NormalizationResult with normalized text and metadata
        
    Examples:
        >>> normalize_czech_query("Jaké jsou naše tržby v Q3?")
        NormalizationResult(
            original_text="Jaké jsou naše tržby v Q3?",
            normalized_text="What are our revenue in Q3?",
            coverage=0.8,
            ...
        )
        
        >>> normalize_czech_query("Jake jsou nase trzby v Q3?")  # diacritic-free
        NormalizationResult(
            original_text="Jake jsou nase trzby v Q3?",
            normalized_text="What are our revenue in Q3?",
            coverage=0.8,
            ...
        )
    """
    if not text or not text.strip():
        return NormalizationResult(
            original_text=text,
            normalized_text=text,
            coverage=0.0,
            replacements={},
            categories_used=[]
        )
    
    # Step 1: Normalize input (lowercase + strip diacritics)
    normalized = normalize_czech_text(text)
    original_words = set(normalized.split())
    
    # Step 2: Load compiled patterns
    patterns = _compile_patterns()
    
    # Step 3: Apply replacements (longest-match-first within each category)
    replacements: Dict[str, str] = {}
    categories_used: List[str] = []
    
    # Process categories in priority order
    category_order = [
        'time_periods',     # Highest priority (most specific)
        'time_windows',
        'metrics',
        'subjects',
        'intents',
        'dimensions',
        'granularity',      # Lowest priority (most generic)
    ]
    
    for category in category_order:
        if category not in patterns:
            continue
        
        category_patterns: List[Tuple[re.Pattern[str], str]] = patterns[category]
        for pattern, replacement in category_patterns:
            match = pattern.search(normalized)
            if match:
                czech_phrase = match.group(0)
                # Replace in the normalized text
                normalized = pattern.sub(replacement, normalized)
                replacements[czech_phrase] = replacement
                if category not in categories_used:
                    categories_used.append(category)
    
    # Step 4: Calculate coverage
    normalized_words = set(normalized.split())
    
    # Words that changed (were normalized)
    changed_words = original_words - normalized_words
    
    # Coverage = fraction of original words that were normalized
    if len(original_words) > 0:
        coverage = len(changed_words) / len(original_words)
    else:
        coverage = 0.0
    
    return NormalizationResult(
        original_text=text,
        normalized_text=normalized,
        coverage=round(coverage, 3),
        replacements=replacements,
        categories_used=categories_used
    )


def quick_normalize(text: str) -> str:
    """
    Quick normalization without detailed metadata.
    
    Args:
        text: Input Czech query
        
    Returns:
        Normalized text with English tokens
    """
    result = normalize_czech_query(text)
    return result.normalized_text


def get_coverage(text: str) -> float:
    """
    Get normalization coverage for input text.
    
    Args:
        text: Input Czech query
        
    Returns:
        Coverage score (0.0 to 1.0)
    """
    result = normalize_czech_query(text)
    return result.coverage
