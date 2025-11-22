from pathlib import Path
import sys

lambda_dir = Path(__file__).parent.parent.parent / 'lambda'
sys.path.insert(0, str(lambda_dir))

from normalization.exemplar_store import retrieve_similar_cz  # type: ignore
from normalization.diacritic_utils import strip_diacritics  # type: ignore


def test_retrieve_similar_basic():
    res = retrieve_similar_cz("proc klesly prijmy")
    assert res, "Expected exemplar matches"
    assert res[0]["en"] == "why is our revenue decreasing?"
    assert res[0]["score"] >= 0.8


def test_retrieve_uses_diacritic_free():
    res = retrieve_similar_cz("proč klesly příjmy")
    assert res, "Expected exemplar match even with diacritics"

