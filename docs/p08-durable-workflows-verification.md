# P08 Durable Workflow Verification

## Delivered behavior

Phase P08 composes the existing P03-P07 domain services into `drive-lifecycle-v1`, a durable human-supervised LangGraph workflow. The graph stores scoped identifiers and versions only. Original files, full cohorts, tokens, signed URLs, and raw communication bodies remain in their existing domain stores rather than checkpoint state.

The coordinator can start a run from the drive workflow screen and observe intake, clarification, policy approval, deterministic evaluation, publication, communication approval, and monitoring checkpoints. Existing approval and clarification endpoints atomically create deduplicated workflow resume commands. A tenant-scoped relay publishes those intents; a trusted worker resolves the opaque thread mapping and resumes only after validating the canonical domain reference. No public endpoint accepts LangGraph `Command`, a thread UUID, or checkpoint data.

Monitoring accepts small persisted event envelopes for registration, document, policy, deadline, and dispatch changes. Unique event keys prevent duplicate handling. Each event uses a bounded handler and returns to the monitoring interrupt without replaying JD interpretation or announcement creation. Operational holds block new workflow execution while preserving completed history and pending events. The exception inbox surfaces unresolved input, stale/rejected approval, delivery uncertainty, failed execution, and incompatible graph-version cases with an owner and recorded actions.

## Persistence and recovery boundaries

- Institution-scoped `workflow_runs`, `workflow_commands`, `workflow_events`, and `exception_cases` use the application database, row-level security, and explicit drive authorization.
- LangGraph checkpoints use a private schema and a separate no-bypass role. Run authorization occurs before the thread UUID is read or used.
- Checkpoint serialization disables pickle fallback and permits no arbitrary MessagePack modules.
- The domain transaction and checkpoint transaction are deliberately not represented as atomic. Idempotent domain lookups recover a domain-ahead gap; durable command replay and command markers recover decision/checkpoint coordination gaps.
- Broker failure leaves commands pending with bounded backoff. A stale claimed command is relayable after its lease window.
- Only `drive-lifecycle-v1` / state schema `1` is currently compatible. Unknown versions stop as `incompatible` and open a case.

## Verification scenarios

The P08 integration suite exercises:

1. Fresh accepted source to persisted clarification interrupt, authenticated resolution, policy proposal interrupt, exact approval resume, deterministic evaluation, and publication-input case.
2. A process-independent checkpoint connection reopening and reaching monitoring using the same P04/P05/P06/P07 artifacts and approvals.
3. Duplicate and concurrent monitoring events, proving one handling result per event and no intake replay.
4. Operational hold, event preservation during the hold, release, and subsequent processing.
5. Cross-institution workflow lookup denial and absence of thread UUIDs in public responses.
6. Duplicate command execution returning the persisted result without duplicating domain effects.
7. An unknown graph version stopping with an owned exception case instead of blind resume.

The normal phase gate runs the backend suite, Ruff, Mypy, contract drift, API-client TypeScript, Next lint/build, the P08-to-P07-to-P08 Alembic cycle, and the idempotent checkpoint setup command.

## Honest limits

The monitoring handlers update bounded event-processing evidence and open deterministic baseline cases; advanced multi-step impact analysis and proposed recovery plans remain P12. Closure is intentionally deferred to P09. The fixture JD interpreter, development document scanner, and Mailpit transport remain visible local-development adapters and are not production integrations.
