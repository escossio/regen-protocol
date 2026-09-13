# REGEN Reference Runtime V0 plan

1. Confirm published base, clean checkout, absent feature branch and valid V0
   contracts/fixtures. Create the feature branch without changing main.
2. Freeze the runtime design and self-review the boundaries before implementation.
3. Write RED tests in the eight requested test modules: contracts, policy, engine,
   CLI, HTTP, OpenAI, fixture acceptance and container contract. No live inference.
4. Implement the minimal provider interface, typed errors, normative validation,
   deterministic guard and stateless engine. Add OpenAI Responses adapter with
   strict output, store=false and SDK retries disabled. Implement configuration,
   CLI and HTTP using that same engine. Reach GREEN.
5. Package Python >=3.12 and unchanged schemas; add non-root Dockerfile, localhost
   Compose with read-only filesystem and no mounts/volumes, ignores and env example.
   Document protocol vs reference runtime and operational limits.
6. Run pytest, Ruff, compileall and diff checks. Build Compose without cache;
   inspect configuration/image without exposing environment secrets.
7. Start only the local service. Check health, readiness and isolation. If the
   environment supplies an API key, make exactly one fixture request, save its
   decision outside Git, validate schema/policy and review semantics. Otherwise
   report BLOCKED_MISSING_API_KEY; do not retrieve credentials elsewhere.
8. Restart only this container and recheck health/readiness without another model
   request. Confirm no persistent state/volumes. Review secrets and final diff.
9. Commit design/plan as `docs: define REGEN Reference Runtime V0`, then runtime,
   tests and README as `feat: add containerized REGEN Reference Runtime V0`.
   Push feature branch, open PR against main and stop without merging.

Acceptance evidence: test count, SDK version, one-call/no-retry tests, normative
schema identity, Docker smoke, missing-key or single-live-call result, restart
proof, clean branch and PR. Structural safety failures stop the workflow.
