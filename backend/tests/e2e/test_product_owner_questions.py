import csv
import json
import os
import time
from pathlib import Path
from typing import Dict, Any

import pytest

# Add lambda directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classify import lambda_handler as classify_handler
from classification.config_loader import get_metrics_config, get_time_config

DATA_FILE = Path(__file__).parent.parent / "data" / "product_owner_questions.csv"
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Default to real AI via Ollama unless explicitly overridden in environment
os.environ.setdefault("AI_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "dolphin-mistral:latest")  # Quick test: 100% subject/intent, 80% measure, 2.6s/q
os.environ.setdefault("USE_HIER_PASSES", "true")
VERBOSE_E2E = os.environ.get("VERBOSE_E2E", "false").lower() in ("true", "1", "yes")
SUPPRESS_INFO_LOGS = os.environ.get("SUPPRESS_INFO_LOGS", "true").lower() in ("true", "1", "yes")

if SUPPRESS_INFO_LOGS:
    # Suppress noisy INFO logs from classification pipeline during test streaming.
    import logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    ai_logger = logging.getLogger("ai_adapter")
    ai_logger.setLevel(logging.WARNING)
    # Ensure existing handlers respect the elevated level.
    for h in root_logger.handlers:
        h.setLevel(logging.WARNING)
    for h in ai_logger.handlers:
        h.setLevel(logging.WARNING)

# Strict / waterproof testing configuration (env-overridable)
STRICT_E2E = os.environ.get("STRICT_E2E", "true").lower() in ("true", "1", "yes")
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.5"))
MIN_INTENT_MATCH_RATE = float(os.environ.get("MIN_INTENT_MATCH_RATE", "0.9"))
MIN_SUBJECT_MATCH_RATE = float(os.environ.get("MIN_SUBJECT_MATCH_RATE", "0.9"))
MIN_MEASURE_MATCH_RATE = float(os.environ.get("MIN_MEASURE_MATCH_RATE", "0.85"))
MIN_DIMENSION_MATCH_RATE = float(os.environ.get("MIN_DIMENSION_MATCH_RATE", "0.6"))
MIN_TIME_MATCH_RATE = float(os.environ.get("MIN_TIME_MATCH_RATE", "0.6"))

# Sample tenant for all questions (can parameterize later)
TEST_TENANT = "acme-corp-001"

REQUIRED_FIELDS = ["intent", "subject", "measure"]


def load_rows():
    with DATA_FILE.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def create_event(question: str, tenant_id: str) -> Dict[str, Any]:
    return {
        "body": json.dumps({"question": question}),
        "requestContext": {
            "requestId": f"po-questions-{int(time.time()*1000)}",
            "authorizer": {"claims": {"custom:tenant_id": tenant_id}}
        }
    }


def normalize_expected(row: Dict[str, str]) -> Dict[str, Any]:
    dim_raw = row.get("dimension", "{}") or "{}"
    time_raw = row.get("time", "{}") or "{}"
    try:
        dimension = json.loads(dim_raw)
    except Exception:
        dimension = {}
    try:
        time_obj = json.loads(time_raw)
    except Exception:
        time_obj = {}
    # Canonicalize measure aliases in expected (taxonomy-only; no hardcoded synonyms)
    metrics = get_metrics_config()
    aliases = metrics.get("aliases", {})
    def canon_measure(val: str) -> str:
        key = val.strip().lower()
        return aliases.get(key) or val.strip()

    # Canonicalize time tokens (q3 -> Q3, etc.)
    time_cfg = get_time_config()
    def _norm_token(v: str) -> str:
        return v.strip().lower().replace(" ", "_")
    def _build_lookup(values):
        return { _norm_token(x): x for x in values }
    periods = _build_lookup(time_cfg.get("periods", []))
    windows = _build_lookup(time_cfg.get("windows", []))
    gran = _build_lookup(time_cfg.get("granularity", []))
    def canon_time(obj: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj, dict):
            return {}
        out = dict(obj)
        p = out.get("period")
        w = out.get("window")
        g = out.get("granularity")
        if isinstance(p, str):
            out["period"] = periods.get(_norm_token(p), p)
        if isinstance(w, str):
            out["window"] = windows.get(_norm_token(w), w)
        if isinstance(g, str):
            out["granularity"] = gran.get(_norm_token(g), g)
        return out

    return {
        "intent": row["intent"].strip(),
        "subject": row["subject"].strip(),
        "measure": canon_measure(row["measure"].strip()),
        "dimension": dimension,
        "time": canon_time(time_obj),
    }


def _value_matches(expected_v, actual_v) -> bool:
    # Exact match for scalars
    if isinstance(expected_v, (str, int, float, bool)) or expected_v is None:
        return expected_v == actual_v
    # For lists: expected list must be subset (order-agnostic)
    if isinstance(expected_v, list):
        if not isinstance(actual_v, list):
            return False
        return all(item in actual_v for item in expected_v)
    # For dicts: recursive subset
    if isinstance(expected_v, dict):
        if not isinstance(actual_v, dict):
            return False
        return all(k in actual_v and _value_matches(v, actual_v[k]) for k, v in expected_v.items())
    return False


def assert_classification(result: Dict[str, Any], expected: Dict[str, Any]):
    # Structure checks
    for field in REQUIRED_FIELDS:
        assert field in result, f"Missing classification field: {field}"
    # Intent/subject/measure exact match (PO dataset is deterministic)
    assert result["intent"] == expected["intent"], f"Intent mismatch: expected {expected['intent']} got {result['intent']}"
    assert result["subject"] == expected["subject"], f"Subject mismatch: expected {expected['subject']} got {result['subject']}"
    assert result["measure"] == expected["measure"], f"Measure mismatch: expected {expected['measure']} got {result['measure']}"
    # Optional dimension/time: expected must be a subset of actual (key and value)
    exp_dim = expected.get("dimension", {}) or {}
    act_dim = result.get("dimension", {}) or {}
    assert _value_matches(exp_dim, act_dim), f"Dimension mismatch: expected subset {exp_dim}, got {act_dim}"
    exp_time = expected.get("time", {}) or {}
    act_time = result.get("time", {}) or {}
    assert _value_matches(exp_time, act_time), f"Time mismatch: expected subset {exp_time}, got {act_time}"


def assert_minimal_structure(result: Dict[str, Any]):
    # Ensure fundamental structure exists for real-AI runs
    assert isinstance(result, dict), "classification must be a dict"
    for field in REQUIRED_FIELDS:
        assert field in result, f"Missing classification field: {field}"
    # Optional sanity on confidence and refusal flags
    conf = result.get("confidence", {}) or {}
    if isinstance(conf, dict) and "overall" in conf:
        overall = conf.get("overall")
        if isinstance(overall, (int, float)):
            assert 0.0 <= overall <= 1.0, "confidence.overall must be in [0,1]"
    if "refused" in result:
        assert isinstance(result["refused"], bool), "refused must be a boolean"
    # Confidence gating
    overall = result.get("confidence", {}).get("overall")
    if overall is not None and isinstance(overall, (int, float)):
        assert 0.0 <= overall <= 1.0, "confidence.overall must be in [0,1]"
        assert overall >= MIN_CONFIDENCE, f"confidence.overall {overall} below minimum {MIN_CONFIDENCE}"


@pytest.mark.e2e
class TestProductOwnerQuestionSuite:
    """E2E classification validation for Product Owner curated question set.

    For each question in CSV:
    - Invoke classify lambda using real AI provider via env (Ollama/Bedrock)
    - Validate structure and record comparisons to expected dimension/time
    - Log full response JSON to logs/product_owner_run_<timestamp>.json
    """

    @pytest.fixture(scope="class", autouse=True)
    def ensure_provider(self):
        """Optionally skip if Ollama provider is selected but not reachable."""
        provider = os.environ.get("AI_PROVIDER", "ollama").lower()
        if provider == "ollama":
            try:
                import requests
                base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
                resp = requests.get(f"{base}/api/tags", timeout=1.5)
                if not resp.ok:
                    pytest.skip("Ollama not reachable (non-200). Start it or set AI_PROVIDER=bedrock")
            except Exception:
                pytest.skip("Ollama not reachable. Start it or set AI_PROVIDER=bedrock")

    @pytest.fixture(scope="class")
    def log_file(self):
        ts = int(time.time())
        path = LOG_DIR / f"product_owner_run_{ts}.json"
        # initialize as JSONL file
        return path

    @pytest.fixture(scope="class")
    def rows(self):
        return list(load_rows())

    @pytest.fixture(scope="class")
    def aggregator(self):
        return {
            "rows": [],
            "counts": {
                "intent": 0,
                "subject": 0,
                "measure": 0,
                "dimension": 0,
                "time": 0,
                "total": 0,
                "dimension_expected_non_empty": 0,
                "time_expected_non_empty": 0,
            }
        }

    @pytest.mark.parametrize("row_index", list(range(0, 100)))
    def test_question_row(self, row_index, rows, log_file, aggregator):
        assert row_index < len(rows), f"Row index {row_index} beyond CSV size"
        row = rows[row_index]
        expected = normalize_expected(row)
        question = row["question"].strip()

        event = create_event(question, TEST_TENANT)
        response = classify_handler(event, None)
        assert response["statusCode"] == 200, f"Non-200 for question '{question}'"
        body = json.loads(response["body"])
        classification = body["classification"]
        
        # Evaluate comparisons for report
        intent_ok = (classification.get("intent") == expected["intent"])
        subject_ok = (classification.get("subject") == expected["subject"])
        measure_ok = (classification.get("measure") == expected["measure"])
        # Canonicalize dimension synonyms for comparison
        def canon_dim(d: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(d, dict):
                return {}
            out = dict(d)
            if out.get("related_metric") == "seasonality":
                out["related_metric"] = "seasonality_index"
            return out
        exp_dim = canon_dim(expected.get("dimension", {}) or {})
        act_dim = canon_dim(classification.get("dimension", {}) or {})
        dim_ok = _value_matches(exp_dim, act_dim)
        # Time: treat 'current' in expected as wildcard period
        exp_time = expected.get("time", {}) or {}
        act_time = classification.get("time", {}) or {}
        if isinstance(exp_time, dict) and exp_time.get("period") == "current" and isinstance(act_time, dict) and act_time.get("period"):
            time_ok = True
        else:
            time_ok = _value_matches(exp_time, act_time)

        # Aggregation bookkeeping BEFORE assertions to capture all rows
        counts = aggregator["counts"]
        counts["total"] += 1
        if intent_ok: counts["intent"] += 1
        if subject_ok: counts["subject"] += 1
        if measure_ok: counts["measure"] += 1
        if expected.get("dimension"):
            counts["dimension_expected_non_empty"] += 1
            if dim_ok: counts["dimension"] += 1
        if expected.get("time"):
            counts["time_expected_non_empty"] += 1
            if time_ok: counts["time"] += 1
        
        # Collect mismatch details for reporting
        mismatch_detail = {
            "question": question,
            "expected_intent": expected["intent"],
            "actual_intent": classification.get("intent"),
            "intent_ok": intent_ok,
            "expected_subject": expected["subject"],
            "actual_subject": classification.get("subject"),
            "subject_ok": subject_ok,
            "expected_measure": expected["measure"],
            "actual_measure": classification.get("measure"),
            "measure_ok": measure_ok,
            "expected_dimension": expected.get("dimension", {}),
            "actual_dimension": classification.get("dimension", {}),
            "dimension_ok": dim_ok,
            "expected_time": expected.get("time", {}),
            "actual_time": classification.get("time", {}),
            "time_ok": time_ok,
        }
        aggregator["rows"].append(mismatch_detail)

        # Streaming verbose output (controlled by VERBOSE_E2E env)
        if VERBOSE_E2E:
            def _icon(ok: bool) -> str:
                return "✓" if ok else "✗"
            refused = classification.get("refused", False)
            intent_val = classification.get("intent")
            subject_val = classification.get("subject")
            measure_val = classification.get("measure")
            # Compact dimension/time indicators
            dim_indicator = _icon(dim_ok)
            time_indicator = _icon(time_ok)
            # Time breakdown
            t = classification.get("time", {}) or {}
            period = t.get("period")
            window = t.get("window")
            granularity = t.get("granularity")
            # Dimension / filters breakdown
            d = classification.get("dimension", {}) or {}
            dim_keys = list(d.keys())
            # Metadata & confidence
            meta = classification.get("metadata", {}) or {}
            # Collapse duplicate corrections while preserving order
            raw_corrections = meta.get("corrections_applied", [])
            seen = set()
            corrections = []
            for c in raw_corrections:
                if c not in seen:
                    corrections.append(c)
                    seen.add(c)
            phase1_status = meta.get("phase1", {}).get("status")
            conf_overall = classification.get("confidence", {}).get("overall")
            lines = [f"[{row_index:03d}] Q: {question}"]
            lines.append(f"    intent   exp={expected['intent']} act={intent_val} {_icon(intent_ok)}")
            lines.append(f"    subject  exp={expected['subject']} act={subject_val} {_icon(subject_ok)}")
            lines.append(f"    measure  exp={expected['measure']} act={measure_val} {_icon(measure_ok)}")
            if d or expected.get("dimension"):
                lines.append(f"    dimension {dim_indicator} keys={dim_keys}")
            if t or expected.get("time"):
                lines.append(f"    time {time_indicator} period={period} window={window} gran={granularity}")
            lines.append(f"    confidence={conf_overall} refused={refused} corrections={corrections} phase1={phase1_status}")
            print("\n".join(lines), flush=True)

        # Enforce structure
        assert_minimal_structure(classification)

        # Strict assertions (waterproof) for core fields
        if STRICT_E2E:
            assert intent_ok, f"Intent mismatch: expected {expected['intent']} got {classification.get('intent')}"
            assert subject_ok, f"Subject mismatch: expected {expected['subject']} got {classification.get('subject')}"
            assert measure_ok, f"Measure mismatch: expected {expected['measure']} got {classification.get('measure')}"
            # Only enforce dimension/time if expectations are non-empty
            if expected.get("dimension"):
                assert dim_ok, f"Dimension mismatch: expected subset {expected.get('dimension')} got {classification.get('dimension')}"
            if expected.get("time"):
                assert time_ok, f"Time mismatch: expected subset {expected.get('time')} got {classification.get('time')}"

        # Append log entry (JSONL)
        entry = {
            "question": question,
            "expected": expected,
            "actual": classification,
            "tenantId": body.get("tenantId"),
            "requestId": body.get("requestId"),
            "checks": {
                "intent_ok": intent_ok,
                "subject_ok": subject_ok,
                "measure_ok": measure_ok,
                "dimension_ok": dim_ok,
                "time_ok": time_ok,
            },
            "time_parts": {
                "period": classification.get("time", {}).get("period"),
                "window": classification.get("time", {}).get("window"),
                "granularity": classification.get("time", {}).get("granularity"),
            },
            "dimension_keys": list((classification.get("dimension") or {}).keys()),
            "refused": classification.get("refused", False),
            "corrections": classification.get("metadata", {}).get("corrections_applied", []),
            "phase1_status": classification.get("metadata", {}).get("phase1", {}).get("status"),
            "confidence_overall": classification.get("confidence", {}).get("overall"),
        }
        with log_file.open("a") as lf:
            lf.write(json.dumps(entry) + "\n")

        # Also append to CSV summary (create header if new)
        csv_path = Path(str(log_file).replace(".json", ".csv"))
        new_file = not csv_path.exists()
        with csv_path.open("a", newline="") as cf:
            writer = csv.writer(cf)
            if new_file:
                writer.writerow([
                    "question",
                    "intent_expected","intent_actual","intent_ok",
                    "subject_expected","subject_actual","subject_ok",
                    "measure_expected","measure_actual","measure_ok",
                    "dimension_expected","dimension_actual","dimension_ok",
                    "time_expected","time_actual","time_ok",
                    "time_period","time_window","time_granularity",
                    "dimension_keys","refused","confidence_overall","corrections","phase1_status",
                    "statusCode",
                ])
            writer.writerow([
                question,
                expected["intent"], classification.get("intent"), intent_ok,
                expected["subject"], classification.get("subject"), subject_ok,
                expected["measure"], classification.get("measure"), measure_ok,
                json.dumps(expected.get("dimension", {})), json.dumps(classification.get("dimension", {})), dim_ok,
                json.dumps(expected.get("time", {})), json.dumps(classification.get("time", {})), time_ok,
                classification.get("time", {}).get("period"),
                classification.get("time", {}).get("window"),
                classification.get("time", {}).get("granularity"),
                ";".join(list((classification.get("dimension") or {}).keys())),
                classification.get("refused", False),
                classification.get("confidence", {}).get("overall"),
                ";".join(classification.get("metadata", {}).get("corrections_applied", [])),
                classification.get("metadata", {}).get("phase1", {}).get("status"),
                response.get("statusCode"),
            ])

    def test_summary_report(self, aggregator):
        counts = aggregator["counts"]
        total = counts["total"]
        assert total == 100, f"Expected 100 test rows processed, got {total}"
        
        # Compute rates
        def rate(passed, denom):
            return (passed / denom) if denom else 1.0
        intent_rate = rate(counts["intent"], total)
        subject_rate = rate(counts["subject"], total)
        measure_rate = rate(counts["measure"], total)
        dimension_rate = rate(counts["dimension"], counts["dimension_expected_non_empty"])
        time_rate = rate(counts["time"], counts["time_expected_non_empty"])

        # Build confusion-style mismatch frequency analysis (top failures)
        from collections import Counter
        intent_mismatches = Counter()
        subject_mismatches = Counter()
        measure_mismatches = Counter()
        
        for row_detail in aggregator["rows"]:
            if not row_detail["intent_ok"]:
                key = f"{row_detail['expected_intent']} -> {row_detail['actual_intent']}"
                intent_mismatches[key] += 1
            if not row_detail["subject_ok"]:
                key = f"{row_detail['expected_subject']} -> {row_detail['actual_subject']}"
                subject_mismatches[key] += 1
            if not row_detail["measure_ok"]:
                key = f"{row_detail['expected_measure']} -> {row_detail['actual_measure']}"
                measure_mismatches[key] += 1

        summary = {
            "total": total,
            "rates": {
                "intent": intent_rate,
                "subject": subject_rate,
                "measure": measure_rate,
                "dimension": dimension_rate,
                "time": time_rate,
            },
            "counts": {
                "intent_correct": counts["intent"],
                "subject_correct": counts["subject"],
                "measure_correct": counts["measure"],
                "dimension_correct": counts["dimension"],
                "time_correct": counts["time"],
            },
            "top_intent_mismatches": intent_mismatches.most_common(10),
            "top_subject_mismatches": subject_mismatches.most_common(10),
            "top_measure_mismatches": measure_mismatches.most_common(10),
            "thresholds": {
                "intent": MIN_INTENT_MATCH_RATE,
                "subject": MIN_SUBJECT_MATCH_RATE,
                "measure": MIN_MEASURE_MATCH_RATE,
                "dimension": MIN_DIMENSION_MATCH_RATE,
                "time": MIN_TIME_MATCH_RATE,
            },
            "strict": STRICT_E2E,
            "distributions": {
                "time_periods": {},
                "time_windows": {},
                "time_granularity": {},
                "dimension_keys": {},
                "refusals": 0,
            }
        }

        # Build distributions
        from collections import Counter
        period_counter = Counter()
        window_counter = Counter()
        gran_counter = Counter()
        dim_key_counter = Counter()
        refusals = 0
        for row_detail in aggregator["rows"]:
            t_act = row_detail.get("actual_time", {}) or {}
            if isinstance(t_act, dict):
                p = t_act.get("period"); w = t_act.get("window"); g = t_act.get("granularity")
                if p: period_counter[p] += 1
                if w: window_counter[w] += 1
                if g: gran_counter[g] += 1
            d_act = row_detail.get("actual_dimension", {}) or {}
            if isinstance(d_act, dict):
                for k in d_act.keys():
                    dim_key_counter[k] += 1
            if row_detail.get("actual_intent") and row_detail.get("actual_measure") and row_detail.get("actual_subject") and row_detail.get("time_ok") and row_detail.get("dimension_ok") and row_detail.get("question"):
                pass  # placeholder if advanced refusal criteria added later
            if row_detail.get("actual_dimension", {}).get("refused") or row_detail.get("actual_time", {}).get("refused") or row_detail.get("actual_measure") is None:
                pass
        for row_detail in aggregator["rows"]:
            if row_detail.get("actual_intent") == "refused" or row_detail.get("refused"):
                refusals += 1
        summary["distributions"]["time_periods"] = period_counter.most_common()
        summary["distributions"]["time_windows"] = window_counter.most_common()
        summary["distributions"]["time_granularity"] = gran_counter.most_common()
        summary["distributions"]["dimension_keys"] = dim_key_counter.most_common()
        summary["distributions"]["refusals"] = refusals

        # Write aggregate JSON for external consumption
        agg_path = LOG_DIR / "product_owner_aggregate.json"
        with agg_path.open("w") as af:
            af.write(json.dumps(summary, indent=2))

        # Write detailed mismatch rows for LLM prompt tuning
        detail_path = LOG_DIR / "product_owner_mismatches.json"
        with detail_path.open("w") as df:
            df.write(json.dumps(aggregator["rows"], indent=2))

        print(f"\n{'='*80}")
        print(f"CLASSIFICATION QUALITY REPORT")
        print(f"{'='*80}")
        print(f"Total questions: {total}")
        print(f"Intent accuracy:   {intent_rate:6.1%}  ({counts['intent']}/{total})")
        print(f"Subject accuracy:  {subject_rate:6.1%}  ({counts['subject']}/{total})")
        print(f"Measure accuracy:  {measure_rate:6.1%}  ({counts['measure']}/{total})")
        print(f"Dimension accuracy: {dimension_rate:6.1%}  ({counts['dimension']}/{counts['dimension_expected_non_empty']} when expected)")
        print(f"Time accuracy:     {time_rate:6.1%}  ({counts['time']}/{counts['time_expected_non_empty']} when expected)")
        print(f"\nTime Periods: {summary['distributions']['time_periods']}")
        print(f"Time Windows: {summary['distributions']['time_windows']}")
        print(f"Time Granularity: {summary['distributions']['time_granularity']}")
        print(f"Dimension Keys: {summary['distributions']['dimension_keys']}")
        print(f"Refusals: {summary['distributions']['refusals']}")
        print(f"\nTop Intent Mismatches:")
        for mismatch, count in intent_mismatches.most_common(5):
            print(f"  {mismatch}: {count}")
        print(f"\nTop Subject Mismatches:")
        for mismatch, count in subject_mismatches.most_common(5):
            print(f"  {mismatch}: {count}")
        print(f"\nTop Measure Mismatches:")
        for mismatch, count in measure_mismatches.most_common(5):
            print(f"  {mismatch}: {count}")
        print(f"{'='*80}\n")
        print(f"Reports written to:")
        print(f"  - {agg_path}")
        print(f"  - {detail_path}")
        print(f"{'='*80}\n")

        # Fail if below thresholds (waterproof criteria)
        assert intent_rate >= MIN_INTENT_MATCH_RATE, f"Intent match rate {intent_rate:.2%} below {MIN_INTENT_MATCH_RATE:.2%}"
        assert subject_rate >= MIN_SUBJECT_MATCH_RATE, f"Subject match rate {subject_rate:.2%} below {MIN_SUBJECT_MATCH_RATE:.2%}"
        assert measure_rate >= MIN_MEASURE_MATCH_RATE, f"Measure match rate {measure_rate:.2%} below {MIN_MEASURE_MATCH_RATE:.2%}"
        if counts["dimension_expected_non_empty"]:
            assert dimension_rate >= MIN_DIMENSION_MATCH_RATE, f"Dimension match rate {dimension_rate:.2%} below {MIN_DIMENSION_MATCH_RATE:.2%}"
        if counts["time_expected_non_empty"]:
            assert time_rate >= MIN_TIME_MATCH_RATE, f"Time match rate {time_rate:.2%} below {MIN_TIME_MATCH_RATE:.2%}"
