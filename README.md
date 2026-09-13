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

V0 consists only of [incident](protocol/v0/incident.schema.json) and
[decision](protocol/v0/decision.schema.json) JSON Schemas (Draft 2020-12), the
[design](docs/superpowers/specs/2026-09-13-regen-protocol-v0-design.md), and a
[real incident fixture](fixtures/0001-codex-task7-remediation-exhausted/incident.json)
with an [expected decision](fixtures/0001-codex-task7-remediation-exhausted/expected-decision.json).
The fixture leaves the root cause unknown and proposes read-only investigation.

There is no AI runtime, API, SDK, database, execution engine, or supervisor
integration. [Future ideas](FUTURE.md) are deferred, not capabilities of V0.

Schema validation checks structure, not truth or authority. Callers must enforce
their policies and constraints before acting on any decision. Validate timestamps
with a Draft 2020-12 validator configured to check `date-time` formats.

Licensed under the [MIT License](LICENSE).
