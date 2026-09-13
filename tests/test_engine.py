from unittest.mock import Mock

import pytest
from test_contracts import decision, incident

from regen_protocol.contracts import ContractError
from regen_protocol.engine import decide
from regen_protocol.policy import PolicyError
from regen_protocol.providers.base import ProviderError, ProviderTimeout


def test_one_call_and_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = Mock()
    p.decide.return_value = decision()
    assert decide(incident(), p) == decision()
    p.decide.assert_called_once()
    assert list(tmp_path.iterdir()) == []


def test_invalid_incident_never_reaches_provider():
    p = Mock()
    with pytest.raises(ContractError):
        decide({}, p)
    p.decide.assert_not_called()


@pytest.mark.parametrize("failure", [ProviderError(), ProviderTimeout(), RuntimeError("SENSITIVE")])
def test_provider_failure_never_retries(failure):
    p = Mock()
    p.decide.side_effect = failure
    with pytest.raises(ProviderError):
        decide(incident(), p)
    assert p.decide.call_count == 1


@pytest.mark.parametrize("candidate", [{}, [], None])
def test_invalid_candidate_rejected(candidate):
    p = Mock()
    p.decide.return_value = candidate
    with pytest.raises(ContractError):
        decide(incident(), p)
    assert p.decide.call_count == 1


def test_provider_cannot_change_input_constraints():
    original = incident()
    def malicious(*, incident, decision_schema):
        incident["constraints"]["mutation_allowed"] = True
        result = decision()
        result["decision_class"] = "CONTINUE_DETERMINISTIC"
        result["requires"]["mutation"] = True
        return result
    p = Mock()
    p.decide.side_effect = malicious
    with pytest.raises(PolicyError):
        decide(original, p)
    assert original["constraints"]["mutation_allowed"] is False
