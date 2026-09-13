import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


class ContractError(Exception):
    def __init__(self, envelope: str):
        self.code = "invalid_incident" if envelope == "incident" else "invalid_decision"
        super().__init__(self.code)


def load_schema(name: str) -> dict:
    if name not in {"incident", "decision"}:
        raise ValueError("unknown schema")
    root = Path(__file__).resolve().parents[1] / "protocol/v0"
    if not root.is_dir():
        root = Path(sys.prefix) / "share/regen-protocol/protocol/v0"
    return json.loads((root / f"{name}.schema.json").read_text(encoding="utf-8"))


def _validate(data, name: str) -> None:
    try:
        # Reject Python-only values and non-finite numbers before schema checking.
        encoded = json.dumps(data, allow_nan=False)
        normalized = json.loads(encoded)
        if normalized != data:
            raise ValueError
        Draft202012Validator(load_schema(name), format_checker=FormatChecker()).validate(data)
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise ContractError(name) from None


def validate_incident(data) -> None:
    _validate(data, "incident")


def validate_decision(data) -> None:
    _validate(data, "decision")
