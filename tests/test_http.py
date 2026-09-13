from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from test_contracts import decision, incident

from regen_protocol.config import Settings
from regen_protocol.http import create_app
from regen_protocol.providers.base import ProviderError, ProviderTimeout


def test_health_and_missing_key_readiness():
    factory = Mock()
    with TestClient(create_app(Settings(), provider_factory=factory)) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert c.get("/ready").status_code == 503
        assert c.post("/v0/decide", json=incident()).status_code == 503
    factory.assert_not_called()


@pytest.mark.parametrize("mode,status", [("invalid", 400), ("failure", 502), ("timeout", 504),
                                         ("policy", 422), ("bad_output", 502), ("valid", 200)])
def test_http_pipeline_and_sanitized_errors(mode, status):
    p = Mock()
    p.__enter__ = Mock(return_value=p)
    p.__exit__ = Mock(return_value=False)
    p.decide.return_value = decision()
    if mode in ("failure", "timeout"):
        p.decide.side_effect = ProviderError() if mode == "failure" else ProviderTimeout()
    elif mode == "policy":
        p.decide.return_value["requires"]["mutation"] = True
    elif mode == "bad_output":
        p.decide.return_value = {"SENSITIVE": "prompt traceback environment"}
    with TestClient(create_app(Settings(api_key="SENSITIVE"), provider_factory=lambda _: p)) as c:
        assert c.get("/ready").status_code == 200
        r = c.post("/v0/decide", json={} if mode == "invalid" else incident())
    assert r.status_code == status
    assert "SENSITIVE" not in r.text
    if status != 200:
        assert set(r.json()) == {"error"}
    assert p.decide.call_count == (0 if mode == "invalid" else 1)


def test_malformed_json_is_400_and_only_declared_routes_exist():
    with TestClient(create_app(Settings())) as c:
        assert c.post("/v0/decide", content="{").status_code == 400
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404
