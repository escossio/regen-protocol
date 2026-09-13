import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from regen_protocol.config import ConfigurationError, Settings
from regen_protocol.contracts import ContractError, validate_incident
from regen_protocol.engine import decide
from regen_protocol.policy import PolicyError
from regen_protocol.providers.base import ProviderError, ProviderTimeout
from regen_protocol.providers.openai import OpenAIProvider


def create_app(settings: Settings | None = None, *, provider_factory=OpenAIProvider) -> FastAPI:
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @application.get("/health")
    def health():
        return {"status": "ok"}

    @application.get("/ready")
    def ready():
        try:
            (settings or Settings.from_env()).require_ready()
        except ConfigurationError:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return {"status": "ready"}

    def process(incident):
        config = settings or Settings.from_env()
        config.require_ready()
        with provider_factory(config) as provider:
            return decide(incident, provider)

    @application.post("/v0/decide")
    async def decide_http(request: Request):
        try:
            try:
                incident = await request.json()
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ContractError("incident") from None
            validate_incident(incident)
            result = await run_in_threadpool(process, incident)
            return JSONResponse(result)
        except ContractError as error:
            return JSONResponse({"error": error.code}, status_code=400 if error.code == "invalid_incident" else 502)
        except PolicyError as error:
            return JSONResponse({"error": error.code}, status_code=422)
        except ConfigurationError as error:
            return JSONResponse({"error": error.code}, status_code=503)
        except ProviderTimeout as error:
            return JSONResponse({"error": error.code}, status_code=504)
        except ProviderError as error:
            return JSONResponse({"error": error.code}, status_code=502)
        except Exception:
            return JSONResponse({"error": "internal_failure"}, status_code=502)

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    config = Settings.from_env()
    uvicorn.run(app, host=config.http_host, port=config.http_port,
                log_level=config.log_level.lower(), access_log=False)
