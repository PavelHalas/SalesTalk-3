"""Exemplar Store for Czech queries

Lightweight retrieval over exemplar JSONL without external dependencies.
Each line: {"cz": <diacritic-free Czech>, "en": <canonical English>, "tags": [...]}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .diacritic_utils import strip_diacritics

EXEMPLAR_DIR = Path(__file__).parent / "exemplars"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _token_overlap(a: str, b: str) -> float:
    at = a.split()
    bt = b.split()
    if not at:
        return 0.0
    inter = len(set(at) & set(bt))
    return inter / float(len(set(at)))


def retrieve_similar_cz(query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    q = strip_diacritics(query_text.lower()).strip()
    exemplars = _load_jsonl(EXEMPLAR_DIR / "cs.jsonl")
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for row in exemplars:
        cz = strip_diacritics(str(row.get("cz", "")).lower())
        score = _token_overlap(q, cz)
        if score > 0.0:
            scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    for s, r in scored[:top_k]:
        out.append({
            "score": round(s, 4),
            "cz": r.get("cz"),
            "en": r.get("en"),
            "tags": r.get("tags", [])
        })
    return out
