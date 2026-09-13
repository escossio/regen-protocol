import sqlite3

import pytest
from test_contracts import decision, incident

from regen_protocol.audit import AuditError, AuditStore


def test_audit_roundtrip_indexes_and_pagination(tmp_path):
    store = AuditStore(tmp_path / 'audit.db')
    store.check()
    ids = [store.receive(incident(), provider='openai', model='test') for _ in range(3)]
    assert store.detail(ids[0])['status'] == 'RECEIVED'
    for status in ('COMPLETED', 'PROVIDER_ERROR', 'PROVIDER_TIMEOUT', 'DECISION_REJECTED', 'CONFIG_ERROR'):
        key = store.receive(incident(), provider='openai', model='test')
        store.finish(key, status=status, http_status=200 if status == 'COMPLETED' else 502,
                     duration_ms=7, decision=decision() if status == 'COMPLETED' else None,
                     error_code=None if status == 'COMPLETED' else 'failure')
        row = store.detail(key)
        assert row['status'] == status and row['incident'] == incident()
        assert row['decision'] == (decision() if status == 'COMPLETED' else None)
        assert row['completed_at'] and row['duration_ms'] == 7
    rows = store.list(limit=2, offset=1)
    assert len(rows) == 2 and rows[0]['received_at'] >= rows[1]['received_at']
    assert 'incident' not in rows[0] and 'incident_json' not in rows[0]
    assert len(store.list(status='RECEIVED')) == 3
    assert len(store.list(incident_id=incident()['incident_id'])) == 8
    assert len(store.list(source_system=incident()['source']['system'])) == 8
    assert len(store.list(decision_class='INVESTIGATE_READ_ONLY')) == 1
    assert store.list(incident_id="' OR 1=1 --") == []
    assert store.detail('missing') is None
    with sqlite3.connect(store.path) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0] == 1
        assert len(c.execute("PRAGMA index_list('exchanges')").fetchall()) >= 6
    with pytest.raises(AuditError):
        store.receive({'invalid': object()}, provider='openai', model='test')


def test_audit_rejects_future_schema_and_unwritable_path(tmp_path):
    path = tmp_path / 'future.db'
    with sqlite3.connect(path) as c:
        c.execute('PRAGMA user_version=2')
    with pytest.raises(AuditError):
        AuditStore(path).check()
    with pytest.raises(AuditError):
        AuditStore(tmp_path / 'absent' / 'db').check()


def test_audit_rejects_secret_fields_and_material(tmp_path):
    store = AuditStore(tmp_path / 'audit.db')
    for value in ({'authorization': 'Bearer private'}, {'nested': {'api_key': 'private'}},
                  {'note': 'sk-proj-' + 'x' * 40}):
        data = incident()
        data['facts'].update(value)
        with pytest.raises(AuditError):
            store.receive(data, provider='openai', model='test')


def test_failed_finalize_rolls_back_and_survives_reopen(tmp_path):
    store = AuditStore(tmp_path / 'audit.db')
    key = store.receive(incident(), provider='openai', model='test')
    with sqlite3.connect(store.path) as c:
        c.execute("""CREATE TRIGGER reject_update BEFORE UPDATE ON exchanges
                     BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    with pytest.raises(AuditError):
        store.finish(key, status='COMPLETED', http_status=200, duration_ms=1, decision=decision())
    row = AuditStore(store.path).detail(key)
    assert row['status'] == 'RECEIVED' and row['decision'] is None
    assert row['completed_at'] is None
