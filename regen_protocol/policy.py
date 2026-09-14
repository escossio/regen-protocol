class PolicyError(Exception):
    code = "policy_rejected"

    def __init__(self, reason_code):
        if reason_code not in POLICY_REASON_CODES:
            raise ValueError("invalid policy rejection reason")
        self.reason_code = reason_code
        super().__init__(self.code)


POLICY_REASON_CODES = frozenset(
    {
        "POLICY_REJECTED_PROTOCOL_MISMATCH",
        "POLICY_REJECTED_INCIDENT_IDENTITY_MISMATCH",
        "POLICY_REJECTED_MUTATION_NOT_ALLOWED",
        "POLICY_REJECTED_RETRY_NOT_ALLOWED",
        "POLICY_REJECTED_HUMAN_REQUIREMENT_MISMATCH",
        "POLICY_REJECTED_READ_ONLY_REQUIRES_MUTATION_OR_RETRY",
        "POLICY_REJECTED_INVALID_HUMAN_ESCALATION_REQUIREMENT",
        "POLICY_REJECTED_REQUESTED_DENIED_CAPABILITY",
        "POLICY_REJECTED_REQUESTED_UNAVAILABLE_CAPABILITY",
    }
)


def guard(incident: dict, decision: dict) -> None:
    constraints, requires = incident["constraints"], decision["requires"]
    if decision["protocol_version"] != incident["protocol_version"]:
        raise PolicyError("POLICY_REJECTED_PROTOCOL_MISMATCH")
    if decision["incident_id"] != incident["incident_id"]:
        raise PolicyError("POLICY_REJECTED_INCIDENT_IDENTITY_MISMATCH")
    if requires["mutation"] and not constraints["mutation_allowed"]:
        raise PolicyError("POLICY_REJECTED_MUTATION_NOT_ALLOWED")
    if requires["retry"] and not constraints["retry_allowed"]:
        raise PolicyError("POLICY_REJECTED_RETRY_NOT_ALLOWED")
    if constraints["human_approval_required"] and not requires["human"]:
        raise PolicyError("POLICY_REJECTED_HUMAN_REQUIREMENT_MISMATCH")
    if decision["decision_class"] == "INVESTIGATE_READ_ONLY" and (
        requires["mutation"] or requires["retry"]
    ):
        raise PolicyError("POLICY_REJECTED_READ_ONLY_REQUIRES_MUTATION_OR_RETRY")
    if decision["decision_class"] == "ESCALATE_HUMAN" and not requires["human"]:
        raise PolicyError("POLICY_REJECTED_INVALID_HUMAN_ESCALATION_REQUIREMENT")
    requested = set(decision["requested_capabilities"])
    if requested.intersection(incident["capabilities"]["denied"]):
        raise PolicyError("POLICY_REJECTED_REQUESTED_DENIED_CAPABILITY")
    if requested.intersection(incident["capabilities"]["unavailable"]):
        raise PolicyError("POLICY_REJECTED_REQUESTED_UNAVAILABLE_CAPABILITY")
