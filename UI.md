# PlacementOS User Actions, Feature Use Cases, and Visible Flows

> Status: product-behavior reference prepared 4 November 2026 from `PROJ_SPECIFICATION.md`, `Architecture.md`, `PLAN.md`, the P11-P13 verification records, and the evidenced local implementation. This document is an input to future information architecture and interface design. It deliberately does not prescribe screens, routes, navigation, layout, components, colors, or visual styling.

## 1. Purpose

This document describes what people can do in PlacementOS and what they must be able to understand while doing it. It focuses on two primary users:

- **Placement coordinator:** prepares and operates recruitment drives, reviews evidence, authorizes consequential actions, handles exceptions, and closes the process.
- **Student:** reviews their own record and opportunities, understands their own eligibility, provides documents, registers, and follows their own schedule and published results.

For each capability, the future interface should make clear:

- what the user is trying to accomplish;
- what must already be true;
- what information the user can inspect;
- which action the user can take;
- whether the action saves a draft, requests approval, authorizes an effect, or executes an effect;
- what changes after success;
- why an action is blocked, stale, failed, or awaiting another person/system; and
- what safe recovery path is available.

This is not a promise that every listed capability is enabled against live providers today. Section 2 distinguishes the evidenced local baseline from integration-gated and planned production behavior.

## 2. Capability status vocabulary

Every later UI plan should label environment-dependent capabilities honestly.

| Label | Meaning |
| --- | --- |
| **Local baseline** | Implemented and evidenced through P13 with synthetic records, development identity, deterministic fixtures, private local storage, and/or a mail sink. |
| **Integration-gated** | The product boundary exists, but real-account use requires provider credentials, explicit connection, appropriate scopes, and isolated live acceptance. This currently applies to Gmail, Google Sheets, and Google Calendar. |
| **Production-transition** | Planned in `AI Provider Integration.md`; requires real OIDC, model, secrets, storage, scanner, mail, observability, privacy, and operational configuration. |
| **Institution-configured** | Behavior cannot be assumed globally. An authorized institution must configure the rule before it affects real users. |
| **Deferred** | Intentionally outside the current approved scope. It must not appear as available merely because a placeholder could be designed. |

Production must begin without demo institutions, personas, students, companies, drives, policies, or documents. Synthetic fixtures may remain isolated to automated tests and explicitly marked demonstrations.

## 3. Interaction and trust principles

### 3.1 Actions with different authority must look different

The experience must never blur these action types:

1. **Inspect:** view evidence, history, or a calculated result.
2. **Edit a draft:** change information that has not been approved or published.
3. **Submit for review:** freeze a revision and request a decision.
4. **Approve or reject:** make an attributable decision about that exact revision.
5. **Publish:** make an approved revision visible to its intended audience.
6. **Execute:** claim a specifically approved external or consequential action.
7. **Reconcile:** resolve an uncertain external outcome using provider or human evidence.

An approval of eligibility rules does not approve drive publication, a message, an export, or a calendar invitation. Each consequential effect requires its own exact proposal and authority.

### 3.2 AI suggestions, deterministic decisions, and human authority remain distinct

- AI may extract JD facts, draft wording, classify a document issue, or propose a recovery plan.
- AI output is visibly a suggestion or draft, with provider/model status and evidence where relevant.
- Academic eligibility is calculated only by the deterministic policy engine from an approved policy and verified student evidence.
- A model cannot approve, publish, send, change a student record, alter a schedule, or execute a recovery command.
- Manual entry and review remain available when a model is disabled, unavailable, invalid, or uncertain.

### 3.3 Separate states remain separately visible

For a student in a drive, the product must show independent values for:

- academic eligibility;
- document readiness;
- registration state;
- schedule/round assignment;
- attendance;
- employer outcome; and
- notification state.

For example, a student can be academically eligible, registered, and still document-pending. A provider can accept an email without confirmed delivery. A published drive can have an operational hold. None of these states should overwrite another.

### 3.4 Evidence, revision, and freshness are part of the user experience

Where a decision can affect participation or an external action, users must be able to see:

- the active revision and whether it is current;
- the source or attributed correction supporting it;
- who created, reviewed, or approved it and when;
- dependencies that can make it stale;
- historical revisions without confusing them with the current one; and
- a plain-language reason when an action can no longer proceed.

### 3.5 Shared feedback behavior

- Long-running work shows queued, processing, succeeded, retryable failure, terminal failure, and cancelled states.
- Refreshing or signing in again does not lose persisted progress.
- Empty states explain what is absent and the next permitted action.
- Validation identifies the exact field or prerequisite and how to correct it.
- Conflicts show that the underlying record changed and require reloading the current revision.
- Deadline displays include the institution timezone; countdowns are informational and the server clock decides acceptance.
- Critical meaning is not communicated by color alone.
- Actions and status changes are keyboard accessible and announced accessibly.
- Private information is minimized to the current user and authorized purpose.

## 4. Access, role, and scope behavior

### 4.1 Coordinator access

A coordinator can:

1. Sign in through the configured identity provider in production, or an explicitly marked development identity adapter locally.
2. Enter only institutions for which they have an active membership.
3. Act only on drives assigned to them and only with the required capability.
4. See their current institution, role, capabilities, and relevant environment status.
5. Sign out and lose access when the session expires or membership is revoked.

The coordinator sees a clear unavailable/unauthorized result rather than partial data when institutional or object scope does not permit access. An institution administrator is not automatically a drive approver.

### 4.2 Student access

A student can:

1. Sign in only through a preauthorized or invited institutional membership.
2. Access only their own profile, correction requests, eligibility explanations, documents, registrations, schedule, and published results.
3. See only published drive facts intended for students.
4. Sign out and receive a clear expired/revoked-session response when access ends.

A student must never discover another student's existence, eligibility reason, document, registration, schedule, result, email address, or duplicate-document relationship by changing an identifier.

### 4.3 Supporting actors that affect the flows

- An authorized records reviewer may verify student evidence.
- An institution administrator may manage membership, provider setup, and institution configuration, but receives no automatic drive-approval authority.
- A read-only auditor may inspect explicitly authorized history and reports.
- A system worker may execute already-authorized operations but cannot become a human approver.

These supporting actors should influence permission and history indicators, but this document does not define a separate administrator or auditor experience.

## 5. Placement coordinator capabilities

### 5.1 Understand operational status and priorities

The coordinator can review the institution's current operational position, including:

- active and held drives;
- drives awaiting source review, clarification, policy approval, publication, or closure;
- eligibility totals by `eligible`, `ineligible`, and `needs_review` for a named evaluation snapshot;
- registrations by state and document readiness;
- pending or stale approvals;
- queued, partial, failed, cancelled, and uncertain dispatch work;
- open exceptions by severity and owner;
- approaching registration, document, and schedule deadlines;
- worker, queue, outbox, storage, scanner, mail, integration, and model-provider readiness where authorized; and
- the release/environment label so a synthetic or mock setup cannot be mistaken for production.

The coordinator can filter or follow a count to the records behind it. Counts identify their denominator and revision rather than presenting ambiguous totals.

### 5.2 Inspect institution operating policy and quotas

With `ops:view`, a coordinator can see:

- onboarding state such as configuration pending, synthetic ready, or pilot ready;
- the maximum allowed open drives;
- CSV/Sheets import row limits;
- export row limits;
- policy revision, last actor, reason, and timestamp; and
- which attempted action is blocked by a quota.

Only a user with `config:manage` can change these limits or onboarding state. A change requires an attributed reason, creates a new revision, and fails on a stale expected revision.

### 5.3 Search and inspect student records

The coordinator can:

- search by institutional identifier, name, or institutional email;
- filter by branch/program, graduation year, verification state, or academic values;
- page through large cohorts without loading every record at once;
- inspect the student's current verified academic revision;
- distinguish missing values from zero or false values;
- see provenance, verification status, prior revisions, and dependent stale results; and
- see only student information needed for the authorized placement purpose.

The experience must not imply that an unverified student proposal is trusted evidence.

### 5.4 Import institutional student records from CSV

The coordinator flow is:

1. Select or provide a CSV source.
2. Map source columns to supported student fields.
3. Preview without changing authoritative records.
4. Review valid rows, invalid rows, missing values, duplicate candidates, unknown branch aliases, and proposed create/update effects.
5. Correct the source or mapping and preview again when necessary.
6. Explicitly commit the exact preview while it is still current.
7. See row-level committed, skipped, and failed outcomes plus the attributable original import.

The commit is blocked when the preview is stale, the row quota is exceeded, a concurrent academic revision changed, or required validation fails. Retrying the same commit does not create duplicate students.

### 5.5 Review student academic-correction proposals

Students can propose changes, but the coordinator or authorized records reviewer controls verification:

1. Inspect the current verified value and the student's proposed value side by side.
2. Review the student's explanation and evidence reference.
3. Add an attributable verification note.
4. Approve or reject the proposal.
5. On approval, create a new verified academic revision rather than editing history.
6. See affected eligibility results marked stale and route them for reevaluation.

Approval does not directly override a drive's eligibility result. The deterministic engine must evaluate the new verified revision against the approved policy.

### 5.6 Maintain companies and create a drive

The coordinator can:

- select an existing company or create an institution-scoped company record;
- capture company name and optional approved metadata;
- create a draft recruitment drive with role/title, cycle, ownership, and internal context;
- see whether the institution's open-drive quota permits creation;
- edit draft metadata using revision checks; and
- inspect drive lifecycle, owner/assignees, current revision, and operational-hold state.

Creating a drive does not publish it, approve criteria, evaluate students, or notify anyone.

### 5.7 Add JD and recruitment source material

The coordinator can add source material through:

- PDF upload;
- DOCX upload;
- pasted email/body text; and
- an explicitly selected Gmail message or attachment when the connector is enabled and accepted for live use.

For every source, the coordinator sees:

- original filename or source label;
- media type, size, hash, uploader, and timestamp;
- sender/received metadata when captured from email;
- upload, quarantine, malware scan, extraction, and failure state;
- whether text extraction used OCR or requires manual handling;
- parser/extractor version and source revision; and
- private preview/download only when authorized and safe.

Encrypted, corrupt, unsupported, over-limit, executable-mismatch, empty, or conflicting sources produce explicit outcomes. The coordinator can retry a bounded extraction where safe, upload a corrected source, or continue through manual structured entry. Multiple attachments remain separate evidence; the system does not silently decide which is authoritative.

### 5.8 Review AI-extracted or manually entered JD facts

The coordinator can create a review revision from an available source. Depending on environment configuration, this may use a deterministic fixture, a real model provider, or manual entry.

The review covers:

- company and role;
- employment type;
- work location and work mode;
- compensation wording and explicit breakdown;
- branch, graduation cohort, CGPA/scale, and backlog criteria;
- required documents;
- registration and document dates;
- recruitment rounds/process;
- contact/support information; and
- unresolved or contradictory facts.

For each material fact, the coordinator can inspect its source artifact, page/paragraph/section locator, supporting excerpt, extraction confidence/status, and whether the value came from AI or a human correction.

The coordinator can:

- accept a supported value into the review revision;
- record a field-level correction with reason and provenance;
- answer a blocking clarification with an exact value;
- record an external clarification received from the company;
- compare before/after values and prior interpretation revisions; or
- abandon invalid model output and complete the same structured review manually.

An absent deadline time or timezone remains unresolved. A model suggestion never becomes approved fact merely because it is schema-valid.

### 5.9 Compile, validate, and approve eligibility policy

After material ambiguities are resolved, the coordinator can compile reviewed facts into a deterministic policy. They can inspect:

- allowed branches or the explicit `all_verified_branches` choice;
- graduation cohorts;
- minimum CGPA and scale;
- maximum active backlogs;
- criteria explicitly marked `not_required` with provenance;
- source evidence for every required predicate;
- a human-readable rule statement;
- affected cohort scope;
- policy version and validation errors; and
- differences from the prior policy revision.

The coordinator flow is:

1. Compile a draft policy.
2. Resolve invalid ranges, unsupported criteria, empty scope, missing evidence, or logical conflicts.
3. Freeze and submit the exact policy revision for review.
4. An authorized reviewer approves, rejects, or requests revision with a reason.
5. An approved policy becomes immutable; later changes create a new version.

The system must prevent approval when blocking clarifications or unsupported required rules remain. No UI action can directly mark students eligible during policy editing.

### 5.10 Run and inspect deterministic eligibility evaluation

For an approved policy, the coordinator can:

1. Select the intended verified cohort scope.
2. Start a persisted evaluation job.
3. See queued/running/completed/failed processing without keeping the request open.
4. Inspect the frozen policy, cohort, academic revisions, normalization configuration, and engine version.
5. Review totals and filter `eligible`, `ineligible`, and `needs_review` outcomes.
6. Inspect every student's predicate-level expected value, actual value, evidence status, outcome, and reason code.
7. See known failures even when an unknown predicate makes the overall outcome `needs_review`.
8. Compare current and historical runs while clearly identifying stale results.

The experience offers no arbitrary eligibility override. The permitted remedies are correcting and verifying academic evidence, revising and approving the policy, or holding an unsupported case for review.

### 5.11 Define document requirements and review readiness

The coordinator can define per-drive requirements for resume, marksheet, college ID, or institution-approved labels, including:

- required/optional status;
- accepted formats;
- maximum size;
- filename rule when applicable;
- deadline and timezone;
- whether the document is required at registration or only before scheduling; and
- operational checks required before acceptance.

For each student's current document revision, the coordinator can see:

- uploader and ownership;
- original metadata and safe download name;
- upload, scan, signature/MIME, integrity, parsing, and manual-review findings;
- finding severity, required remediation, and validator version;
- whether the revision is current, superseded, quarantined, or inaccessible;
- the independently calculated readiness state: `ready`, `pending`, `blocked`, or `needs_review`; and
- audited private-download access where authorized.

The coordinator may request replacement, conduct an authorized manual review, or perform an explicitly authorized assisted upload. They cannot declare a document authentic, use an AI suggestion to bypass malware/security failure, or expose cross-student duplicate identities.

### 5.12 Prepare and approve student-visible drive publication

The coordinator can prepare the exact student-visible revision containing only approved fields. They can inspect:

- company, role, compensation as supplied, location/work mode, and process;
- eligibility requirements;
- required documents;
- registration/document windows with timezone;
- student-visible support details;
- fields excluded as confidential/internal; and
- dependencies that will make the publication stale.

The coordinator submits the publication proposal and an authorized reviewer approves, rejects, or requests revision. Only an approved current revision becomes visible to students. Publication does not prove that an announcement was sent or delivered.

### 5.13 Monitor and assist registrations

The coordinator can:

- view registration totals and filter by submitted, draft, withdrawn, eligibility hold, or cancelled;
- combine registration filters with eligibility and document readiness;
- inspect the drive/policy/evaluation references used at submission;
- see immutable submission and withdrawal events;
- identify students who may register, are blocked, or require review;
- take an assisted action when explicitly permitted, with reason and audit evidence;
- preserve a registration and place it on `eligibility_hold` after a relevant criteria/evidence change; and
- export an authorized candidate list with revision and freshness metadata.

The coordinator cannot silently extend a deadline, delete a submitted registration because eligibility changed, or treat document-pending as academically ineligible.

### 5.14 Draft communications and freeze the audience

Supported communication intents include:

- drive announcement;
- missing-document reminder;
- registration deadline reminder;
- interview schedule;
- schedule correction;
- result notice;
- result correction; and
- clarification request/draft.

The coordinator can:

1. Choose a controlled template or request an AI-assisted draft when enabled.
2. Use only approved structured facts.
3. Select an explicit audience rule such as current eligible students, submitted registrants, students with required-document findings, assigned session participants, or reviewed correction recipients.
4. Preview the frozen recipient snapshot.
5. Inspect inclusion reasons, exclusion counts, duplicate/unresolved addresses, sender, reply-to, attachments, and dependencies.
6. Review samples and any recipient-specific rendering without exposing one student's details to another.
7. Correct content or audience before submitting it.
8. Freeze exact template, merge values, rendered hashes, sender, channel, and audience for approval.

Missing company/role, action, link, deadline/timezone, document instruction, schedule fact, or support contact blocks the proposal when required. AI cannot regenerate or alter wording after approval.

### 5.15 Decide exact communication proposals

An authorized coordinator can inspect the exact content, recipients, dependencies, sender, execution window, and intended effect, then:

- approve the exact batch;
- reject it with a reason; or
- request revision with actionable feedback.

The coordinator sees decision history and any conflict caused by another reviewer or a changed dependency. Editing content, audience, deadline, policy, relevant evidence, schedule, or sender connection invalidates affected approval and requires a new proposal revision.

### 5.16 Monitor, stop, retry, and reconcile message dispatch

After approval, the coordinator can follow:

- batch totals and progress;
- each logical recipient operation;
- claimed and unclaimed work;
- provider attempts and identifiers;
- provider accepted, delivered, retryable failure, permanent failure, unknown, or cancelled status; and
- the reason an operation stopped or became stale.

Permitted controls include:

- stop future unclaimed messages with an attributable reason;
- retry only a known-safe retryable failure under bounded policy;
- inspect partial completion;
- reconcile an ambiguous timeout using provider or coordinator evidence;
- mark confirmed provider acceptance; or
- confirm non-acceptance before allowing a safe retry.

An `unknown` outcome is never blindly resent. Cancelling cannot recall an already transmitted message, and provider acceptance is not displayed as confirmed delivery without evidence.

### 5.17 Start and control the durable drive workflow

The coordinator can start a persisted workflow for the current drive revision and inspect:

- workflow status and current stage;
- last successful step;
- waiting clarification/rule approval/action approval reason;
- workflow implementation and state-schema version;
- referenced source, policy, and evaluation revisions;
- retryable or terminal error category;
- checkpoint/run history; and
- whether an upgrade requires migration or safe restart.

The coordinator can place an operational hold with a reason, release a hold when authorized, resume through a valid approval/clarification command, or cancel where permitted. A hold prevents new consequential work but preserves completed effects and history. Two simultaneous resume attempts do not execute the transition twice.

### 5.18 Configure rounds and sessions

The coordinator can:

- define ordered recruitment rounds;
- draft one or more sessions per round;
- set start/end instants, timezone, capacity, venue or meeting link, and panel;
- assign registered students under current eligibility, readiness, and prerequisite-round rules;
- inspect student, panel, venue, capacity, and configured-buffer conflicts;
- correct the draft and revalidate; and
- submit the exact session revision for publication approval.

Intervals use `[start, end)`, so a session ending at 11:00 does not conflict with one starting at 11:00 unless an institution-configured buffer applies. Draft assignments remain invisible to students.

A document-timing exception, if institutionally allowed, requires explicit capability and reason and never changes academic eligibility.

### 5.19 Publish and revise schedules

An authorized reviewer can approve, reject, or request revision of the exact assignment set. After publication, the coordinator can:

- see which participants can view the assignment;
- create a new revision for material rescheduling;
- preserve the old schedule revision;
- re-run conflict validation;
- see the affected participants; and
- prepare a separately approved correction notice.

Internal scheduling works without Google Calendar. A Calendar write is a separate, approved integration action.

### 5.20 Record attendance and employer outcomes

For a published session, the coordinator can record attendance independently as:

- not recorded;
- present;
- absent; or
- excused.

The coordinator can record employer-provided outcomes such as:

- pending;
- advanced;
- rejected;
- waitlisted;
- selected; or
- withdrawn.

Every result includes source/provenance, recorder, timestamp, and revision. Draft results remain internal. Publishing an exact result revision to the student requires authorization. Correcting a published result creates a new revision and, if communication is desired, a separate correction-message proposal.

Selection, formal offer existence, student acceptance, and joining status are distinct facts. Attendance does not infer an employer decision.

### 5.21 Manage exceptions

The coordinator can inspect exception cases created for:

- unresolved or conflicting JD requirements;
- unsupported policy criteria;
- stale or conflicting academic records;
- missing, failed, quarantined, or review-needed documents;
- invalidated/stale approvals;
- failed jobs;
- ambiguous notification outcomes;
- schedule conflicts;
- external Calendar discrepancies; and
- criteria, deadline, evidence, or schedule changes affecting prior work.

Each case exposes category, severity, affected records, evidence, owner, current status, proposed next action, and history. The coordinator can acknowledge, assign/own, add evidence, dismiss with reason, resolve and resume where safe, or keep it open.

### 5.22 Analyze impact and prepare bounded recovery

For supported changes, the coordinator can record deterministic impact analysis for:

- criteria change;
- verified academic correction;
- deadline revision;
- published schedule revision; or
- failed/unknown notification.

They can inspect exact affected students/resources, before/after revisions, summary counts, dependencies, and a manual fallback. The affected set is calculated by deterministic services, not chosen by an AI planner.

The coordinator can then prepare a manual or AI-assisted structured recovery plan. Allowed plan steps are limited to:

- place a drive on hold;
- stale exact pending proposals;
- prepare an unsent correction draft;
- mark exact external mappings for reconciliation; or
- record a manual follow-up.

For every ordered step, the coordinator sees preconditions, expected effect, required approval, dependency fingerprint, compensation limitation, and irreversible-effect note. They can approve, reject, or request revision of the exact plan.

During execution, the coordinator sees completed, pending, running, failed, stale, and cancelled steps. They can cancel remaining steps without erasing completed evidence. A partially executed plan remains visible, and a prepared correction stays unsent until it passes the ordinary communication approval flow. Successful execution does not silently close the exception; explicit resolution evidence is still required.

### 5.23 Connect and manage Google Workspace capabilities

When integration use is enabled, an authorized coordinator can:

1. Choose only the required feature: Gmail intake, Sheets read/import, Sheets write/export, or owned-calendar events.
2. Begin provider authorization and review requested scopes.
3. Return to PlacementOS and see connection identity, enabled features, revision, status, and expiry/permission problems.
4. Disconnect or revoke the connection.
5. See pending work invalidated when the connection revision changes.

Tokens remain server-side and are never shown. Gmail reading and email sending are separate capabilities; the current Google boundary does not request Gmail-send or unrestricted mailbox access.

### 5.24 Capture an explicit Gmail source

With an active accepted Gmail-read connection, the coordinator can provide/select an exact message and optional attachment rather than granting an unrestricted inbox scan. They can review sender, subject, receipt time, provider message/thread/attachment identity, content hash, and captured immutable source.

The captured source then follows the same quarantine, extraction, evidence, interpretation, and approval flow as an uploaded JD. Disconnect, insufficient scope, missing message, changed connection revision, and provider/rate-limit failure produce explicit recoverable states.

### 5.25 Import a roster from Google Sheets

The coordinator can:

1. Select the exact spreadsheet and range.
2. Map columns.
3. Preview validation, duplicates, conflicts, and intended effects without committing.
4. Review the source fingerprint and expected academic revisions.
5. Commit only while the selected range and dependent records remain current.

If the sheet changed after preview, the commit is blocked and the coordinator must re-preview. Sheets remains a source, not the authoritative database.

### 5.26 Propose and execute an approved Sheets export

The coordinator can choose an authorized report/candidate schema, exact destination spreadsheet/range, frozen values, and audience. They can inspect spreadsheet-formula escaping and export row limits before submitting a specific write proposal.

After approval, execution rechecks authorization, proposal hash, connection revision, drive state, expiry, and dependencies. The coordinator sees completed, failed, retryable, or unknown provider outcome and reconciles uncertainty rather than overwriting blindly.

### 5.27 Propose Calendar events and reconcile external changes

For an approved published session revision, the coordinator can propose an event with:

- exact owned calendar;
- time, timezone, location/meeting data;
- attendee set;
- notification option: none, external attendees only, or all; and
- the invitation side effect disclosed in the proposal.

After exact approval, the coordinator can observe provider operation and stable mapping. They may register a time-limited Calendar change watch when configured. An external change creates a discrepancy/reconciliation need; it never silently overwrites PlacementOS's authoritative schedule.

### 5.28 Export operational data safely

With explicit export capability, the coordinator can:

- select a defined report/candidate schema and filters;
- see the drive, policy/evaluation revision, generation time, row count, and freshness;
- confirm the authorized scope;
- generate a controlled CSV or approved Sheets write; and
- access it for a limited lifetime with an audit record.

User-controlled spreadsheet cells are escaped against formula execution. Export quotas, stale data, missing capability, or unresolved scope block generation with a concrete reason.

### 5.29 Freeze reports and close, cancel, or reopen a drive

Before closure, the coordinator can inspect whether:

- registration is closed;
- all sessions are completed or cancelled;
- outcomes are recorded or explicitly unresolved;
- pending proposals are decided/cancelled;
- queued, claimed, failed, or unknown dispatch is resolved or documented;
- open exceptions satisfy closure policy; and
- required approvals and report dependencies are current.

The coordinator can freeze a deterministic reporting snapshot containing company/role, approved criteria, deadlines, funnel totals, document readiness, attendance/outcomes, delivery summary, unresolved cases, actor/time, and revision references.

With capability and an attributable reason, the coordinator can:

- close registration;
- complete and close the drive;
- cancel a drive while preserving history and separately proposing notices; or
- reopen a completed drive into a new revision.

Reopening does not erase the prior closure report. Closure is blocked by active or uncertain consequential work unless it is safely cancelled/reconciled or explicitly handled under the authorized closure policy.

### 5.30 Inspect history and audit evidence

Within authorized scope, a coordinator can inspect a chronological, revision-aware record of:

- source uploads and access;
- interpretations, clarifications, and corrections;
- policy review and approval;
- academic verification and evaluations;
- document findings and access;
- publication and registration changes;
- proposal decisions;
- provider claims and attempts;
- workflow holds/resumes/cancellation;
- schedules, attendance, results, and corrections;
- exports and integration changes;
- recovery steps; and
- closure, cancellation, and reopening.

History identifies actor/service, institution, action, resource, time, operation/correlation identifier, reason, and relevant before/after revisions. Sensitive details remain restricted and ordinary users cannot edit audit records.

## 6. Student capabilities

### 6.1 Confirm personal and academic profile

The student can inspect:

- institutional identifier;
- name and institutional email;
- branch/program and graduation year;
- academic metric, scale, and active backlog count;
- verification status and source;
- current academic revision; and
- pending or decided correction requests.

Unknown values are shown as unknown, not zero. The student cannot directly edit verified academic evidence or mark it verified.

### 6.2 Propose an academic correction

When a record is wrong or incomplete, the student can:

1. Select the field(s) needing correction.
2. Enter the proposed value.
3. Provide an evidence reference or supporting material as allowed.
4. Explain why the correction is required.
5. Submit the proposal.
6. Follow pending, approved, or rejected status and reviewer notes appropriate for student visibility.

The current verified value remains authoritative until an authorized reviewer approves evidence and creates a new revision. Approval may make prior eligibility stale; the student sees reevaluation/review state rather than an immediate invented result.

### 6.3 Browse relevant published opportunities

The student can see drives allowed by the institution's visibility policy. For each published opportunity they can inspect:

- company and role;
- employment type;
- location/work mode;
- compensation exactly as supplied and approved;
- student-visible eligibility requirements;
- required documents;
- registration/document openings and deadlines with timezone;
- recruitment stages/rounds when published;
- support contact or review path; and
- drive lifecycle state such as open, registration closed, in progress, completed, or cancelled.

Internal notes, confidential contacts, other students, draft revisions, unapproved changes, and internal exception details are not visible.

### 6.4 Understand personal eligibility

For each relevant evaluated drive, the student can see only their own:

- current status: `eligible`, `ineligible`, or `needs_review`;
- whether the result is current or awaiting reevaluation;
- plain-language explanation for every required predicate;
- known failures and unresolved evidence separately;
- policy/evaluation reference in understandable terms; and
- next action, if one exists.

`Needs review` explains which evidence is missing, invalid, unverified, contradictory, or on an unsupported scale. It is not presented as rejection. An ineligible result shows source-backed deterministic reasons without exposing internal notes or another student's data.

### 6.5 Request eligibility evidence review

The student can describe which academic evidence should be checked and submit a review request tied to the current result. They can see that the request was recorded and whether it is pending or resolved.

The request does not override eligibility. Resolution occurs through a verified academic correction, a corrected approved policy, or documented review of an unsupported case.

### 6.6 Understand the document checklist

For a drive, the student can see:

- every required document type and accepted label;
- formats, size, filename guidance, and deadline;
- whether it is required at registration or later before scheduling;
- the current document revision, if any;
- validation progress and findings safe for student disclosure;
- readiness as `ready`, `pending`, `blocked`, or `needs_review`; and
- the exact remediation needed, such as replace corrupt PDF or submit missing marksheet.

The checklist must not imply authenticity verification when only structural/security checks occurred.

### 6.7 Upload and replace personal documents

The student can:

1. Select a required document category.
2. Choose a file for their own record.
3. See immediate type/size/name validation.
4. Upload through the private, quarantined flow.
5. Follow malware scan, integrity, MIME/signature, parsing, and review progress.
6. Replace a failed or outdated file with a new revision.
7. Review upload history and privately download an authorized own revision.

A replay cannot silently replace an accepted revision. Quarantined files are not previewable. Replacing a file preserves the old audit history and recalculates readiness from the new current revision.

### 6.8 Save a registration draft

The student can save an intention to participate while evidence or documents are still under review. The draft shows unmet prerequisites and does not claim a completed registration.

Saving a draft does not reserve a place, bypass a deadline, or make the student interview-ready.

### 6.9 Submit registration

The student can submit once when all required conditions are current:

- the drive revision is published;
- the registration window satisfies `opens_at <= server time < deadline_at`;
- current deterministic eligibility is `eligible`;
- documents required at submission are ready; and
- no drive hold/cancellation or stale dependency prevents the action.

On success, the student sees an immutable confirmation with submission time and current state. Repeated clicks or retries return the existing registration instead of creating duplicates.

When submission is blocked, the student sees the specific reason: not open yet, deadline passed, current result unavailable/stale, ineligible, needs review, required document missing/failed, drive on hold, or drive cancelled.

### 6.10 Track post-registration readiness

After submission, the student can see:

- registration remains submitted;
- documents that are permitted after registration but due before scheduling;
- current readiness and deadlines;
- whether eligibility changes placed the registration on hold; and
- what evidence or coordinator review is needed next.

A pending later document is not shown as a failed registration. An eligibility hold preserves the original submission evidence.

### 6.11 Withdraw or request assisted withdrawal

Before the configured withdrawal cutoff, the student can withdraw with a reason and see the recorded state. After the cutoff, direct withdrawal is unavailable and the student is directed to request coordinator assistance.

The history retains the prior submission and withdrawal event. Withdrawing does not erase uploaded documents or audit evidence according to retention policy.

### 6.12 View personal published schedule

The student sees only approved assignments for them, including:

- drive and round;
- date, start/end time, and timezone;
- venue or meeting link;
- current schedule revision/status; and
- an approved correction when rescheduled.

Draft sessions and other participants are hidden. A schedule change remains distinguishable from the prior assignment and any notification delivery state.

### 6.13 View personal published outcomes

The student can see only their own explicitly published employer outcome revision. They can understand:

- the round or process stage;
- outcome such as advanced, rejected, waitlisted, selected, or withdrawn;
- whether a later correction superseded the prior published result; and
- any approved next-step information.

Internal draft outcomes are invisible. `Selected` does not claim that a formal offer exists, was accepted, or led to joining unless those separate facts are explicitly recorded and published.

### 6.14 Receive approved communications safely

The student may receive approved announcements, reminders, schedule updates, result notices, or corrections through configured channels. Messages:

- contain only the recipient's own personalized values;
- do not expose a bulk recipient list;
- use the exact approved wording and sender;
- state relevant deadline/timezone and support contact; and
- may have a delivery state independent of what the application displays internally.

The student experience should not claim delivery merely because a provider accepted the message. Important published information remains available in the authenticated application even when email fails.

### 6.15 Request help without gaining internal access

The student can use the visible support/review path for academic evidence, document remediation, registration assistance, or schedule/result clarification. They receive a reference or confirmation appropriate to the request.

Support does not expose internal exception plans, other students' cases, coordinator-only notes, model prompts, provider tokens, or workflow/checkpoint details.

### 6.16 Review own activity and privacy boundaries

Where enabled, the student can see a safe subset of their own meaningful activity: correction submitted/decided, document uploaded/replaced, registration submitted/withdrawn/held, schedule published/revised, and result published/corrected.

The application should explain that records are institution-managed, show the configured support/privacy contact, and never make unsupported legal-compliance claims. Data export or deletion requests, if later supported, must follow institution policy and must not be inferred from the current MVP.

## 7. Cross-role end-to-end flows

### 7.1 New drive from JD to student registration

1. Coordinator creates a draft drive.
2. Coordinator uploads/pastes/captures a JD source.
3. System validates and extracts it; coordinator handles any failure.
4. AI or fixture proposes structured facts, or coordinator enters them manually.
5. Coordinator verifies evidence, resolves ambiguities, and records corrections.
6. System compiles a deterministic policy.
7. Authorized coordinator approves the exact policy.
8. Coordinator runs evaluation over a verified cohort and reviews all three outcomes.
9. Coordinator defines document requirements.
10. Coordinator prepares and approves the student-visible drive revision.
11. Coordinator drafts an announcement and freezes audience/content.
12. Authorized coordinator approves the exact communication.
13. Worker dispatches safely; coordinator monitors partial/uncertain outcomes.
14. Student sees the published opportunity and personal eligibility.
15. Student resolves required evidence/documents and submits registration.
16. Coordinator monitors registrations and readiness without changing academic decisions.

### 7.2 Student academic correction and reevaluation

1. Student sees a wrong, missing, or unverified academic value.
2. Student proposes an exact correction with explanation/evidence.
3. Reviewer compares current and proposed values.
4. Reviewer approves or rejects with an attributable note.
5. Approval creates a new verified academic revision.
6. Dependent evaluation becomes stale.
7. Coordinator reevaluates the student/cohort under the current approved policy.
8. Student sees the new deterministic result and explanation.
9. Any held registration is resolved through an explicit audited transition.

### 7.3 Criteria or deadline changes after notification

1. Coordinator adds revised source evidence or proposes a change with reason.
2. System creates a new revision and shows old/new values.
3. Deterministic impact analysis identifies evaluations, registrations, schedules, proposals, recipients, and provider mappings affected.
4. Coordinator reviews and approves the new exact policy/publication as applicable.
5. Pending actions tied to old dependencies become stale; completed effects remain in history.
6. Eligibility is recomputed from current verified evidence.
7. Existing registrations that no longer qualify move to `eligibility_hold`, not deletion.
8. Coordinator reviews a bounded recovery plan.
9. Correction messages or schedule changes enter their own approval flows.
10. Students see only approved current facts and their own resulting state.

### 7.4 Ambiguous email/provider outcome

1. Provider request times out after acceptance may have occurred.
2. Operation becomes `unknown`; automatic retry stops.
3. Coordinator sees recipient, attempt, provider identifiers, and ambiguity reason.
4. Coordinator/provider reconciliation determines accepted or confirmed not accepted.
5. If accepted, history records provider acceptance without inventing delivery.
6. If confirmed not accepted and still authorized/current, a bounded retry may proceed.
7. If evidence remains unavailable, the exception stays visible for manual handling.

### 7.5 Scheduling through published result

1. Coordinator defines ordered rounds and drafts a session.
2. Coordinator assigns qualifying registered students.
3. System detects capacity, participant, venue, and panel conflicts.
4. Coordinator resolves conflicts and submits the exact schedule revision.
5. Authorized reviewer publishes it.
6. Student sees only their approved assignment.
7. Coordinator records attendance independently.
8. Coordinator records employer outcome with source.
9. Authorized reviewer publishes the exact result revision.
10. Student sees only their published outcome.
11. Corrections create new revisions and separate notices when needed.

### 7.6 Drive closure and reopening

1. Coordinator closes registration.
2. System checks session, outcome, proposal, dispatch, and exception prerequisites.
3. Coordinator resolves or explicitly documents allowed unresolved work.
4. System freezes reproducible report totals and revision references.
5. Authorized coordinator closes the drive with reason.
6. Ordinary mutation becomes restricted; history/report remain available.
7. If reopening is authorized, coordinator supplies reason and creates a new revision.
8. Prior closure evidence remains intact.

### 7.7 Google Sheets import/export

1. Coordinator explicitly connects the needed Sheets capability.
2. For import, they select range, map columns, preview, resolve errors, and commit only if the fingerprint remains current.
3. Imported records become authoritative only after the normal verified import service succeeds.
4. For export, they select exact schema, destination, and frozen data.
5. Export write receives exact approval.
6. Worker executes idempotently and coordinator sees provider outcome/reconciliation state.

### 7.8 Google Calendar publication

1. Internal session is drafted, checked, approved, and published first.
2. Coordinator selects exact owned calendar and notification behavior.
3. Calendar payload and attendee side effects are frozen in a proposal.
4. Authorized coordinator approves the external write.
5. Worker creates/updates idempotently and stores provider mapping.
6. External change notifications create reconciliation work rather than silently changing the internal session.

## 8. Visible state dictionary

Future interface language should preserve these meanings.

| Domain object | States users may need to distinguish |
| --- | --- |
| Drive | `draft`, `published`, `registration_closed`, `in_progress`, `completed`, `archived`, `cancelled`; operational hold is separate. |
| Workflow | `queued`, `running`, `waiting_clarification`, `waiting_rule_approval`, `waiting_action_approval`, `monitoring`, `failed_retryable`, `failed_terminal`, `completed`, `cancelled`, plus held context. |
| Policy | `draft`, `in_review`, `approved`, `superseded`, `rejected`. |
| Proposal | `draft`, `pending_approval`, `approved`, `rejected`, `stale`, `expired`, `cancelled`, `executing`, `partially_executed`, `executed`, `failed`. |
| Approval decision | `approved`, `rejected`, `revision_requested`; authorization can later expire or become invalid. |
| Eligibility | `eligible`, `ineligible`, `needs_review`; freshness/currentness is separate. |
| Document validation | `pending`, `validating`, `passed`, `failed`, `needs_review`, `quarantined`, `superseded`. |
| Document readiness | `ready`, `pending`, `blocked`, `needs_review`. |
| Registration | `draft`, `submitted`, `withdrawn`, `eligibility_hold`, `cancelled`. |
| Notification recipient | `pending`, `claimed`, `provider_accepted`, `delivered`, `failed_retryable`, `failed_permanent`, `unknown`, `cancelled`. |
| Session | `draft`, `published`, `completed`, `cancelled`; revision/freshness is separate. |
| Attendance | `not_recorded`, `present`, `absent`, `excused`. |
| Employer outcome | `pending`, `advanced`, `rejected`, `waitlisted`, `selected`, `withdrawn`; draft/published is separate. |
| Exception | `open`, `triaged`/`acknowledged`, `plan_proposed`, `waiting_approval`, `executing`, `resolved`, `dismissed`. |
| Recovery step | `pending`, `running`, `completed`, `failed`, `stale`, `cancelled`; partial plan execution must remain visible. |
| Provider connection | configuration pending, active, expired/insufficient permission, disconnected/revoked, or failed; connection revision matters. |
| External operation | pending/queued, claimed, succeeded/provider accepted, retryable failure, permanent failure, unknown, cancelled/stale. |

State copy should use plain language while retaining exact meaning. Historical and stale objects must never look current merely because they once succeeded.

## 9. Failure, conflict, and recovery use cases

The UI direction derived from this document must account for at least these non-happy paths:

- unauthenticated, expired session, revoked membership, missing capability, or wrong institution;
- no data yet in a production-empty institution;
- open-drive/import/export quota exceeded;
- duplicate or concurrently modified student import;
- unknown branch alias or unsupported academic scale;
- corrupt, encrypted, scanned, over-limit, quarantined, or MIME-mismatched source/document;
- extraction timeout, model unavailable, invalid structured output, unsupported claim, or prompt-injection content;
- unresolved date-only deadline or contradictory criteria;
- invalid/empty policy or stale policy approval;
- evaluation queued, failed, or stale after evidence/policy change;
- document still validating, replacement superseding old readiness, or deadline passed;
- registration not open, exactly at/after cutoff, stale eligibility, duplicate submit, or hold;
- changed content/audience/dependency during approval;
- provider transient/permanent failure, rate limiting, partial batch, or unknown outcome;
- cancellation racing with in-flight external work;
- simultaneous workflow resume or incompatible workflow version;
- schedule capacity/participant/panel/venue conflict;
- corrected published result;
- recovery plan partially executed or made stale by a newer event;
- OAuth permission denied/expired, disconnect, connection revision changed, or webhook discrepancy;
- Sheet changed after preview;
- Calendar changed externally;
- closure blocked by unresolved sessions, outcomes, proposals, dispatch, or exceptions; and
- report/export too large, stale, unauthorized, or unavailable.

Each case needs a specific explanation, preserved user input where safe, a permitted next action, and a correlation/reference identifier when support may be needed.

## 10. Environment and production-transition disclosures

The user experience must make the active operating mode unambiguous:

- development personas are visibly development-only;
- fixture interpretation/planning is visibly synthetic and rejected in production;
- a mail sink is visibly not live email;
- disconnected or unaccepted Google capabilities are not advertised as operational;
- model-disabled mode offers manual structured entry rather than pretending AI ran;
- production readiness shows unresolved OIDC, storage, scanner, mail, model, retention, backup, worker, or operating-owner gates;
- real model calls expose useful processing status without showing secrets, full prompts, raw private documents, or token credentials; and
- no production workflow depends on pre-seeded demo records.

The production-transition phases in `AI Provider Integration.md` add real model/provider operation, real identity and data onboarding, production infrastructure, shadow evaluation, and controlled launch. They do not change the authority boundaries described here.

## 11. Deliberately excluded user capabilities

Do not derive UI for these features unless scope is separately approved:

- recruiter/employer login or employer portal;
- automated employer hiring decisions;
- resume ranking or automatic candidate rejection;
- personality, protected-attribute, facial, biometric, or forged-document scoring;
- AI-established academic eligibility;
- arbitrary per-student eligibility override;
- AI bypass of document security findings;
- unrestricted mailbox scanning;
- unrestricted Gmail-send, Drive, shell, SQL, or storage-administration access;
- autonomous correction email or Calendar execution;
- public student directory;
- payment workflows;
- WhatsApp or SMS automation;
- general-purpose autonomous assistant;
- silent deadline extension, silent schedule change, or deletion of historical effects; or
- claims of legal compliance, document authenticity, message delivery, formal offer, acceptance, or joining without corresponding evidence.

## 12. Feature-to-requirement traceability

| Feature family | Canonical requirement groups |
| --- | --- |
| Identity, membership, permissions, tenant scope | `FR-ID`, `INV-06`, `INV-10` |
| Student import, records, corrections | `FR-STU`, `INV-02`, `INV-09` |
| JD source intake and extraction | `FR-JD`, `INV-03`, `INV-10` |
| AI/manual structured interpretation | `FR-AI-JD`, runtime AI constraints |
| Policy review and deterministic eligibility | `FR-POL`, `FR-ELIG`, `INV-01`, `INV-02`, `INV-11` |
| Documents and readiness | `FR-DOC`, `INV-10`, `INV-12` |
| Publication, registration, withdrawal | `FR-REG`, `INV-05`, `INV-11` |
| Communication drafting and audiences | `FR-COM`, `INV-04`, `INV-10` |
| Approval and dispatch | `FR-APP`, `FR-DISP`, `INV-04`, `INV-05`, `INV-07`, `INV-08`, `INV-12` |
| Workflow holds, resume, retry, monitoring | `FR-WF`, `INV-08`, `INV-09` |
| Scheduling, attendance, results | `FR-SCHED`, `FR-RESULT`, `INV-11`, `INV-12` |
| Exceptions and recovery plans | `FR-EXC`, P12 recovery boundary |
| Gmail, Sheets, Calendar | `FR-INT`, P11 connector boundary |
| Reporting, exports, audit, closure | `FR-AUD`, `FR-REPORT`, `FR-CLOSE` |
| Quotas, measured scaling, recovery evidence | P13 operating policy and measured-expansion boundary |

## 13. Definition of completeness for later UI planning

A future UI direction based on this catalogue is incomplete if it only covers successful coordinator setup. It must account for:

- both primary roles and their privacy boundaries;
- capability-based authorization, not role labels alone;
- production-empty onboarding and meaningful empty states;
- manual fallback for AI/provider failure;
- review of evidence beside suggested facts;
- exact approval and revision invalidation;
- all three eligibility outcomes and predicate explanations;
- document, registration, eligibility, scheduling, result, and delivery states independently;
- asynchronous progress and safe recovery after refresh/restart;
- stale, partial, unknown, conflict, hold, cancellation, and reconciliation states;
- current versus historical revisions;
- internal versus published information;
- connector unavailable/disconnected/expired states;
- closure prerequisites and reproducible reports;
- accessible interaction and mobile/responsive use; and
- explicit environment/provider disclosure so fixtures cannot masquerade as production.

This behavioural catalogue should be treated as the source input for later journey mapping, information architecture, screen inventory, content design, permissions mapping, and interface acceptance scenarios.
