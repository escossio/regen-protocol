from typing import Protocol


class ProviderError(Exception):
    code = "provider_failure"

    def __init__(self):
        super().__init__(self.code)


class ProviderTimeout(ProviderError):
    code = "provider_timeout"


class ReasoningProvider(Protocol):
    def decide(self, *, incident: dict, decision_schema: dict) -> dict: ...
