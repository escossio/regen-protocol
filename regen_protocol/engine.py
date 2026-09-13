from copy import deepcopy

from regen_protocol.contracts import load_schema, validate_decision, validate_incident
from regen_protocol.policy import guard
from regen_protocol.providers.base import ProviderError, ProviderTimeout, ReasoningProvider


def decide(incident: dict, provider: ReasoningProvider) -> dict:
    validate_incident(incident)
    trusted_incident = deepcopy(incident)
    try:
        candidate = provider.decide(
            incident=deepcopy(trusted_incident), decision_schema=load_schema("decision")
        )
    except ProviderError:
        raise
    except TimeoutError:
        raise ProviderTimeout() from None
    except Exception:
        raise ProviderError() from None
    validate_decision(candidate)
    guard(trusted_incident, candidate)
    return candidate
