# PlacementOS: Source Traceability and Release Boundary Matrix

> Phase P00 Deliverable: P00-T01 and P00-T02  
> Date: 29 October 2026  
> Status: Validated and Approved Baseline

---

## 1. Executive Summary and Alignment

This document establishes definitive source-to-requirement traceability across the original source materials (`Description.txt`, `Agents detail.png`, `Workflow detail.png`) and the four canonical planning documents (`Agents.md`, `PROJ_SPECIFICATION.md`, `Architecture.md`, `PLAN.md`).

It resolves terminology discrepancies, formalizes the separation of AI drafting from deterministic execution, and confirms the release boundaries across the project milestones.

---

## 2. Terminology Reconciliation: The "5 Responsibilities" vs. Runtime Architecture

The original `Description.txt` describes five agent responsibilities:
1. **Agent 1 — JD Intelligence Agent**
2. **Agent 2 — Eligibility and Policy Engine**
3. **Agent 3 — Document Verification and Triage Agent**
4. **Agent 4 — Communication and Outreach Agent**
5. **Agent 5 — Exception Resolution Agent**

### Contradiction and Resolution

- **The Problem:** In common LLM agent patterns, an "agent" refers to an autonomous LLM loop with tool-calling capabilities. Treating the Eligibility Engine as an LLM agent creates an unacceptable risk of non-deterministic, hallucinatory, or unexplainable filtering of student careers (violating Invariant `INV-01`).
- **The Resolution:** 
  - As formalized in `PROJ_SPECIFICATION.md` Section 18 and `Architecture.md` Section 14, the five conceptual responsibilities are realized in production as **four scoped AI components** plus **one purely deterministic, non-LLM business engine**:
    1. **JD Intelligence Agent (AI):** Scoped LLM structured extraction, producing candidate structured facts with source locators (`FR-AI-JD`). Fallback: manual structured entry.
    2. **Eligibility and Policy Engine (Deterministic Backend Service):** Zero LLM involvement. Pure mathematical/logical predicate evaluation over verified snapshots using exact decimal arithmetic (`FR-ELIG`, `FR-POL`).
    3. **Document Verification and Triage (Hybrid):** Primary validation is deterministic container/signature/hash verification (`FR-DOC`). Optional secondary AI triage provides categorization suggestions or reading assistance.
    4. **Communication and Outreach Agent (AI):** LLM-assisted draft text generation using approved structured facts and templates (`FR-COM`). Recipient querying, merge values, and dispatch are strictly owned by backend services. The model cannot call send tools.
    5. **Exception Resolution Agent (AI, Advanced Phase P12):** Analyzes discrepancies and proposes structured recovery plans (`FR-EXC`). Cannot execute commands or mutate state directly; execution is performed by backend services upon explicit coordinator approval.

---

## 3. Comprehensive Source Traceability Matrix (P00-T01)

| Source Input Concept | Source Reference | Specification Requirement Group | Architecture Implementation Section | Primary Phase | Invariants Enforced |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Intake & Multi-format JD Extraction** | `Description.txt` L22-26, L38-54; `Workflow detail.png` | `FR-JD-01` to `06`, `FR-AI-JD-01` to `08` | `Architecture.md` Sec 14, 15 | P03, P04 | `INV-03`, `INV-07`, `INV-11` |
| **Requirements Clarification Loop** | `Description.txt` L52-54; `Workflow detail.png` | `FR-AI-JD-04`, `FR-AI-JD-05`, `FR-POL-03` | `Architecture.md` Sec 7.2, 13.2 | P04 | `INV-03`, `INV-11`, `INV-12` |
| **Coordinator Rule Approval Gate** | `Description.txt` L30-33; `Workflow detail.png` | `FR-POL-01` to `06`, `FR-APP-01` to `07` | `Architecture.md` Sec 10, 11 | P04, P07 | `INV-04`, `INV-05`, `INV-09` |
| **Deterministic Eligibility Engine** | `Description.txt` L25-27, L56-82 | `FR-ELIG-01` to `08`, `FR-STU-01` to `07` | `Architecture.md` Sec 10 | P02, P05 | `INV-01`, `INV-02`, `INV-09` |
| **Conservative Unknown Precedence** | `Description.txt` L68, L81-82 | `FR-ELIG-03`, Sec 10.1 | `Architecture.md` Sec 10 | P05 | `INV-01`, `INV-02` |
| **Student Document Verification & Triage** | `Description.txt` L28-29, L84-102 | `FR-DOC-01` to `10` | `Architecture.md` Sec 15 | P03, P06 | `INV-06`, `INV-08`, `INV-12` |
| **Communication Drafting & Audience Snapshot** | `Description.txt` L30-32, L104-113 | `FR-COM-01` to `08`, `FR-APP-01` to `07` | `Architecture.md` Sec 11, 12 | P07 | `INV-04`, `INV-05`, `INV-10` |
| **Human Approval & Pause/Resume Gate** | `Description.txt` L32-34; `Agents detail.png` | `FR-APP-01` to `07`, `FR-WF-01` to `09` | `Architecture.md` Sec 11, 13 | P07, P08 | `INV-04`, `INV-05`, `INV-08` |
| **Controlled Outbox & Safe Dispatch** | `Description.txt` L32-34, L112-113; `Workflow detail.png` | `FR-DISP-01` to `07` | `Architecture.md` Sec 11, 12 | P07 | `INV-04`, `INV-07`, `INV-08` |
| **Student Registration & Portal** | `Description.txt` L15, L33; `Workflow detail.png` | `FR-REG-01` to `10` | `Architecture.md` Sec 7.3 | P06 | `INV-06`, `INV-10`, `INV-11` |
| **Scheduling, Sessions, & Conflicts** | `Description.txt` L16; `Workflow detail.png` | `FR-SCHED-01` to `08` | `Architecture.md` Sec 16 | P09 | `INV-06`, `INV-11`, `INV-12` |
| **Employer Results & Publication** | `Description.txt` L17; `Workflow detail.png` | `FR-RESULT-01` to `05` | `Architecture.md` Sec 16 | P09 | `INV-04`, `INV-09`, `INV-12` |
| **Closure & Reproducible Reporting** | `Description.txt` L17; `Workflow detail.png` | `FR-REPORT-01` to `05`, `FR-CLOSE-01` to `05` | `Architecture.md` Sec 7.5, 17 | P09 | `INV-08`, `INV-09`, `INV-12` |
| **Exception Handling & Adaptive Recovery** | `Description.txt` L115-133 | `FR-EXC-01` to `07` | `Architecture.md` Sec 17.1 | P08, P12 | `INV-04`, `INV-05`, `INV-08` |
| **Core Architecture & Technical Stack** | `Agents detail.png` | `NFR-01` to `NFR-12`, `FR-INT-01` to `02` | `Architecture.md` Sec 1 to 5 | P01 | `INV-06`, `INV-07`, `INV-08` |

---

## 4. Release Boundary Confirmation (P00-T02)

To avoid scope creep while ensuring a complete, testable recruitment lifecycle, the release boundaries are formally confirmed as follows:

```
[Milestone M0: Foundations]
   └── P00: Scope, Contracts, & Decision Register (Current)
   └── P01: Monorepo, Local Dev, Docker Services, Shells
   └── P02: Identity, Scope, Student Revisions & CSV Imports

[Milestone M1: Reviewed Intelligence]
   └── P03: Drives, Private S3 Intake, Extraction & Locators
   └── P04: JD Intelligence, Clarification Loop, Rule Review
   └── P05: Deterministic Eligibility Engine & Cohort Snapshots

[Milestone M2: Participation & Controlled Actions]
   └── P06: Student Documents, Validation, Registration Portal
   └── P07: Proposals, Approvals Center, Outbox & Mail Dispatch
   └── P08: Durable LangGraph Orchestration & Checkpoints

[Milestone M3: Complete Local MVP]
   └── P09: Scheduling, Rounds/Sessions, Results, Closure & Reports

===================== [MVP RELEASE BOUNDARY] =====================

[Milestone M4: Pilot Readiness Gate]
   └── P10: Hardening, Security/Load Testing, Pilot Configuration Gate

[Milestone M5: External Connectors (Post-MVP)]
   └── P11: Live Gmail, Google Sheets, & Google Calendar Connectors

[Milestone M6: Adaptive Recovery (Advanced)]
   └── P12: Exception Resolution Agent & Impact-Driven Recovery Plans

[Milestone M7: Measured Expansion]
   └── P13: Multi-tenant Scaling, Advanced Optimizations
```

### Confirmation Checklist:
1. **Full Local MVP Scope (P00 - P09):** Covers every operational phase of a recruitment drive (from raw JD upload to student registration, interview scheduling, employer results recording, and final report generation) completely offline/locally using synthetic data, Dockerized services (Postgres, Redis, MinIO, Mailpit), and deterministic adapters.
2. **No Orphaned Workflow Steps:** No step from `Workflow detail.png` or `Description.txt` is missing from the local MVP. Basic scheduling and results are intentionally retained in P09 rather than deferred.
3. **Pilot Hardening Gate (P10):** Real student records, live email providers, real OIDC identity providers, and live ClamAV scanner integration are gated behind P10 verification.
4. **Connector Independence (P11):** Live Google Workspace connections (Gmail, Sheets, Calendar) are strictly post-MVP extensions. The system operates fully via manual uploads, exports, and internal calendars when Google is unavailable.
