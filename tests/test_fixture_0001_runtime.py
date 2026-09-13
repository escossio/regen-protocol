from unittest.mock import Mock

from test_contracts import decision, incident

from regen_protocol.engine import decide


def test_fixture_0001_full_fake_chain():
    p = Mock()
    p.decide.return_value = decision()
    result = decide(incident(), p)
    assert result == decision()
    assert result["decision_class"] == "INVESTIGATE_READ_ONLY"
    assert not any(result["requires"].values())
    assert p.decide.call_count == 1
