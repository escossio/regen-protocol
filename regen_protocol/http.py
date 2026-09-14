import hmac
import json
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from regen_protocol.audit import AuditError, AuditStore, safe_envelope
from regen_protocol.config import ConfigurationError, Settings
from regen_protocol.contracts import ContractError, validate_incident
from regen_protocol.engine import decide
from regen_protocol.policy import PolicyError
from regen_protocol.providers.base import ProviderError, ProviderTimeout
from regen_protocol.providers.openai import OpenAIProvider


def create_app(settings: Settings | None = None, *, provider_factory=OpenAIProvider,
               audit_store=None) -> FastAPI:
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def token():
        return settings.api_token if settings else os.environ.get('REGEN_API_TOKEN')

    def authorized(request):
        expected = token()
        supplied = request.headers.get('authorization', '')
        return bool(expected and expected.strip() and supplied.startswith('Bearer ') and
                    hmac.compare_digest(supplied[7:].encode(), expected.encode()))

    def store():
        return audit_store if audit_store is not None else AuditStore(
            settings.audit_db_path if settings else os.environ.get('REGEN_AUDIT_DB_PATH',
                                                                   '/data/regen-audit.sqlite3'))

    def error(code, status, key=None):
        return JSONResponse({'error': code}, status_code=status,
                            headers={'X-REGEN-Exchange-ID': key} if key else None)

    @application.exception_handler(RequestValidationError)
    async def invalid_query(request, exception):
        return error('invalid_query', 400) if authorized(request) else error('unauthorized', 401)

    @application.get('/health')
    def health():
        return {'status': 'ok'}

    @application.get('/ready')
    def ready():
        try:
            (settings or Settings.from_env()).require_ready()
            if not token() or not token().strip():
                raise ConfigurationError()
            store().check()
        except (ConfigurationError, AuditError):
            return JSONResponse({'status': 'not_ready'}, status_code=503)
        return {'status': 'ready'}

    def process(incident):
        started = time.monotonic()
        audit = store()
        try:
            key = audit.receive(incident, provider='openai', model=settings.model if settings else
                                os.environ.get('REGEN_OPENAI_MODEL', 'gpt-6-astra'))
        except AuditError:
            return error('audit_failure', 503)
        result, status, http_status, code = None, 'COMPLETED', 200, None
        audit_code = None
        try:
            config = settings or Settings.from_env()
            config.require_ready()
            with provider_factory(config) as provider:
                result = decide(incident, provider)
            safe_envelope(result, (config.api_key, token()))
        except ConfigurationError:
            status, http_status, code = 'CONFIG_ERROR', 503, 'not_ready'
        except ProviderTimeout:
            status, http_status, code = 'PROVIDER_TIMEOUT', 504, 'provider_timeout'
        except PolicyError as policy_error:
            status, http_status, code = 'DECISION_REJECTED', 422, 'policy_rejected'
            audit_code = policy_error.reason_code
        except (ContractError, AuditError):
            status, http_status, code = 'DECISION_REJECTED', 502, 'invalid_decision'
        except ProviderError:
            status, http_status, code = 'PROVIDER_ERROR', 502, 'provider_failure'
        except Exception:
            status, http_status, code = 'PROVIDER_ERROR', 502, 'internal_failure'
        try:
            audit.finish(key, status=status, http_status=http_status,
                         duration_ms=int((time.monotonic() - started) * 1000),
                         decision=result if status == 'COMPLETED' else None,
                         error_code=audit_code or code)
        except AuditError:
            logging.getLogger(__name__).error('audit_finalize_failed')
            return error('audit_failure', 503, key)
        return (JSONResponse(result, headers={'X-REGEN-Exchange-ID': key}) if code is None
                else error(code, http_status, key))

    @application.post('/v0/decide')
    async def decide_http(request: Request):
        if not authorized(request):
            return error('unauthorized', 401)
        try:
            incident = await request.json()
            validate_incident(incident)
            safe_envelope(incident, (token(), settings.api_key if settings else os.environ.get('OPENAI_API_KEY')))
        except (ContractError, json.JSONDecodeError, UnicodeDecodeError, AuditError, ValueError, TypeError):
            return error('invalid_incident', 400)
        return await run_in_threadpool(process, incident)

    @application.get('/v0/exchanges')
    def exchanges(request: Request, limit: int = 50, offset: int = 0, incident_id: str | None = None,
                  source_system: str | None = None, decision_class: str | None = None, status: str | None = None):
        if not authorized(request):
            return error('unauthorized', 401)
        if not 1 <= limit <= 100 or offset < 0:
            return error('invalid_query', 400)
        try:
            return store().list(limit=limit, offset=offset, incident_id=incident_id,
                                source_system=source_system, decision_class=decision_class, status=status)
        except AuditError:
            return error('audit_failure', 503)

    @application.get('/v0/exchanges/{exchange_id}')
    def exchange(request: Request, exchange_id: str):
        if not authorized(request):
            return error('unauthorized', 401)
        try:
            item = store().detail(exchange_id)
            return item if item is not None else error('exchange_not_found', 404)
        except AuditError:
            return error('audit_failure', 503)

    return application


app = create_app()

if __name__ == '__main__':
    import uvicorn

    config = Settings.from_env()
    uvicorn.run(app, host=config.http_host, port=config.http_port,
                log_level=config.log_level.lower(), access_log=False)
