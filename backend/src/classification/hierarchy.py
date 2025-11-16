"""Phase 1 hierarchical taxonomy passes.

This module enforces the multi-pass classification plan:
- Pass 1: restrict subject + intent to taxonomy definitions.
- Pass 2: constrain measures to the metric list for the chosen subject.
- Pass 3: sanitize dimension/time tokens to canonical vocab.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from classification.config_loader import get_classification_config


class PhaseOneClassificationError(RuntimeError):
    """Raised when the hierarchical pipeline cannot produce a valid result."""


@dataclass(frozen=True)
class _DynamicPeriodRule:
    prefix: str
    style: str = "canonical"


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
    dimension_passthrough_keys: List[str]
    time_period_map: Dict[str, str]
    time_window_map: Dict[str, str]
    time_granularity_map: Dict[str, str]
    dynamic_period_rules: List[_DynamicPeriodRule]
    time_passthrough_keys: List[str]

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

        base_dimension_key_map = {
            "regions": "region",
            "segments": "segment",
            "channels": "channel",
            "status": "status",
        }
        base_dimension_key_map.update(dimensions.get("dimension_keys", {}))

        dimension_value_maps: Dict[str, Dict[str, str]] = {}
        for config_key, values in dimensions.items():
            # Skip special keys and non-list values (synonyms, related_metric_patterns, etc.)
            if config_key in {"rank", "dimension_keys", "passthrough_keys", "synonyms", "related_metric_patterns"}:
                continue
            if not isinstance(values, list):
                continue
            dim_key = str(base_dimension_key_map.get(config_key, config_key)).strip()
            if not dim_key:
                continue
            dimension_value_maps[dim_key] = _build_lookup(values)

        dimension_passthrough_keys: List[str] = [
            str(key)
            for key in dimensions.get("passthrough_keys", [])
            if isinstance(key, str) and key
        ]

        time_period_map = _build_lookup(time_config.get("periods", []))
        time_window_map = _build_lookup(time_config.get("windows", []))
        time_granularity_map = _build_lookup(time_config.get("granularity", []))
        dynamic_rules = _parse_dynamic_period_rules(time_config.get("dynamic_period_prefixes", []))
        time_passthrough_keys: List[str] = [
            str(key)
            for key in time_config.get("passthrough_keys", [])
            if isinstance(key, str) and key
        ]

        return cls(
            subjects=subjects,
            metrics_registry=metrics_bundle,
            intents_registry=intents,
            dimensions=dimensions,
            time_config=time_config,
            subject_alias_map=subject_alias_map,
            dimension_value_maps=dimension_value_maps,
            dimension_passthrough_keys=dimension_passthrough_keys,
            time_period_map=time_period_map,
            time_window_map=time_window_map,
            time_granularity_map=time_granularity_map,
            dynamic_period_rules=dynamic_rules,
            time_passthrough_keys=time_passthrough_keys,
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

    # Default routing: rank/breakdown questions should use dimension subjects when dimension keys are present
    # Map dimension keys to their corresponding dimensional subjects
    dim_to_subject = {
        "region": "regions",
        "segment": "segments",
        "channel": "channels",
        "productLine": "productLines",
    }
    try:
        dimension = payload.get("dimension") if isinstance(payload.get("dimension"), dict) else {}
    except Exception:
        dimension = {}
    intent = (payload.get("intent") or "").lower()
    # Prefer dimensional subjects for rank/breakdown when the matching dimension key exists
    if intent in {"rank", "breakdown"} and isinstance(dimension, dict):
        for dim_key, dim_subject in dim_to_subject.items():
            if dim_key in dimension and subject_slug != dim_subject:
                corrections.append(f"phase1.subject_defaulted_from_dimension:{subject_slug}->{dim_subject}({dim_key})")
                subject_slug = dim_subject
                payload["subject"] = dim_subject
                # Re-apply intent restriction for the new subject
                allowed = state.allowed_intents(subject_slug)
                if allowed and intent not in allowed:
                    payload["intent"] = allowed[0]
                break

    # Time-based defaults: if ranking/breakdown across explicit periods or month/quarter granularity, use timePeriods
    try:
        time_payload = payload.get("time") if isinstance(payload.get("time"), dict) else {}
    except Exception:
        time_payload = {}
    has_multi_periods = isinstance(time_payload.get("periods"), list) and len(time_payload.get("periods") or []) > 1
    gran = (time_payload.get("granularity") or "").lower()
    if intent in {"rank", "breakdown"} and (has_multi_periods or gran in {"month", "quarter"}):
        if subject_slug != "timePeriods":
            corrections.append(f"phase1.subject_defaulted_from_time:{subject_slug}->timePeriods")
            subject_slug = "timePeriods"
            payload["subject"] = "timePeriods"
            allowed = state.allowed_intents(subject_slug)
            if allowed and intent not in allowed:
                payload["intent"] = allowed[0]

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
        canonical = _canonical_dimension_value(lookup, value)
        if canonical:
            sanitized_dimension[dim_key] = canonical
            if canonical != value:
                corrections.append(f"phase1.dimension_value_canonicalized:{dim_key}={value}->{canonical}")
        else:
            corrections.append(f"phase1.dimension_value_dropped:{dim_key}={value}")

    for passthrough_key in state.dimension_passthrough_keys:
        value = dimension.get(passthrough_key)
        if value is None:
            continue
        sanitized_value = _sanitize_passthrough_dimension_list(value)
        if sanitized_value:
            sanitized_dimension[passthrough_key] = sanitized_value
            if sanitized_value != value:
                corrections.append(
                    f"phase1.dimension_passthrough_canonicalized:{passthrough_key}={value}->{sanitized_value}"
                )
        elif value:
            corrections.append(f"phase1.dimension_passthrough_dropped:{passthrough_key}={value}")

    # Special normalization: map common alias to canonical related_metric values
    if "related_metric" in sanitized_dimension:
        rm_val = str(sanitized_dimension.get("related_metric") or "")
        if rm_val == "seasonality":
            sanitized_dimension["related_metric"] = "seasonality_index"
            corrections.append("phase1.dimension_value_canonicalized:related_metric=seasonality->seasonality_index")

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
    canonical_period = _canonical_time_token(period, state.time_period_map, state.dynamic_period_rules)
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
    canonical_granularity = _canonical_time_token(
        granularity,
        state.time_granularity_map,
        [],
        allow_plural_trim=True,
    )
    if canonical_granularity:
        sanitized_time["granularity"] = canonical_granularity
        if canonical_granularity != granularity:
            corrections.append(f"phase1.time_granularity_canonicalized:{granularity}->{canonical_granularity}")
    elif granularity:
        corrections.append(f"phase1.time_granularity_dropped:{granularity}")

    periods_list = time_payload.get("periods")
    canonical_periods, periods_changed = _canonical_period_list(periods_list, state)
    if canonical_periods:
        sanitized_time["periods"] = canonical_periods
        if periods_changed:
            corrections.append(f"phase1.time_periods_canonicalized:{periods_list}->{canonical_periods}")
    elif periods_list:
        corrections.append(f"phase1.time_periods_dropped:{periods_list}")

    for passthrough_key in state.time_passthrough_keys:
        if passthrough_key == "periods":
            continue
        value = time_payload.get(passthrough_key)
        if value is None:
            continue
        if isinstance(value, (str, int, float)):
            sanitized_time[passthrough_key] = value
        else:
            corrections.append(f"phase1.time_passthrough_dropped:{passthrough_key}={value}")

    payload["time"] = sanitized_time


def _build_lookup(values: List[str]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for value in values:
        if not value:
            continue
        lookup[_normalize_token(value)] = value
    return lookup


def _canonical_dimension_value(lookup: Dict[str, str], raw_value: Any) -> Optional[Union[str, List[str]]]:
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        canonical_list: List[str] = []
        changed = False
        for entry in raw_value:
            canonical_entry = lookup.get(_normalize_token(str(entry)))
            if canonical_entry:
                canonical_list.append(canonical_entry)
                if canonical_entry != entry:
                    changed = True
            else:
                changed = True
        if canonical_list:
            return canonical_list if changed or len(canonical_list) != len(raw_value) else raw_value
        return None

    canonical = lookup.get(_normalize_token(str(raw_value)))
    return canonical


def _sanitize_passthrough_dimension_list(value: Any) -> Optional[List[str]]:
    items: List[str] = []
    if isinstance(value, list):
        source = value
    elif isinstance(value, str):
        source = [value]
    else:
        return None

    for entry in source:
        if not isinstance(entry, str):
            continue
        token = entry.strip()
        if token:
            items.append(token)

    return items or None


def _canonical_period_list(
    value: Any,
    state: _PipelineState,
) -> Tuple[Optional[List[str]], bool]:
    if value is None:
        return None, False
    if not isinstance(value, list):
        return None, True
    canonical_values: List[str] = []
    changed = False
    for entry in value:
        canonical_entry = _canonical_time_token(entry, state.time_period_map, state.dynamic_period_rules)
        if canonical_entry:
            canonical_values.append(canonical_entry)
            if canonical_entry != entry:
                changed = True
        else:
            changed = True
    if not canonical_values:
        return None, True
    return canonical_values, changed


def _canonical_time_token(
    raw_value: Optional[str],
    lookup: Dict[str, str],
    dynamic_rules: List[_DynamicPeriodRule],
    allow_plural_trim: bool = False,
) -> Optional[str]:
    if not raw_value:
        return None
    normalized = _normalize_token(raw_value)
    canonical = lookup.get(normalized)
    if canonical:
        return canonical
    if allow_plural_trim and normalized.endswith("s"):
        canonical = lookup.get(normalized[:-1])
        if canonical:
            return canonical
    for rule in dynamic_rules:
        prefix = rule.prefix
        if normalized.startswith(prefix):
            suffix = normalized[len(prefix) :]
            formatted = _format_dynamic_period(rule, suffix)
            if formatted:
                return formatted
    quarter_with_year = _maybe_format_quarter_year(normalized)
    if quarter_with_year:
        return quarter_with_year
    return None


def _parse_dynamic_period_rules(entries: Any) -> List[_DynamicPeriodRule]:
    rules: List[_DynamicPeriodRule] = []
    if not isinstance(entries, list):
        return rules
    for entry in entries:
        if isinstance(entry, str):
            rules.append(_DynamicPeriodRule(prefix=entry.lower(), style="canonical"))
            continue
        if isinstance(entry, dict):
            prefix = entry.get("prefix")
            if not prefix:
                continue
            style = str(entry.get("style", "canonical")).lower()
            rules.append(_DynamicPeriodRule(prefix=str(prefix).lower(), style=style))
    return rules


def _format_dynamic_period(rule: _DynamicPeriodRule, suffix: str) -> Optional[str]:
    if rule.style == "canonical":
        return f"{rule.prefix}{suffix}"

    trimmed_suffix = suffix.lstrip("_")
    if rule.style == "upper":
        label = rule.prefix.rstrip("_").upper()
        suffix_label = _format_dynamic_suffix(trimmed_suffix, mode="upper")
        return f"{label} {suffix_label}".strip()
    if rule.style == "title":
        label = _title_case_prefix(rule.prefix)
        suffix_label = _format_dynamic_suffix(trimmed_suffix, mode="title")
        return f"{label} {suffix_label}".strip()
    return f"{rule.prefix}{suffix}"


def _format_dynamic_suffix(value: str, mode: str) -> str:
    if not value:
        return ""
    tokens = value.split("_")
    formatted_tokens: List[str] = []
    for token in tokens:
        if not token:
            continue
        if token.isdigit():
            formatted_tokens.append(token)
        elif mode == "upper":
            formatted_tokens.append(token.upper())
        elif mode == "title":
            formatted_tokens.append(token.title())
        else:
            formatted_tokens.append(token)
    return " ".join(formatted_tokens)


def _title_case_prefix(prefix: str) -> str:
    tokens = prefix.rstrip("_").split("_")
    return " ".join(token.title() for token in tokens if token)


def _maybe_format_quarter_year(normalized: str) -> Optional[str]:
    if "_" not in normalized:
        return None
    quarter, suffix = normalized.split("_", 1)
    if len(quarter) != 2 or not quarter.startswith("q"):
        return None
    quarter_num = quarter[1]
    if quarter_num not in {"1", "2", "3", "4"}:
        return None
    if not suffix.isdigit() or len(suffix) != 4:
        return None
    return f"Q{quarter_num} {suffix}"


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
