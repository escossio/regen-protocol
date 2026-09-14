import json
import logging

import httpx2
import pytest
from test_contracts import decision, incident

from regen_protocol.config import Settings
from regen_protocol.contracts import load_schema
from regen_protocol.providers.base import ProviderError, ProviderTimeout
from regen_protocol.providers.openai import OpenAIProvider, structured_schema


def response(candidate=None):
    return {"id": "resp_fixture", "object": "response", "created_at": 1,
            "model": "gpt-6-astra", "status": "completed",
            "output": [{"id": "msg_fixture", "type": "message", "role": "assistant",
                        "status": "completed", "content": [{"type": "output_text",
                        "text": json.dumps(candidate or decision()), "annotations": []}]}]}


def test_actual_sdk_request_contract_and_no_retry():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx2.Response(200, json=response())
    config = Settings(api_key="test-only", model="gpt-6-astra", reasoning_effort="high")
    with OpenAIProvider(config, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as p:
        assert p.client.max_retries == 0
        assert p.decide(incident=incident(), decision_schema=load_schema("decision")) == decision()
    assert len(calls) == 1 and calls[0].url.path == "/v1/responses"
    body = json.loads(calls[0].content)
    assert body["model"] == config.model
    assert body["reasoning"] == {"effort": "high"}
    assert body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "requested_evidence and recommended_next_step never execute actions" in body[
        "instructions"
    ]
    assert "A new caller-bound capability action is not a retry" in body["instructions"]
    assert "requires.retry describes reissuing a prior operation" in body["instructions"]
    assert "capability_semantics" in body["instructions"]
    for forbidden in ("tools", "conversation", "previous_response_id", "background", "stream"):
        assert forbidden not in body
    assert json.loads(body["input"]) == incident()


@pytest.mark.parametrize("kind", ["http", "timeout", "refusal", "incomplete", "invalid", "array"])
def test_actual_sdk_failures_make_one_request(kind):
    calls = []
    def handler(request):
        calls.append(request)
        if kind == "http":
            return httpx2.Response(500, json={"error": {"message": "SENSITIVE"}})
        if kind == "timeout":
            raise httpx2.ReadTimeout("SENSITIVE", request=request)
        data = response()
        if kind == "incomplete":
            data["status"] = "incomplete"
        elif kind == "refusal":
            data["output"][0]["content"] = [{"type": "refusal", "refusal": "SENSITIVE"}]
        elif kind in ("invalid", "array"):
            data["output"][0]["content"][0]["text"] = "SENSITIVE" if kind == "invalid" else "[]"
        return httpx2.Response(200, json=data)
    with OpenAIProvider(Settings(api_key="test-only"), http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as p:
        with pytest.raises(ProviderTimeout if kind == "timeout" else ProviderError) as caught:
            p.decide(incident=incident(), decision_schema=load_schema("decision"))
        assert "SENSITIVE" not in str(caught.value)
    assert len(calls) == 1


def test_schema_adaptation_only_removes_dialect_annotation():
    original = load_schema("decision")
    adapted = structured_schema(original)
    assert adapted == {key: value for key, value in original.items() if key != "$schema"}
    assert "$schema" in original


def test_sdk_debug_logging_does_not_expose_incident(caplog):
    caplog.set_level(logging.DEBUG, logger="openai._base_client")
    def handler(request):
        return httpx2.Response(200, json=response())
    data = incident()
    data["summary"] = "SENSITIVE_INCIDENT_PAYLOAD"
    with OpenAIProvider(Settings(api_key="test-only"), http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as p:
        p.decide(incident=data, decision_schema=load_schema("decision"))
    assert "SENSITIVE_INCIDENT_PAYLOAD" not in caplog.text
