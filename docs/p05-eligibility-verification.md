# P05 Deterministic Eligibility Verification

Date: 29 October 2026
Engine: `eligibility-v1.0.0`

## Acceptance evidence

- The pure engine evaluates only a typed approved `eligibility-v1` policy and an immutable academic-facts value. It imports no database, HTTP, model, queue, or storage adapter.
- Section 10.2 Students A-J match all expected outcomes and reason codes, including unknown-first precedence for Student H, unverified evidence for I, unsupported scale for J, exact threshold equality for F, and no rounding for G.
- Empty or entirely `not_required` policies fail validation before any student classification.
- Evaluation runs persist the policy hash, engine/normalization versions, frozen student membership and academic revision IDs, cohort fingerprint, per-student input fingerprint, predicate findings, and reconciled outcome counts.
- A later academic import, approved correction, policy approval, or active-roster change conservatively marks affected completed runs stale without changing historical results.
- Coordinator result access is assigned-drive scoped. Student endpoints select the authenticated student's profile server-side and expose only that student's result for published drives.
- Review requests create an attributable evidence-review task and never edit the persisted eligibility outcome.

## Benchmark

Development measurement on Windows 11, Python 3.12.16, using the four required predicates and exact `Decimal` arithmetic:

```text
10,000 pure evaluations: 176.66 ms
Per student: 0.017666 ms
Agreement: 10,000 / 10,000 eligible for the benchmark fixture
```

This is a local engine measurement, not a production service-level claim. Database snapshot creation, queue latency, authorization, and result persistence are intentionally excluded and are measured independently by integration tests and persisted `duration_ms` values.
