"""Classification Normalizer

Lightweight, always-on normalization that maps aliases/synonyms to canonical
taxonomy tokens without enforcing subject/intent restrictions. This is intended
to be applied to the LLM output prior to querying and optionally in tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from .config_loader import get_classification_config


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _build_lookup(values: List[str]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for v in values:
        if not v:
            continue
        lookup[_normalize_token(v)] = v
    return lookup


def _canonical_time_token(raw: Optional[str], lookup: Dict[str, str]) -> Optional[str]:
    if not raw:
        return None
    key = _normalize_token(str(raw))
    # Direct hit
    if key in lookup:
        return lookup[key]
    # Trim trailing s for plural forms
    if key.endswith("s") and key[:-1] in lookup:
        return lookup[key[:-1]]
    return raw

"""
No-hardcoding policy:
- All measure/subject/time aliases must live in taxonomy JSON under
    backend/src/classification/taxonomy/default/** and be loaded via config.
- This normalizer performs only file-driven canonicalization; no hardcoded
    synonym tables are permitted here.
"""


def normalize_classification(classification: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the classification with canonical subject/measure/time/dimension tokens.

    Does not raise or enforce subject/intent/metric constraints; purely a mapping step.
    """
    cfg = get_classification_config()
    result = dict(classification)

    # Subjects
    subject_alias_map: Dict[str, str] = {}
    for slug, payload in cfg.get("subjects", {}).items():
        subject_alias_map[slug] = slug
        for alias in payload.get("meta", {}).get("aliases", []):
            subject_alias_map[_normalize_token(alias)] = slug
    raw_subject = result.get("subject")
    if isinstance(raw_subject, str):
        sub_key = _normalize_token(raw_subject)
        canonical_subject = subject_alias_map.get(sub_key)
        if canonical_subject and canonical_subject != raw_subject:
            result["subject"] = canonical_subject

    # Measures
    metrics_index = cfg.get("metrics", {})
    metric_aliases = metrics_index.get("aliases", {})
    raw_measure = result.get("measure")
    if isinstance(raw_measure, str):
        m_key = _normalize_token(raw_measure)
        canonical = metric_aliases.get(m_key)
        if canonical and canonical != raw_measure:
            result["measure"] = canonical

    # Time
    time_cfg = cfg.get("time", {})
    periods = _build_lookup(time_cfg.get("periods", []))
    windows = _build_lookup(time_cfg.get("windows", []))
    granularity = _build_lookup(time_cfg.get("granularity", []))
    time_obj = result.get("time") if isinstance(result.get("time"), dict) else {}
    if time_obj:
        p = time_obj.get("period")
        w = time_obj.get("window")
        g = time_obj.get("granularity")
        cp = _canonical_time_token(p, periods)
        cw = _canonical_time_token(w, windows)
        cg = _canonical_time_token(g, granularity)
        if cp:
            time_obj["period"] = cp
        if cw:
            time_obj["window"] = cw
        if cg:
            time_obj["granularity"] = cg
        result["time"] = time_obj

    # Dimensions – canonicalize related_metric simple alias
    dim_obj = result.get("dimension") if isinstance(result.get("dimension"), dict) else {}
    if dim_obj and "related_metric" in dim_obj:
        if str(dim_obj.get("related_metric")) == "seasonality":
            dim_obj["related_metric"] = "seasonality_index"
            result["dimension"] = dim_obj

    return result
