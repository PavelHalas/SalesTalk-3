import pytest

from classification.hierarchy import (
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
