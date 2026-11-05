"""
Badge Dictionary for PlacementOS.
"""

def get_badge_dictionary():
    return '''---

## 5. Comprehensive State and Status Badge Reference Dictionary

This dictionary serves as the single source of truth for all status tags, pill chips, and badges across PlacementOS. All badges adhere to the strict component pattern defined in `DESIGN.md`: **Border Radius 9999px (full pill), DM Sans 12px weight 600, padding 4px 12px, zero drop shadows**.

### 5.1 Academic Eligibility & Predicate Statuses
Academic eligibility is strictly deterministic. Badges reflect verified evidence evaluations and the conservative aggregation rule (Invariant INV-01, INV-02).

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Overall Eligible | `ELIGIBLE` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Overall Ineligible | `INELIGIBLE` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Overall Needs Review | `NEEDS_REVIEW` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Predicate Pass | `PASS` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | None |
| Predicate Fail | `FAIL` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | None |
| Predicate Unknown | `UNKNOWN` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Frost Gray (`#e0e0e0`) |
| Evidence Verified | `EVID_VERIFIED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | None |
| Evidence Missing | `EVID_MISSING` | Cream | `#faf7e8` | Coral Pulse | `#ff643b` | None |
| Evidence Unverified | `EVID_UNVERIFIED` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Evaluation Stale | `RESULTS_STALE` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |

### 5.2 Document Readiness & Scan Finding Statuses
Document readiness is evaluated independently of academic eligibility and represents file integrity, antivirus scanning, and structural validation.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Ready / Clean | `DOCS_READY` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Pending Upload | `DOCS_PENDING` | Cloud Gray | `#f2f2f2` | Slate | `#7a7a7a` | None |
| Blocked Corrupt | `DOC_BLOCKED` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Quarantined Virus | `QUARANTINED` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 2px solid Coral Pulse (`#ff643b`) |
| Scanning Progress | `SCANNING` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Needs Review | `DOC_REVIEW` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Optional Missing | `NOT_UPLOADED` | Cloud Gray | `#f2f2f2` | Ash | `#a6a6a6` | 1px solid Frost Gray (`#e0e0e0`) |

### 5.3 Registration & Participation Statuses
Tracks the student's formal intention to participate in a specific recruitment drive.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Submitted / Confirmed | `REGISTERED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Registration Draft | `REG_DRAFT` | Cloud Gray | `#f2f2f2` | Graphite | `#3d3d3d` | 1px solid Frost Gray (`#e0e0e0`) |
| Withdrawn Pre-Cutoff | `WITHDRAWN` | Sand | `#f4ece9` | Slate | `#7a7a7a` | None |
| Eligibility Hold | `ELIGIBILITY_HOLD` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Cancelled Post-Cutoff | `CANCELLED` | Cloud Gray | `#f2f2f2` | Coral Pulse | `#ff643b` | 1px solid Frost Gray (`#e0e0e0`) |
| Not Registered | `NOT_REGISTERED` | Cloud Gray | `#f2f2f2` | Ash | `#a6a6a6` | None |

### 5.4 Drive Lifecycle Stages
Represents the macro operational progress of a campus recruitment drive from intake to closure.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Draft Setup | `DRAFT` | Cloud Gray | `#f2f2f2` | Graphite | `#3d3d3d` | 1px solid Frost Gray (`#e0e0e0`) |
| Intake In Progress | `INTAKE` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Policy Review | `POLICY_REVIEW` | Lilac Wash | `#fdf0ff` | Indigo Bloom | `#460095` | None |
| Registration Open | `REGISTRATION_OPEN` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Registration Closed | `REGISTRATION_CLOSED` | Cream | `#faf7e8` | Charcoal | `#333333` | None |
| In Progress Rounds | `IN_PROGRESS` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | 1px solid Sky Signal (`#00b4dc`) |
| Operational Hold | `OPERATIONAL_HOLD` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 2px solid Coral Pulse (`#ff643b`) |
| Concluded / Closed | `DRIVE_CLOSED` | Paper White | `#ffffff` | Canopy Green | `#0a3922` | 1px solid Canopy Green (`#0a3922`) |
| Cancelled | `DRIVE_CANCELLED` | Cloud Gray | `#f2f2f2` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |

### 5.5 LangGraph Durable Workflow States
Reflects the durable state machine checkpoints persisted in PostgreSQL.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Node Running | `WORKFLOW_RUNNING` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Waiting Clarification | `WAITING_CLARIFICATION` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Waiting Policy Approval| `WAITING_POLICY_APPROVAL`| Lilac Wash | `#fdf0ff` | Indigo Bloom | `#460095` | 1px solid Indigo Bloom (`#460095`) |
| Waiting Action Approval| `WAITING_ACTION_APPROVAL`| Lilac Wash | `#fdf0ff` | Indigo Bloom | `#460095` | 1px solid Indigo Bloom (`#460095`) |
| State Persisted | `CHECKPOINT_SAVED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | None |
| Checkpoint Failed | `CHECKPOINT_FAILED` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Workflow Concluded | `WORKFLOW_COMPLETED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |

### 5.6 Consequential Approval Proposal Statuses
Tracks the lifecycle of immutable proposals submitted for attributable human authorization (Invariants INV-04, INV-05).

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Pending Review | `PENDING_REVIEW` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Formally Approved | `APPROVED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Formally Rejected | `REJECTED` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Revision Requested | `REVISION_REQUESTED` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Proposal Stale | `PROPOSAL_STALE` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 2px solid Coral Pulse (`#ff643b`) |
| Proposal Expired | `EXPIRED` | Cloud Gray | `#f2f2f2` | Slate | `#7a7a7a` | None |

### 5.7 Message Dispatch & Outbox Statuses
Tracks individual communication deliveries through the asynchronous email outbox worker.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Claimed by Worker | `DISPATCH_CLAIMED` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Provider Accepted | `PROVIDER_ACCEPTED` | Sage Wash | `#e4f7ee` | Canopy Green | `#0a3922` | None |
| Confirmed Delivered | `DELIVERED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Retryable Failure | `RETRYABLE_FAILURE` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Permanent Failure | `PERMANENT_FAILURE` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Ambiguous Unknown | `UNKNOWN_STATUS` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 2px solid Coral Pulse (`#ff643b`) |
| Stopped by User | `DISPATCH_STOPPED` | Sand | `#f4ece9` | Slate | `#7a7a7a` | None |

### 5.8 Operational Exception Severity & Statuses
Categorizes operational anomalies and their bounded recovery progress.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| High Severity | `HIGH_SEVERITY` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Medium Severity | `MEDIUM_SEVERITY` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Low Severity | `LOW_SEVERITY` | Cloud Gray | `#f2f2f2` | Graphite | `#3d3d3d` | 1px solid Frost Gray (`#e0e0e0`) |
| Exception Open | `OPEN` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | None |
| Plan Drafted | `PLAN_DRAFTED` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| In Recovery | `IN_RECOVERY` | Lilac Wash | `#fdf0ff` | Indigo Bloom | `#460095` | None |
| Plan Stale | `PLAN_STALE` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 2px solid Coral Pulse (`#ff643b`) |
| Resolved & Closed | `RESOLVED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |

### 5.9 System Health & Production Readiness Gates
Observability statuses for infrastructure workers, storage, scanners, and readiness compliance.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gate Passed | `GATE_PASSED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Gate Pending | `GATE_PENDING` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Gate Sign-off Req | `GATE_SIGNOFF_REQ` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Service Active | `SERVICE_ACTIVE` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | None |
| Service Degraded | `SERVICE_DEGRADED` | Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Ash (`#a6a6a6`) |
| Service Offline | `SERVICE_OFFLINE` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | 1px solid Coral Pulse (`#ff643b`) |
| Synthetic Demo | `SYNTHETIC_DEMO` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Canopy Green (`#0a3922`) |
| Production Pilot | `PILOT_PRODUCTION` | Canopy Green | `#0a3922` | Paper White | `#ffffff` | None |

### 5.10 Scheduling & Employer Selection Outcome Statuses
Rounds, sessions, attendance, and official recruitment outcomes.

| Logical State | Badge Text | Surface Fill (Token) | Hex Fill | Text Color (Token) | Hex Text | Border Definition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Session Published | `SESSION_PUBLISHED`| Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Session Draft | `SESSION_DRAFT` | Cloud Gray | `#f2f2f2` | Slate | `#7a7a7a` | 1px solid Frost Gray (`#e0e0e0`) |
| Session Rescheduled | `SESSION_RESCHEDULED`| Cream | `#faf7e8` | Charcoal | `#333333` | 1px solid Coral Pulse (`#ff643b`) |
| Attendance Present | `PRESENT` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | None |
| Attendance Absent | `ABSENT` | Peach Wash | `#ffede8` | Coral Pulse | `#ff643b` | None |
| Attendance Excused | `EXCUSED` | Sand | `#f4ece9` | Slate | `#7a7a7a` | None |
| Outcome Advanced | `ADVANCED` | Sky Wash | `#ccf0f8` | Deep Teal | `#003642` | None |
| Outcome Selected | `OFFER_EXTENDED` | Mint Wash | `#d2f2e3` | Canopy Green | `#0a3922` | 1px solid Leaf Bright (`#1dbf73`) |
| Outcome Rejected | `NOT_SELECTED` | Cloud Gray | `#f2f2f2` | Slate | `#7a7a7a` | 1px solid Frost Gray (`#e0e0e0`) |
| Outcome Waitlisted | `WAITLISTED` | Lilac Wash | `#fdf0ff` | Indigo Bloom | `#460095` | None |
| Outcome Pending | `OUTCOME_PENDING` | Cream | `#faf7e8` | Charcoal | `#333333` | None |
'''

print("Badge dictionary defined.")
