import math
import os
from dataclasses import dataclass, field


class ConfigurationError(Exception):
    code = "not_ready"

    def __init__(self):
        super().__init__(self.code)


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(default=None, repr=False)
    model: str = "gpt-6-astra"
    reasoning_effort: str = "high"
    timeout_seconds: float = 120
    http_host: str = "0.0.0.0"
    http_port: int = 8080
    log_level: str = "INFO"

    def __post_init__(self):
        if (not self.model.strip() or self.reasoning_effort not in {"low", "medium", "high", "xhigh", "max"}
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
                or not 1 <= self.http_port <= 65535 or not self.http_host
                or self.log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}):
            raise ConfigurationError()

    @classmethod
    def from_env(cls):
        try:
            return cls(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model=os.environ.get("REGEN_OPENAI_MODEL", "gpt-6-astra"),
                reasoning_effort=os.environ.get("REGEN_OPENAI_REASONING_EFFORT", "high"),
                timeout_seconds=float(os.environ.get("REGEN_OPENAI_TIMEOUT_SECONDS", "120")),
                http_host=os.environ.get("REGEN_HTTP_HOST", "0.0.0.0"),
                http_port=int(os.environ.get("REGEN_HTTP_PORT", "8080")),
                log_level=os.environ.get("REGEN_LOG_LEVEL", "INFO").upper(),
            )
        except (ValueError, TypeError):
            raise ConfigurationError() from None

    def require_ready(self):
        if not self.api_key or not self.api_key.strip():
            raise ConfigurationError()
