"""Shared taxonomy loader for classification components."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

_TAXONOMY_ENV_VAR = "CLASSIFICATION_TAXONOMY_PATH"
_DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent / "taxonomy" / "default"


class ClassificationConfigError(RuntimeError):
    """Raised when the taxonomy configuration is missing or invalid."""


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ClassificationConfigError(f"Taxonomy file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ClassificationConfigError(f"Failed to parse taxonomy file {path}: {exc}") from exc


def _resolve_taxonomy_root() -> Path:
    root = Path(os.getenv(_TAXONOMY_ENV_VAR, str(_DEFAULT_TAXONOMY_PATH))).expanduser()
    if not root.exists():
        raise ClassificationConfigError(f"Taxonomy root does not exist: {root}")
    return root


def _load_intents(root: Path) -> Dict[str, Dict[str, Any]]:
    intents_dir = root / "intents"
    if not intents_dir.exists():
        return {}

    intents: Dict[str, Dict[str, Any]] = {}
    for intent_file in intents_dir.glob("*.json"):
        intent_data = _read_json(intent_file)
        intent_id = intent_data.get("id")
        if not intent_id:
            raise ClassificationConfigError(f"Intent file {intent_file} missing 'id'")
        intent_id = intent_id.lower()
        intents[intent_id] = intent_data
    return intents


def _load_metrics(root: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    metrics_dir = root / "metrics"
    if not metrics_dir.exists():
        raise ClassificationConfigError(f"Taxonomy metrics directory missing: {metrics_dir}")

    metrics: Dict[str, Dict[str, Any]] = {}
    subject_map: Dict[str, str] = {}
    alias_map: Dict[str, str] = {}

    for metric_file in metrics_dir.glob("*.json"):
        metric_data = _read_json(metric_file)
        metric_id = metric_data.get("id")
        subject_name = metric_data.get("subject")
        if not metric_id or not subject_name:
            raise ClassificationConfigError(f"Metric file {metric_file} missing 'id' or 'subject'")
        metric_id = metric_id.lower()
        subject_name = subject_name.lower()
        metric_data.setdefault("aliases", [])
        metrics[metric_id] = metric_data

        subject_map[metric_id] = subject_name
        for alias in metric_data.get("aliases", []):
            raw_alias = alias.strip().lower()
            norm_alias = raw_alias.replace(" ", "_")
            variants = {raw_alias, norm_alias}
            for alias_key in variants:
                existing = alias_map.get(alias_key)
                if existing and existing != metric_id:
                    raise ClassificationConfigError(
                        f"Alias '{alias}' collides between metrics '{existing}' and '{metric_id}'"
                    )
                if alias_key != metric_id:
                    alias_map[alias_key] = metric_id
                    subject_map.setdefault(alias_key, subject_name)

    if not metrics:
        raise ClassificationConfigError("No metrics defined in taxonomy")

    return metrics, {
        "registry": metrics,
        "subject_map": subject_map,
        "aliases": alias_map,
    }


def _load_subjects(
    root: Path,
    metrics_registry: Dict[str, Dict[str, Any]],
    intents_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    subjects_dir = root / "subjects"
    if not subjects_dir.exists():
        raise ClassificationConfigError(f"Taxonomy subjects directory missing: {subjects_dir}")

    subjects: Dict[str, Dict[str, Any]] = {}
    for subject_file in subjects_dir.glob("*.json"):
        subject_data = _read_json(subject_file)
        subject_name = subject_data.get("subject")
        if not subject_name:
            raise ClassificationConfigError(f"Subject file {subject_file} missing 'subject'")
        subject_slug = subject_name.lower()

        metric_ids = subject_data.get("metrics", [])
        if not metric_ids:
            raise ClassificationConfigError(f"Subject {subject_name} missing 'metrics' list")

        resolved_metrics: Dict[str, Dict[str, Any]] = {}
        for metric_id in metric_ids:
            metric_slug = metric_id.lower()
            if metric_slug not in metrics_registry:
                raise ClassificationConfigError(
                    f"Subject {subject_name} references unknown metric '{metric_id}'"
                )
            resolved_metrics[metric_slug] = metrics_registry[metric_slug]

        resolved_intents: List[Dict[str, Any]] = []
        for intent_id in subject_data.get("intents", []):
            intent_slug = intent_id.lower()
            intent_payload = intents_registry.get(intent_slug)
            if intent_payload:
                resolved_intents.append(intent_payload)

        subjects[subject_slug] = {
            "meta": subject_data,
            "metrics": resolved_metrics,
            "intents": resolved_intents,
        }

    if not subjects:
        raise ClassificationConfigError("No subjects defined in taxonomy")

    return subjects


def _load_taxonomy() -> Dict[str, Any]:
    root = _resolve_taxonomy_root()

    shared_dir = root / "shared"
    dimensions = _read_json(shared_dir / "dimensions.json")
    time_config = _read_json(shared_dir / "time.json")

    intents_registry = _load_intents(root)
    metrics_registry, metrics_index = _load_metrics(root)
    subjects = _load_subjects(root, metrics_registry, intents_registry)

    return {
        "dimensions": dimensions,
        "time": time_config,
        "subjects": subjects,
        "metrics": metrics_index,
        "intents": intents_registry,
    }


@lru_cache(maxsize=1)
def get_classification_config() -> Dict[str, Any]:
    """Load the full taxonomy with caching."""
    return _load_taxonomy()


def get_dimensions_config() -> Dict[str, Any]:
    config = get_classification_config().get("dimensions")
    if not config:
        raise ClassificationConfigError("Missing 'dimensions' section in taxonomy")
    return config


def get_metrics_config() -> Dict[str, Any]:
    config = get_classification_config().get("metrics")
    if not config:
        raise ClassificationConfigError("Missing 'metrics' section in taxonomy")
    return config


def get_time_config() -> Dict[str, Any]:
    config = get_classification_config().get("time")
    if not config:
        raise ClassificationConfigError("Missing 'time' section in taxonomy")
    return config
