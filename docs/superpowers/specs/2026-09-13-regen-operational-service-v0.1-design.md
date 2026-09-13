# Operational Service V0.1

The caller owns reasoning history. The service may own operational audit history.
Audit history is observable service data. It is never implicit reasoning context.

## Scope and boundaries

Preserve Protocol V0 schemas, engine, policy and provider interfaces. Only HTTP
owns AuditStore. Each provider invocation receives only the current incident.
No retrieval, ORM, retention scheduler, integrations, UI or automatic execution.

## Audit and failures

SQLite stdlib, user_version=1, one exchanges table with UUID identifiers, UTC
timestamps, source/incident/decision identifiers, status, provider/model, duration,
HTTP/error metadata and validated JSON envelopes. Index time, incident, source,
class and status. Each operation uses its own connection and transaction;
synchronous=FULL. Reject unsupported database versions. No schema auto-upgrade.

Authentication and incident validation precede insertion. Commit RECEIVED before
provider creation/call; store failure prevents inference. Update the same row once
to COMPLETED, PROVIDER_ERROR, PROVIDER_TIMEOUT, DECISION_REJECTED or CONFIG_ERROR.
Finalization failure returns audit_failure and keeps the transaction uncommitted;
log only a fixed code. No provider retry. RECEIVED rows remain observable after crashes.

Store only envelopes and selected metadata, never transport headers, prompts,
raw provider responses or exceptions. Reject envelopes containing sensitive field
names or credential material before persistence, including configured secrets;
reject unsafe decisions before storage/return. Callers must sanitize their data;
this deterministic screen is not a guarantee against arbitrary encoded secrets.

## HTTP

Bearer authentication uses constant-time comparison; all three /v0 routes require
REGEN_API_TOKEN, without a default. Health is public; readiness also verifies key,
token, configuration and a SQLite write transaction rolled back without fake rows.
Decision body remains normative; X-REGEN-Exchange-ID identifies the audit record,
including terminal errors. List returns metadata only, newest first, limit 1..100,
offset >=0 and parameterized filters. Detail returns envelopes; missing ID is 404.

## Deployment

Only /midia/regen-protocol mounts RW at /data; SQLite defaults to
/data/regen-audit.sqlite3. /midia must be the separate /dev/sdb1 RW mount.
Non-root UID/GID, read-only root, ephemeral /tmp, dropped capabilities and no-new-privileges.
Compose defaults to localhost; approved local deployment binds 192.168.88.2:18210.
No host project/socket mounts, public NAT, TLS changes or other container changes.
Secrets remain in ignored mode-0600 deployment .env. Audit has no automatic retention.

## Acceptance

TDD for SQLite transactions, HTTP auth/error/audit paths, queries and cognitive
isolation. Existing offline gates remain green. Exactly one new live fixture call,
then authenticated detail/list and restart persistence proof; no second inference.
Self-review: persistent operational records never flow into the reasoning core.
