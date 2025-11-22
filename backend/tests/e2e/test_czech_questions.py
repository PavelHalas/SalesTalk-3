import csv
import json
import os
import time
from pathlib import Path
from typing import Dict, Any

import pytest

# Add lambda and src directories to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from classify import lambda_handler as classify_handler

DATA_FILE = Path(__file__).parent.parent / "data" / "czech_questions.csv"
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Ensure Czech processing path is active
os.environ.setdefault("ENABLE_LANG_DETECT", "true")
# Default to mock AI unless explicitly enabled
USE_REAL_AI = os.environ.get("USE_REAL_AI", "false").lower() in ("true", "1", "yes")
VERBOSE_E2E = os.environ.get("VERBOSE_E2E", "false").lower() in ("true", "1", "yes")
# Confidence gating (applies when real AI is used)
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.5"))

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
            "requestId": f"cz-questions-{int(time.time()*1000)}",
            "authorizer": {"claims": {"custom:tenant_id": tenant_id}}
        }
    }


def _value_matches(expected_v, actual_v) -> bool:
    if isinstance(expected_v, (str, int, float, bool)) or expected_v is None:
        return expected_v == actual_v
    if isinstance(expected_v, list):
        if not isinstance(actual_v, list):
            return False
        return all(item in actual_v for item in expected_v)
    if isinstance(expected_v, dict):
        if not isinstance(actual_v, dict):
            return False
        return all(k in actual_v and _value_matches(v, actual_v[k]) for k, v in expected_v.items())
    return False


def assert_minimal_structure(result: Dict[str, Any]):
    assert isinstance(result, dict), "classification must be a dict"
    for field in REQUIRED_FIELDS:
        assert field in result, f"Missing classification field: {field}"
    conf = result.get("confidence", {}) or {}
    if isinstance(conf, dict) and "overall" in conf:
        overall = conf.get("overall")
        if isinstance(overall, (int, float)):
            assert 0.0 <= overall <= 1.0, "confidence.overall must be in [0,1]"
            assert overall >= MIN_CONFIDENCE, f"confidence.overall {overall} below minimum {MIN_CONFIDENCE}"


@pytest.fixture(scope="class")
def rows():
    return list(load_rows())


@pytest.fixture
def mock_ai_adapter():
    class MockAdapter:
        def __init__(self, payload: Dict[str, Any]):
            self.payload = payload
        def classify(self, *_args, **_kwargs):
            return self.payload
    return MockAdapter


@pytest.mark.e2e
class TestCzechQuestionSuite:
    @pytest.mark.parametrize("row_index", list(range(0, 30)))
    def test_question_row(self, row_index, rows, mock_ai_adapter, monkeypatch):
        assert row_index < len(rows)
        row = rows[row_index]
        question = row["question"].strip()

        # Build expected payload for mock path
        expected_dimension = row.get("dimension", "{}") or "{}"
        expected_time = row.get("time", "{}") or "{}"
        try:
            dim_obj = json.loads(expected_dimension)
        except Exception:
            dim_obj = {}
        try:
            time_obj = json.loads(expected_time)
        except Exception:
            time_obj = {}
        payload = {
            "intent": row["intent"].strip(),
            "subject": row["subject"].strip(),
            "measure": row["measure"].strip(),
            "dimension": dim_obj,
            "time": time_obj,
            "confidence": {
                "overall": 0.90,
                "components": {
                    "intent": 0.95,
                    "subject": 0.90,
                    "measure": 0.88,
                    "time": 0.92,
                    "dimension": 0.85,
                },
            },
            "refused": False,
        }

        if not USE_REAL_AI:
            # Patch classify.get_adapter to return deterministic payload
            import classify as _classify
            adapter = mock_ai_adapter(payload)
            monkeypatch.setattr(_classify, "get_adapter", lambda *a, **k: adapter)

        event = create_event(question, TEST_TENANT)
        response = classify_handler(event, None)
        assert response["statusCode"] == 200, f"Non-200 for question '{question}'"
        body = json.loads(response["body"])
        classification = body["classification"]

        # Minimal structural checks (works for real or mock)
        assert_minimal_structure(classification)

        if not USE_REAL_AI:
            # Strict equality against expected when mocked
            assert classification["intent"] == payload["intent"]
            assert classification["subject"] == payload["subject"]
            assert classification["measure"] == payload["measure"]
            assert _value_matches(payload["dimension"], classification.get("dimension", {}))
            assert _value_matches(payload["time"], classification.get("time", {}))

        if VERBOSE_E2E:
            print(f"[CZ] Q: {question}\n    intent={classification.get('intent')} subject={classification.get('subject')} measure={classification.get('measure')}", flush=True)
