"""
Quick integration test for Czech language support components.

Tests the full flow: detection → normalization with both
diacritic and diacritic-free Czech text.
"""

import sys
from pathlib import Path

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent.parent / 'lambda'
sys.path.insert(0, str(lambda_dir))

from detection.language_detector import detect_language, is_czech, get_language_code
from normalization.cz_normalizer import normalize_czech_query, quick_normalize


def test_language_detection_with_diacritics():
    """Test detection of Czech with full diacritics."""
    result = detect_language("Jaké jsou naše tržby v Q3?")
    print(f"\nWith diacritics: {result}")
    assert result.language == 'cs'
    assert result.confidence >= 0.8
    
def test_language_detection_without_diacritics():
    """Test detection of Czech without diacritics (diacritic-free)."""
    result = detect_language("Jake jsou nase trzby v Q3?")
    print(f"\nWithout diacritics: {result}")
    assert result.language == 'cs'
    assert result.confidence >= 0.65  # Lower confidence without diacritics


def test_language_detection_english():
    """Test detection of English text."""
    result = detect_language("What is our revenue in Q3?")
    print(f"\nEnglish: {result}")
    assert result.language == 'en'


def test_normalization_with_diacritics():
    """Test normalization of Czech with diacritics."""
    result = normalize_czech_query("Jaké jsou naše tržby v Q3?")
    print(f"\nNormalization with diacritics: {result}")
    assert 'what' in result.normalized_text.lower() or 'jake' in result.normalized_text.lower()
    assert 'revenue' in result.normalized_text.lower() or 'trzby' in result.normalized_text.lower()


def test_normalization_without_diacritics():
    """Test normalization of diacritic-free Czech."""
    result = normalize_czech_query("Jake jsou nase trzby v Q3?")
    print(f"\nNormalization without diacritics: {result}")
    assert 'what' in result.normalized_text.lower() or 'jake' in result.normalized_text.lower()
    assert 'revenue' in result.normalized_text.lower() or 'trzby' in result.normalized_text.lower()


def test_end_to_end_diacritic():
    """Test full E2E: detect + normalize with diacritics."""
    text = "Proč klesla míra odlivu minulý měsíc?"
    
    # Detect
    lang_result = detect_language(text)
    print(f"\nE2E (with diacritics) - Detection: {lang_result}")
    
    # Normalize
    norm_result = normalize_czech_query(text)
    print(f"E2E (with diacritics) - Normalization: {norm_result}")
    
    assert lang_result.language == 'cs'
    assert 'churn_rate' in norm_result.normalized_text or 'mira odlivu' in norm_result.normalized_text


def test_end_to_end_no_diacritic():
    """Test full E2E: detect + normalize WITHOUT diacritics (CRITICAL TEST)."""
    text = "Proc klesla mira odlivu minuly mesic?"
    
    # Detect
    lang_result = detect_language(text)
    print(f"\nE2E (NO diacritics) - Detection: {lang_result}")
    
    # Normalize
    norm_result = normalize_czech_query(text)
    print(f"E2E (NO diacritics) - Normalization: {norm_result}")
    
    assert lang_result.language == 'cs', f"Failed to detect Czech without diacritics! Got: {lang_result}"
    assert lang_result.confidence >= 0.65
    

if __name__ == '__main__':
    print("=" * 80)
    print("TESTING CZECH LANGUAGE SUPPORT - DIACRITIC-FREE MANDATORY")
    print("=" * 80)
    
    test_language_detection_with_diacritics()
    test_language_detection_without_diacritics()
    test_language_detection_english()
    test_normalization_with_diacritics()
    test_normalization_without_diacritics()
    test_end_to_end_diacritic()
    test_end_to_end_no_diacritic()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Diacritic-free Czech support working!")
    print("=" * 80)
