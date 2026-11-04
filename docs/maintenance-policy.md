# PlacementOS maintenance policy

This policy applies to the synthetic implementation baseline and becomes an operational policy only after an institution assigns owners, review cadence, and production change authority.

## Review cadence

| Area | Baseline cadence | Required evidence |
| --- | --- | --- |
| Security advisories and exposed dependencies | Weekly and before release | Lockfile diff, advisory review, relevant regression tests |
| Routine dependency updates | Monthly | Official compatibility notes, targeted tests, full checks before merge |
| API and client contracts | Every API change | Additive-versus-breaking classification, exported OpenAPI, drift check |
| Database migrations and restore | Every schema release; restore drill at least quarterly for a pilot | Empty/upgrade rehearsal, downgrade boundary, isolated restore report |
| Durable workflow graph versions | Every graph change | Waiting-run inventory, compatibility/migration decision, restart/replay tests |
| Retention and deletion configuration | Quarterly and whenever institution policy changes | Approved owner, configured periods, tombstone/restore evidence |
| Institution operating limits | Before onboarding and after measured capacity changes | Revision reason, tenant-scoped benchmark, alert/queue review |

## Compatibility rules

- Prefer additive versioned contracts. Do not remove or reinterpret an existing field or endpoint inside the current API version.
- Eligibility and schedule semantic changes require a new immutable policy/contract version and regression tests for old versions.
- Alembic is the only production schema path. Rehearse the migration against an empty database and an upgrade database; never rely on runtime `create_all`.
- A workflow graph release must preserve or explicitly migrate durable waiting runs. Unknown graph versions fail visibly rather than resuming with new semantics.
- External provider and model SDK upgrades require current official documentation review and fake-boundary tests before isolated live acceptance.

## Operational change controls

- Institution configuration is revisioned and attributed. Administrators may manage configuration only through explicit capabilities; they do not inherit coordinator approvals.
- Capacity limits change from measured demand, not speculative scale. Record the before/after benchmark and keep rollback as a new configuration or application revision.
- Security, privacy, backup, or retention changes require the relevant runbook and readiness gate to be updated in the same change.
- Keep synthetic development defaults visibly synthetic. Never use a maintenance task to enable live sending, connect an account, load real records, or deploy without specific authority.

## End-of-life and rollback

Before removing a contract, dependency, graph version, or migration path, inventory active consumers and durable records, publish the replacement window, and retain a tested rollback or forward-fix procedure. Database rollback must not discard records created by the newer release. Provider effects are reconciled, not undone by replay.
