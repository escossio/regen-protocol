import json
from unittest.mock import Mock

import pytest
from test_contracts import FIXTURE, decision

from regen_protocol import cli
from regen_protocol.config import ConfigurationError, Settings
from regen_protocol.providers.base import ProviderError, ProviderTimeout


def test_validate_never_calls_provider(monkeypatch, capsys):
    factory = Mock()
    monkeypatch.setattr(cli, "OpenAIProvider", factory)
    assert cli.main(["validate", "--incident", str(FIXTURE / "incident.json")]) == 0
    factory.assert_not_called()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("mode,code", [("valid", 0), ("input", 2), ("provider", 3),
                                      ("policy", 4), ("config", 5), ("timeout", 6)])
def test_cli_exit_codes_and_output(mode, code, monkeypatch, tmp_path, capsys):
    p = Mock()
    p.__enter__ = Mock(return_value=p)
    p.__exit__ = Mock(return_value=False)
    p.decide.return_value = decision()
    if mode in ("provider", "timeout"):
        p.decide.side_effect = ProviderError() if mode == "provider" else ProviderTimeout()
    if mode == "policy":
        p.decide.return_value["requires"]["retry"] = True
    monkeypatch.setattr(cli.Settings, "from_env", lambda: Settings(api_key=None if mode == "config" else "SENSITIVE"))
    monkeypatch.setattr(cli, "OpenAIProvider", lambda _: p)
    path = FIXTURE / "incident.json"
    if mode == "input":
        path = tmp_path / "bad.json"
        path.write_text("{}")
    assert cli.main(["decide", "--incident", str(path), "--provider", "openai"]) == code
    output = capsys.readouterr()
    assert "SENSITIVE" not in output.out + output.err
    if code == 0:
        assert json.loads(output.out) == decision()
    else:
        assert output.out == ""
        assert output.err.strip() in {
            "invalid_incident", "provider_failure", "policy_rejected", "not_ready", "provider_timeout"
        }


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_valid_config_efforts(effort):
    assert Settings(reasoning_effort=effort).reasoning_effort == effort


@pytest.mark.parametrize("values", [{"reasoning_effort": "unknown"}, {"timeout_seconds": 0},
                                  {"timeout_seconds": float("nan")}, {"http_port": -1}])
def test_invalid_configuration(values):
    with pytest.raises(ConfigurationError):
        Settings(**values)


def test_key_not_in_repr():
    assert "SENSITIVE" not in repr(Settings(api_key="SENSITIVE"))
