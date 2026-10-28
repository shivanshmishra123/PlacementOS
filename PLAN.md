# PlacementOS: Implementation Plan

> Baseline dated 28 October 2026. This plan describes work to perform. The repository begins with three source inputs and four planning documents; it does not yet contain an application, infrastructure, tests, or live integrations.

## 1. How to execute this plan

Read [Agents.md](Agents.md), [PROJ_SPECIFICATION.md](PROJ_SPECIFICATION.md), and [Architecture.md](Architecture.md) before starting a phase. The specification defines behavior; architecture defines technical contracts; this file defines delivery order and evidence of completion.

Use task IDs in change summaries and review notes. Complete dependency-ready tasks in small, working slices. A checked box means the deliverable exists and its verification passed. It does not mean a design was discussed, a UI was mocked, or a dependency was installed.

The current request creates these references only. Do not interpret the checklist as authorization to start implementation, create provider accounts, spend money, deploy infrastructure, or send real messages. Once implementation is requested, routine reversible coding and local verification within that scope can proceed without repeated approval questions. Product approval gates are implemented application behavior.

### 1.1 Status and evidence convention

- `[ ]` = not complete. Add `in progress` or a blocker note beside the task when appropriate.
- `[x]` = completed with implementation/document evidence and relevant checks.
- If partially delivered, keep the parent task unchecked and describe the missing behavior.
- If scope changes, update requirements and architecture before marking an incompatible implementation complete.
- Record blocked dependencies with a concrete owner/input and continue independent authorized work.
- Maintain concise phase evidence: change reference, commands/checks and result, demonstrated scenario, open limitations, and next task.

No application task is marked complete in this baseline. The existence of these reference files does not mean P00's configuration/contract decisions or later phase gates have been satisfied.

### 1.2 Global definition of done

A phase is complete when its user-visible deliverable works, relevant backend permissions and state transitions are enforced, migrations/contracts are current, meaningful checks pass, failure/recovery behavior is exercised where relevant, and documentation accurately states the remaining limits. Never check off a feature that uses fixtures while presenting it as a live integration.

Security, audit, accessibility, error handling, and revision semantics are part of each slice. P10 consolidates and exercises them; it is not the first point at which they are added.

## 2. Milestones and dependencies

| Milestone | Phases | Demonstrable outcome |
| --- | --- | --- |
| M0: foundations | P00-P02 | Reproducible environment, scoped sign-in, verified student records. |
| M1: reviewed intelligence | P03-P05 | Source-backed JD review and reproducible eligibility for a cohort. |
| M2: participation and controlled actions | P06-P08 | Student registration/documents, exact approvals, safe mail, persistent workflow pauses. |
| M3: complete local MVP | P09 | Scheduling, recorded/published results, closure and reproducible report. |
| M4: pilot readiness | P10 | Demonstrated recovery, security, operational setup, and real-data readiness decisions. |
| M5: external connectors | P11 | Approved Gmail/Sheets/Calendar operations with reconciliation. |
| M6: adaptive recovery | P12 | Explainable exception impact plans and approved controlled execution. |
| M7: evidence-driven expansion | P13 | Broader rollout or scale improvements justified by measured needs. |

```mermaid
flowchart TD
    P00[P00 Contracts and decisions] --> P01[P01 Repository and infrastructure]
    P01 --> P02[P02 Identity and student data]
    P02 --> P03[P03 Source intake and extraction]
    P03 --> P04[P04 JD intelligence and rule review]
    P02 --> P05[P05 Eligibility engine]
    P04 --> P05
    P05 --> P06[P06 Student documents and registration]
    P06 --> P07[P07 Proposals and notification execution]
    P07 --> P08[P08 Durable orchestration]
    P08 --> P09[P09 Scheduling results and closure]
    P09 --> P10[P10 MVP hardening and pilot gate]
    P10 --> P11[P11 Live Google connectors]
    P10 --> P12[P12 Advanced exception recovery]
    P11 --> P13[P13 Measured rollout and scaling]
    P12 --> P13
```

P11 and P12 can be independent after P10, except connector-specific exception cases require the relevant connector. This diagram expresses dependencies, not permission to delegate work to other agents. Do not start several feature branches simultaneously merely because they are technically independent.

## 3. Phase summary

| Phase | State | Primary requirements | Exit artifact |
| --- | --- | --- | --- |
| P00 | Not started; planning references authored | Scope and invariants | Agreed executable contracts and decision register. |
| P01 | Not started | FR-INT-01/02 foundations; NFR-03/09/12 | Reproducible monorepo and local services. |
| P02 | Not started | FR-ID, FR-STU, FR-AUD foundation | Scoped identities and verified student dataset. |
| P03 | Not started | FR-JD; FR-DOC security foundation | Private source ingestion and located extracted text. |
| P04 | Not started | FR-AI-JD, FR-POL, initial FR-APP | Reviewed JD and immutable approved rules. |
| P05 | Not started | FR-ELIG, NFR-01 | Reproducible cohort results and explanations. |
| P06 | Not started | FR-DOC, FR-REG | Functional student participation journey. |
| P07 | Not started | FR-COM, FR-APP, FR-DISP | Exact approved communications and durable dispatch. |
| P08 | Not started | FR-WF, baseline FR-EXC | Persistent end-to-end orchestration. |
| P09 | Not started | FR-SCHED, FR-RESULT, FR-REPORT, FR-CLOSE | Complete local recruitment lifecycle. |
| P10 | Not started | Cross-cutting NFRs, privacy, real-data gate | Verified MVP release and documented pilot readiness. |
| P11 | Not started; post-MVP | FR-INT-03 through FR-INT-09 | Reconciled live Google integrations. |
| P12 | Not started; advanced | FR-EXC-04 through FR-EXC-07 | Approved recovery plans for changing information. |
| P13 | Not started; demand-driven | Measured expansion | Reliable operation at demonstrated additional demand. |

Do not assign calendar dates before the developer's capacity and providers are known. Estimate each phase after its dependencies work. A sequence of verified milestones is more useful than unsupported delivery promises.

## 4. P00: Validate scope, contracts, and unresolved decisions

**Objective:** Make the initial implementation choices explicit without expanding the product. **Dependencies:** the three source inputs and these four references.

- [ ] **P00-T01: Validate source traceability.** Confirm the specification covers both diagrams and the written description. Resolve contradictions in terminology, especially the five responsibilities versus four AI components plus a deterministic engine. Evidence: reviewed source-to-requirement mapping.
- [ ] **P00-T02: Confirm the release boundary.** Adopt the complete local MVP through P09, with P10 pilot gating and P11/P12 extensions. Preserve basic scheduling/results in the MVP. Evidence: no core source workflow step is left without a phase.
- [ ] **P00-T03: Freeze initial state contracts.** Review lifecycle/status enums, unknown-first eligibility aggregation, document readiness, publication/approval distinctions, and deadline semantics. Evidence: shared schemas or contract examples ready for implementation.
- [ ] **P00-T04: Establish the decision register.** Record baselines for OIDC, branch/scale configuration, source trust, self-review, model/mail/scanner adapters, and retention. Mark production-only inputs as unresolved without blocking synthetic work.
- [ ] **P00-T05: Define synthetic acceptance fixtures.** Specify two institutions, coordinator/student personas, the Section 10.2 eligibility cohort, a normal JD, an ambiguous JD, and failure documents. Evidence: a fixture inventory with expected outcomes, no real personal data.
- [ ] **P00-T06: Confirm architecture and API conventions.** Adopt one backend authority, exact proposal approvals, outbox semantics, immutable source versions, and generated client contracts. Evidence: no alternative ORM/auth/queue architecture introduced incidentally.
- [ ] **P00-T07: Select the next vertical slice.** Turn P01/P02 into the first executable work batch, identify local runtime constraints on Windows, and define the initial sign-in/import demonstration. Evidence: runnable task order with concrete acceptance.

**Exit gate:** a developer can explain what is fixed by the source, what is a design baseline, and what needs institution input. No production provider purchase or access is required to proceed locally.

## 5. P01: Establish the repository and local development system

**Objective:** Make a reproducible, testable skeleton with the intended boundaries. **Dependencies:** P00. **Requirements:** architecture foundations and NFR-03/09/12.

- [ ] **P01-T01: Bootstrap the monorepo.** Create the planned web/backend/package/infra/fixture structure without generating all future modules as empty abstractions. Configure package/import paths and root workspace scripts. Evidence: clean-checkout setup can resolve both applications.
- [ ] **P01-T02: Verify and pin compatible versions.** Select supported Node/Python/PostgreSQL and compatible Next.js/FastAPI/LangGraph/Celery packages from official documentation. Commit JS/Python locks and container pins. Evidence: reproducible install and recorded compatibility choices.
- [ ] **P01-T03: Create local infrastructure.** Add Compose services for PostgreSQL, Redis, private S3-compatible storage, Mailpit, and optional scanner profile. Bind safely and provide synthetic credentials only. Evidence: health checks and persistence across container restart.
- [ ] **P01-T04: Add settings and migration foundation.** Validate required environment values, environment mode, database roles, Alembic paths, and initial migrations. Evidence: migration from empty DB and clear startup failure for invalid settings.
- [ ] **P01-T05: Create API and web shells.** Add versioned route registration, common error shape, health/readiness, role-neutral layouts, accessible base components, and API connectivity. Evidence: a real request renders a persisted/health response with a correlation ID.
- [ ] **P01-T06: Add contract generation.** Generate OpenAPI and a TypeScript client/types package; make generation deterministic and detect drift. Evidence: frontend consumes generated types rather than a parallel manual DTO.
- [ ] **P01-T07: Establish checks and safe defaults.** Configure lint/type checks, focused test runners, CI skeleton, secret-ignore rules, no-live-send defaults, and explicit development adapters. Evidence: checks execute and production mode rejects development identity/sending shortcuts.
- [ ] **P01-T08: Document and verify the developer interface.** Implement the commands listed in `Agents.md`/`Architecture.md`, including worker, relay, scanner, migrations, and seed entry points. Evidence: walkthrough on the supported Windows/WSL/container arrangement.

**Exit gate:** web and API run locally, database migrations are repeatable, private storage and mail sink are reachable, checks pass, and commands match the documentation. Redis and object storage do not yet imply any product workflow is complete.

## 6. P02: Implement identity, scope, and verified student records

**Objective:** Establish trusted institutional data and permissions before building AI features. **Dependencies:** P01. **Requirements:** FR-ID, FR-STU, FR-AUD foundation, INV-06/10.

- [ ] **P02-T01: Model institutions and membership.** Add users, memberships, capability assignments, drive-assignment foundation, config versions, and student identifiers. Enforce scoped uniqueness and cross-institution foreign-key rules. Evidence: the same student number is valid in two institutions without leakage.
- [ ] **P02-T02: Implement session authentication.** Add the maintained OIDC client boundary, backend opaque sessions, secure cookies, logout/revocation, CSRF/origin checks, and isolated development personas. Evidence: spoofed domain/role claims cannot create elevated membership.
- [ ] **P02-T03: Centralize authorization.** Implement actor/institution/object context for API and worker services, non-owner runtime DB access, and row-security setup. Evidence: direct-ID/list/file/job negative tests and transaction-pool scope reset.
- [ ] **P02-T04: Implement academic revisions.** Store verified facts, scale/branch normalization, source, verification state, and immutable history. Evidence: missing backlog differs from zero and an unverified revision cannot be used as trusted evidence.
- [ ] **P02-T05: Build CSV preview and commit.** Add column mapping, row validation, duplicate detection, expected-target revisions, idempotent commit, and import reports. Evidence: preview makes no academic mutations; stale/duplicate commits behave predictably.
- [ ] **P02-T06: Implement correction review.** Let students propose changes and authorized reviewers accept/reject with evidence. Evidence: accepted changes create a new academic revision; rejected/student-only edits do not change verified facts.
- [ ] **P02-T07: Deliver initial record screens.** Provide scoped coordinator search/detail and student profile/correction interfaces with empty/error states. Evidence: a student sees only their record and can follow a correction's status.
- [ ] **P02-T08: Add audit and revocation verification.** Record import, correction, membership, and access-sensitive events; verify revocation blocks commands and worker work. Evidence: negative permissions suite and an attributable revision history.

**Exit gate:** two synthetic institutions and multiple personas work through scoped sign-in, import, and verified correction. Authentication and record trust are not placeholders that later AI code can bypass.

## 7. P03: Implement drives, private intake, and text extraction

**Objective:** Persist sources securely and expose located text before interpreting it. **Dependencies:** P02. **Requirements:** FR-JD and FR-DOC security foundation.

- [ ] **P03-T01: Model drive roots and revisions.** Add companies, draft drives, revision pointers, lifecycle/hold fields, source associations, and concurrency control. Evidence: assigned coordinators can create/edit drafts; unauthorized identities cannot.
- [ ] **P03-T02: Implement owner-bound upload sessions.** Issue random quarantine keys with short-lived signed instructions and backend limits. Evidence: another student/institution cannot reuse or complete the session for a different owner/purpose.
- [ ] **P03-T03: Bind immutable accepted bytes.** Validate actual metadata/checksum, pin object version or server-copy accepted bytes to a protected final key. Evidence: replaying an unexpired upload URL cannot change the accepted source/document unnoticed.
- [ ] **P03-T04: Add scanning and bounded parsing.** Implement signature/MIME/container checks, scanner adapter, parser resource limits, and typed failure categories. Evidence: corrupt, encrypted, mismatched, oversized, and decompression-bomb fixtures fail safely.
- [ ] **P03-T05: Extract PDF/DOCX/text with locators.** Persist parser/method version, text object/hash, page/paragraph map, and empty/scanned outcomes. Evidence: displayed evidence can be traced to the correct original page/paragraph.
- [ ] **P03-T06: Create durable source jobs.** Add scoped jobs/outbox foundation, idempotent extraction requests, worker progress, bounded retry, and manual failure handling. Evidence: a worker restart does not duplicate source versions or lose the job.
- [ ] **P03-T07: Deliver intake/review UI.** Support JD upload and pasted email text, processing states, source preview/download, and clear error/replacement paths. Evidence: real source text reaches the coordinator screen through the API.
- [ ] **P03-T08: Verify storage isolation and provenance.** Test authorized short-lived downloads, quarantine denial, source deduplication scope, and uploader/hash history. Evidence: no public object access, secret URLs in logs, or cross-tenant duplicate disclosure.

**Exit gate:** a source can be uploaded, safely accepted, extracted, located, reviewed, and replaced through revisions. OCR can remain deferred if scanned sources have a useful manual path. Real scanning is required before P10's real-data gate.

## 8. P04: Implement JD intelligence, clarification, and rule review

**Objective:** Turn source text into reviewed facts and approved policy. **Dependencies:** P03. **Requirements:** FR-AI-JD, FR-POL, initial FR-APP.

- [ ] **P04-T01: Define interpretation and policy schemas.** Add typed fields, explicit unknowns, compensation structure, evidence locators, supported criteria, and schema versions. Evidence: absent fields and unsupported criteria cannot be silently accepted.
- [ ] **P04-T02: Implement fixture/model adapters.** Add scoped structured calls, prompt/output versions, budgets, metadata, timeout and repair behavior. Evidence: fixture mode is explicit and an unavailable provider does not silently produce fake production facts.
- [ ] **P04-T03: Validate evidence and ambiguity.** Check source locators/excerpts, conflicting values, date-only cutoffs, scale ambiguity, and missing material facts. Evidence: golden fixtures identify their labeled blocking questions.
- [ ] **P04-T04: Build review/correction workflows.** Provide side-by-side evidence, field edits with rationale, clarification ownership/resolution, and manual structured entry. Evidence: an unsupported model claim needs correction/provenance before approval.
- [ ] **P04-T05: Compile typed policy drafts.** Normalize reviewed rules through configured branch/scale mappings; validate ranges, explicit not-required modes, and unsupported criteria. Evidence: invalid policy cannot reach the approved state.
- [ ] **P04-T06: Establish reusable proposal/decision core.** Create immutable rule-review proposals, dependency hashes, capability checks, expected revisions, and append-only decisions. This is the minimal approval foundation expanded in P07, not a temporary boolean flag.
- [ ] **P04-T07: Deliver rule approval UI/API.** Show readable criteria, sources, version/diff, required clarifications, and the exact decision target. Evidence: changed facts invalidate the pending review and stale decisions return conflict.
- [ ] **P04-T08: Verify AI boundaries and fallback.** Run golden facts, malformed output, unsupported evidence, malicious JD instructions, model timeout, and manual completion scenarios. Evidence: no model output can approve rules, call send tools, or classify students.

**Exit gate:** a coordinator can obtain an immutable approved policy from a source with provenance, including the manual fallback. Date-only/contradictory requirements block approval until resolved. The example deadline must never become a production default.

## 9. P05: Implement the deterministic eligibility engine

**Objective:** Reproducibly evaluate a verified cohort and explain every outcome. **Dependencies:** P02 and P04. **Requirements:** FR-ELIG, NFR-01, INV-01/02/05.

- [ ] **P05-T01: Implement pure predicates.** Support branch, exact decimal CGPA/scale, graduation cohort, and maximum active backlog count. Evidence: predicates have no model/network/database dependency and return stable reason codes.
- [ ] **P05-T02: Implement conservative aggregation.** Required unknown takes precedence, then known failure, then pass; invalid policy fails the run. Evidence: the entire fictional Section 10.2 dataset and mixed unknown/failure cases match the specification.
- [ ] **P05-T03: Snapshot cohort inputs.** Persist student membership and academic revision references, policy/config/engine versions, and fingerprints. Evidence: a mid-run academic update cannot produce a mixed-version cohort.
- [ ] **P05-T04: Add queued evaluation and persistence.** Process bounded chunks under one frozen run and persist immutable results/counts. Evidence: restart/rerun yields the same logical results without duplicate rows.
- [ ] **P05-T05: Implement freshness/invalidation.** Academic, policy, normalization, or relevant roster change marks dependent current projections stale. Evidence: a historical pass cannot authorize a new submission under changed criteria.
- [ ] **P05-T06: Deliver coordinator eligibility views.** Show three groups, predicate details, source revisions, historical/current state, and filters. Evidence: counts reconcile to the run's cohort and no row is silently omitted.
- [ ] **P05-T07: Expose student explanations.** Return only personal outcomes/reasons and review-request actions. Evidence: a student cannot infer another candidate's academics through IDs, filters, or error details.
- [ ] **P05-T08: Benchmark and audit.** Evaluate the target synthetic cohort, record environment/timing, and preserve engine/version references. Evidence: initial performance target is measured and any shortfall is reported honestly without weakening correctness.

**Exit gate:** academic eligibility is deterministic, exact, explainable, versioned, and independent of document readiness. There is no direct editable eligibility override or LLM cohort classifier.

## 10. P06: Implement student documents, publication, and registration

**Objective:** Deliver a functional student participation journey. **Dependencies:** P03 and P05. **Requirements:** FR-DOC, FR-REG.

- [ ] **P06-T01: Model document requirements/revisions.** Bind requirements to a drive revision and validation to immutable file plus requirement revision. Evidence: a replaced resume or changed format rule cannot reuse an obsolete pass.
- [ ] **P06-T02: Implement operational document checks.** Add presence, format, filename, integrity, duplicate triage, and required-stage checks on top of P03 scanning. Evidence: the resume/marksheet/ID example produces distinct passed/missing findings without authenticity claims.
- [ ] **P06-T03: Compute readiness independently.** Implement blocked/review/pending/ready precedence and deadline behavior. Evidence: document failure does not alter academic eligibility and readiness explains each unmet requirement.
- [ ] **P06-T04: Publish approved student facts.** Extend the proposal core for exact drive publication/window and expose a minimal student DTO. Evidence: internal notes and draft facts remain hidden; publication does not imply email dispatch.
- [ ] **P06-T05: Implement registration/withdrawal commands.** Enforce current eligible status, server-side time bounds, document-at-submission requirements, uniqueness, and audited assisted actions. Evidence: concurrent submission and exact-cutoff tests pass.
- [ ] **P06-T06: Add revision-driven registration holds.** Preserve submitted records when eligibility becomes unresolved/ineligible and require a current audited restoration path. Evidence: prior submission evidence survives without automatic rejection mail.
- [ ] **P06-T07: Deliver the student portal.** Implement drive detail, personal status/reasons, document checklist/upload history, submit/withdraw confirmation, and review requests with accessible state handling. Evidence: an end-to-end eligible and needs-review journey works.
- [ ] **P06-T08: Deliver coordinator participation views.** Add combined eligibility/readiness/registration filters and candidate-list snapshot/export foundation. Evidence: unique-student counts reconcile and export is scoped and CSV-safe.

**Exit gate:** an eligible student can register with the drive's permitted document timing; unknown/ineligible/stale cases are blocked appropriately. Upload replacements and deadline changes remain traceable. No shared public student-document links exist.

## 11. P07: Implement exact proposals, approvals, and safe dispatch

**Objective:** Execute approved communications without losing intent or hiding uncertain outcomes. **Dependencies:** P04-P06. **Requirements:** FR-COM, FR-APP, FR-DISP.

- [ ] **P07-T01: Complete generic proposal contracts.** Extend the P04 core with immutable action payloads, canonical hashes, dependencies, expiry, sender/connection revision, and execution bounds. Evidence: policy approval never grants generic send authority.
- [ ] **P07-T02: Implement explicit audience snapshots.** Compute backend audience queries, deduplicate contacts, store inclusion/exclusion reasons, merge data, and per-recipient renders. Evidence: no LLM chooses recipient IDs and the exact intended audience is inspectable.
- [ ] **P07-T03: Add drafting and content validation.** Provide deterministic templates and optional AI drafts for announcements/reminders/schedules/corrections. Evidence: required facts/links/timezones are validated and approved content is never regenerated during send.
- [ ] **P07-T04: Deliver the approval center.** Show exact versions, audience, content, effects, and decision history with approve/reject/revision actions. Evidence: concurrent decisions, stale edits, expired proposals, and revoked reviewers fail safely.
- [ ] **P07-T05: Complete transactional outbox and relay.** Commit execution intent alongside decision/audit and publish recoverably. Evidence: broker outage, relay crash after publish, and lost Redis messages do not lose or duplicate logical work.
- [ ] **P07-T06: Implement per-item claim and attempts.** Apply final freshness/capability checks, operation uniqueness, leases, exact renders, known-safe retries, and unknown-outcome reconciliation. Evidence: provider crash-window fixtures behave as specified.
- [ ] **P07-T07: Deliver mail adapters and progress UI.** Wire the sink first, classify acceptance/delivery/failure/unknown honestly, show partial batch progress, and configure sender/allowlist safeguards. Evidence: one logical message appears per approved recipient in the local scenario.
- [ ] **P07-T08: Verify invalidation and cancellation races.** Change criteria/deadline/content/recipient and stop affected unclaimed operations; preserve in-flight/sent history. Evidence: documented claim boundary and no false promise that cancellation recalls sent mail.
- [ ] **P07-T09: Define production transport readiness.** Identify the selected production adapter's sender, quota, receipt, idempotency, and lookup behavior. Implement/configure it only within authorized scope. Evidence: limitations are explicit before a real-data pilot.

**Exit gate:** an exact reviewed proposal dispatches through the sink with durable intent, immutable content/audience, deduplicated logical operations, and visible uncertain outcomes. Unapproved direct API/task calls cannot send.

## 12. P08: Implement durable LangGraph orchestration

**Objective:** Compose existing services into a persistent human-supervised workflow. **Dependencies:** P07. **Requirements:** FR-WF and baseline FR-EXC.

- [ ] **P08-T01: Define versioned graph state.** Store scoped IDs/revisions, thread mapping, pending proposal/case, event reference, and errors. Evidence: state excludes full cohorts, tokens, signed URLs, and raw files.
- [ ] **P08-T02: Configure protected PostgreSQL checkpoints.** Establish package migrations/setup, trusted thread access, connection lifecycle, and restart persistence. Evidence: arbitrary client thread IDs cannot expose or mutate another run.
- [ ] **P08-T03: Compose intake-to-review nodes.** Reuse source, interpretation, clarification, and policy services rather than reimplementing them in prompts/nodes. Evidence: replay finds existing domain artifacts by operation keys.
- [ ] **P08-T04: Add authenticated pause/resume.** Use persisted proposal decisions and outbox resume events, with serialization and freshness checks. Evidence: API/worker restart while waiting resumes the original run once and rejects unauthorized/stale responses.
- [ ] **P08-T05: Compose evaluation/publication/communication execution.** Coordinate approved domain services and enqueue effects; do not give the graph a raw send tool. Evidence: the happy path reaches monitoring with the same audited approvals as direct commands.
- [ ] **P08-T06: Implement monitoring handlers and event deduplication.** Route registration, document, policy, and deadline events to bounded handlers. Evidence: a new document event does not repeat original JD analysis or announcement dispatch.
- [ ] **P08-T07: Add operational holds and baseline cases.** Surface unresolved inputs, stale approvals, delivery uncertainty, and failed jobs with owners and manual actions. Evidence: a hold blocks new consequential work while preserving completed history.
- [ ] **P08-T08: Test coordination gaps and version upgrades.** Crash between domain commits and checkpoints, replay decisions, and exercise duplicate/out-of-order events. Define compatible-run migration policy. Evidence: no duplicate approvals/effects and no blind incompatible resume.

**Exit gate:** the source workflow can pause, restart, resume, and monitor without a continuously occupied worker or hidden duplicate actions. Manual service paths remain available and use the same authority checks.

## 13. P09: Implement scheduling, results, closure, and reporting

**Objective:** Finish the complete local recruitment lifecycle. **Dependencies:** P08. **Requirements:** FR-SCHED, FR-RESULT, FR-REPORT, FR-CLOSE, completed FR-AUD coverage.

- [ ] **P09-T01: Model rounds and session revisions.** Add ordered stages, published pointers, timezones, capacity, venues/panels, and participants. Evidence: draft sessions do not appear as confirmed student assignments.
- [ ] **P09-T02: Implement conflict and participation checks.** Validate half-open intervals, buffers, student/panel/venue overlap, capacity, current registration/eligibility/readiness, and prerequisites. Evidence: concurrent publication cannot bypass conflict checks.
- [ ] **P09-T03: Publish/reschedule through proposals.** Freeze session/participant revisions, record decisions, prepare exact notifications, and preserve old schedules. Evidence: a material timing change stales unsent old notices and generates a new reviewable action.
- [ ] **P09-T04: Add attendance and employer results.** Record distinct attendance and source-backed outcome revisions; separate internal results from student publication. Evidence: absence never automatically becomes rejection and corrected results preserve history.
- [ ] **P09-T05: Deliver coordinator/student schedule and result views.** Show only authorized published assignments/outcomes, actionable changes, and accessible conflict/error states. Evidence: two students cannot inspect each other's results.
- [ ] **P09-T06: Implement deterministic reports and exports.** Define metric denominators, frozen dataset/revision references, safe CSV output, and controlled download expiry. Evidence: report counts reproduce exactly from the snapshot.
- [ ] **P09-T07: Implement closure, cancellation, and reopening.** Enforce pending-work/session/result checks, unresolved-case acknowledgment, explicit reasons, and new report revisions on reopening. Evidence: closure cannot hide active or unknown delivery work.
- [ ] **P09-T08: Complete audit coverage and MVP demonstration.** Run the specification's twelve-step local acceptance scenario from intake to closure, including revision and access-denial cases. Evidence: walkthrough and check results identify any remaining mock-only capability.

**Exit gate:** M3 is complete only when scheduling, results, and closure work alongside intake, eligibility, registration, documents, approvals, and durable workflow. A polished intake dashboard alone is not an MVP.

## 14. P10: Harden the MVP and establish pilot readiness

**Objective:** Verify the cross-cutting guarantees and prepare an intentionally configured pilot. **Dependencies:** P09. **Requirements:** NFR-01 through NFR-12 and specification Section 22.2.

- [ ] **P10-T01: Run risk-based authorization/security checks.** Exercise cross-institution/student IDs, worker/resume scope, CSRF, caching, private exports, revoked capabilities, secret handling, and malicious uploads/prompts. Evidence: findings resolved or release-blocking, not hidden in a generic pass.
- [ ] **P10-T02: Exercise resilience boundaries.** Interrupt API/worker/relay/broker/storage/model/provider paths at meaningful points. Evidence: pending work recovers, uncertain effects remain visible, and no unapproved/duplicate logical execution occurs.
- [ ] **P10-T03: Measure realistic performance and cost.** Benchmark the documented 5,000-student/20-drive/100-user envelope and model/parser limits. Evidence: environment, distributions, bottlenecks, and per-drive usage are recorded; optimize only measured problems.
- [ ] **P10-T04: Complete accessibility and usability review.** Exercise keyboard-only coordinator/student journeys, approval evidence, file errors, deadlines, and responsive layouts. Evidence: core interaction defects are fixed and limits are stated without unsupported certification claims.
- [ ] **P10-T05: Configure observability and runbooks.** Add actionable metrics/alerts, redacted traces, health checks, and recovery procedures. Evidence: an operator can locate a stuck job/unknown send and follow a safe documented resolution.
- [ ] **P10-T06: Demonstrate backup and retention procedures.** Restore database plus objects/checkpoints, reconcile pending work, reapply deletion records, and measure recovery objectives. Evidence: successful drill and institution-configured retention rather than untested backup settings.
- [ ] **P10-T07: Resolve real-data configuration.** Establish OIDC/membership ownership, branch/scale trust, real scanner, selected model policy/provider, production sender, privacy/retention policy, host/region, and operational owners. Evidence: no development identity/scanner/mail/model fixture can masquerade as production.
- [ ] **P10-T08: Prepare and verify deployment artifacts.** Build images, migration job, secret injection, network restrictions, release/rollback sequence, and compatible workflow handling. Evidence: staging smoke test; actual deployment occurs only when authorized.
- [ ] **P10-T09: Record release evidence.** Re-run the main acceptance journey on the release candidate and document feature status, deferred connectors, known limits, and pilot readiness. Evidence: a future agent/operator can distinguish local MVP completion from a live pilot launch.

**Exit gate:** M4 requires passing evidence and configured owners. If institution/provider inputs are missing, the local MVP can be released as a synthetic-data demonstration, but the real-data pilot remains explicitly unready. Do not request production access merely to finish a local demonstration.

## 15. P11: Add live Gmail, Sheets, and Calendar connectors

**Objective:** Reduce tool switching while preserving the same approval/data boundaries. **Dependencies:** P10 and explicit authorization for the actual account connections/external test actions. **Requirements:** FR-INT-03 through FR-INT-09.

- [ ] **P11-T01: Validate provider contracts and scopes.** Check current official APIs, minimal per-feature scopes, consent/verification requirements, quotas, and supported reconciliation behavior. Evidence: documented permissions match enabled features; no broad scope is requested by habit.
- [ ] **P11-T02: Implement encrypted connection lifecycle.** Add connect, status, refresh, disconnect, revocation, scope/version changes, and audit. Evidence: token material never enters browser storage, checkpoints, logs, or fixtures.
- [ ] **P11-T03: Add explicit Gmail source selection.** Let a coordinator choose a message/attachment, capture immutable content and provenance, and feed existing intake services. Evidence: no default whole-inbox ingestion and disconnect blocks subsequent reads.
- [ ] **P11-T04: Add Sheets import preview/commit.** Select a spreadsheet/range, map fields, fingerprint the source, and detect concurrent academic/source changes. Evidence: a changed sheet or newer academic revision cannot be overwritten silently.
- [ ] **P11-T05: Add approved Sheets export/write.** Freeze target, range/schema, snapshot and content, and execute through controlled integration work. Evidence: incorrect scope/target and duplicate queue delivery do not create unauthorized writes.
- [ ] **P11-T06: Add approved Calendar create/update.** Capture schedule/attendee/notification options, use stable mapping, and reconcile provider IDs/versions. Evidence: duplicate attempts do not silently duplicate events and invite side effects are shown before approval.
- [ ] **P11-T07: Handle external change/webhook events.** Verify signatures/tokens where supported, deduplicate, reconcile missed events, and open discrepancies for external edits. Evidence: an untrusted callback cannot change approved internal facts.
- [ ] **P11-T08: Run isolated connector acceptance.** Exercise expired tokens, disconnect, 429/backoff, partial failures, unknown outcomes, external edits, and safe manual fallback. Evidence: only explicitly authorized test accounts/recipients are touched and connector limits are documented.

**Exit gate:** advertise each connector separately only after its tests pass. Internal scheduling and uploaded-source intake continue to work when Google is unavailable.

## 16. P12: Add structured exception impact analysis and recovery

**Objective:** Adapt to changing drive information with reviewable, controlled plans. **Dependencies:** P10; P11 only for connector-specific cases. **Requirements:** advanced FR-EXC.

- [ ] **P12-T01: Define supported exception schemas.** Start with criteria change, verified academic correction, deadline/schedule revision, and notification failure. Evidence: each type has explicit inputs, impact rules, and manual fallback; avoid unrestricted problem solving.
- [ ] **P12-T02: Build deterministic impact analysis.** Compare old/new policy/evaluation and identify affected notified students, registrations, schedules, proposals, and external mappings. Evidence: an agent's wording cannot alter the computed affected set.
- [ ] **P12-T03: Define typed recovery operations.** Allow only versioned domain commands with preconditions, expected revisions, dependencies, approval type, and irreversible-effect notes. Evidence: unsupported actions fail validation.
- [ ] **P12-T04: Add proposal-only exception agent.** Supply scoped evidence/impact summaries and validate its structured plan. Evidence: the model cannot send, mutate records, expand permissions, or mark a case resolved.
- [ ] **P12-T05: Deliver plan review and approval.** Show step ordering, affected students, exact communications/external effects, and reasons. Evidence: approval binds the exact plan and required action proposals; stale inputs block execution.
- [ ] **P12-T06: Execute bounded plans through services.** Revalidate each step, deduplicate operations, preserve partial completion, and stop stale/cancelled remaining steps. Evidence: a mid-plan failure does not replay already completed external effects.
- [ ] **P12-T07: Verify change scenarios.** Demonstrate CGPA 7.50 -> 8.00, a corrected student record, a changed deadline after announcement, and an uncertain notification outcome. Evidence: no silent registration deletion or automatic correction mail.
- [ ] **P12-T08: Evaluate usefulness and fallback.** Compare proposed plans against curated expected plans and coordinator edits; cap model cost/attempts. Evidence: manual resolution works for every supported case when the model is unavailable.

**Exit gate:** M6 demonstrates concrete adaptive recovery with deterministic impact and exact approvals. An impressive free-text plan without safe execution/recovery is incomplete.

## 17. P13: Expand only from measured needs

**Objective:** Improve operation or scope based on pilot evidence. **Dependencies:** relevant P10/P11/P12 capabilities and explicit requested expansion. This phase is not necessary for the initial MVP.

- [ ] **P13-T01: Review pilot evidence.** Identify coordinator friction, extraction corrections, unresolved cases, delivery issues, and operating cost. Evidence: prioritized problems tied to observed usage rather than speculative features.
- [ ] **P13-T02: Optimize demonstrated bottlenecks.** Consider indexed projections, chunking, queue separation, or incremental invalidation. Evidence: before/after measurements and preserved correctness/recovery tests.
- [ ] **P13-T03: Validate additional institution/tenant operation.** Test configuration isolation, onboarding, access administration, quotas, exports, and restore scope. Evidence: operating multiple institutions does not weaken isolation.
- [ ] **P13-T04: Add requested policy or scheduling extensions.** Version new criteria/operators/normalizations and conflicts with explicit institution rules. Evidence: no silent change to old policy semantics.
- [ ] **P13-T05: Review stronger availability and recovery needs.** Adopt HA/managed services only when goals require them; test failover and outbox behavior. Evidence: revised objectives are measured and supported operationally.
- [ ] **P13-T06: Refresh documentation and maintenance policy.** Review dependencies, API compatibility, retention, graph upgrades, runbooks, and feature status. Evidence: a clean environment and current references reproduce the intended release.

**Exit gate:** each expansion has a measurable benefit, a bounded scope, and passing guarantees. A more complicated deployment alone is not progress.

## 18. Cross-cutting work tracks

| Track | Start | Ongoing obligation | Consolidated proof |
| --- | --- | --- | --- |
| Authorization and privacy | P02 | Every new endpoint, worker, file, report, and connector carries scope tests. | P10 security review. |
| Audit and provenance | P02/P03 | Every material command records actor/revision/evidence. | P09 report reproducibility and P10 review. |
| Immutable revisions and stale handling | P02/P04 | New actions declare dependencies; no mutable approved payloads. | P07/P08 race and replay scenarios. |
| Durable work/idempotency | P03 | Persist intent before asynchronous effects and classify retries. | P07/P08/P10 recovery tests. |
| Accessibility and status clarity | P01 | Build accessible controls and honest asynchronous/error states. | P10 manual journeys. |
| AI evidence/cost controls | P04 | Validate supported facts, cap attempts, retain manual paths. | P04 golden fixtures and P10 usage review. |
| Migrations and contracts | P01 | Version schemas, test upgrades, regenerate API types. | Each phase and P10 release candidate. |
| Operational documentation | P01 | Add a runbook when a recoverable failure mode appears. | P10 operator walkthrough. |

## 19. Critical scenario matrix

| Scenario | Expected outcome | Primary phase evidence |
| --- | --- | --- |
| Missing required academic value | `needs_review`, even if another predicate fails; show both findings. | P05 |
| CGPA equals threshold | Pass that predicate without rounding. | P05 |
| Unverified student correction | No change to verified eligibility until authorized verification. | P02/P05 |
| Ambiguous deadline or contradictory source | Blocking clarification; no invented cutoff. | P04 |
| Replayed upload URL after validation | Accepted immutable revision remains bound to original validated bytes. | P03 |
| Missing/corrupt document | Separate readiness finding; academic outcome unchanged. | P06 |
| Submission exactly at deadline | Rejected by server clock with actionable reason. | P06 |
| Approval subject/audience/deadline changes | Stale proposal; affected unclaimed operations stop. | P07 |
| Reviewer/connection revoked | Future claims fail authority/freshness checks. | P07/P11 |
| Queue task delivered twice | Same logical operation, no duplicate business action. | P07/P08 |
| Timeout after possible email acceptance | `unknown`; reconcile before resend. | P07 |
| Restart while waiting for human approval | Same persisted run/proposal resumes. | P08 |
| Crash between domain record and checkpoint | Replay/reconciliation finds existing domain operation. | P08 |
| Concurrent schedule publication | Conflict/capacity invariants preserved. | P09 |
| Result correction after publication | New revision/publication, prior history retained. | P09 |
| Closure with pending/uncertain work | Block or require explicit permitted resolution/acknowledgment. | P09 |
| Criteria change after announcement | New policy/evaluation, retained history, holds, approved correction proposal. | P08 baseline/P12 advanced |
| Cross-institution/student guessed ID | No record/file/export disclosure. | P02 onward/P10 |
| Restore from backup after a deletion | Reapply deletion/tombstones and reconcile work before exposure. | P10 |

## 20. Change and handoff discipline

Before a schema/API/status change, identify affected requirement IDs, stored revisions, API clients, workflow state, audit/reporting, and migration/rollback implications. Update the canonical references in the same change where practical. Preserve historical interpretation of approved versions; do not rewrite old evidence to fit new semantics.

After each completed task/phase, record:

```text
Task/phase:
Behavior delivered:
Requirements covered:
Files/change reference:
Verification commands and results:
Demonstrated user/recovery scenario:
Remaining limits or decisions:
Next dependency-ready task:
```

Avoid accumulating a long conversational diary in this plan. Keep current progress and links to concrete evidence. Report failed or unrun checks explicitly. A future coding agent should be able to resume from the checked tasks, current contracts, and repository state without reconstructing the chat.

The first implementation task after authorization is P00 validation followed by P01 bootstrap. Do not start with a broad autonomous agent or a visually polished dashboard disconnected from the underlying records and approval rules.
