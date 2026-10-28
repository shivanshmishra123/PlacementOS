# PlacementOS: Product Specification

> Planning baseline dated 28 October 2026. This is a detailed implementation specification derived from the three supplied project inputs. It describes intended behavior; no feature is implemented merely because it appears here.

## 1. Product definition

PlacementOS is an operations platform for a college placement cell. It turns recruitment information received from a company into a reviewed, executable campus recruitment drive. It helps coordinators organize eligibility, student documents, announcements, registrations, assessment and interview schedules, results, and the final drive report.

The central product promise is: **a coordinator can manage an entire recruitment drive from one traceable workspace, with AI preparing interpretations and drafts, deterministic services enforcing rules, and authorized people approving consequential actions.**

The system is not the employer's selection authority. It records employer outcomes and applies approved institutional/company rules. It does not invent hiring criteria, rank students by inferred suitability, or promise that a technically valid document is authentic.

### 1.1 Source material and interpretation

| Source | Requirements carried forward |
| --- | --- |
| `Description.txt` | The placement coordinator's problem, JD extraction, deterministic eligibility, missing-data review, document validation, approved communications, durable orchestration, and advanced exception recovery. |
| `Agents detail.png` | Next.js frontend; FastAPI backend; LangGraph orchestration; specialized JD, document, communication, and exception components; deterministic services; approval enforcement; PostgreSQL; object storage; email, Sheets, and Calendar integration boundaries. |
| `Workflow detail.png` | Intake, extraction, requirements clarification loop, coordinator rule approval, eligibility evaluation, document verification, communication drafting and revision, human approval, notification dispatch, registration/event tracking, and drive closure/reporting. |

The clarification loop produces a request for human review or a clarification draft; it does not authorize automatically emailing a company. The rule-approval gate and communication-approval gate are distinct. Document checks can occur before an invitation and repeat after new submissions. Monitoring is an event-driven process that can last days or weeks.

### 1.2 Status of added detail

The source fixes the product direction and primary stack. The exact permissions, schemas, statuses, limits, API behavior, and delivery sequence below are **design baselines** that make implementation concrete. Institution-specific placement policies, identity provider, retention periods, actual deadlines, and production providers remain configuration decisions.

Technical design is canonical in [Architecture.md](Architecture.md); execution order is canonical in [PLAN.md](PLAN.md); coding-agent instructions are in [Agents.md](Agents.md).

## 2. Problem and desired outcomes

A coordinator currently reads PDFs and emails, extracts criteria, compares spreadsheets, identifies missing documents, composes messages, collects registrations, reconciles scheduling changes, and records results across disconnected tools. This creates repeated transcription, inconsistent criteria, outdated recipient lists, unclear deadlines, duplicated messages, and weak evidence of who approved an action.

PlacementOS should produce these outcomes:

1. A reviewed structured drive record linked to the original recruitment information.
2. Reproducible eligibility results with understandable reasons for each student.
3. A separate, accurate view of document readiness and registration progress.
4. Messages that use approved facts and reach an approved, explainable audience.
5. Persistent workflow progress that survives restarts and human response delays.
6. Clear handling of changed criteria, records, deadlines, schedules, and delivery failures.
7. A defensible operational history and final report.

### 2.1 Success measures

Establish a manual-work baseline before a pilot. Measure coordinator minutes from JD receipt to reviewed announcement, percentage of extracted material fields corrected, unresolved eligibility cases, student document completion, approval turnaround, delivery failures, and reconciliation work.

Safety acceptance is absolute for the tested release: no unapproved external actions, no known cross-institution or cross-student exposure, and no eligibility decision attributed to an LLM. Efficiency targets are hypotheses until measured; do not advertise a specific percentage improvement without pilot evidence.

## 3. Users, roles, and access

### 3.1 Personas

- **Placement coordinator:** owns drives, reviews sources and proposed rules, resolves academic-data issues, approves messages, manages schedules and results, and closes drives.
- **Institution administrator:** manages membership, institution configuration, identity/integration setup, and operational access. This role does not automatically grant approval rights over recruitment actions.
- **Student:** maintains their own profile, proposes academic corrections, sees published opportunities and their eligibility reasons, submits documents, registers, and follows personal schedules/results.
- **Read-only auditor:** inspects authorized institutional history and reports. This is optional for the pilot and does not bypass file restrictions.
- **System worker:** a noninteractive service principal that executes narrowly scoped, already authorized operations. It is not a superuser or a human approver.

There is no employer/recruiter login in the MVP. Coordinators enter externally supplied results and clarifications with provenance.

### 3.2 Permission matrix

| Operation | Student | Assigned coordinator with capability | Institution administrator | Auditor |
| --- | --- | --- | --- | --- |
| View own profile/documents/registrations | Yes | Within authorized drive/record scope | Only with explicit record-access capability | Explicit read scope only |
| Propose own academic correction | Yes | Can review/verify | If granted verification capability | No |
| Import or verify academic records | No | With records capability | With records capability | No |
| Create/review a drive | No | Yes | Only if also assigned coordinator capability | Read only |
| Approve rules, publication, messages, changes | No | Explicit approval capability required | No automatic right | No |
| Register or withdraw | Own registration only | Assisted action with reason | No automatic right | No |
| Manage institutional settings | No | Limited configured settings | Yes | No |
| Export a candidate list/report | Own data export if supported | Explicit export capability | Explicit export capability | Explicit export capability |
| Inspect audit records | Own visible activity only | Authorized drive scope | Authorized institutional scope | Authorized scope |

Membership can have several capabilities. Drive assignment and institutional membership must both be valid. A coordinator may review their own draft in the pilot because a placement cell may have one coordinator; the decision is still explicit and audited. Optional dual review is a later configurable policy, not an MVP prerequisite.

## 4. Release scope

### 4.1 MVP: complete drive using controlled adapters

- Institutional sign-in and role/object authorization.
- CSV student import with preview, verification, and revision history; manual correction review.
- PDF/DOCX JD upload and pasted email-text intake.
- Text extraction, structured AI interpretation, evidence locators, clarification tasks, and manual entry fallback.
- Review and approval of drive facts and a versioned eligibility policy.
- Deterministic cohort evaluation and student-facing reasons.
- Student portal, document upload/checks, registration, and withdrawal.
- Email templates/AI drafts, exact audience preview, approval, and queued dispatch through a mail adapter.
- Persistent LangGraph workflow with rule and action approval pauses.
- Basic manually configured rounds, sessions, venue/panel/student conflict detection, attendance, results, and closure reports.
- Audit trails, retry/reconciliation controls, synthetic demo data, and operational health visibility.

Local development uses a mail sink; a real-data pilot additionally requires an explicitly configured production mail adapter, identity provider, malware scanning, backups, and the readiness gate in Section 22.

### 4.2 Subsequent releases

1. Explicit selection of a JD email from a connected Gmail account.
2. Controlled Google Sheets imports/exports with revision-aware reconciliation.
3. Approved Google Calendar event creation/update, with invitation side effects disclosed.
4. Structured change-impact workflows and the advanced Exception Resolution Agent.
5. More complex institutional policies, advanced scheduling, and broader deployment support when justified.

### 4.3 Out of scope unless separately approved

Automated employer decisions, resume ranking, inferred personality or protected-attribute screening, biometric checks, forged-document adjudication, payment flows, public student directories, a general employer ATS, unrestricted mailbox ingestion, WhatsApp/SMS integrations, and fully autonomous exception execution.

## 5. Domain glossary

| Term | Meaning |
| --- | --- |
| Institution | The data-isolation and policy boundary, initially one college per deployment/pilot. |
| Drive | One recruitment opportunity and its operational lifecycle; MVP has one primary role per drive. |
| Source artifact | An immutable uploaded file or captured email/text source with content hash and provenance. |
| Extraction revision | One parser/model interpretation of a source, distinct from approved facts. |
| Drive revision | An immutable published or reviewable version of company, role, deadlines, requirements, and process details. |
| Eligibility policy | A typed, versioned rule set derived from reviewed company requirements and explicit institutional configuration. |
| Academic revision | A verified snapshot of student academic evidence; unverified proposals are separate. |
| Cohort snapshot | The exact students and academic revisions included in an evaluation run. |
| Eligibility result | `eligible`, `ineligible`, or `needs_review`, with predicate-level reasons. |
| Document readiness | Whether the required accepted document revisions are present and pass configured operational checks. |
| Proposal | An immutable revision of an action awaiting authorization, such as publishing a drive or sending messages. |
| Approval | An attributable decision binding an authorized person to a particular proposal and dependency fingerprint. |
| Workflow run | A durable orchestration instance that coordinates a drive's current processing revision. |
| Outbox | Durable database work records committed alongside the domain action before queue/provider execution. |
| Exception case | A tracked disruption or discrepancy with an owner, evidence, resolution plan, and resolution state. |

## 6. End-to-end journeys

### 6.1 Coordinator creates and launches a drive

1. Sign in and select the active institution.
2. Create a draft drive; upload the JD or paste email content.
3. See upload validation and extraction progress. On failure, retry a bounded operation or enter facts manually.
4. Review company, role, compensation, work location, criteria, required documents, deadlines, and rounds beside their source evidence.
5. Resolve material ambiguities; record external clarification if obtained. A clarification email is a separate approved communication.
6. Review the normalized policy and its human-readable equivalent; approve that exact policy and drive revision.
7. Evaluate a verified student cohort. Inspect eligible, ineligible, and needs-review groups and individual reason codes.
8. Review existing document readiness without changing academic decisions.
9. Prepare a student-visible publication and registration window. Approve publication separately from outgoing announcements.
10. Prepare an announcement using approved facts, an explicit audience policy, registration link, deadline/timezone, and document instructions.
11. Preview exact recipients, exclusions, rendered content, sender identity, and dependencies; approve or request revision.
12. Observe dispatch progress and partial failures. Track registrations, document submissions, and reminders.
13. Configure/publish sessions, record attendance and company results, resolve open work, then close the drive and generate a versioned report.

### 6.2 Student participates

1. Sign in to a preauthorized institution membership and confirm their profile.
2. View published drives relevant to their cohort, with the institution's configured visibility policy.
3. See their own eligibility status and explanations. A needs-review result explains which evidence is unresolved and offers a correction/review request.
4. Upload required files and see validation progress, actionable errors, and the accepted revision.
5. If academically eligible and the registration window is open, submit one registration; document readiness may remain pending if the drive allows later completion.
6. Correct failed documents before the document deadline, see schedules assigned to them, and receive approved updates.
7. Withdraw before the allowed cutoff, or request coordinator assistance after the cutoff. See only results explicitly published to them.

### 6.3 Criteria change after students were notified

1. A coordinator uploads a revised source or proposes a criterion change with a reason.
2. The system creates a new revision, shows the old/new facts, and identifies affected evaluations, proposals, registrations, schedules, and recipients.
3. A coordinator approves the revised rule set. Pending actions tied to old dependencies become stale; already sent messages remain in history.
4. Recompute affected results. Preserve prior decisions as historical evidence.
5. Registrations that no longer meet the current rules enter `eligibility_hold`; do not delete them or silently send rejection notices.
6. Propose correction communications and schedule changes, each requiring specific approval.
7. Resume operations with a clear history of what changed and what was executed.

The MVP supports revisioning, stale detection, and manual resolution. Automated impact proposals are expanded in the later exception phase.

## 7. Lifecycle and state semantics

Maintain separate state machines. Do not use one drive-status field to represent model work, eligibility, document readiness, delivery, and registration simultaneously.

| Aggregate | States and meaning |
| --- | --- |
| Drive lifecycle | `draft` -> `published` -> `registration_closed` -> `in_progress` -> `completed` -> `archived`; `cancelled` is an authorized terminal alternative. |
| Workflow run | `queued`, `running`, `waiting_clarification`, `waiting_rule_approval`, `waiting_action_approval`, `monitoring`, `failed_retryable`, `failed_terminal`, `completed`, `cancelled`. |
| Policy version | `draft`, `in_review`, `approved`, `superseded`, `rejected`. An approved version is immutable. |
| Proposal | `draft`, `pending_approval`, `approved`, `rejected`, `stale`, `expired`, `cancelled`, `executing`, `partially_executed`, `executed`, `failed`. |
| Approval decision | `approved`, `rejected`, `revision_requested`; the associated authorization may later expire or be invalidated. |
| Eligibility | `eligible`, `ineligible`, `needs_review`. Evaluation processing state belongs to its job/run. |
| Document validation | `pending`, `validating`, `passed`, `failed`, `needs_review`, `quarantined`. Older revisions can be `superseded`. |
| Document readiness | `ready`, `pending`, `blocked`, `needs_review`; computed from required accepted revisions and deadlines. |
| Registration | `draft`, `submitted`, `withdrawn`, `eligibility_hold`, `cancelled`. Scheduling and selection results are separate. |
| Notification recipient | `pending`, `claimed`, `provider_accepted`, `delivered`, `failed_retryable`, `failed_permanent`, `unknown`, `cancelled`. Delivery is recorded only when supported by reliable evidence. |
| Session | `draft`, `published`, `completed`, `cancelled`. Rescheduling creates a new revision. |
| Exception case | `open`, `triaged`, `plan_proposed`, `waiting_approval`, `executing`, `resolved`, `dismissed`. |

`published` means student-visible approved facts exist, not that every notification was delivered. A published drive remains published while a revised policy is being reviewed; affected operations can be placed on an explicit operational hold. `completed` requires closure checks; `archived` restricts ordinary mutation but does not bypass retention rules.

## 8. Functional requirements: identity and student data

### FR-ID: identity and institutional access

- **FR-ID-01:** Support OIDC sign-in through a configured provider, mapped to preauthorized/invited institutional membership. A verified email domain alone must not grant coordinator privileges.
- **FR-ID-02:** Support role/capability checks, drive assignments, session expiry, logout, and membership revocation. Revocation must block future commands and unclaimed external actions.
- **FR-ID-03:** Enforce institution and object scope on lists, direct-ID reads, mutations, exports, downloads, jobs, and workflow resumes.
- **FR-ID-04:** Provide a clearly isolated development identity adapter with seeded personas. It must not be enabled in a production environment.

### FR-STU: student records

- **FR-STU-01:** Import CSV using a preview, column mapping, row validation, duplicate review, and explicit commit. The original import and a row-level result report remain attributable.
- **FR-STU-02:** Store institutional student identifier, name, institutional email, branch/program, graduation year, academic metric and scale, active backlog count, verification state, and source. Other fields are collected only when required by approved policy.
- **FR-STU-03:** Distinguish absent values from zero, false, or an empty list. Unknown backlog status is not equivalent to zero backlogs.
- **FR-STU-04:** Normalize branch codes through a reviewed institution mapping. Unknown aliases require review; do not use fuzzy model output to silently map a branch.
- **FR-STU-05:** Student corrections create proposals. An authorized records reviewer verifies the evidence and creates a new academic revision before it can affect eligibility.
- **FR-STU-06:** Detect concurrent edits and imports with optimistic revision checks. A stale import must not overwrite a newer verified record.
- **FR-STU-07:** Provide searchable, filterable, paginated coordinator views and a student view limited to the current student's data.

Acceptance: two institutions may use the same student number without collision; a student cannot retrieve another student's record by guessing an ID; duplicate import commit requests cannot create duplicate students; a changed verified CGPA creates a new revision and stales dependent results.

## 9. Functional requirements: intake and JD intelligence

### FR-JD: sources and extraction

- **FR-JD-01:** Accept PDF, DOCX, and pasted email text in the MVP. Capture original filename, media type, hash, uploader, timestamp, institution, and optional sender/received metadata.
- **FR-JD-02:** Validate size, file signature, container integrity, parser limits, and scan status before processing. Use private storage and immutable accepted versions.
- **FR-JD-03:** Extract text with page locators for PDFs and paragraph/section locators for DOCX/text. Retain the parser version and whether OCR was used.
- **FR-JD-04:** Route empty/scanned, encrypted, corrupt, unsupported, or conflicting sources to explicit errors or manual review. Scanned content is not automatically an invalid JD; OCR is a later adapter or a manual fallback in the MVP.
- **FR-JD-05:** Deduplicate identical source uploads within authorized scope while preserving distinct user intent and provenance. Do not reveal that another institution uploaded the same file.
- **FR-JD-06:** Treat multiple attachments as distinct evidence. Do not silently choose the newest filename as authoritative when facts conflict.

### FR-AI-JD: structured interpretation

- **FR-AI-JD-01:** Produce validated structured fields for company, role, employment type, location/work mode, compensation, eligibility, document requirements, registration dates, selection process, contact, and unresolved questions.
- **FR-AI-JD-02:** Attach a source locator and concise supporting excerpt to each material extracted fact. Unsupported model claims cannot enter an approved policy without an attributed human correction.
- **FR-AI-JD-03:** Preserve stated compensation wording and distinguish fixed pay, variable pay, benefits, CTC, currency, and period when explicitly present. Do not treat annual CTC as monthly take-home salary.
- **FR-AI-JD-04:** Represent uncertain or absent facts explicitly. Date-only deadlines remain unresolved until a coordinator supplies a time and timezone or confirms an institutional convention with attribution.
- **FR-AI-JD-05:** Identify conflicting criteria and material ambiguity. Approval is blocked while required ambiguities remain unresolved.
- **FR-AI-JD-06:** Support field-level coordinator correction, rationale, and before/after history; preserve the underlying extraction revision.
- **FR-AI-JD-07:** Support a manual structured-entry path when a model is unavailable or its output fails validation. The same approval and policy validation apply.
- **FR-AI-JD-08:** Record model/provider identifier, prompt/schema version, latency, token/cost metadata if available, and extraction outcome without exposing private source text in general logs.

Example interpretation only; this fictional example does not establish a live drive or a default deadline:

```json
{
  "company_name": "Nexora Technologies",
  "role_title": "Software Development Engineer",
  "eligibility_draft": {
    "allowed_branches": ["CSE", "IT"],
    "minimum_cgpa": "7.50",
    "cgpa_scale": "10.00",
    "graduation_years": [2027],
    "maximum_active_backlogs": 0
  },
  "registration_deadline": {
    "source_date": "2026-11-05",
    "confirmed_instant": null,
    "timezone": null
  },
  "requires_clarification": true,
  "clarifications": ["Confirm registration cutoff time and timezone"],
  "evidence": [
    {
      "field_path": "eligibility_draft.minimum_cgpa",
      "source_artifact_id": "example-source-1",
      "locator": {"kind": "pdf_page", "page": 2},
      "excerpt": "Minimum CGPA: 7.5 on a 10-point scale"
    }
  ]
}
```

The sample uses string decimals to preserve precision. Real IDs follow the architecture contract. Source locators use human-visible page numbering and must map to the actual extracted artifact.

Acceptance: an absent deadline time is not filled by the model; contradictory CGPA values create a blocking clarification; a coordinator can finish a drive review when the model is unavailable; instructions embedded in a JD cannot call tools, change permissions, or approve a proposal.

## 10. Functional requirements: policy and deterministic eligibility

### FR-POL: rule authoring and approval

- **FR-POL-01:** Support explicit branch scope, graduation cohorts, minimum CGPA with scale, and maximum active backlog count in the MVP.
- **FR-POL-02:** Support `all_verified_branches` as an explicit approved choice; an absent branch restriction is unresolved until reviewed. Do not interpret an absent list as either none or everyone.
- **FR-POL-03:** Permit a criterion to be explicitly `not_required` with provenance. An unsupported criterion in a JD blocks policy approval until it is deterministically modeled or source-backed clarification confirms it does not apply. Keep the drive on a review hold; do not silently omit the criterion.
- **FR-POL-04:** Validate numeric ranges, scale compatibility, nonempty scopes, required evidence, and logical consistency before policy approval. Require at least one supported required academic predicate; an empty or entirely `not_required` policy is invalid in the MVP.
- **FR-POL-05:** Show a human-readable rule summary, source evidence, affected cohort, version, and reviewer identity at approval. Approved policy versions are immutable.
- **FR-POL-06:** Institutional policies such as one-offer restrictions, placement caps, percentages, or CGPA conversion formulas are deferred until explicitly configured and implemented. Do not hardcode them from assumptions about a college.

### FR-ELIG: evaluation and explanation

- **FR-ELIG-01:** Evaluate only a validated, approved policy using verified academic revisions. Snapshot the cohort, academic revisions, normalization configuration, and engine version.
- **FR-ELIG-02:** Evaluate every required predicate as `true`, `false`, or `unknown`, with machine-readable reason codes and a student-readable explanation.
- **FR-ELIG-03:** Apply the aggregation rule in Section 10.1 consistently in backend, UI labels, tests, exports, and reports.
- **FR-ELIG-04:** Persist immutable per-student results under an evaluation run; repeat evaluation of identical inputs must produce identical outcomes and explanations.
- **FR-ELIG-05:** Show counts and filters for all three outcomes and drill down to predicate-level evidence. The UI may explain but cannot recompute an alternative authoritative result.
- **FR-ELIG-06:** Mark results stale when a policy or relevant academic/cohort revision changes. Display historical results as historical and do not use them for new registration or dispatch claims.
- **FR-ELIG-07:** Do not provide arbitrary direct eligibility overrides in the MVP. Resolve a discrepancy by verified data correction, corrected policy, or a documented unsupported-case review hold.
- **FR-ELIG-08:** Do not send student records to an LLM for bulk eligibility classification. AI may explain rule wording or help triage a discrepancy, while backend services compute the result.

### 10.1 Exact decision semantics

For each student `s`, the four baseline predicates are branch `B(s)`, minimum CGPA `C(s)`, graduation cohort `G(s)`, and active backlog allowance `N(s)`. Only required predicates participate. A predicate is unknown if necessary data is missing, invalid, unverified, contradictory, or on an unsupported scale.

```text
if policy configuration is invalid:
    reject the evaluation run with a configuration error
elif any required predicate is unknown:
    overall = needs_review
elif any required predicate is false:
    overall = ineligible
else:
    overall = eligible
```

This deliberately prioritizes unresolved required evidence, matching the source requirement that missing information goes to review. If a student has both a known failed predicate and an unknown predicate, show both reasons and keep the overall outcome `needs_review`. A later institution-specific alternative aggregation rule would require a versioned specification and engine change.

Use `CGPA >= threshold` with decimal arithmetic, not binary floating-point rounding. Zero active backlogs is a known value. A blank backlog field is unknown. A scale mismatch is unknown unless an approved deterministic conversion exists. An empty policy cannot grant eligibility accidentally.

### 10.2 Fictional acceptance dataset

Assume every record below has verified graduation year 2027 and a 10-point CGPA scale unless stated otherwise. The approved policy allows CSE/IT, requires CGPA at least 7.50, and permits zero active backlogs.

| Student | Branch | CGPA | Active backlogs | Expected outcome |
| --- | --- | --- | --- | --- |
| A | CSE | 8.20 | 0 | `eligible` |
| B | ECE | 8.80 | 0 | `ineligible`: branch |
| C | IT | 7.20 | 0 | `ineligible`: CGPA |
| D | CSE | 8.00 | 1 | `ineligible`: backlog |
| E | IT | 7.90 | Unknown | `needs_review`: backlog evidence |
| F | CSE | 7.50 | 0 | `eligible`: equality passes |
| G | IT | 7.49 | 0 | `ineligible`: no automatic rounding |
| H | ECE | 8.80 | Unknown | `needs_review`: show branch failure and missing backlog |
| I | CSE | 8.20, unverified | 0 | `needs_review`: verification |
| J | CSE | 3.80 on 4-point scale | 0 | `needs_review`: unsupported scale |

When the minimum changes to 8.00, persist a new policy version and a new evaluation. Student F's old pass remains in history; the current outcome becomes ineligible. Previously sent notices remain recorded and any correction requires a new approval.

## 11. Functional requirements: documents and readiness

### FR-DOC: collection and validation

- **FR-DOC-01:** Define per-drive required document types, accepted formats, maximum size, filename pattern, deadline, and whether the document is required at registration or before scheduling.
- **FR-DOC-02:** Support resume, marksheet, and college-ID categories initially; allow institution-configured display labels without inventing new validation semantics.
- **FR-DOC-03:** Accept uploads only for the authenticated student's own record or an explicitly authorized assisted upload. Preserve uploader identity and student ownership.
- **FR-DOC-04:** Check presence, extension, sniffed MIME/signature, size, safe filename, PDF/DOCX integrity, malware scan, and duplicate content where useful. A filename check is not a content-type check.
- **FR-DOC-05:** Report concrete findings, severity, required action, validator version, and the validated object revision. A file replacement creates a new audit and invalidates readiness derived from the old current revision.
- **FR-DOC-06:** Separate deterministic checks from optional AI triage. AI may propose a document category or summarize a parsing problem; it cannot assert authenticity or override failed security checks.
- **FR-DOC-07:** Store originals privately, use short-lived authorized download links, and audit coordinator file access. Quarantined documents cannot be previewed by ordinary users.
- **FR-DOC-08:** Detect same-student accidental duplicate submissions. Cross-student exact matches may create a restricted review finding, not an automatic accusation or rejection.
- **FR-DOC-09:** Display whether the file was structurally checked, text extraction succeeded, or manual inspection is required. A readable scanned PDF may need review for text extraction while still passing container integrity.
- **FR-DOC-10:** Never rewrite the student's original document without an explicit separate action. Suggest a filename or let the backend use a safe download name while retaining the original filename as metadata.

### 11.1 Readiness semantics

- `ready`: every required document has an accepted current revision that passed required checks.
- `pending`: uploads or checks are incomplete but can still be completed normally before the applicable cutoff.
- `blocked`: a required document has a definite failing condition, or required completion is overdue.
- `needs_review`: no definite blocking failure dominates, but at least one required check requires human review.

For multiple findings, priority is `blocked`, then `needs_review`, then `pending`, then `ready`. Document readiness is separate from eligibility and registration. The coordinator UI can filter combinations such as eligible plus document-blocked.

Suggested development limits are 10 MiB per student document, 20 MiB per JD, and 100 extracted pages. These are configurable baseline limits to validate during implementation, not promises about an existing parser. Reject over-limit input with an actionable message before expensive processing.

Acceptance: a corrupt PDF fails structural validation; a missing semester marksheet is shown as missing; a `.pdf` file containing executable bytes is rejected/quarantined; an upload replay cannot replace a previously accepted document unnoticed; a student never sees another student's document or duplicate match identity.

## 12. Functional requirements: publication and registration

### FR-REG: student opportunity and participation

- **FR-REG-01:** Publish only an approved student-visible drive revision. Confidential company contact details and internal notes are excluded from student responses.
- **FR-REG-02:** Display role, company, compensation as supplied, location, requirements, timezone-aware registration/document deadlines, rounds, and the student's own eligibility/readiness.
- **FR-REG-03:** Permit one registration per student per drive, with an immutable submission event, submitted drive/policy/evaluation references, and current state. Retry must return the existing registration rather than duplicate it.
- **FR-REG-04:** A student may save a draft while data is under review. Submission requires current `eligible` status, a published drive, an open window, and any documents explicitly required at submission.
- **FR-REG-05:** Documents due later may remain pending after registration. This must be clear in the UI and must not imply the student is interview-ready.
- **FR-REG-06:** Use the server clock: opening is inclusive and cutoff is exclusive, so `opens_at <= now < deadline_at`. Client countdowns are informational.
- **FR-REG-07:** Support withdrawal under a configured cutoff. After cutoff, coordinator-assisted changes require a reason and audit event; no silent deadline extension.
- **FR-REG-08:** If current eligibility becomes non-eligible or unresolved, preserve the registration and place it on `eligibility_hold`. Resolve through current evidence and an explicit audited transition; do not auto-delete or auto-email rejection.
- **FR-REG-09:** Allow deadline changes only through a new drive revision and specific publication approval. Prepare, but do not automatically send, an update to affected students.
- **FR-REG-10:** Provide coordinator filters and counts for registration state, eligibility, and readiness, with safe candidate-list export.

Acceptance: concurrent submissions create one row; a submission exactly at the deadline is rejected; a stale evaluation cannot authorize a new submission; a submitted registration with documents due tomorrow remains submitted and document-pending; an eligibility change retains prior evidence.

## 13. Functional requirements: communications and approvals

### FR-COM: drafting and audience control

- **FR-COM-01:** Support drive announcements, missing-document reminders, registration deadline reminders, interview schedules, schedule corrections, result notices, and clarification drafts.
- **FR-COM-02:** Generate drafts from approved structured facts and controlled templates. AI output is optional; deterministic templates provide a reliable fallback.
- **FR-COM-03:** Choose an explicit audience query and freeze the exact recipient snapshot. Baseline audience types are current eligible students, submitted registrants, students with required-document findings, assigned session participants, and explicitly reviewed correction recipients.
- **FR-COM-04:** Show inclusion reasons, exclusion counts, duplicate addresses, unresolved addresses, and sample/individual rendered messages. Personalize without exposing another student's details.
- **FR-COM-05:** Validate company/role, action, registration link if applicable, deadline and timezone, required documents, reply/support contact, and relevant schedule data. Block missing required fields and unapproved facts.
- **FR-COM-06:** Send individual messages or provider-supported private-recipient deliveries; do not expose a bulk student address list in `To`/`Cc`.
- **FR-COM-07:** Avoid conflicting or excessive reminders with a configurable cadence and an explicit approved batch. MVP reminders are proposed by the system and approved per exact audience/content; no open-ended blanket approval.
- **FR-COM-08:** Store the frozen template, merge data, rendered-content hashes, attachments, sender, reply-to, and channel. No model call may change the approved body at dispatch time.

### FR-APP: approval center

- **FR-APP-01:** Present the exact proposal revision, action type, evidence, current dependencies, scope, recipient count/list, sender, and effect before approval.
- **FR-APP-02:** Support approve, reject, and request revision, with actor, timestamp, reason/comment, expected revision, and authorization context.
- **FR-APP-03:** Bind approval to a content/audience/dependency fingerprint and execution expiry. Approval of policy rules does not approve a message or calendar invite.
- **FR-APP-04:** Invalidate affected authorization when content, recipients, policy, relevant student evidence, deadline, schedule, sender connection, or other declared dependencies change.
- **FR-APP-05:** Prevent concurrent conflicting decisions. A stale approval attempt returns a conflict and current revision rather than silently approving newer content.
- **FR-APP-06:** Before each external action is claimed, confirm authorization, freshness, execution window, drive hold/cancellation state, and recipient validity. Stop unclaimed work when these checks fail.
- **FR-APP-07:** A reviewer can inspect history and see what was approved versus actually executed. Already transmitted messages cannot be recalled by changing local status.

### FR-DISP: controlled execution

- **FR-DISP-01:** Commit the approved execution intent and outbox record transactionally. Queue or network availability must not lose approved work.
- **FR-DISP-02:** Assign a unique operation key to each logical recipient message and record each provider attempt. Duplicate tasks cannot create a new logical send.
- **FR-DISP-03:** Use bounded retry/backoff for known transient failures; permanent failures remain visible with a reason.
- **FR-DISP-04:** A timeout after possible provider acceptance becomes `unknown`. Reconcile using provider evidence or a coordinator review; do not blindly resend an uncertain message.
- **FR-DISP-05:** Show batch progress, partial results, failures, and provider acceptance distinctly from confirmed delivery. Unsupported delivery receipts stay unknown, not implicitly delivered.
- **FR-DISP-06:** Cancellation/staleness stops future unclaimed work. In-flight actions may finish; disclose this limit and preserve the claim/attempt history.
- **FR-DISP-07:** Development/test environments use a sink and recipient allowlist by default. Production sending requires a deliberately configured adapter and sender identity.

Acceptance: editing a subject after approval requires a new approval; changing a deadline stops affected unsent reminders; double-clicking approve and redelivering a queue task do not create a duplicate logical message; a provider timeout is visible as uncertain; rejected proposals cannot dispatch through a direct API call.

## 14. Functional requirements: scheduling, attendance, and results

### FR-SCHED: basic recruitment events

- **FR-SCHED-01:** Configure ordered recruitment rounds, such as aptitude test, technical interview, and HR interview. A round can contain multiple sessions with start/end instants, timezone, capacity, venue or meeting link, panel, and participants.
- **FR-SCHED-02:** Provide coordinator-controlled assignment in the MVP. Validate student, panel, and venue conflicts and session capacity before publication. Automatic optimization is deferred.
- **FR-SCHED-03:** Treat intervals as half-open `[start, end)`: a session ending at 11:00 does not conflict with one starting at 11:00, unless a configured buffer applies. End must be after start.
- **FR-SCHED-04:** Require current registration, eligibility, document readiness, and prerequisite-round outcome as configured before publishing an assignment. An override to document timing, where permitted by institutional policy, requires a specific reason and coordinator capability; it never rewrites academic eligibility.
- **FR-SCHED-05:** Separate draft planning from published assignments. Publication and material rescheduling require an explicit approved action. Notifications require their own approved recipient/content snapshot.
- **FR-SCHED-06:** Store attendance as a distinct fact: `not_recorded`, `present`, `absent`, or `excused`, with recorder and timestamp. Absence does not automatically become an employer rejection.
- **FR-SCHED-07:** On schedule change, preserve old revisions, identify affected participants, validate conflicts again, and prepare a correction notice.
- **FR-SCHED-08:** Basic scheduling must work without Google Calendar. External writes belong to the later connector phase.

### FR-RESULT: selection outcomes

- **FR-RESULT-01:** Record employer-supplied round outcomes such as `pending`, `advanced`, `rejected`, `waitlisted`, `selected`, and `withdrawn`, with source, recorder, and revision.
- **FR-RESULT-02:** Distinguish draft internal results from student-published results. Require explicit authorized publication of an exact result revision and audience.
- **FR-RESULT-03:** Support corrected results without deleting the previous record. A change after publication requires a new publication decision and separately approved correction message if a message is sent.
- **FR-RESULT-04:** Treat an offer's existence, student acceptance, and joining status as distinct recorded facts if collected. Recording `selected` does not fabricate a formal offer or joining confirmation.
- **FR-RESULT-05:** Student views expose only that student's published outcomes. Coordinator reports can aggregate authorized results.

Acceptance: two overlapping assignments for one student are rejected; a half-open boundary is accepted without a buffer; draft results are invisible to students; corrected published results preserve the earlier version; calendar integration being disconnected does not prevent internal scheduling.

## 15. Functional requirements: durable orchestration and exceptions

### FR-WF: workflow execution

- **FR-WF-01:** Orchestrate intake, interpretation, clarification, rule approval, eligibility, document review, proposal preparation, action approval, controlled execution, monitoring, and closure using LangGraph.
- **FR-WF-02:** Persist checkpoints in PostgreSQL. Store identifiers and revisions rather than copying full student datasets or raw documents into graph state.
- **FR-WF-03:** Persist approval requests independently of checkpoints. Human waiting does not occupy a worker indefinitely; resume through a new authenticated command/job.
- **FR-WF-04:** Serialize commands for a workflow run/drive operation with concurrency control. Two resumes cannot execute the same transition twice.
- **FR-WF-05:** Permit bounded retry for transient extraction/provider failures and manual continuation for interpretation failures. Permanent validation or authorization errors do not enter an endless retry loop.
- **FR-WF-06:** Preserve workflow implementation version, state-schema version, source/policy/evaluation revisions, last successful step, and error category for recovery.
- **FR-WF-07:** Support an operational hold and cancellation. A hold stops new consequential work without deleting the drive or its completed effects.
- **FR-WF-08:** Process registration, document, schedule, and result events during monitoring without re-running intake or re-sending the original announcement.
- **FR-WF-09:** Handle graph upgrades explicitly: finish existing runs on compatible code, migrate state deliberately, or restart from a safe domain boundary. Never resume old state blindly under an incompatible graph.

### FR-EXC: exception management

- **FR-EXC-01:** Create visible cases for unresolved requirements, unsupported policy, stale academic records, missing/failed documents, invalidated approvals, ambiguous delivery, and scheduling conflicts.
- **FR-EXC-02:** Include case category, severity, affected records, evidence, owner, status, proposed next action, and resolution history.
- **FR-EXC-03:** In the MVP, use deterministic classification and manual resolution where sufficient. A useful exception inbox does not depend on an advanced agent.
- **FR-EXC-04:** Later, allow an Exception Resolution Agent to retrieve scoped summaries and propose a structured, ordered recovery plan, with preconditions, dependencies, expected effects, approvals, and compensation limitations.
- **FR-EXC-05:** Execute approved plans only through allowlisted backend commands. The agent cannot mutate criteria, change records, send correction mail, or alter a calendar directly.
- **FR-EXC-06:** Revalidate every plan step at execution. A partially executed plan must show completed, pending, failed, and irreversible actions. A newer event can stale the remainder.
- **FR-EXC-07:** Keep already sent messages and published histories intact. Recovery usually means a new compensating action, not pretending the original effect never happened.

Acceptance: the application can restart while awaiting approval and resume the same run; an unauthorized user cannot resume it; duplicate event delivery is harmless; an eligibility revision produces an impact case without automatically mailing newly ineligible students; manual review remains available when the exception model fails.

## 16. Functional requirements: integrations

### FR-INT: adapter boundaries and later connectors

- **FR-INT-01:** Abstract mail, model, object storage, and future Google connectors behind narrow backend interfaces. Persist provider identifiers and connection versions.
- **FR-INT-02:** Support a local mail sink and a deterministic model fixture for development. Production adapters must not be silently replaced with fixtures on failure.
- **FR-INT-03:** Gmail intake requires explicit connection and message selection. Capture source message/attachment identifiers, content hash, sender metadata, and receipt time. Do not scan an entire inbox by default.
- **FR-INT-04:** Request the minimum scopes needed for enabled features; inbox reading and mail sending are separate capabilities. Document current provider requirements at implementation time.
- **FR-INT-05:** Sheets imports use a selected spreadsheet/range, column mapping, preview, conflict report, and explicit commit. Sheets is not a second authoritative database.
- **FR-INT-06:** Sheets exports contain an explicitly selected schema and audience. Writing a sheet is an external action requiring a specific approved export/write proposal.
- **FR-INT-07:** Calendar creation/update uses an approved session revision, calendar, attendees, notification options, and stable provider mapping. Any invitation email side effect must be included in the approved proposal.
- **FR-INT-08:** Store OAuth tokens encrypted server-side, support disconnect/revocation, show expired permissions, and stop affected pending work when connection versions change.
- **FR-INT-09:** Verify supported webhooks, deduplicate events, rate-limit provider calls, and reconcile missed updates. Never trust an external change merely because it arrived via webhook.

Live integrations are not required to finish the local MVP. They are required before advertising those individual capabilities as available.

## 17. Functional requirements: reporting, audit, and closure

### FR-AUD: auditability

- **FR-AUD-01:** Record actor/service identity, institution, action, resource, timestamp, correlation/operation ID, reason, and relevant before/after revisions for material mutations and external actions.
- **FR-AUD-02:** Include source review, policy approval, academic verification, evaluation, document findings, proposal decisions, dispatch attempts, schedule/results publication, exports, holds, cancellation, and closure.
- **FR-AUD-03:** Make audit records append-only to the ordinary application role. Do not claim this alone prevents a database administrator from altering history.
- **FR-AUD-04:** Restrict access to sensitive audit details. Ordinary application logs and student activity views receive redacted subsets.

### FR-REPORT: operational views and reports

- **FR-REPORT-01:** Show counts for drives requiring review, current eligibility outcomes, registration states, document readiness, pending approvals, notification status, and exceptions.
- **FR-REPORT-02:** Candidate-list exports identify the drive, policy/evaluation revision, filters, generation time, and whether the data is current. Escape spreadsheet formula prefixes in user-controlled CSV cells.
- **FR-REPORT-03:** Closure reports include company/role, approved criteria, deadlines, funnel counts, document completion, round attendance/outcomes, delivery summary, unresolved cases, closure actor/time, and revision references.
- **FR-REPORT-04:** Define denominators: eligibility counts are for a named cohort snapshot; registration counts are unique students with explicit state filters; selection counts derive from recorded outcomes, not message delivery.
- **FR-REPORT-05:** Generate reports deterministically from a frozen reporting snapshot. AI narrative is optional and cannot introduce unsupported totals or claims.

### FR-CLOSE: drive closure

- **FR-CLOSE-01:** Require registration closure, completed/cancelled sessions, recorded or explicitly unresolved outcomes, and review of pending proposals/dispatch before completion.
- **FR-CLOSE-02:** Block closure while active sends are claimed or queued unless those unsent operations are cancelled and in-flight/unknown outcomes are resolved or explicitly documented by an authorized coordinator.
- **FR-CLOSE-03:** Open low-severity cases may be carried forward only with owner, reason, and acknowledgment in the report. Security-critical unresolved cases block closure pending an authorized resolution process.
- **FR-CLOSE-04:** Freeze a closure/report revision and restrict ordinary mutations. Reopening requires explicit capability, reason, and a new revision; it does not erase the previous report.
- **FR-CLOSE-05:** Support authorized drive cancellation with student-visible state and separately approved notices where needed. Cancellation is not deletion.

Acceptance: a report's totals can be reproduced from its snapshot; a CSV containing a student name beginning with `=` is safe to open; closure does not claim all mail was delivered when only provider acceptance is known; reopening preserves the prior completed report.

## 18. Runtime AI components

The five responsibilities from the source are implemented as four AI-assisted components plus one deterministic engine. These are runtime product components, not instructions to spawn autonomous coding agents.

| Component | Input | Output | Permitted authority | Failure/fallback |
| --- | --- | --- | --- | --- |
| JD Intelligence Agent | Authorized source text and locators | Schema-validated candidate facts, evidence, ambiguities | Read current source; produce draft only | Review task and manual entry |
| Eligibility and Policy Engine | Approved policy and verified snapshots | Deterministic predicate results and explanations | Evaluate approved typed rules | Configuration error or `needs_review` |
| Document Verification and Triage | Validation findings and minimum necessary document excerpt | Suggested category/review note | Read scoped findings; recommend | Deterministic findings and human review |
| Communication and Outreach Agent | Approved facts, explicit audience type, template | Validated draft content | Draft only; no send permission | Deterministic template |
| Exception Resolution Agent, later | Scoped case/effect summaries | Structured recovery proposal | Propose allowlisted operations | Manual triage and resolution |

### 18.1 AI execution constraints

- Schema validation is required, but a syntactically valid response can still be unsupported; evidence validation and human review remain necessary.
- External content cannot redefine tools, system instructions, policy, audience, or approval authority.
- Model calls receive minimum necessary data. Full student cohorts and unrestricted database tools are prohibited.
- Use bounded timeouts, bounded output, one initial call plus at most one repair attempt as an initial configurable budget, and an explicit failed/manual outcome.
- Cache an extraction only when source hash, parser/prompt/schema/model versions, and privacy scope match. Never share institution-specific source caches across tenants.
- Store enough metadata to reproduce the processing configuration, but do not promise identical generative output. Reuse persisted accepted drafts instead of regenerating them during approval/dispatch.
- Model provider, region, data-processing terms, and actual model identifier must be chosen before a real-data pilot. No specific paid provider is assumed by this specification.

## 19. Screens and interaction requirements

### 19.1 Coordinator application

| Screen | Required content and actions |
| --- | --- |
| Dashboard | Actionable queue of reviews, holds, deadlines, delivery issues, and active drives; drill-down counts. |
| Drive list | Search and filter by company, cohort, lifecycle, owner, and operational hold. |
| Drive workspace | Overview, sources, rules, eligibility, documents, registrations, communications, schedule, results, exceptions, and history. |
| Source review | Original preview or download, extracted text, field evidence, uncertainty, coordinator corrections, and clarification tasks. |
| Rule review | Typed criteria, readable summary, validation errors, policy diff, cohort scope, and explicit approval. |
| Eligibility view | Current/historical marker, three outcome groups, student details, predicate reasons, and stale indicators. |
| Document queue | Per-student/type findings, current revision, deadline, scan/validation state, and remediation action. |
| Approval center | Exact proposal and dependency summary, recipients, rendered preview, decision, and conflict/expiry feedback. |
| Dispatch view | Logical batch/recipient progress, attempts, provider evidence, unknown outcomes, and safe retry/reconciliation controls. |
| Schedule/results | Draft/published sessions, conflict feedback, attendance, result provenance, and publication actions. |
| Exception inbox | Severity, owner, affected resources, evidence, proposed resolution, approval state, and history. |
| Closure/report | Preconditions, unresolved items, frozen totals, export controls, and reopening history. |
| Institution settings | Authorized identity, branch mappings, academic rules, provider connections, retention, and environment status. |

### 19.2 Student application

Provide an opportunity list, drive detail, profile and correction request, document checklist/upload history, registration confirmation/withdrawal, personal schedule, approved published results, and a clear way to request support. Students should not need to understand LangGraph, queue jobs, model tokens, or internal table names.

### 19.3 Shared interaction rules

- Clearly distinguish saved draft, submitted for approval, approved, published, processing, stale, and failed states.
- Keep critical approval details visible without relying on a tooltip or color alone.
- Use accessible labels, keyboard navigation, visible focus, meaningful validation messages, and responsive tables/cards.
- Confirm destructive user actions in the product when needed, but avoid repeated confirmation for ordinary editing.
- Display deadlines in the institution timezone and retain an unambiguous offset/timezone label in detailed views.
- Never display another student's eligibility reasons or documents in a student-facing audience preview.
- Announce asynchronous completion/failure accessibly; retain state across refresh and give a safe retry path.

## 20. Nonfunctional requirements

The following numbers are initial engineering targets for a single-institution pilot. Benchmark them using synthetic data on a documented environment; they are not current measurements or contractual SLAs.

| ID | Requirement | Verification target |
| --- | --- | --- |
| NFR-01 | Correctness and reproducibility | Exact eligibility agreement with deterministic fixtures; reports reproduce frozen snapshot totals. |
| NFR-02 | Authorization | Automated negative cases for institution, student, file, export, worker, and resume boundaries. |
| NFR-03 | Reliability | Restart at every important approval/dispatch boundary without lost work or duplicate logical operations. |
| NFR-04 | Ordinary API latency | Warm list/detail requests p95 below 500 ms server-side for the pilot dataset, excluding upload/provider/model work. |
| NFR-05 | Cohort evaluation | Evaluate 5,000 students under the baseline four-predicate policy within 60 seconds on the recorded test environment. |
| NFR-06 | Async usability | Persist and acknowledge long jobs promptly, target below 2 seconds under normal load; expose progress and bounded errors. |
| NFR-07 | Pilot load | Validate 5,000 student records, 20 active drives, and 100 concurrent interactive users as a planning envelope. |
| NFR-08 | Accessibility | Aim for WCAG 2.2 AA on core journeys; automated checks plus keyboard/manual review, without claiming certification. |
| NFR-09 | Observability | Correlate API command, workflow, job, approval, and dispatch attempt without logging private payloads. |
| NFR-10 | Recovery | Initial pilot objective: database RPO at most 24 hours and RTO at most 8 hours, subject to infrastructure selection and a demonstrated restore drill. |
| NFR-11 | Cost control | Configurable model-call/token budgets, upload/parse limits, queue limits, and per-drive usage reporting. |
| NFR-12 | Maintainability | Typed contracts, locked dependencies, migrations, documented environment, and independent domain tests. |

Availability goals depend on the chosen hosting environment. External email delivery and model response time cannot be guaranteed by local API latency targets.

## 21. Privacy, security, and institutional configuration

### 21.1 Required controls

Use encrypted transport and private object storage. Separate runtime and migration database roles. Apply institution scope and row-security defense in depth. Treat files, emails, and spreadsheet cells as untrusted. Use server-managed sessions, CSRF/origin checks, output encoding, upload quarantine, parser sandbox/resource limits, and scoped short-lived download URLs.

Provider credentials and OAuth tokens are server-side secrets. Audit access and exports. Keep telemetry free of full documents, academic datasets, message bodies, access tokens, and signed URLs. Restricted evidence storage can hold necessary details under the institution's configured retention and access policy.

### 21.2 Configuration that must be explicit

| Configuration | Why it matters | Safe planning default |
| --- | --- | --- |
| Institution timezone | Defines deadlines and schedule display | `Asia/Kolkata` for the initial intended Indian pilot; confirm before use. |
| Academic scale and branch mapping | Controls deterministic comparisons | No unreviewed conversion or fuzzy mapping. |
| Authorized record sources/reviewers | Establishes trust in academic evidence | Student edits remain proposed/unverified. |
| Approval capabilities and assignments | Determines who can authorize effects | Least privilege; explicit coordinator assignment. |
| Drive visibility and rejection explanations | Protects private operational details | Students see published fields and their own reasons. |
| Registration/document/withdrawal cutoffs | Defines allowed participation transitions | No invented timestamps; require configuration. |
| Model provider and data handling | Controls external processing of source data | Disabled or fixture mode until selected. |
| Email sender and enabled channels | Controls external identity and delivery | Development sink, no live recipients by default. |
| Retention and deletion policy | Governs records, objects, checkpoints, exports, backups | Unconfigured production policy blocks a real-data pilot; use synthetic local data. |
| Backup/restore and operating ownership | Determines recoverability | Pilot readiness requires a tested procedure. |

This specification does not determine applicable privacy law, a lawful processing basis, or institutional consent obligations. The institution supplies its policy and obtains any needed review. Implement configurable controls and avoid claims of legal compliance that have not been established.

## 22. Acceptance and release gates

### 22.1 Local MVP acceptance scenario

Using only synthetic records and local adapters:

1. Import a cohort containing all three eligibility outcomes and verify record provenance.
2. Upload a readable JD with the fictional policy in Section 10.2 plus one deliberate ambiguity.
3. Confirm the ambiguity blocks rule approval; resolve it with an attributed correction.
4. Approve the policy, evaluate the cohort, and inspect explanations and historical references.
5. Publish the drive, log in as a student, upload a valid and an invalid file, and observe separate readiness.
6. Register an eligible student, prevent a needs-review student's submission, and prevent a deadline-boundary submission.
7. Draft an announcement, inspect its exact audience, request revision, then approve the corrected immutable revision.
8. Restart the API/worker while awaiting approval and resume the existing run after sign-in.
9. Dispatch to the local sink, redeliver a task, and demonstrate one logical send per approved recipient.
10. Change the policy/deadline; show staleness, preserved sent history, recomputation, and a registration hold.
11. Publish conflict-free sessions, record attendance and results, publish only the intended result revision, and close the drive.
12. Reproduce the closure totals and show an audit trail. Demonstrate blocked cross-student and cross-institution reads.

Passing this demonstrates a local MVP, not production readiness or implemented Google integrations.

### 22.2 Real-data pilot readiness

Before a real institution uses student data, require configured OIDC and membership administration, a reviewed permissions matrix, private storage and malware scanning, a selected model policy/provider, intentional live mail setup, configured retention, tested backups/restores, monitored workers/outbox, reviewed approval/retry behavior, and named operational ownership. Run the risk-based security and recovery checks in `PLAN.md`.

### 22.3 Later integration/exception acceptance

Each connector must demonstrate authorization, minimal scopes, disconnect handling, revision/conflict control, approved external effects, and failure reconciliation. Exception automation must demonstrate a criteria-change impact plan, exact approval boundaries, partial execution recovery, and safe manual fallback before being described as available.

## 23. Risks and resolutions

| Risk | Product response |
| --- | --- |
| Incorrect or unsupported JD extraction | Evidence-backed review, blocking ambiguity, structured validation, manual entry. |
| False eligibility due to missing data | Required unknown evidence goes to `needs_review`; no LLM adjudication. |
| Old criteria used after a revision | Immutable versions, freshness checks, stale proposals, recomputation. |
| Duplicate or uncertain notifications | Transactional intent, unique operations, recipient attempt tracking, unknown-outcome reconciliation. |
| Long human waits | Durable checkpoint/domain approval; no continuously occupied worker. |
| Private information leaked to students or models | Object-level authorization, minimum DTOs, private storage, scoped model inputs. |
| Malicious uploaded content | Quarantine, scanning, resource-limited parsing, prompt-injection separation. |
| Excessive scope for a solo project | Complete local vertical slices first; defer live Google connectors and advanced recovery. |
| Conflicting external edits | Preview/diff/version checks; PostgreSQL remains authoritative. |
| Unclear institution placement rules | Explicit configuration; no inferred one-offer/branch/rounding policy. |

## 24. Decision register

These are not reasons to stop local development. Use the design baselines for synthetic workflows and resolve the relevant configuration before enabling the affected production capability.

| Decision | Baseline / outstanding input | Resolution phase |
| --- | --- | --- |
| Primary architecture | Modular backend, separate workers, Next.js UI | P00/P01 |
| Identity provider | OIDC; institution chooses provider and invite/mapping rules | P00/P02, before real data |
| Supported runtime/dependency versions | Verify compatible supported releases and pin exact versions | P01 |
| Academic record trust | Authorized import plus verified corrections | P02 |
| CGPA scale/branch map | Institution supplies exact configuration | P02/P05 |
| Deadline conventions | Time and timezone explicitly confirmed | P04, per drive |
| Publication/approval capabilities | Assigned coordinators; self-review allowed in pilot, audited | P02/P07 |
| Production email provider | Adapter chosen to support institutional sender; local sink first | P07/P10 |
| LLM provider/model/region | Provider-neutral interface; choose after fixture-based evaluation and policy review | P04/P10 |
| File scanner and parser limits | Real scanner for pilot; fixture scanner only in development | P03/P06/P10 |
| Privacy/retention/deletion periods | Institution-owned configuration; no invented legal periods | P10 |
| Hosting and recovery objectives | Container-based pilot; validate backup/RPO/RTO against selected environment | P10 |
| Google connector scope/verification | Confirm current provider requirements when implemented | P11 |
| Exception automation depth | Deterministic cases first, proposal-only agent later | P12 |

## 25. Source-to-delivery traceability

| Source concept | Specification groups | Primary implementation phases |
| --- | --- | --- |
| JD/email intake and interpretation | FR-JD, FR-AI-JD | P03, P04, later P11 |
| Clear requirements and approved rules | FR-POL, FR-APP | P04, P07, P08 |
| Deterministic transparent eligibility | FR-STU, FR-ELIG | P02, P05 |
| Missing/corrupt documents | FR-DOC | P06 |
| Draft/revise/approve/dispatch communication | FR-COM, FR-APP, FR-DISP | P07, P08 |
| Registration and ongoing tracking | FR-REG, FR-WF | P06, P08 |
| Scheduling and results | FR-SCHED, FR-RESULT | P09 |
| Durable state and human pauses | FR-WF | P01 foundations, P08 integration |
| Exception recovery | FR-EXC | P08 baseline, P12 advanced |
| Close drive and report | FR-AUD, FR-REPORT, FR-CLOSE | Cross-cutting audit, P09 |
| Proposed stack/storage/integrations | FR-ID, FR-INT, NFR-01 through NFR-12 | Architecture baseline, P01/P10/P11 |
