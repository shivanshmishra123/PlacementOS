# PlacementOS: Architectural and Operational Decision Register

> Phase P00 Deliverable: P00-T04  
> Date: 29 October 2026  
> Status: Authoritative Decision Baseline

---

## 1. Classification Framework

Decisions throughout PlacementOS are categorized into four explicit tiers:
1. **Source Requirement:** Hard constraints dictated by the original problem description and domain specifications.
2. **Design Baseline:** Technical choices adopted for implementation that can be revised through an ADR with justified rationale.
3. **Institution Configuration:** Parameters that must be provided by a adopting institution before deployment with real student data.
4. **Deferred:** Capabilities outside the MVP boundary scheduled for subsequent milestones.

---

## 2. Core Architectural Decisions (ADR Register)

| ADR ID | Title & Scope | Classification | Decision Summary & Invariants | Resolution / Status |
| :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | **Monorepo & Process Model** | Design Baseline | Single Git repository containing Next.js frontend (`apps/web`), modular FastAPI backend (`backend/src/placementos`), and separate worker entry points for Celery/LangGraph. Avoids distributed microservice overhead while enforcing strict layer boundaries. | Accepted Baseline for P01. |
| **ADR-002** | **Deterministic Eligibility Engine** | Source Requirement | Zero LLM involvement in cohort filtering. Pure mathematical and logical evaluation over immutable verified student snapshots. Aggregation rule enforces unknown-first precedence (`needs_review`). Enforces `INV-01`, `INV-02`. | Accepted Baseline for P02, P05. |
| **ADR-003** | **OIDC & Backend Opaque Sessions** | Design Baseline | Institutional SSO via standard OIDC authorization code flow with PKCE. Tokens remain on the backend; frontend communicates via an `HttpOnly`, `Secure`, `SameSite=Lax` opaque cookie session behind a single reverse-proxy origin. Enforces `INV-06`, `INV-10`. | Accepted Baseline for P02; Identity provider selection resolved before pilot. |
| **ADR-004** | **PostgreSQL as Source of Truth & Outbox** | Design Baseline | PostgreSQL stores all domain aggregates, proposal histories, and outbox records. Redis acts solely as transport for Celery and volatile cache. Work remains durable even during broker restart. Enforces `INV-08`. | Accepted Baseline for P01, P07. |
| **ADR-005** | **LangGraph Checkpoints Separation** | Design Baseline | LangGraph coordinates durable pause/resume across human approval gates with PostgreSQL checkpoint persistence. Graph state references domain aggregate IDs; it does not duplicate student datasets or bypass business authorization. Enforces `INV-04`, `INV-08`. | Accepted Baseline for P08. |
| **ADR-006** | **Exact Proposal Approval & Dependency Fingerprint** | Source Requirement | Consequential operations (rule approval, drive publication, email dispatch, schedule release) require an immutable action proposal and SHA-256 fingerprint binding. In pilot single-coordinator setups, self-review is permitted but fully audited. Enforces `INV-04`, `INV-05`, `INV-09`. | Accepted Baseline for P04, P07. |
| **ADR-007** | **Immutable Accepted Storage & Quarantine** | Design Baseline | Uploads land in a private quarantine S3 bucket/prefix with short-lived presigned URLs. After scanning, accepted bytes are promoted to an immutable server-controlled key or version-pinned. Download URLs are short-lived and authorized. Enforces `INV-06`, `INV-12`. | Accepted Baseline for P03. |
| **ADR-008** | **Adapter Strategy: Model, Mail, & Scanner** | Design Baseline | Interfaces abstract third-party providers. Development utilizes local fixtures: Mailpit for email, deterministic JSON fixtures for LLM extraction, and mock scanner. Production switches to configured providers via environment flags without changing business code. Enforces `INV-07`. | Accepted Baseline for P01; Live providers gated at P10. |
| **ADR-009** | **Intake Before Live Connectors** | Design Baseline | Local MVP accepts direct file uploads (PDF, DOCX) and pasted email text. Direct Gmail inbox sync, Google Sheets sync, and Google Calendar writes are deferred to Phase P11. Enforces release boundary. | Accepted Baseline for P03, P11. |
| **ADR-010** | **Manual Scheduling & Deterministic Conflicts** | Design Baseline | MVP supports coordinator-defined rounds and sessions with deterministic half-open interval conflict detection $[start, end)$. Complex automated timetable optimization is deferred. | Accepted Baseline for P09. |
| **ADR-011** | **Conservative Stale Invalidation** | Design Baseline | Any change to eligibility policy, student academic record, or drive deadline immediately invalidates dependent evaluations, unapproved proposals, and unsent outbox items. Incremental fine-grained invalidation is deferred until measured. Enforces `INV-05`. | Accepted Baseline for P05, P07, P08. |
| **ADR-012** | **Containerized Topology without Kubernetes** | Design Baseline | Local environment uses Docker Compose / container runtime (Postgres, Redis, SeaweedFS S3, Mailpit, API, Web, Worker). On Windows, workers run in Linux containers or WSL. Kubernetes, service meshes, and vector databases are deliberately excluded as unnecessary operational complexity. | Accepted Baseline for P01, P10. |

---

## 3. Operational Baselines & Unresolved Production Inputs

The following operational configurations are recorded as explicit baselines for synthetic local development, while marking real institutional parameters as unresolved without blocking progress:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        OPERATIONAL DECISION BASELINES TABLE                            │
├──────────────────────┬───────────────────────────────┬─────────────────────────────────┤
│ Domain Area          │ Synthetic Dev Baseline        │ Real-Data Pilot Requirement     │
├──────────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ Institution Timezone │ Asia/Kolkata (UTC+05:30)      │ Institution must confirm IANA tz│
│ Branch Normalization │ Explicit alias map:           │ Institution canonical mapping   │
│                      │   CSE -> Computer Science     │   approved by placement head    │
│                      │   IT  -> Information Tech     │                                 │
│ CGPA Scale & Metric  │ Decimal 10.00 scale;          │ Institution grading policy      │
│                      │   strictly >= check           │   (e.g., percentage conversion) │
│ Academic Trust       │ CSV import + manual review    │ Authorized registrar feed       │
│ Coordinator Review   │ Single coordinator may self-   │ Optional 4-eyes dual review     │
│                      │   approve with audit log      │   policy configurable           │
│ Email Transport      │ Mailpit SMTP sink (localhost) │ Verified institutional SMTP/SES │
│ LLM Model Provider   │ Scoped JSON fixture / mock    │ Enterprise tenant contract      │
│ Malware Scanner      │ Mock clean / signature check  │ Live ClamAV container/daemon    │
│ Data Retention       │ Ephemeral local storage       │ Institutional compliance policy │
└──────────────────────┴───────────────────────────────┴─────────────────────────────────┘
```

### Unresolved Production Items (Non-Blocking for MVP):
1. **OIDC Provider Specifics:** Client IDs, issuer endpoints, and claim mapping schemas for the pilot institution (e.g. Google Workspace, Azure AD, Keycloak).
2. **Institutional Grade Conversions:** Institutional formulas for converting percentage marks to CGPA or handling letter grades.
3. **Formal Retention Periods:** Regulatory legal retention timeline for student resumes and academic records post-graduation.
4. **Production Outbound Mail Quotas:** Institutional SMTP server hourly throttling limits and bounce-handling webhooks.
