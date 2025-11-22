"""
Language Detection for Czech/English Classification

Fast, heuristic-based language detection optimized for Czech business queries.
Designed to work reliably with diacritic-free text since Czech users often
omit háčky and čárky when typing quickly.

Detection Strategy (cascading):
1. Primary: Stopword matching (diacritic-free Czech stopwords)
2. Secondary: Character pattern hints (if diacritics present, boost confidence)
3. Fallback: Embedding similarity (for ambiguous short queries)

Performance Target: <10ms p95
Accuracy Target: ≥98% on mixed EN/CZ dataset
"""

import logging
import os
import re
from typing import Dict, Set, Tuple, Optional
from dataclasses import dataclass

# Import diacritic utilities (sibling module)
import sys
from pathlib import Path
lambda_dir = Path(__file__).parent.parent
if str(lambda_dir) not in sys.path:
    sys.path.insert(0, str(lambda_dir))

from normalization.diacritic_utils import strip_diacritics, contains_czech_diacritics

logger = logging.getLogger(__name__)


# Czech stopwords (diacritic-free for robustness)
# These are common words that appear frequently in Czech but rarely/never in English
CZECH_STOPWORDS: Set[str] = {
    # Verbs (to be)
    'je', 'jsou', 'byl', 'byla', 'bylo', 'byli', 
    'jsem', 'jsi', 'jsme', 'jste',
    
    # Prepositions
    'v', 'na', 'z', 'do', 'od', 'k', 'po', 'o', 's',
    
    # Conjunctions
    'a', 'ale', 'nebo',
    
    # Demonstratives
    'tento', 'tato', 'toto', 'ten', 'ta', 'to',
    'tyto', 'ty',
    
    # Time adjectives (diacritic-free)
    'minuly', 'minula', 'minule', 'minuli',
    'letosni', 'loni',
    
    # Question words (diacritic-free)
    'jaky', 'jaka', 'jake', 'jaci',
    'ktery', 'ktera', 'ktere', 'kteri',
    'kolik', 'proc', 'jak', 'kde', 'kdy',
    'co', 'kdo',
    
    # Other common words
    'nas', 'nase', 'nasi',
    'se', 'si',
}

# English stopwords that overlap with Czech (exclude these from detection)
ENGLISH_STOPWORDS: Set[str] = {
    'a', 'v', 'to', 'is', 'are', 'was', 'were',
    'on', 'in', 'at', 'by', 'for', 'with',
    'the', 'of', 'and', 'or',
}

# Czech-specific stopwords (high confidence indicators)
CZECH_ONLY_STOPWORDS: Set[str] = CZECH_STOPWORDS - ENGLISH_STOPWORDS

# Czech diacritic characters (for secondary confidence boost)
CZECH_DIACRITIC_PATTERN = re.compile(r'[čďěňřšťžůáéíóúý]', re.IGNORECASE)


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: str  # 'cs' or 'en'
    confidence: float  # 0.0 to 1.0
    method: str  # 'stopword', 'diacritic', 'embedding', 'default'
    details: Dict[str, any]  # Debug info


def detect_language(
    text: str,
    confidence_threshold: float = 0.8,
    enable_embedding_fallback: bool = False
) -> LanguageDetectionResult:
    """
    Detect whether input text is Czech or English.
    
    Uses cascading detection strategy:
    1. Stopword-based detection (primary)
    2. Diacritic pattern hints (secondary boost)
    3. Embedding similarity (fallback for ambiguous cases)
    
    Args:
        text: Input text to classify
        confidence_threshold: Minimum confidence for detection (default 0.8)
        enable_embedding_fallback: Use embedding similarity for low-confidence cases
        
    Returns:
        LanguageDetectionResult with language, confidence, and method
        
    Examples:
        >>> detect_language("Jake jsou nase trzby?")
        LanguageDetectionResult(language='cs', confidence=0.95, method='stopword', ...)
        
        >>> detect_language("Jaké jsou naše tržby?")
        LanguageDetectionResult(language='cs', confidence=1.0, method='stopword+diacritic', ...)
        
        >>> detect_language("What is our revenue?")
        LanguageDetectionResult(language='en', confidence=0.9, method='stopword', ...)
    """
    if not text or not text.strip():
        return LanguageDetectionResult(
            language='en',
            confidence=0.5,
            method='default',
            details={'reason': 'empty_input'}
        )
    
    # Normalize text for stopword matching (lowercase, strip diacritics)
    normalized_text = strip_diacritics(text.lower())
    words = normalized_text.split()
    
    if not words:
        return LanguageDetectionResult(
            language='en',
            confidence=0.5,
            method='default',
            details={'reason': 'no_words'}
        )
    
    # Primary: Stopword-based detection
    czech_stopword_count = sum(1 for word in words if word in CZECH_ONLY_STOPWORDS)
    total_words = len(words)
    czech_stopword_density = czech_stopword_count / total_words if total_words > 0 else 0
    
    # Calculate base confidence from stopword matching
    base_confidence = 0.5
    method = 'stopword'
    
    if czech_stopword_count >= 2:
        # High confidence Czech (multiple Czech stopwords)
        base_confidence = min(0.85 + (czech_stopword_count * 0.05), 1.0)
        language = 'cs'
    elif czech_stopword_density >= 0.3:
        # Medium-high confidence Czech (high stopword density)
        base_confidence = 0.75 + (czech_stopword_density * 0.2)
        language = 'cs'
    elif czech_stopword_count == 1:
        # Low-medium confidence Czech (single stopword)
        base_confidence = 0.65
        language = 'cs'
    else:
        # Default to English
        base_confidence = 0.7
        language = 'en'
    
    # Secondary: Diacritic pattern boost
    has_diacritics = contains_czech_diacritics(text)
    if has_diacritics and language == 'cs':
        # Boost confidence if diacritics present and already detected as Czech
        base_confidence = min(base_confidence + 0.15, 1.0)
        method = 'stopword+diacritic'
    elif has_diacritics and language == 'en':
        # Diacritics present but stopwords say English - likely Czech
        # Override to Czech with medium confidence
        language = 'cs'
        base_confidence = 0.75
        method = 'diacritic_override'
    
    # Fallback: Embedding similarity (if enabled and low confidence)
    if enable_embedding_fallback and base_confidence < confidence_threshold:
        # TODO: Implement embedding-based detection
        # For now, stick with stopword result
        logger.debug(
            f"Low confidence detection ({base_confidence:.2f}), "
            f"but embedding fallback not implemented yet"
        )
    
    details = {
        'czech_stopword_count': czech_stopword_count,
        'czech_stopword_density': round(czech_stopword_density, 3),
        'total_words': total_words,
        'has_diacritics': has_diacritics,
        'normalized_text': normalized_text[:100],  # First 100 chars for debug
    }
    
    return LanguageDetectionResult(
        language=language,
        confidence=round(base_confidence, 3),
        method=method,
        details=details
    )


def is_czech(text: str, confidence_threshold: float = 0.8) -> bool:
    """
    Simple boolean check: is text Czech?
    
    Args:
        text: Input text
        confidence_threshold: Minimum confidence to consider Czech (default 0.8)
        
    Returns:
        True if detected as Czech with sufficient confidence, False otherwise
    """
    result = detect_language(text, confidence_threshold=confidence_threshold)
    return result.language == 'cs' and result.confidence >= confidence_threshold


def get_language_code(text: str) -> str:
    """
    Get ISO 639-1 language code ('cs' or 'en').
    
    Args:
        text: Input text
        
    Returns:
        'cs' for Czech, 'en' for English (default)
    """
    result = detect_language(text)
    return result.language
