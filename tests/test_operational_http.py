import ast
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from test_contracts import decision, incident

from regen_protocol.audit import AuditError, AuditStore
from regen_protocol.config import Settings
from regen_protocol.http import create_app
from regen_protocol.providers.base import ProviderError, ProviderTimeout

AUTH = {'Authorization': 'Bearer test-bearer'}


def client(tmp_path, mode='valid', store=None, key='test-key', token='test-bearer'):
    store = store or AuditStore(tmp_path / 'audit.db')
    provider = Mock()
    provider.__enter__ = Mock(return_value=provider)
    provider.__exit__ = Mock(return_value=False)

    def answer(*, incident, decision_schema):
        assert store.list(status='RECEIVED'), 'audit must be committed before provider'
        if mode == 'error':
            raise ProviderError()
        if mode == 'timeout':
            raise ProviderTimeout()
        output = decision()
        output['incident_id'] = incident['incident_id']
        if mode == 'policy':
            output['requires']['mutation'] = True
            output['rationale_summary'] = 'PRIVATE_REJECTED_CANDIDATE_SENTINEL'
        if mode == 'invalid':
            return {}
        return output
    provider.decide.side_effect = answer
    app = create_app(Settings(api_key=key, api_token=token, audit_db_path=str(tmp_path / 'audit.db')),
                     provider_factory=lambda _: provider, audit_store=store)
    return TestClient(app), store, provider


@pytest.mark.parametrize('mode,http,status', [('valid', 200, 'COMPLETED'), ('error', 502, 'PROVIDER_ERROR'),
                                             ('timeout', 504, 'PROVIDER_TIMEOUT'),
                                             ('policy', 422, 'DECISION_REJECTED'),
                                             ('invalid', 502, 'DECISION_REJECTED')])
def test_exchange_terminal_and_headers(tmp_path, mode, http, status):
    c, store, provider = client(tmp_path, mode)
    response = c.post('/v0/decide', json=incident(), headers=AUTH)
    assert response.status_code == http
    key = response.headers['X-REGEN-Exchange-ID']
    row = store.detail(key)
    assert row['status'] == status and row['http_status'] == http
    assert row['incident'] == incident() and row['provider'] == 'openai'
    assert provider.decide.call_count == 1
    assert row['completed_at'] and row['duration_ms'] >= 0
    if http == 200:
        assert row['decision'] == response.json()
    if mode == 'policy':
        assert response.json() == {'error': 'policy_rejected'}
        assert row['error_code'] == 'POLICY_REJECTED_MUTATION_NOT_ALLOWED'
        detail = c.get('/v0/exchanges/' + key, headers=AUTH)
        assert detail.status_code == 200
        assert detail.json()['error_code'] == 'POLICY_REJECTED_MUTATION_NOT_ALLOWED'
        assert detail.json()['decision'] is None
        assert row['decision'] is None
        assert 'PRIVATE_REJECTED_CANDIDATE_SENTINEL' not in str(row)
        assert b'PRIVATE_REJECTED_CANDIDATE_SENTINEL' not in store.path.read_bytes()


@pytest.mark.parametrize('endpoint', ['/v0/decide', '/v0/exchanges', '/v0/exchanges/missing'])
@pytest.mark.parametrize('header', [{}, {'Authorization': 'Bearer wrong'}])
def test_auth_required(tmp_path, endpoint, header):
    c, store, provider = client(tmp_path)
    request = c.post if endpoint == '/v0/decide' else c.get
    r = request(endpoint, headers=header)
    assert r.status_code == 401 and r.json() == {'error': 'unauthorized'}
    assert not store.path.exists()
    provider.decide.assert_not_called()


@pytest.mark.parametrize('key,token,ready', [(None, 'test-bearer', 503), ('test-key', None, 503),
                                          ('test-key', 'test-bearer', 200)])
def test_readiness(tmp_path, key, token, ready):
    c, store, provider = client(tmp_path, key=key, token=token)
    assert c.get('/health').status_code == 200
    assert c.get('/ready').status_code == ready
    provider.decide.assert_not_called()


def test_invalid_incident_zero_audit_and_config_failure_audited(tmp_path):
    c, store, provider = client(tmp_path, key=None)
    assert c.post('/v0/decide', headers=AUTH, json={}).status_code == 400
    assert not store.path.exists()
    r = c.post('/v0/decide', headers=AUTH, json=incident())
    assert r.status_code == 503
    assert store.detail(r.headers['X-REGEN-Exchange-ID'])['status'] == 'CONFIG_ERROR'
    provider.decide.assert_not_called()


def test_store_failures_no_inference_or_false_success(tmp_path, monkeypatch):
    c, store, provider = client(tmp_path)
    with monkeypatch.context() as m:
        m.setattr(store, 'check', Mock(side_effect=AuditError()))
        assert c.get('/ready').status_code == 503
    with monkeypatch.context() as m:
        m.setattr(store, 'receive', Mock(side_effect=AuditError()))
        assert c.post('/v0/decide', headers=AUTH, json=incident()).status_code == 503
        provider.decide.assert_not_called()
    monkeypatch.setattr(store, 'finish', Mock(side_effect=AuditError()))
    r = c.post('/v0/decide', headers=AUTH, json=incident())
    assert r.status_code == 503 and r.json() == {'error': 'audit_failure'}
    assert store.detail(r.headers['X-REGEN-Exchange-ID'])['status'] == 'RECEIVED'
    assert provider.decide.call_count == 1


def test_query_and_cognitive_isolation(tmp_path):
    c, store, provider = client(tmp_path)
    a, b = incident(), incident()
    a['incident_id'], b['incident_id'] = 'ONLY-A', 'ONLY-B'
    ra = c.post('/v0/decide', headers=AUTH, json=a)
    rb = c.post('/v0/decide', headers=AUTH, json=b)
    assert provider.decide.call_count == 2
    assert provider.decide.call_args.kwargs['incident'] == b
    assert 'ONLY-A' not in str(provider.decide.call_args)
    key = ra.headers['X-REGEN-Exchange-ID']
    detail = c.get('/v0/exchanges/' + key, headers=AUTH).json()
    assert detail['incident'] == a and detail['decision'] == ra.json()
    rows = c.get('/v0/exchanges?limit=1', headers=AUTH).json()
    assert rows[0]['exchange_id'] == rb.headers['X-REGEN-Exchange-ID']
    assert 'incident' not in rows[0] and 'decision' not in rows[0]
    assert c.get('/v0/exchanges?limit=101', headers=AUTH).status_code == 400
    assert c.get('/v0/exchanges?offset=-1', headers=AUTH).status_code == 400
    assert c.get('/v0/exchanges', params={'incident_id': "' OR 1=1 --"}, headers=AUTH).json() == []
    assert c.get('/v0/exchanges/missing', headers=AUTH).status_code == 404
    restarted, _, _ = client(tmp_path)
    assert restarted.get('/v0/exchanges/' + key, headers=AUTH).json() == detail


def test_secrets_never_stored(tmp_path):
    c, store, _ = client(tmp_path)
    data = incident()
    data['facts']['note'] = 'test-bearer'
    r = c.post('/v0/decide', headers=AUTH, json=data)
    assert r.status_code == 400 and not store.path.exists()
    assert 'test-bearer' not in r.text


def test_reasoning_modules_do_not_import_audit():
    root = Path(__file__).resolve().parents[1] / 'regen_protocol'
    for path in [root / 'engine.py', root / 'policy.py', *root.glob('providers/*.py')]:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert 'audit' not in (node.module or '')
            elif isinstance(node, ast.Import):
                assert all('audit' not in alias.name for alias in node.names)


def test_provider_secret_output_rejected_without_persistence(tmp_path):
    c, store, provider = client(tmp_path)
    output = decision()
    output['rationale_summary'] = 'test-key'
    provider.decide.side_effect = None
    provider.decide.return_value = output
    r = c.post('/v0/decide', headers=AUTH, json=incident())
    assert r.status_code == 502 and 'test-key' not in r.text
    row = store.detail(r.headers['X-REGEN-Exchange-ID'])
    assert row['status'] == 'DECISION_REJECTED' and row['decision'] is None
    assert b'test-key' not in store.path.read_bytes()
    assert b'test-bearer' not in store.path.read_bytes()


def test_unexpected_exception_is_sanitized_and_audited(tmp_path, caplog):
    c, store, provider = client(tmp_path)
    provider.decide.side_effect = RuntimeError('test-key test-bearer prompt traceback environment')
    r = c.post('/v0/decide', headers=AUTH, json=incident())
    assert r.status_code == 502 and provider.decide.call_count == 1
    row = store.detail(r.headers['X-REGEN-Exchange-ID'])
    assert row['status'] == 'PROVIDER_ERROR'
    assert 'test-key' not in r.text + caplog.text + str(row)
    assert 'test-bearer' not in r.text + caplog.text + str(row)
