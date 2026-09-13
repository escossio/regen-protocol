import json
from pathlib import Path

import pytest

from regen_protocol.contracts import ContractError, load_schema, validate_decision, validate_incident

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/0001-codex-task7-remediation-exhausted"


def incident():
    return json.loads((FIXTURE / "incident.json").read_text())


def decision():
    return json.loads((FIXTURE / "expected-decision.json").read_text())


def test_normative_fixtures_and_schema_identity():
    validate_incident(incident())
    validate_decision(decision())
    for name in ("incident", "decision"):
        assert load_schema(name) == json.loads((ROOT / f"protocol/v0/{name}.schema.json").read_text())


@pytest.mark.parametrize("bad", [{}, [], None, {"summary": "SENSITIVE"}])
def test_invalid_input_is_sanitized(bad):
    with pytest.raises(ContractError) as caught:
        validate_incident(bad)
    assert str(caught.value) == "invalid_incident"


def test_datetime_is_validated():
    data = incident()
    data["occurred_at"] = "yesterday"
    with pytest.raises(ContractError):
        validate_incident(data)


def test_non_json_values_fail_closed():
    data = incident()
    data["facts"]["bad"] = float("nan")
    with pytest.raises(ContractError):
        validate_incident(data)
