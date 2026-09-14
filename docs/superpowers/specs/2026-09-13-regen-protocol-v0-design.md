# REGEN Protocol V0 Design

Date: 2026-09-13

Scope: frozen V0 envelopes, documentation, and fixture only.

## 1. Purpose

REGEN is a protocol-first, stateless protocol for regenerative incident reasoning
under explicitly declared capabilities and constraints. It interprets an incident
and proposes the next decision. It neither executes that decision nor grants the
authority to execute it.

**REGEN reasons. Controllers authorize. Executors act.**

## 2. Core principles

- Every request is independent and self-contained.
- REGEN has no memory between calls, sessions, or implicit context.
- The caller owns history, capabilities, policies, and execution authority.
- Knowledge does not imply authority.
- Capability requests may be denied, unavailable, or partially fulfilled.
- A caller may provide previous results in a new incident to request regeneration.
- Explanations contain observable evidence and a concise rationale summary.
- Private chain-of-thought must not be required or persisted.
- Implementations may use any reasoning provider; model selection is outside V0.

## 3. Stateless contract

One self-contained IncidentEnvelope yields one DecisionEnvelope. Neither envelope
implicitly refers to a server-side conversation. `incident_id` associates a
decision with the submitted incident; it does not authorize hidden history lookup.
The caller checks that the returned identifier matches its request.

V0 uses JSON Schema Draft 2020-12. Top-level objects reject unknown fields. Required
nested contract objects also reject unknown fields except `state` and `facts`,
which intentionally support caller-specific structured JSON. Arrays may be empty.
Validators must enable `date-time` format checking. Schema validation alone does
not establish factual accuracy, evidence sufficiency, or policy compliance.

## 4. Caller-owned history

The caller decides which prior outcomes, evidence, and constraints to include in
a subsequent request, for example as explicitly named data in `facts`. REGEN does
not retrieve or store them between calls. A denial or partial capability result
can become evidence in the next independent incident. The caller must sanitize
that context and avoid private reasoning or sensitive material.

## 5. IncidentEnvelope V0

The normative structural contract is `protocol/v0/incident.schema.json`.

All top-level fields are required:

- `protocol_version`: string constant `"0"`.
- `message_type`: string constant `"INCIDENT"`.
- `incident_id`: non-empty string.
- `source`: required non-empty `system`, optional string `instance`.
- `occurred_at`: RFC 3339 date-time string.
- `summary`: non-empty incident summary.
- `state`: required non-empty `status` and string-or-null `phase`; caller-specific fields are allowed.
- `facts`: structured facts asserted by the caller; arbitrary JSON properties are allowed.
- `unknowns`: array of strings naming evidence gaps.
- `capabilities`: required `available`, `denied`, and `unavailable` string arrays.
- `constraints`: required boolean `mutation_allowed`, `retry_allowed`, and `human_approval_required`.
- `desired_outcome`: non-empty string describing the caller's intended result.

The caller remains responsible for the meaning and scope of capability names.
Availability is not unrestricted authority and cannot override a constraint.
`retry_allowed` governs reissuing an operation whose effect identity already
exists, whether its result is known or uncertain. It does not govern a new
caller-bound capability action with a new fingerprint, durable intent,
execution identity, and result. Provider transport retries and later REGEN
rounds are separate mechanisms; neither is authorized by this flag.

## 6. DecisionEnvelope V0

The normative structural contract is `protocol/v0/decision.schema.json`.

All top-level fields are required:

- `protocol_version`: string constant `"0"`.
- `message_type`: string constant `"DECISION"`.
- `incident_id`: non-empty string semantically matching the received incident.
- `decision_id`: non-empty decision identifier.
- `decision_class`: exactly one of `CONTINUE_DETERMINISTIC`, `INVESTIGATE_READ_ONLY`, `REQUEST_CONTEXT`, `REQUEST_CAPABILITY`, `ESCALATE_HUMAN`.
- `summary`: short, non-empty decision summary.
- `rationale_summary`: non-empty justification using observable facts, not private chain-of-thought.
- `requested_evidence` and `requested_capabilities`: string arrays of proposals for caller evaluation.
- `alternatives`: objects with required non-empty `label`, non-empty `summary`, and numeric `confidence` in [0, 1].
- `confidence`: numeric confidence in the proposed decision in [0, 1], not proof of a root cause.
- `resilience`: required boolean `fallback_available` and string `summary`.
- `requires`: required boolean `mutation`, `retry`, and `human`.
- `recommended_next_step`: non-empty proposed next step, never automatic execution.

Decision classes categorize proposals, not permissions. Even a deterministic
continuation requires caller evaluation. An implementation must acknowledge
insufficient evidence rather than inventing a cause.

## 7. Capability/authority separation

The caller evaluates every proposed action and evidence request against its own
capabilities and policies. REGEN cannot upgrade availability, override a denial,
waive human approval, or expand authority through a recommendation. `requires`
describes what a proposal needs; it does not change the incident's constraints.
If required authority is missing, the caller may reject the proposal or return a
new incident with the denial and ask for a different decision.

## 8. Fixture 0001

`fixtures/0001-codex-task7-remediation-exhausted/` records a real supervised Task 7
acceptance that ended in `BLOCKED` with `REMEDIATION_BUDGET_EXHAUSTED`. Three Codex
cycles and two remediations were consumed. `VERIFY_LOCAL` was never reached.
There were no changed paths, candidate SHA, PR, or merge. The worktree remained
clean and HEAD remained at the base SHA. The original worker failure was not
preserved, and no last-message was available.

The public fixture includes only necessary operational facts. Internal paths,
credentials, personal data, and raw command output are excluded. Its timestamp
is the recorded final checkpoint time.

The expected decision is `INVESTIGATE_READ_ONLY`, with high but non-certain
confidence in the investigation strategy. It requests state, journal, runtime
inventory, Codex CLI/readiness and attempt-window metadata, and worktree evidence.
No new attempt, mutation, or human approval is required by the proposal. The
caller must still authorize each read. Root cause is explicitly unknown; missing
metadata may require a context request instead of a diagnosis.

The expected decision is a contract example, not evidence that REGEN ran, an
implementation-generated output, or an integration with the source supervisor.

## 9. Security boundary

Treat incident content and proposed decisions as data, not executable authority.
Do not include credentials, API keys, private environment inventories, personal
data, or private chain-of-thought. Evidence should be minimized and sanitized.
REGEN must not infer permission from knowledge, confidence, source names, or
instructions embedded in evidence. The controller enforces access, mutation,
retry, and human-review boundaries independently.

V0 has no transport, authentication, signing, or execution implementation. It
makes no claim that a source identifier cryptographically authenticates a caller.

## 10. Explicit non-goals

The following are deferred and not implemented in V0:

- HTTP API; Python SDK; TypeScript SDK.
- Persistent storage; sessions; conversation memory.
- Event bus; streaming; message fragmentation.
- TTL/deadline protocol; payload signing; cryptographic identity; CRC/checksum protocol.
- Priorities/severity negotiation; rate limiting.
- Model routing; multi-model ensemble; semantic retrieval.
- Automatic execution; automatic capability granting; supervisor integration.

No AI runtime, server, database, or action executor is part of this bootstrap.

## 11. V0 acceptance criteria

1. Both schemas are valid JSON Schema Draft 2020-12 documents.
2. All JSON parses and both fixture envelopes validate against their schemas, with date-time checking.
3. Required fields, closed contract objects, exact decision classes, and confidence bounds are enforced.
4. Fixture identifiers match; its decision respects mutation/retry constraints and admits insufficient evidence.
5. Public artifacts contain no credential material, private environment addresses, unnecessary sensitive paths, or personal data.
6. The final tree contains only the two schemas, two fixture envelopes, README, MIT LICENSE, FUTURE, and this design.
7. Git whitespace checks pass and the public repository has a clean `main` matching the published commit.

V0 acceptance does not authorize any subsequent implementation or execution phase.
