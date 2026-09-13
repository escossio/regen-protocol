class PolicyError(Exception):
    code = "policy_rejected"

    def __init__(self):
        super().__init__(self.code)


def guard(incident: dict, decision: dict) -> None:
    constraints, requires = incident["constraints"], decision["requires"]
    valid = (
        decision["protocol_version"] == incident["protocol_version"]
        and decision["incident_id"] == incident["incident_id"]
        and (constraints["mutation_allowed"] or not requires["mutation"])
        and (constraints["retry_allowed"] or not requires["retry"])
        and (not constraints["human_approval_required"] or requires["human"])
        and (decision["decision_class"] != "INVESTIGATE_READ_ONLY"
             or not (requires["mutation"] or requires["retry"]))
        and (decision["decision_class"] != "ESCALATE_HUMAN" or requires["human"])
    )
    prohibited = set(incident["capabilities"]["denied"]) | set(incident["capabilities"]["unavailable"])
    if not valid or prohibited.intersection(decision["requested_capabilities"]):
        raise PolicyError()
