from pathlib import Path
import sys

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent.parent / 'lambda'
sys.path.insert(0, str(lambda_dir))

from normalization.fuzzy_matcher import apply_fuzzy_czech_patterns  # type: ignore
from normalization.diacritic_utils import strip_diacritics  # type: ignore


def test_fuzzy_handles_common_typos():
    variants = [
        "proc jdem dolu",  # missing "e" in jdeme
        "procc jdeme dolu",  # extra c
        "kdo nam odchazii",  # extra i
        "jak se nam vde",  # missing letter
        # From expanded anchors
        "jak jsme na tom celkove",
        "proc klesaji trzby",
        "proc je marze nizsi",
        "kdo nejvic odchazi",
        "ktery region je nejlepsi",
        "ktere produkty rostou",
        "ktery produkt pada nejvic",
        "kolik mame zakazniku",
        "jaky je trend",
        "jak jsme proti loni",
        "co nas taha nahoru",
        "co nas taha dolu"
    ]
    for v in variants:
        text = strip_diacritics(v.lower())
        res = apply_fuzzy_czech_patterns(text)
        assert res["matched"], f"No fuzzy match for: {v}" 
        assert res["rewrite"], f"No rewrite for: {v}"


def test_fuzzy_returns_best_score_monotonic():
    t1 = strip_diacritics("proc jdeme dolu".lower())
    t2 = strip_diacritics("proc jdee dolu".lower())  # slightly worse
    r1 = apply_fuzzy_czech_patterns(t1)
    r2 = apply_fuzzy_czech_patterns(t2)
    assert r1["score"] >= r2["score"]
