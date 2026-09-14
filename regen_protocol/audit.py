"""Operational audit only. Never imported by the reasoning core."""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from regen_protocol.contracts import validate_decision, validate_incident
from regen_protocol.policy import POLICY_REASON_CODES

META = ('exchange_id', 'received_at', 'completed_at', 'status', 'source_system',
        'source_instance', 'incident_id', 'decision_id', 'decision_class', 'provider',
        'model', 'duration_ms', 'http_status', 'error_code')
TERMINAL = {'COMPLETED', 'PROVIDER_ERROR', 'PROVIDER_TIMEOUT', 'DECISION_REJECTED', 'CONFIG_ERROR'}
SAFE_ERROR_CODES = POLICY_REASON_CODES | {
    'not_ready',
    'provider_timeout',
    'invalid_decision',
    'provider_failure',
    'internal_failure',
}


class AuditError(Exception):
    def __init__(self):
        super().__init__('audit_failure')


def safe_envelope(data, secrets=()):
    """Reject obvious sensitive fields/material; never rewrite caller evidence."""
    forbidden = {'authorization', 'api_key', 'apikey', 'password', 'token', 'secret',
                 'environment', 'env', 'traceback', 'chain_of_thought', 'private_reasoning',
                 'prompt', 'raw_response', 'access_token', 'id_token'}

    def check(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower().replace('-', '_') in forbidden:
                    raise AuditError()
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
        elif isinstance(value, str):
            if any(secret and secret in value for secret in secrets):
                raise AuditError()
            if re.search(r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|'
                         r'-----BEGIN .*PRIVATE KEY-----', value):
                raise AuditError()
    check(data)
    return json.dumps(data, allow_nan=False, separators=(',', ':'))


def now():
    return datetime.now(timezone.utc).isoformat()


class AuditStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA synchronous=FULL')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise AuditError()
            if version == 0:
                with connection:
                    connection.execute('''CREATE TABLE IF NOT EXISTS exchanges (
                        exchange_id TEXT PRIMARY KEY, received_at TEXT NOT NULL,
                        completed_at TEXT, status TEXT NOT NULL, source_system TEXT NOT NULL,
                        source_instance TEXT, incident_id TEXT NOT NULL, decision_id TEXT,
                        decision_class TEXT, provider TEXT, model TEXT, duration_ms INTEGER,
                        http_status INTEGER, error_code TEXT, incident_json TEXT NOT NULL,
                        decision_json TEXT)''')
                    for column in ('received_at', 'incident_id', 'source_system', 'decision_class', 'status'):
                        connection.execute(f'CREATE INDEX IF NOT EXISTS idx_{column} ON exchanges ({column})')
                    connection.execute('PRAGMA user_version=1')
            yield connection
        except (sqlite3.Error, OSError, ValueError, TypeError):
            raise AuditError() from None
        finally:
            if connection is not None:
                connection.close()

    def check(self):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('UPDATE exchanges SET status=status WHERE 0')
            c.rollback()

    def receive(self, incident: dict, *, provider, model):
        try:
            validate_incident(incident)
            payload = safe_envelope(incident)
        except Exception:
            raise AuditError() from None
        key = str(uuid4())
        with self.connection() as c, c:
            c.execute('''INSERT INTO exchanges
                (exchange_id,received_at,status,source_system,source_instance,incident_id,
                 provider,model,incident_json) VALUES (?,?,?,?,?,?,?,?,?)''',
                      (key, now(), 'RECEIVED', incident['source']['system'], incident['source'].get('instance'),
                       incident['incident_id'], provider, model, payload))
        return key

    def finish(self, key, *, status, http_status, duration_ms, decision=None, error_code=None):
        if status not in TERMINAL or (status == 'COMPLETED') != (decision is not None):
            raise AuditError()
        if error_code is not None and error_code not in SAFE_ERROR_CODES:
            raise AuditError()
        payload = None
        if decision is not None:
            try:
                validate_decision(decision)
                payload = safe_envelope(decision)
            except Exception:
                raise AuditError() from None
        with self.connection() as c, c:
            cursor = c.execute('''UPDATE exchanges SET completed_at=?,status=?,decision_id=?,decision_class=?,
                duration_ms=?,http_status=?,error_code=?,decision_json=? WHERE exchange_id=? AND status='RECEIVED' ''',
                               (now(), status, decision.get('decision_id') if decision else None,
                                decision.get('decision_class') if decision else None,
                                duration_ms, http_status, error_code, payload, key))
            if cursor.rowcount != 1:
                raise AuditError()

    def list(self, *, limit=50, offset=0, **filters):
        allowed = {'incident_id', 'source_system', 'decision_class', 'status'}
        if not 1 <= limit <= 100 or offset < 0 or not filters.keys() <= allowed:
            raise AuditError()
        filters = {k: v for k, v in filters.items() if v is not None}
        where = ' AND '.join(f'{key}=?' for key in filters) or '1=1'
        with self.connection() as c:
            return [dict(row) for row in c.execute(
                f"SELECT {','.join(META)} FROM exchanges WHERE {where} "
                'ORDER BY received_at DESC,exchange_id DESC LIMIT ? OFFSET ?',
                (*filters.values(), limit, offset))]

    def detail(self, key):
        with self.connection() as c:
            row = c.execute('SELECT * FROM exchanges WHERE exchange_id=?', (key,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result['incident'] = json.loads(result.pop('incident_json'))
        result['decision'] = json.loads(result['decision_json']) if result['decision_json'] else None
        del result['decision_json']
        return result
