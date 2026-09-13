# REGEN Protocol

REGEN is a stateless protocol for regenerative incident reasoning.

It receives a self-contained incident envelope and produces a structured decision envelope.

REGEN does not execute actions, own caller history, grant capabilities, or mutate the caller environment.

**REGEN reasons. Controllers authorize. Executors act.**

The conceptual cycle is:

```text
Incident
→ Decision
→ caller evaluates requested capabilities/actions
→ new evidence or constraints
→ new Incident
→ regenerated Decision
```

Every request is independent. Callers own history and execution authority; the
protocol has no implicit context or memory between calls. A new request may
include previous decisions and evidence explicitly, but nothing is recalled
automatically. Knowledge does not imply authority. Capability requests may be
denied, unavailable, or only partially satisfied.

Implementations may use any reasoning provider. Provider/model choice is outside
the wire contract. Only observable evidence and a structured rationale summary
are exchanged; private chain-of-thought is neither required nor persisted.

## Protocol V0

The normative V0 contract consists of [incident](protocol/v0/incident.schema.json) and
[decision](protocol/v0/decision.schema.json) JSON Schemas (Draft 2020-12), the
[design](docs/superpowers/specs/2026-09-13-regen-protocol-v0-design.md), and a
[real incident fixture](fixtures/0001-codex-task7-remediation-exhausted/incident.json)
with an [expected decision](fixtures/0001-codex-task7-remediation-exhausted/expected-decision.json).
The fixture leaves the root cause unknown and proposes read-only investigation.

The protocol is independent of the reference runtime below. No provider choice
changes its wire contract. There is no database, session store, execution engine
or supervisor integration. [Future ideas](FUTURE.md) do not expand V0 authority.

Schema validation checks structure, not truth or authority. Callers must enforce
their policies and constraints before acting on any decision. Validate timestamps
with a Draft 2020-12 validator configured to check `date-time` formats.

## Reference Runtime V0

Python >=3.12 reference implementation: normative input validation → shared engine
→ one reasoning provider call → normative output validation → deterministic
Policy Guard → accepted DecisionEnvelope. CLI and HTTP use this exact pipeline.
OpenAI is the reference provider, not a requirement of the protocol.

The default configurable model is `gpt-6-astra` with reasoning effort `high`.
Responses use strict Structured Outputs and `store=false`; the SDK has
`max_retries=0`. No tools, conversation, previous response, streaming, automatic
retry, fallback, or model routing is used. Any failure ends that request.

The guard rejects identity/version mismatches, forbidden mutation/retry,
missing human approval and denied/unavailable capability requests. It never
repairs output or executes a decision. Semantic adequacy remains a caller review
responsibility: schema validity and confidence do not establish a root cause.

### Docker quickstart

```bash
docker compose build regen
docker compose up -d regen
curl http://127.0.0.1:18200/health
curl -i http://127.0.0.1:18200/ready
```

The service is published only on localhost by default, with no HTTP authentication
or TLS in this version. Do not expose it publicly. It uses a non-root user,
read-only filesystem, ephemeral `/tmp`, no-new-privileges and all capabilities
dropped. No host project, Docker socket, credential directory or persistent volume
is mounted. Restart policy is `unless-stopped`.

Supply `OPENAI_API_KEY` through your external secret configuration when inference
is authorized. Compose reads environment substitution; a local `.env` is ignored
by Git and Docker. Do not place a real key in shell examples, Git or the image.
Without a key, health is 200, readiness is 503, and decisions fail closed without
a model request. Readiness verifies configuration, not account quota/model access.
Do not dump `docker compose config` or container environment with a real key set.

Configuration:

| Variable | Default |
| --- | --- |
| `OPENAI_API_KEY` | absent |
| `REGEN_OPENAI_MODEL` | `gpt-6-astra` |
| `REGEN_OPENAI_REASONING_EFFORT` | `high`; low/medium/high/xhigh/max allowed |
| `REGEN_OPENAI_TIMEOUT_SECONDS` | `120` |
| `REGEN_HTTP_HOST` | `0.0.0.0` inside container |
| `REGEN_HTTP_PORT` | `8080` inside container |
| `REGEN_HOST_PORT` | `18200` on localhost (Compose) |
| `REGEN_LOG_LEVEL` | `INFO` |

Compose fixes the internal port at 8080; use REGEN_HOST_PORT to select another
localhost port. Direct Python launch honors HTTP host/port settings.

### HTTP

- `GET /health`: 200 `{"status":"ok"}`, no provider call.
- `GET /ready`: 200 `{"status":"ready"}` or 503 `{"status":"not_ready"}`.
- `POST /v0/decide`: raw IncidentEnvelope in, accepted DecisionEnvelope out.

After configuration and explicit authorization, a single inference request is:

```bash
curl --max-time 130 --silent --show-error \
  -H 'Content-Type: application/json' \
  --data-binary @fixtures/0001-codex-task7-remediation-exhausted/incident.json \
  http://127.0.0.1:18200/v0/decide
```

No client retry is implied. Error bodies contain only `{"error":"stable_code"}`:
400 invalid incident, 422 policy rejection, 502 provider or output-contract
failure, 503 missing/invalid configuration, 504 provider timeout. Raw responses,
request bodies, credentials, tracebacks and private reasoning are not returned.

### CLI and development

```bash
python -m pip install '.[dev]'
python -m regen_protocol.cli validate --incident fixtures/0001-codex-task7-remediation-exhausted/incident.json
python -m regen_protocol.cli decide --incident fixtures/0001-codex-task7-remediation-exhausted/incident.json --provider openai
```

`validate` is offline. `decide` makes at most one model request and prints only
the accepted JSON decision to stdout. Sanitized status/errors go to stderr.
Exit codes: 0 success, 2 invalid incident, 3 provider failure, 4 decision/policy
rejection, 5 configuration error, 6 timeout.

```bash
python -m pytest -q
ruff check .
python -m compileall -q regen_protocol tests
git diff --check
```

Tests are offline and include the real SDK with mock transport. Fixture 0001 fake
acceptance does not imply live model acceptance. Missing credentials block the
live check rather than authorizing key discovery in another project.

### Statelessness and limits

No incident or decision is retained between calls. Callers must explicitly supply
any history they want considered. Restart needs only configuration, not previous
incidents. There are no databases, caches of decisions, queues, sessions, or
volumes. `store=false` is the Responses storage setting; it does not assert a
broader data-retention guarantee for the external provider.

No decision is automatically executed. There is no integration with Andy Codex
Supervisor or Attention Router. Runtime design and plan are in
[the design delta](docs/superpowers/specs/2026-09-13-regen-reference-runtime-v0-design.md)
and [implementation plan](docs/superpowers/plans/2026-09-13-regen-reference-runtime-v0.md).

Licensed under the [MIT License](LICENSE).
