"""Lexicon Loader for Czech normalization

Reads per-category lexicon files (canonical_en -> [cz aliases]) and produces
flattened category -> (cz_phrase -> canonical_en) mapping with diacritic-free,
lowercased aliases to avoid duplication.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .diacritic_utils import strip_diacritics

LEXICON_FILES = {
    "subjects": "subjects_cs.json",
    "metrics": "metrics_cs.json",
    "intents": "intents_cs.json",
    "time_periods": "time_periods_cs.json",
    "time_windows": "time_windows_cs.json",
    "dimensions": "dimensions_cs.json",
    "granularity": "granularity_cs.json",
}


def load_lexicons(lexicon_dir: Path) -> Dict[str, Dict[str, str]]:
    mapping: Dict[str, Dict[str, str]] = {}
    for category, filename in LEXICON_FILES.items():
        file_path = lexicon_dir / filename
        if not file_path.exists():
            continue
        data = json.loads(file_path.read_text(encoding="utf-8"))
        cat_map: Dict[str, str] = {}
        for canonical_en, aliases in data.items():
            for alias in aliases:
                key = strip_diacritics(alias.lower()).strip()
                if not key:
                    continue
                # Later entries can override earlier ones in case of conflict
                cat_map[key] = canonical_en
        if cat_map:
            mapping[category] = cat_map
    return mapping
