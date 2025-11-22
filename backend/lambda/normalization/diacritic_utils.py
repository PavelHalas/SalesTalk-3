"""
Diacritic Utilities for Czech Language Support

Provides fast, deterministic stripping of Czech diacritics (háčky and čárky)
to enable robust language detection and normalization when users type without
diacritical marks.

Performance: <1ms for typical query strings (<200 chars)
"""

from typing import Dict


# Czech diacritic mappings
# háčky (caron/wedge): č, ď, ě, ň, ř, š, ť, ž
# čárky (acute accent): á, é, í, ó, ú, ý
# ů (ring above) - special u variant
CZECH_DIACRITIC_MAP: Dict[str, str] = {
    # Lowercase háčky
    'č': 'c',
    'ď': 'd',
    'ě': 'e',
    'ň': 'n',
    'ř': 'r',
    'š': 's',
    'ť': 't',
    'ž': 'z',
    
    # Uppercase háčky
    'Č': 'C',
    'Ď': 'D',
    'Ě': 'E',
    'Ň': 'N',
    'Ř': 'R',
    'Š': 'S',
    'Ť': 'T',
    'Ž': 'Z',
    
    # Lowercase čárky
    'á': 'a',
    'é': 'e',
    'í': 'i',
    'ó': 'o',
    'ú': 'u',
    'ý': 'y',
    
    # Uppercase čárky
    'Á': 'A',
    'É': 'E',
    'Í': 'I',
    'Ó': 'O',
    'Ú': 'U',
    'Ý': 'Y',
    
    # Special cases
    'ů': 'u',  # Ring above (used in middle of words)
    'Ů': 'U',
}


def strip_diacritics(text: str) -> str:
    """
    Remove Czech diacritics from text, converting to ASCII equivalents.
    
    This function normalizes Czech text by removing háčky (č→c, š→s, etc.)
    and čárky (á→a, é→e, etc.), enabling matching against diacritic-free
    user input.
    
    Args:
        text: Input text potentially containing Czech diacritics
        
    Returns:
        Text with diacritics replaced by ASCII equivalents
        
    Examples:
        >>> strip_diacritics("tržby")
        'trzby'
        >>> strip_diacritics("zákazníci")
        'zakaznici'
        >>> strip_diacritics("Jaké jsou naše tržby?")
        'Jake jsou nase trzby?'
        >>> strip_diacritics("minulý měsíc")
        'minuly mesic'
    """
    if not text:
        return text
    
    # Fast path: if no diacritics present, return original
    if not any(c in CZECH_DIACRITIC_MAP for c in text):
        return text
    
    # Character-by-character replacement
    result = []
    for char in text:
        result.append(CZECH_DIACRITIC_MAP.get(char, char))
    
    return ''.join(result)


def contains_czech_diacritics(text: str) -> bool:
    """
    Check if text contains any Czech diacritical marks.
    
    Useful for detecting whether user typed with full diacritics
    (potentially native speaker with proper keyboard) vs without
    (common for quick typing or non-Czech keyboards).
    
    Args:
        text: Input text to check
        
    Returns:
        True if any Czech diacritics found, False otherwise
        
    Examples:
        >>> contains_czech_diacritics("tržby")
        True
        >>> contains_czech_diacritics("trzby")
        False
        >>> contains_czech_diacritics("revenue")
        False
    """
    return any(c in CZECH_DIACRITIC_MAP for c in text)


def normalize_czech_text(text: str) -> str:
    """
    Normalize Czech text for comparison/matching.
    
    Applies:
    1. Lowercase conversion
    2. Diacritic stripping
    3. Whitespace normalization
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text suitable for matching
        
    Examples:
        >>> normalize_czech_text("  Tržby v Q3  ")
        'trzby v q3'
        >>> normalize_czech_text("ZÁKAZNÍCI")
        'zakaznici'
    """
    if not text:
        return text
    
    # Lowercase first
    normalized = text.lower()
    
    # Strip diacritics
    normalized = strip_diacritics(normalized)
    
    # Normalize whitespace (collapse multiple spaces, strip edges)
    normalized = ' '.join(normalized.split())
    
    return normalized
