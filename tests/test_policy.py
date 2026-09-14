import copy

import pytest
from test_contracts import decision, incident

from regen_protocol.policy import PolicyError, guard


@pytest.mark.parametrize(
    ("case", "reason_code"),
    [
        ("version", "POLICY_REJECTED_PROTOCOL_MISMATCH"),
        ("id", "POLICY_REJECTED_INCIDENT_IDENTITY_MISMATCH"),
        ("mutation", "POLICY_REJECTED_MUTATION_NOT_ALLOWED"),
        ("retry", "POLICY_REJECTED_RETRY_NOT_ALLOWED"),
        ("human", "POLICY_REJECTED_HUMAN_REQUIREMENT_MISMATCH"),
        (
            "read_mutation",
            "POLICY_REJECTED_READ_ONLY_REQUIRES_MUTATION_OR_RETRY",
        ),
        ("read_retry", "POLICY_REJECTED_READ_ONLY_REQUIRES_MUTATION_OR_RETRY"),
        ("escalate", "POLICY_REJECTED_INVALID_HUMAN_ESCALATION_REQUIREMENT"),
        ("denied", "POLICY_REJECTED_REQUESTED_DENIED_CAPABILITY"),
        ("unavailable", "POLICY_REJECTED_REQUESTED_UNAVAILABLE_CAPABILITY"),
    ],
)
def test_each_policy_invariant_has_a_closed_deterministic_reason(case, reason_code):
    i, d = incident(), decision()
    if case == "version":
        d["protocol_version"] = "1"
    elif case == "id":
        d["incident_id"] = "wrong"
    elif case in ("mutation", "retry"):
        d["decision_class"] = "CONTINUE_DETERMINISTIC"
        d["requires"][case] = True
    elif case == "human":
        i["constraints"]["human_approval_required"] = True
    elif case.startswith("read_"):
        field = case.removeprefix("read_")
        i["constraints"][field + "_allowed"] = True
        d["requires"][field] = True
    elif case == "escalate":
        d["decision_class"] = "ESCALATE_HUMAN"
    else:
        i["capabilities"][case] = [d["requested_capabilities"][0]]
    before = copy.deepcopy(d)
    with pytest.raises(PolicyError) as caught:
        guard(i, d)
    assert caught.value.reason_code == reason_code
    assert str(caught.value) == "policy_rejected"
    assert d == before


def test_multiple_violations_use_documented_rule_precedence():
    i, d = incident(), decision()
    d["protocol_version"] = "1"
    d["incident_id"] = "wrong"

    with pytest.raises(PolicyError) as caught:
        guard(i, d)

    assert caught.value.reason_code == "POLICY_REJECTED_PROTOCOL_MISMATCH"


def test_valid_decision_is_not_modified():
    i, d = incident(), decision()
    before = copy.deepcopy(d)
    guard(i, d)
    assert d == before
