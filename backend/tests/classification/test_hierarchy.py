import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classification.hierarchy import (  # noqa: E402
    PhaseOneClassificationError,
    run_hierarchical_pipeline,
)


def _base_classification(**overrides):
    payload = {
        "intent": "what",
        "subject": "revenue",
        "measure": "revenue",
        "dimension": {},
        "time": {},
        "confidence": {"overall": 0.9},
        "metadata": {},
        "refused": False,
        "refusal_reason": None,
    }
    payload.update(overrides)
    return payload


def test_subject_inferred_from_metric():
    classification = _base_classification(subject="unknown", measure="churn_rate")

    result = run_hierarchical_pipeline("How many churned customers?", classification)

    assert result["subject"] == "customers"
    assert result["measure"] == "churn_rate"
    corrections = result["metadata"].get("corrections_applied", [])
    assert "phase1.subject_inferred_from_metric:churn_rate->customers" in corrections


def test_intent_restricted_to_subject_allow_list():
    classification = _base_classification(intent="forecast", subject="revenue")

    result = run_hierarchical_pipeline("Project revenue", classification)

    assert result["intent"] == "what"
    assert "phase1.intent_restricted:forecast->what" in result["metadata"].get("corrections_applied", [])


def test_measure_alias_normalized_and_subject_reassign():
    classification = _base_classification(subject="revenue", measure="arpu")

    result = run_hierarchical_pipeline("Average revenue per user", classification)

    assert result["subject"] == "customers"
    assert result["measure"] == "arpu"
    corrections = result["metadata"].get("corrections_applied", [])
    assert "phase1.subject_reassigned_for_metric:revenue->customers" in corrections


def test_dimension_and_time_sanitized():
    classification = _base_classification(
        dimension={"region": "Mars", "channel": "Email", "limit": 50000, "direction": "Top"},
        time={"period": "This Month", "window": "YTD", "granularity": "Months"},
    )

    result = run_hierarchical_pipeline("Top email revenue this month", classification)

    assert result["dimension"] == {"channel": "email", "limit": 1000, "direction": "top"}
    assert result["time"] == {"period": "this_month", "window": "ytd", "granularity": "month"}
    corrections = result["metadata"].get("corrections_applied", [])
    assert "phase1.dimension_value_dropped:region=Mars" in corrections
    assert "phase1.dimension_value_canonicalized:channel=Email->email" in corrections
    assert "phase1.rank_limit_capped:50000->1000" in corrections
    assert "phase1.time_period_canonicalized:This Month->this_month" in corrections


def test_unknown_metric_raises():
    classification = _base_classification(measure="mystery_metric")

    with pytest.raises(PhaseOneClassificationError):
        run_hierarchical_pipeline("Unknown metric", classification)


def test_product_line_and_related_metric_dimension_preserved():
    classification = _base_classification(
        dimension={
            "productLine": ["hardware", "Software"],
            "related_metric": "page_load_time",
        }
    )

    result = run_hierarchical_pipeline("Compare product lines", classification)

    assert result["dimension"]["productLine"] == ["Hardware", "Software"]
    assert result["dimension"]["related_metric"] == "page_load_time"
    corrections = result["metadata"].get("corrections_applied", [])
    assert any(c.startswith("phase1.dimension_value_canonicalized:productLine") for c in corrections)


def test_breakdown_by_passthrough_and_time_periods_preserved():
    classification = _base_classification(
        dimension={"breakdown_by": ["productLine", "region", ""]},
        time={"periods": ["Q3", "Q4"], "comparison": "sequential"},
    )

    result = run_hierarchical_pipeline("Compare periods", classification)

    assert result["dimension"]["breakdown_by"] == ["productLine", "region"]
    assert result["time"]["periods"] == ["Q3", "Q4"]
    assert result["time"]["comparison"] == "sequential"


@pytest.mark.parametrize(
    "raw_period,expected",
    [
        ("black friday 2025", "Black Friday 2025"),
        ("eoy_2025", "EOY 2025"),
        ("q1 2026", "Q1 2026"),
    ],
)
def test_dynamic_period_formatting(raw_period, expected):
    classification = _base_classification(time={"period": raw_period})

    result = run_hierarchical_pipeline("Event period question", classification)

    assert result["time"]["period"] == expected


def test_time_of_week_dimension_list_canonicalized():
    classification = _base_classification(dimension={"timeOfWeek": ["Weekend", "weekday"]})

    result = run_hierarchical_pipeline("Weekend vs weekday", classification)

    assert result["dimension"]["timeOfWeek"] == ["weekend", "weekday"]
