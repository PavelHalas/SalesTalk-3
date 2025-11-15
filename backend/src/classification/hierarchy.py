"""Phase 1 hierarchical taxonomy passes.

This module enforces the multi-pass classification plan:
- Pass 1: restrict subject + intent to taxonomy definitions.
- Pass 2: constrain measures to the metric list for the chosen subject.
- Pass 3: sanitize dimension/time tokens to canonical vocab.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, cast

from classification.config_loader import get_classification_config


class PhaseOneClassificationError(RuntimeError):
    """Raised when the hierarchical pipeline cannot produce a valid result."""


@dataclass
class _PipelineState:
    """Cached lookups derived from the taxonomy config."""

    subjects: Dict[str, Dict[str, Any]]
    metrics_registry: Dict[str, Any]
    intents_registry: Dict[str, Dict[str, Any]]
    dimensions: Dict[str, Any]
    time_config: Dict[str, Any]
    subject_alias_map: Dict[str, str]
    dimension_value_maps: Dict[str, Dict[str, str]]
    time_period_map: Dict[str, str]
    time_window_map: Dict[str, str]
    time_granularity_map: Dict[str, str]
    dynamic_period_prefixes: List[str]

    @classmethod
    def from_taxonomy(cls, taxonomy: Dict[str, Any]) -> "_PipelineState":
        subjects = taxonomy.get("subjects", {})
        metrics_bundle = taxonomy.get("metrics", {})
        intents = taxonomy.get("intents", {})
        dimensions = taxonomy.get("dimensions", {})
        time_config = taxonomy.get("time", {})

        subject_alias_map: Dict[str, str] = {}
        for slug, payload in subjects.items():
            subject_alias_map[slug] = slug
            for alias in payload.get("meta", {}).get("aliases", []):
                subject_alias_map[alias.lower()] = slug

        dimension_value_maps: Dict[str, Dict[str, str]] = {
            "region": _build_lookup(dimensions.get("regions", [])),
            "segment": _build_lookup(dimensions.get("segments", [])),
            "channel": _build_lookup(dimensions.get("channels", [])),
            "status": _build_lookup(dimensions.get("status", [])),
        }

        time_period_map = _build_lookup(time_config.get("periods", []))
        time_window_map = _build_lookup(time_config.get("windows", []))
        time_granularity_map = _build_lookup(time_config.get("granularity", []))
        dynamic_prefixes = [p.lower() for p in time_config.get("dynamic_period_prefixes", [])]

        return cls(
            subjects=subjects,
            metrics_registry=metrics_bundle,
            intents_registry=intents,
            dimensions=dimensions,
            time_config=time_config,
            subject_alias_map=subject_alias_map,
            dimension_value_maps=dimension_value_maps,
            time_period_map=time_period_map,
            time_window_map=time_window_map,
            time_granularity_map=time_granularity_map,
            dynamic_period_prefixes=dynamic_prefixes,
        )

    def resolve_subject_slug(self, raw_subject: Optional[str]) -> Optional[str]:
        if not raw_subject:
            return None
        slug = raw_subject.strip().lower()
        return self.subject_alias_map.get(slug)

    def allowed_intents(self, subject_slug: str) -> List[str]:
        payload = self.subjects.get(subject_slug, {})
        intents = payload.get("meta", {}).get("intents", [])
        return [intent.lower() for intent in intents]

    def subject_metrics(self, subject_slug: str) -> Dict[str, Any]:
        payload = self.subjects.get(subject_slug, {})
        return payload.get("metrics", {})

    def resolve_metric_slug(self, raw_metric: Optional[str]) -> Optional[str]:
        if not raw_metric:
            return None
        metric_slug = raw_metric.strip().lower()
        registry = self.metrics_registry.get("registry", {})
        if metric_slug in registry:
            return metric_slug
        alias_lookup = self.metrics_registry.get("aliases", {})
        return alias_lookup.get(metric_slug)

    def metric_subject(self, metric_slug: str) -> Optional[str]:
        return self.metrics_registry.get("subject_map", {}).get(metric_slug)

    def canonical_subject(self, slug: str) -> str:
        return self.subjects[slug]["meta"].get("subject", slug)


def run_hierarchical_pipeline(
    question: str,
    classification: Dict[str, Any],
    taxonomy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the hierarchical taxonomy passes and return a sanitized classification."""
    config = taxonomy or get_classification_config()
    state = _PipelineState.from_taxonomy(config)
    result = deepcopy(classification)

    metadata = result.setdefault("metadata", {})
    phase_meta = metadata.setdefault("phase1", {"status": "pending", "passes": []})
    corrections: List[str] = []

    subject_slug = _subject_intent_pass(state, result, corrections)
    phase_meta["passes"].append({"name": "subject_intent", "subject": subject_slug, "intent": result.get("intent")})

    subject_slug, metric_slug = _measure_pass(state, result, subject_slug, corrections)
    phase_meta["passes"].append({"name": "measure", "subject": subject_slug, "measure": metric_slug})

    _context_pass(state, result, corrections)
    phase_meta["passes"].append({"name": "context", "dimension_keys": sorted(list(result.get("dimension", {}).keys())), "time_keys": sorted(list(result.get("time", {}).keys()))})

    phase_meta["status"] = "ok"
    if corrections:
        metadata.setdefault("corrections_applied", []).extend(corrections)

    return result


def _subject_intent_pass(
    state: _PipelineState,
    payload: Dict[str, Any],
    corrections: List[str],
) -> str:
    subject_slug = state.resolve_subject_slug(payload.get("subject"))
    metric_slug_from_payload = state.resolve_metric_slug(payload.get("measure"))

    if not subject_slug and metric_slug_from_payload:
        inferred_subject = state.metric_subject(metric_slug_from_payload)
        if inferred_subject:
            subject_slug = inferred_subject
            payload["subject"] = inferred_subject
            corrections.append(f"phase1.subject_inferred_from_metric:{metric_slug_from_payload}->{inferred_subject}")

    if not subject_slug:
        raise PhaseOneClassificationError("unknown_subject")

    canonical_subject = state.canonical_subject(subject_slug).lower()
    if payload.get("subject") != canonical_subject:
        corrections.append(f"phase1.subject_alias_normalized:{payload.get('subject')}->{canonical_subject}")
        payload["subject"] = canonical_subject

    allowed_intents = state.allowed_intents(subject_slug)
    current_intent = (payload.get("intent") or "").lower()
    if allowed_intents:
        if current_intent not in allowed_intents:
            fallback = allowed_intents[0]
            corrections.append(f"phase1.intent_restricted:{current_intent or 'none'}->{fallback}")
            payload["intent"] = fallback
        else:
            payload["intent"] = current_intent

    return subject_slug


def _measure_pass(
    state: _PipelineState,
    payload: Dict[str, Any],
    subject_slug: str,
    corrections: List[str],
) -> Tuple[str, str]:
    metric_slug = state.resolve_metric_slug(payload.get("measure"))
    if not metric_slug:
        raise PhaseOneClassificationError("unknown_measure")

    metric_subject = state.metric_subject(metric_slug)
    if metric_subject and metric_subject != subject_slug:
        corrections.append(f"phase1.subject_reassigned_for_metric:{subject_slug}->{metric_subject}")
        subject_slug = metric_subject
        payload["subject"] = metric_subject
        allowed_intents = state.allowed_intents(subject_slug)
        if allowed_intents and payload.get("intent") not in allowed_intents:
            fallback = allowed_intents[0]
            corrections.append(f"phase1.intent_restricted:{payload.get('intent') or 'none'}->{fallback}")
            payload["intent"] = fallback

    available_metrics = state.subject_metrics(subject_slug)
    if metric_slug not in available_metrics:
        raise PhaseOneClassificationError("metric_not_allowed_for_subject")

    if payload.get("measure") != metric_slug:
        corrections.append(f"phase1.measure_alias_normalized:{payload.get('measure')}->{metric_slug}")
    payload["measure"] = metric_slug

    return subject_slug, metric_slug


def _context_pass(
    state: _PipelineState,
    payload: Dict[str, Any],
    corrections: List[str],
) -> None:
    raw_dimension = payload.get("dimension")
    if isinstance(raw_dimension, dict):
        dimension = cast(Dict[str, Any], raw_dimension)
    else:
        dimension = {}
    sanitized_dimension: Dict[str, Any] = {}

    for dim_key, lookup in state.dimension_value_maps.items():
        value = dimension.get(dim_key)
        if not value:
            continue
        canonical = _canonical_from_lookup(lookup, value)
        if canonical:
            sanitized_dimension[dim_key] = canonical
            if canonical != value:
                corrections.append(f"phase1.dimension_value_canonicalized:{dim_key}={value}->{canonical}")
        else:
            corrections.append(f"phase1.dimension_value_dropped:{dim_key}={value}")

    rank_cfg = state.dimensions.get("rank", {})
    max_limit = int(rank_cfg.get("max_limit", 1000))
    limit = dimension.get("limit")
    if limit is not None:
        try:
            limit_value = int(limit)
            if limit_value < 1:
                raise ValueError
        except (TypeError, ValueError):
            corrections.append(f"phase1.rank_limit_dropped:{limit}")
        else:
            if limit_value > max_limit:
                corrections.append(f"phase1.rank_limit_capped:{limit_value}->{max_limit}")
                limit_value = max_limit
            sanitized_dimension["limit"] = limit_value
            direction = (dimension.get("direction") or "").lower()
            if direction in {"top", "bottom"}:
                sanitized_dimension["direction"] = direction
            elif direction:
                corrections.append(f"phase1.rank_direction_dropped:{direction}")

    payload["dimension"] = sanitized_dimension

    raw_time = payload.get("time")
    if isinstance(raw_time, dict):
        time_payload = cast(Dict[str, Any], raw_time)
    else:
        time_payload = {}
    sanitized_time: Dict[str, Any] = {}

    period = time_payload.get("period")
    canonical_period = _canonical_time_token(period, state.time_period_map, state.dynamic_period_prefixes)
    if canonical_period:
        sanitized_time["period"] = canonical_period
        if canonical_period != period:
            corrections.append(f"phase1.time_period_canonicalized:{period}->{canonical_period}")
    elif period:
        corrections.append(f"phase1.time_period_dropped:{period}")

    window = time_payload.get("window")
    canonical_window = _canonical_time_token(window, state.time_window_map, [])
    if canonical_window:
        sanitized_time["window"] = canonical_window
        if canonical_window != window:
            corrections.append(f"phase1.time_window_canonicalized:{window}->{canonical_window}")
    elif window:
        corrections.append(f"phase1.time_window_dropped:{window}")

    granularity = time_payload.get("granularity")
    canonical_granularity = _canonical_time_token(granularity, state.time_granularity_map, [])
    if canonical_granularity:
        sanitized_time["granularity"] = canonical_granularity
        if canonical_granularity != granularity:
            corrections.append(f"phase1.time_granularity_canonicalized:{granularity}->{canonical_granularity}")
    elif granularity:
        corrections.append(f"phase1.time_granularity_dropped:{granularity}")

    payload["time"] = sanitized_time


def _build_lookup(values: List[str]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for value in values:
        if not value:
            continue
        lookup[_normalize_token(value)] = value
    return lookup


def _canonical_from_lookup(lookup: Dict[str, str], raw_value: Any) -> Optional[str]:
    if raw_value is None:
        return None
    canonical = lookup.get(_normalize_token(str(raw_value)))
    return canonical


def _canonical_time_token(
    raw_value: Optional[str],
    lookup: Dict[str, str],
    dynamic_prefixes: List[str],
) -> Optional[str]:
    if not raw_value:
        return None
    normalized = _normalize_token(raw_value)
    canonical = lookup.get(normalized)
    if canonical:
        return canonical
    for prefix in dynamic_prefixes:
        if normalized.startswith(prefix):
            return f"{prefix}{normalized[len(prefix):]}"
    return None


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
