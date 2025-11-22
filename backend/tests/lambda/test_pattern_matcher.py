import sys
from pathlib import Path

# Ensure lambda directory (which contains normalization) is on path
ROOT = Path(__file__).resolve().parents[2]
LAMBDA_DIR = ROOT / "lambda"
if str(LAMBDA_DIR) not in sys.path:
    sys.path.append(str(LAMBDA_DIR))

from typing import Any, Dict
from normalization.pattern_matcher import apply_czech_patterns  # type: ignore
from normalization.diacritic_utils import strip_diacritics  # type: ignore


def test_overall_performance_pattern_basic():
    text: str = "jak se nam vede"
    res: Dict[str, Any] = apply_czech_patterns(text)
    assert "overall_performance" in res["matched"]
    assert res["rewrite"] == "what is our overall performance?"


def test_overall_performance_pattern_with_diacritics():
    original: str = "jak se nám vede"
    # Pattern matcher expects diacritic-free pre-normalized input; simulate pipeline
    text: str = strip_diacritics(original.lower())
    res: Dict[str, Any] = apply_czech_patterns(text)
    assert res["rewrite"] == "what is our overall performance?"


def test_downward_trend_reason_variants():
    for variant in [
        "proc jdeme dolu",
        "proč jdeme dolů",
        "proc klesame",
        "proč klesáme"
    ]:
        text: str = strip_diacritics(variant.lower())
        res: Dict[str, Any] = apply_czech_patterns(text)
        assert "downward_trend_reason" in res["matched"], variant
        assert res["rewrite"] == "why is our performance decreasing?"


def test_who_is_churning_variants():
    for variant in [
        "kdo nam odchazi",
        "kdo nám odchází",
        "kdo odchazi",
        "kdo odchází"
    ]:
        text: str = strip_diacritics(variant.lower())
        res: Dict[str, Any] = apply_czech_patterns(text)
        assert "who_is_churning" in res["matched"], variant
        assert res["rewrite"] == "who is churning?"


def test_no_pattern_match():
    text: str = "jak je pocasi"  # Irrelevant phrase
    res: Dict[str, Any] = apply_czech_patterns(text)
    assert res["matched"] == []
    assert res["rewrite"] is None
