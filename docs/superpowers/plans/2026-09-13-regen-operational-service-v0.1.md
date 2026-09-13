# V0.1 implementation plan

1. Verify V0 gates, correct PR evidence, merge normally and create fresh branch.
2. Validate /midia read-only as /dev/sdb1 RW with sufficient capacity.
3. Write failing SQLite/auth/audit/query/isolation tests before runtime changes.
4. Implement AuditStore and HTTP orchestration; keep core/schema unchanged.
5. Configure dedicated storage, token, LAN binding and secure Docker mount.
6. Run full pytest, Ruff, compileall, normative schema validation, secret/diff
   checks and no-cache Docker build before replacing only REGEN.
7. Smoke health/readiness; one authenticated fixture inference; validate its
   decision and audit detail/list. Restart and retrieve the same exchange.
8. Document results, commit, push and open V0.1 PR; do not merge.
