# REGEN Reference Runtime V0

Date: 2026-09-13. Scope: Python >=3.12, Linux container, local reference runtime.

REGEN reasons. Controllers authorize. Executors act.

## Pipeline and authority

CLI and minimal HTTP are adapters of the same `engine.decide(incident, provider)`.
The core knows only a provider protocol, never FastAPI or OpenAI. Each invocation
validates the incident, passes a detached copy to exactly one provider call,
validates the candidate against the original decision schema, then runs the
deterministic Policy Guard. Invalid input causes zero model calls. A failed call
ends immediately: no retry, fallback, loop, routing, or tools.

The existing `protocol/v0/*.schema.json` files remain the only normative wire
contracts, validated with Draft 2020-12 and date-time checking. They are packaged
unchanged with the runtime. No Pydantic model replaces them. Schema failures,
provider errors/timeouts, policy violations and configuration errors are typed;
adapters expose fixed error codes only, never exception text or request content.

The guard rejects version/incident mismatches, forbidden mutation/retry, omitted
required human approval, read-only decisions requiring mutation/retry, escalation
without human approval, and requests for denied/unavailable capabilities. It does
not repair a candidate or grant authority. Natural-language correctness still
requires caller review; a boolean policy guard cannot prove a root cause.

## Provider

OpenAI is the first reference provider, not a protocol requirement. Default model
`gpt-6-astra`, effort `high` (allowed: low, medium, high, xhigh, max), timeout 120s.
Use Responses with strict JSON Schema `text.format`, `store=False`, no tools,
conversation, previous_response_id, background mode or streaming. Instantiate the
SDK with `max_retries=0`; one HTTP request produces at most one model request.
Incomplete, refused, malformed or non-object output is rejected. A provider-local
schema copy removes only the `$schema` dialect annotation; required fields,
closure, enum values and numeric bounds remain intact. Final validation always
uses the original schema. No reasoning summary is requested from the API.

Instructions require a self-contained incident, observable rationale only,
acknowledged uncertainty and respect for constraints and capability denials.
Private chain-of-thought is never requested, returned or persisted by the runtime.

API verification: SDK 3.13.0 inspected locally; official references:
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/models/gpt-6-astra

## Adapters and configuration

`GET /health` is always 200; it does not instantiate a provider. `GET /ready`
checks configuration only, returning 200 or 503 without a network request.
`POST /v0/decide` accepts raw JSON and delegates to the engine. Status mapping:
400 invalid incident, 422 policy violation, 502 provider/decision contract failure,
503 unavailable configuration, 504 timeout. Errors contain only `error` codes.
Documentation/OpenAPI endpoints are disabled; there is no authentication in V0.

CLI: validate or decide from a file; JSON decision only on success stdout.
Exit codes: 0 success, 2 input, 3 provider, 4 decision/policy, 5 config, 6 timeout.
Configuration uses only the declared environment variables. The key is external,
excluded from repr/logging and never baked into an image. Missing key permits
health and offline validation but prevents inference. HTTP defaults to
0.0.0.0:8080 inside the container; host publication is localhost:18200.

## Stateless container

No persistent state, history, sessions, databases, queues, caches of incidents,
or execution capabilities. Callers own history and execution. Per-request clients
are closed; request bodies and candidates are not logged. The container is
non-root, read-only, with ephemeral /tmp, dropped capabilities and
no-new-privileges. No persistent volume, Docker socket, host HOME, project or SSH
mounts. No external deployment, integration or execution authority is added.

## Acceptance and self-review

TDD covers schemas, every guard rule, one-call/no-retry behavior (including actual
SDK mock transport), sanitized adapters, fixture 0001 and static container safety.
Local tests/lint/compile precede image build and health/readiness smoke. A live
fixture call is allowed exactly once only with a supplied key and green gates;
missing key blocks live acceptance without searching other projects. Restart
smoke must work without an incident store. Provider stateless request parameters
do not claim zero retention outside the runtime beyond the API's documented policy.

Self-review: schemas remain unchanged; provider cannot mutate caller constraints
through the supplied object; HTTP/CLI share engine and error taxonomy; SDK retries
are explicitly disabled; packaging includes normative schemas; no authority or
persistence path is introduced. Live semantic correctness remains unproven when
credentials are absent. No expansion beyond the user-approved scope is needed.
