"""
Unit tests for Czech diacritic utilities.

Tests the strip_diacritics() and related functions to ensure proper
handling of Czech characters (háčky and čárky) in both diacritic and
diacritic-free forms.
"""

import pytest
import sys
from pathlib import Path

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent.parent / 'lambda'
sys.path.insert(0, str(lambda_dir))

from normalization.diacritic_utils import (
    strip_diacritics,
    contains_czech_diacritics,
    normalize_czech_text,
    CZECH_DIACRITIC_MAP
)


class TestStripDiacritics:
    """Test diacritic stripping functionality."""
    
    def test_hacky_characters(self):
        """Test háčky (caron) character stripping."""
        assert strip_diacritics('č') == 'c'
        assert strip_diacritics('ď') == 'd'
        assert strip_diacritics('ě') == 'e'
        assert strip_diacritics('ň') == 'n'
        assert strip_diacritics('ř') == 'r'
        assert strip_diacritics('š') == 's'
        assert strip_diacritics('ť') == 't'
        assert strip_diacritics('ž') == 'z'
    
    def test_hacky_uppercase(self):
        """Test uppercase háčky characters."""
        assert strip_diacritics('Č') == 'C'
        assert strip_diacritics('Ď') == 'D'
        assert strip_diacritics('Ě') == 'E'
        assert strip_diacritics('Ň') == 'N'
        assert strip_diacritics('Ř') == 'R'
        assert strip_diacritics('Š') == 'S'
        assert strip_diacritics('Ť') == 'T'
        assert strip_diacritics('Ž') == 'Z'
    
    def test_carky_characters(self):
        """Test čárky (acute accent) character stripping."""
        assert strip_diacritics('á') == 'a'
        assert strip_diacritics('é') == 'e'
        assert strip_diacritics('í') == 'i'
        assert strip_diacritics('ó') == 'o'
        assert strip_diacritics('ú') == 'u'
        assert strip_diacritics('ý') == 'y'
    
    def test_carky_uppercase(self):
        """Test uppercase čárky characters."""
        assert strip_diacritics('Á') == 'A'
        assert strip_diacritics('É') == 'E'
        assert strip_diacritics('Í') == 'I'
        assert strip_diacritics('Ó') == 'O'
        assert strip_diacritics('Ú') == 'U'
        assert strip_diacritics('Ý') == 'Y'
    
    def test_special_u_with_ring(self):
        """Test ů (u with ring above) character."""
        assert strip_diacritics('ů') == 'u'
        assert strip_diacritics('Ů') == 'U'
    
    def test_common_czech_words(self):
        """Test common Czech business terms."""
        assert strip_diacritics('tržby') == 'trzby'
        assert strip_diacritics('zákazníci') == 'zakaznici'
        assert strip_diacritics('objednávky') == 'objednavky'
        assert strip_diacritics('marže') == 'marze'
        assert strip_diacritics('průměrná') == 'prumerna'
        assert strip_diacritics('měsíc') == 'mesic'
        assert strip_diacritics('předpověď') == 'predpoved'
        assert strip_diacritics('žebříček') == 'zebricek'
    
    def test_mixed_text(self):
        """Test sentences with mixed diacritic and ASCII characters."""
        assert strip_diacritics('Jaké jsou naše tržby?') == 'Jake jsou nase trzby?'
        assert strip_diacritics('Proč klesla míra odlivu?') == 'Proc klesla mira odlivu?'
        assert strip_diacritics('tento měsíc vs minulý měsíc') == 'tento mesic vs minuly mesic'
    
    def test_already_normalized(self):
        """Test text without diacritics (should return unchanged)."""
        assert strip_diacritics('revenue') == 'revenue'
        assert strip_diacritics('customers') == 'customers'
        assert strip_diacritics('Jake jsou trzby?') == 'Jake jsou trzby?'
    
    def test_empty_and_none(self):
        """Test edge cases: empty string and whitespace."""
        assert strip_diacritics('') == ''
        assert strip_diacritics('   ') == '   '
    
    def test_preserves_non_czech(self):
        """Test that non-Czech characters are preserved."""
        assert strip_diacritics('Hello, world!') == 'Hello, world!'
        assert strip_diacritics('123 ABC') == '123 ABC'
        assert strip_diacritics('Q3 MRR') == 'Q3 MRR'


class TestContainsCzechDiacritics:
    """Test detection of Czech diacritics in text."""
    
    def test_with_hacky(self):
        """Detect háčky characters."""
        assert contains_czech_diacritics('tržby') is True
        assert contains_czech_diacritics('už') is True
        assert contains_czech_diacritics('též') is True
    
    def test_with_carky(self):
        """Detect čárky characters."""
        assert contains_czech_diacritics('zákazníci') is True
        assert contains_czech_diacritics('náš') is True
        assert contains_czech_diacritics('jíst') is True
    
    def test_with_ring(self):
        """Detect ů (ring above)."""
        assert contains_czech_diacritics('může') is True
        assert contains_czech_diacritics('průměr') is True
    
    def test_without_diacritics(self):
        """Text without Czech diacritics."""
        assert contains_czech_diacritics('trzby') is False
        assert contains_czech_diacritics('revenue') is False
        assert contains_czech_diacritics('123') is False
        assert contains_czech_diacritics('Jake jsou nase trzby?') is False
    
    def test_mixed_sentences(self):
        """Sentences with some diacritics."""
        assert contains_czech_diacritics('Jaké jsou tržby?') is True
        assert contains_czech_diacritics('Jake jsou trzby?') is False


class TestNormalizeCzechText:
    """Test full normalization (lowercase + diacritic strip + whitespace)."""
    
    def test_full_normalization(self):
        """Test complete normalization pipeline."""
        assert normalize_czech_text('  Tržby v Q3  ') == 'trzby v q3'
        assert normalize_czech_text('ZÁKAZNÍCI') == 'zakaznici'
        assert normalize_czech_text('Minulý  Měsíc') == 'minuly mesic'
    
    def test_whitespace_collapse(self):
        """Test whitespace normalization."""
        assert normalize_czech_text('třiřřř    rrrřřř    prostor') == 'trirrr rrrrrr prostor'
        assert normalize_czech_text('   leading and trailing   ') == 'leading and trailing'
    
    def test_case_conversion(self):
        """Test lowercase conversion."""
        assert normalize_czech_text('TRŽBY') == 'trzby'
        assert normalize_czech_text('Tržby') == 'trzby'
        assert normalize_czech_text('TrŽbY') == 'trzby'
    
    def test_empty(self):
        """Test empty string handling."""
        assert normalize_czech_text('') == ''
        assert normalize_czech_text('   ') == ''


class TestDiacriticMap:
    """Test completeness of diacritic mapping table."""
    
    def test_all_lowercase_present(self):
        """Ensure all lowercase Czech diacritics are mapped."""
        expected = ['č', 'ď', 'ě', 'ň', 'ř', 'š', 'ť', 'ž', 'á', 'é', 'í', 'ó', 'ú', 'ý', 'ů']
        for char in expected:
            assert char in CZECH_DIACRITIC_MAP, f"Missing lowercase: {char}"
    
    def test_all_uppercase_present(self):
        """Ensure all uppercase Czech diacritics are mapped."""
        expected = ['Č', 'Ď', 'Ě', 'Ň', 'Ř', 'Š', 'Ť', 'Ž', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ý', 'Ů']
        for char in expected:
            assert char in CZECH_DIACRITIC_MAP, f"Missing uppercase: {char}"
    
    def test_mapping_correctness(self):
        """Verify correct ASCII mappings."""
        assert CZECH_DIACRITIC_MAP['č'] == 'c'
        assert CZECH_DIACRITIC_MAP['ř'] == 'r'
        assert CZECH_DIACRITIC_MAP['š'] == 's'
        assert CZECH_DIACRITIC_MAP['ž'] == 'z'
        assert CZECH_DIACRITIC_MAP['á'] == 'a'
        assert CZECH_DIACRITIC_MAP['é'] == 'e'
        assert CZECH_DIACRITIC_MAP['í'] == 'i'
        assert CZECH_DIACRITIC_MAP['ů'] == 'u'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
