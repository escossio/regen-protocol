import copy

import pytest
from test_contracts import decision, incident

from regen_protocol.policy import PolicyError, guard


@pytest.mark.parametrize("case", ["version", "id", "mutation", "retry", "human",
                                  "read_mutation", "read_retry", "escalate", "denied", "unavailable"])
def test_all_policy_invariants_reject_without_repair(case):
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
    with pytest.raises(PolicyError):
        guard(i, d)
    assert d == before


def test_valid_decision_is_not_modified():
    i, d = incident(), decision()
    before = copy.deepcopy(d)
    guard(i, d)
    assert d == before
