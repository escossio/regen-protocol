# Deferred ideas

These are candidates for separately designed future versions, not promises or
implemented V0 features. None grants REGEN memory, execution authority, or an
implicit right to use a capability.

- Source/destination addressing and correlation identifiers.
- Deadlines/TTL and canonical payload digest.
- Signing and cryptographic identity.
- Transport adapters, HTTP, queues, and event buses.
- Priorities and rate limits.
- Richer capability negotiation, including partial fulfillment and denial.
- Provider/model routing.
- Python and TypeScript SDKs.
- Replay/benchmark corpus.
- Evaluation of different models against identical incident fixtures.

Provider experiments must preserve the same wire contracts and caller policies.
Caller-managed replay data must not become implicit protocol memory.
