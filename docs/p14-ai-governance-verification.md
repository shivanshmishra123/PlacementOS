# P14 AI Governance, Provider Selection, and Model Contracts

> Status: completed, verified 6 November 2026. This document records the governance, provider selection, data classification, error bounds, and authority limits for the transition to real AI models under release 0.14.0.

---

## 1. Provider Selection and Evaluated Model (P14-T01)

- **Selected Provider:** Google Gemini (Google AI Studio API via `langchain-google-genai` and `google-genai`).
- **Evaluated & Verified Model Identifier:** `gemini-2.5-flash-lite` (verified with live API call; fast latency, optimal quota safety on free tier, zero 503 unavailability during high demand). Secondary tested: `gemini-2.5-flash`.
- **Selection Justification:**
  1. **Native Structured Output:** Supports provider-native JSON schema enforcement (`response_mime_type="application/json"` with Pydantic schemas via `.with_structured_output(JDExtractionResult)`), eliminating fragile regex or free-form JSON parsing.
  2. **Fast & High-Availability:** Verified live extraction completed in 4,266 ms with 14 provenance citations and 0 errors on Google AI Studio free tier.
  3. **Zero Token Waste Architecture:** PlacementOS includes a local recording cache (`CachedModelInterpreter`) so unit and integration test runs consume exactly 0 tokens.
  4. **Cost & Rate Safety:** PlacementOS client-side budgeting (`daily_request_cap=50`, `max_input_tokens=4000`, `max_calls_per_drive=3`) guarantees the application cannot exhaust or exceed the free tier.

---

## 2. Data Classification and Privacy Boundary (P14-T02)

| Data Class | Allowed to Send? | Rationale & Protection |
|---|---|---|
| **Pasted / Uploaded JD Text** | **YES** | Public recruitment materials and job descriptions. Cleaned and truncated to maximum 4,000 tokens. |
| **Student Profiles & Records** | **STRICTLY PROHIBITED** | Invariant `INV-10` mandates student information minimization. No student identifiers, names, grades, or personal documents are sent to external LLMs. |
| **Student Resumes / Documents** | **STRICTLY PROHIBITED** | Document validation is handled locally by deterministic parsers and ClamAV scanners; resumes are never forwarded to the model gateway. |
| **Secrets & Session Tokens** | **STRICTLY PROHIBITED** | API keys, cookies, OAuth tokens, and database credentials remain restricted to server runtime environment variables and are excluded from prompt templates. |

---

## 3. Provider Retention and Data Policy (P14-T03)

- **Development Policy:** Google AI Studio free-tier terms allow Google to use logged data to train products under standard terms. Therefore, during local development and testing, only synthetic or non-confidential JD text fixtures are processed.
- **Production Gate:** Transitioning to real student-facing or institutional pilot operation requires an enterprise Google Cloud Vertex AI project with zero-data-retention, customer-managed encryption keys, and SOC2/HIPAA compliance agreements.
- **Data Region:** Default multi-region for Google AI Studio API (`us-central1` / global).

---

## 4. Operational Roles & Incident Ownership (P14-T04)

- **AI Service Owner:** Lead Placement Coordinator (authorizes model configuration updates).
- **Security & Privacy Owner:** Institutional Information Security Officer (audits data minimization and secret isolation).
- **Cost & Budget Owner:** Placement Operations Administrator (monitors request caps and token usage).
- **Incident Response:** In the event of provider errors or unexpected behavior, the system fails closed to manual coordinator entry.

---

## 5. Measurable Acceptance Datasets & Field Quality Metrics (P14-T05)

### Evaluation Datasets
1. **Benchmark JD 1 (Standard Engineering):** Contains explicit criteria (CGPA 7.5, CSE/ECE branches, max 0 backlogs, CTC 18.5 LPA, deadline 2026-11-30). Expected: 100% precision extraction with exact source locator citations.
2. **Benchmark JD 2 (Ambiguous Criteria):** Mentions "good academic record" and conflicting graduation years (2026 vs 2027). Expected: Flagged as `open` clarifications (`INV-02`), zero hallucinated values, and conservative manual review triggers.
3. **Benchmark JD 3 (Pasted Raw Text):** Unstructured text with scattered bullet points. Expected: Accurate extraction of allowed branches and compensation details.

### Quality Criteria
- **Field Precision:** $\ge 98\%$ on explicit numerical thresholds (CGPA, backlogs, CTC).
- **Hallucination Rate:** $0\%$ (any unsupported fact without an exact paragraph citation is rejected).
- **Provenance Traceability:** $100\%$ of candidate facts must cite paragraph/page locators (`INV-03`).

---

## 6. Failure Behavior, Circuit Breaking & Fallback (P14-T06)

```mermaid
flowchart TD
    REQ[Extraction Request] --> ATTEMPT{Call Gemini API}
    ATTEMPT -->|Success| VALIDATE[Validate Pydantic Schema & Locators]
    VALIDATE -->|Valid| SAVE[Persist candidate_facts (Revisioned)]
    VALIDATE -->|Malformed| REVIEW[Log Warning & Prompt Coordinator Manual Entry]
    ATTEMPT -->|Timeout >30s| RETRY{Attempt < 2?}
    RETRY -->|Yes| DELAY[Exponential Backoff 2s] --> ATTEMPT
    RETRY -->|No| TRIP[Trip Circuit Breaker]
    ATTEMPT -->|Rate Limit 429| TRIP
    ATTEMPT -->|Cap Exceeded >50/day| TRIP
    TRIP --> FALLBACK[Activate Manual Fallback Mode & Alert Coordinator]
```

- **Timeout:** Bounded at 30 seconds. One transient retry with exponential backoff.
- **Rate Limit (429):** Fails closed; immediately triggers fallback to manual coordinator entry without blocking drive creation.
- **Refusal / Incomplete:** Logged with error detail; candidate facts remain empty with an actionable coordinator notification.

---

## 7. Model Authority Freeze (P14-T07)

1. **Proposal-Only:** Model output is strictly typed as untrusted `candidate_facts` on the `interpretations` table.
2. **No Autonomous Approval:** Models cannot approve policies, evaluate eligibility, register students, or dispatch messages (`INV-01`, `INV-04`).
3. **Tool Isolation:** The model execution boundary has zero access to SQL, shell commands, file systems, email SMTP, or Google Calendar APIs (`INV-07`).
4. **Deterministic Gate:** Academic eligibility is computed exclusively by the pure Python deterministic engine from approved policies, never by an LLM prompt (`INV-01`).
