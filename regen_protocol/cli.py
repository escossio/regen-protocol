import argparse
import json
import sys
from pathlib import Path

from regen_protocol.config import ConfigurationError, Settings
from regen_protocol.contracts import ContractError, validate_incident
from regen_protocol.engine import decide
from regen_protocol.policy import PolicyError
from regen_protocol.providers.base import ProviderError, ProviderTimeout
from regen_protocol.providers.openai import OpenAIProvider


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="REGEN stateless incident reasoning")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "decide"):
        command = commands.add_parser(name)
        command.add_argument("--incident", type=Path, required=True)
        if name == "decide":
            command.add_argument("--provider", choices=["openai"], required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    try:
        try:
            incident = json.loads(args.incident.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ContractError("incident") from None
        validate_incident(incident)
        if args.command == "validate":
            print("incident_valid", file=sys.stderr)
            return 0
        settings = Settings.from_env()
        settings.require_ready()
        with OpenAIProvider(settings) as provider:
            result = decide(incident, provider)
        print(json.dumps(result, allow_nan=False))
        return 0
    except ContractError as error:
        return _error(error.code, 2 if error.code == "invalid_incident" else 4)
    except PolicyError as error:
        return _error(error.code, 4)
    except ConfigurationError as error:
        return _error(error.code, 5)
    except ProviderTimeout as error:
        return _error(error.code, 6)
    except ProviderError as error:
        return _error(error.code, 3)
    except Exception:
        return _error("provider_failure", 3)


def _error(message: str, exit_code: int) -> int:
    print(message, file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
