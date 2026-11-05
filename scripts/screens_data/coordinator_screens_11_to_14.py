"""
Screens 11 to 14 for PlacementOS.
"""

def get_screens_11_to_14():
    return '''## SCREEN 11: Student Roster (`/coordinator/students`)

### 1. Screen Identity & Route
- **Screen Name:** Institutional Student Roster, CSV Import & Correction Review
- **Route:** `/coordinator/students`
- **Primary Audience:** Placement Coordinator, Academic Records Reviewer

### 2. User Role & Capabilities
- **Role:** Placement Coordinator / Records Reviewer (`student:view`, `student:import`, `student:verify_correction`)
- **Capabilities:** Search and filter verified student records, inspect immutable academic revisions, execute multi-step CSV roster imports with column mapping and dry-run preview, and adjudicate student-submitted academic correction proposals.

### 3. Core Purpose
Maintain institutional academic evidence integrity: ensure that only verified administrative student records inform deterministic eligibility calculations, while providing a strict two-phase commit import flow and an attributable correction review process (Invariant INV-02).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Bar:** Institution context header with 2 Master Tabs: `[Tab 1: Student Roster]` and `[Tab 2: Correction Requests (3 Pending)]`, and primary **Import Students (CSV)** CTA.
- **Roster Area:** Filter ribbon + Full-width data table (White Product Card `#ffffff`, 16px radius).
- **Import Modal Layer:** 4-Step Multi-Stage CSV Import Wizard (Overlaid White Product Card `#ffffff` with 24px padding).

### 5. Key UI Sections & Component Breakdown
1. **Master Tabs & Action Ribbon:**
   - Tabs:
     - `Student Roster (480 Active Records)`
     - `Correction Requests (3 Pending Review)` (Badge: `#ccf0f8` Sky Wash pill)
   - Primary Action: **Import Students (CSV)** (Coral Filled Button `#ff643b`, 40px radius, white text).
   - Secondary Action: **Export Verified Roster** (Ghost Outline Button `#000000`, 40px radius).
2. **Tab 1: Student Roster View:**
   - *Filter Bar:* Search input ("Search by roll number, name, or institutional email...") + Dropdown filters for Branch (`CSE`, `IT`, `ECE`, `EE`, `ME`, `CE`), Graduation Batch (`2026`, `2027`), and Verification Status (`Verified`, `Unverified`, `Pending Correction`).
   - *Student Master Table (White Product Card `#ffffff`):*
     - Columns: Roll Number | Student Name | Branch | Batch | CGPA / Scale | Active Backlogs | Verification Badge | Last Import Revision | Actions.
     - Row Example 1: `2023CS104` | Rahul Verma | CSE | 2027 | `8.42 / 10.00` | `0` | `VERIFIED` [Leaf Bright tag] | `Rev 2 (Registrar Import)` | Actions: **View Profile**, **History**.
     - Row Example 2: `2023EC089` | Priya Nair | ECE | 2027 | `7.90 / 10.00` | `null (Unknown)` | `UNVERIFIED` [Cream tag] | `Rev 1 (Draft Import)` | Actions: **Verify**.
3. **Tab 2: Academic Correction Requests Review:**
   - Table of student-submitted correction proposals:
     - Columns: Roll Number | Student Name | Requested Field | Verified Value | Proposed Value | Student Explanation | Supporting Document | Attributable Actions.
     - Row Item: `2023CS104` | Rahul Verma | `CGPA` | `8.42` | `8.65` | "6th Sem re-evaluation marks updated by Exam Cell" | `Sem6_Revised_Marksheet.pdf` (Download) | Actions: **Approve Correction** (Coral Filled Button, 32px), **Reject Correction** (Ghost Outline Button, 32px).
   - *Approval Note Requirement:* Approving creates a new verified academic revision (`Rev 3`) and automatically marks dependent eligibility evaluations stale.
4. **CSV Import Multi-Step Wizard (Modal Container):**
   - *Step 1: File Upload:* Drag-and-drop zone for roster CSV file (Max 2,000 rows per institutional quota).
   - *Step 2: Column Mapping:* Interactive mapping table matching CSV headers to PlacementOS schema:
     - `Student_ID` → `roll_number` (String, required)
     - `Full_Name` → `full_name` (String, required)
     - `Dept_Code` → `branch` (Normalized enum: CSE, IT, ECE...)
     - `Cum_CGPA` → `cgpa` (Decimal, 0.00 to 10.00)
     - `Current_Arrears` → `backlogs` (Integer >= 0)
   - *Step 3: Validation & Dry-Run Preview Table (Sage Wash `#e4f7ee` card):*
     - Summary Metrics: Total Rows: `450` | Valid Rows: `442` | Invalid Rows: `3` (Missing roll) | Duplicates: `5` | Unknown Branch Aliases: `0`.
     - Data preview table highlighting invalid cells in red and duplicates in amber.
   - *Step 4: Attributable Commit:*
     - Reviewer Rationale Field: "Enter import attribution / registrar source memo..."
     - Fingerprint: `sha256:3a1b89...`
     - Action: **Commit Import to Database** (Coral Filled Button `#ff643b` — disabled if preview is stale).

### 6. Interface States & Exact Copy
- **Normal Roster State:** 480 verified student records displayed with paginated navigation (50 per page).
- **Import Preview Stale State (Step 4 Modal):**
  - High-Severity Warning Banner: Cream `#faf7e8` card with 1px solid Coral Pulse `#ff643b` border.
  - Headline: "IMPORT PREVIEW STALE: COMMIT DISABLED"
  - Copy: "The dry-run preview is older than 5 minutes or the institutional roster was modified concurrently. In accordance with Invariant INV-08, re-run preview before committing."
  - Action: **Refresh Validation Preview** (Coral Filled Button `#ff643b`).
- **Duplicate Records Warning:**
  - Amber chip on preview rows: "Duplicate Roll No 2023CS012 detected. Existing record is identical; row will be skipped."
- **Empty State (Initial Setup):**
  - Headline: "No student records imported yet" (DM Sans 24px weight 600, `#0a3922`).
  - Copy: "Upload the registrar's official CSV export to establish the verified student roster for the 2026–27 placement season."
  - Action: **Import Students (CSV)** (Coral Filled Button `#ff643b`).

### 7. Primary & Secondary Actions
- **Primary CTA:** **Import Students (CSV)** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Modal Commit CTA:** **Commit Import to Database** (Coral Filled Button `#ff643b`, 40px radius).
- **Correction Action:** **Approve Correction** (Coral Filled Button, 32px height).
- **Secondary Action:** **Export Verified Roster** (Ghost Outline Button `#000000`, 40px radius).

### 8. Data Displayed & Visual Formats
- Decimal academic scores: `8.42 / 10.00`. Missing values strictly rendered as `null (Unknown)`, never coerced to `0.00`.
- Cryptographic import hash: `sha256:3a1b89...`.
- Roll numbers formatted in monospace DM Sans: `2023CS104`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Student: Verified | `RECORD_VERIFIED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Student: Unverified | `RECORD_UNVERIFIED`| Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Correction: Pending | `CORRECTION_PENDING`| Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Correction: Approved | `CORRECTION_APPROVED`| Mint Wash (`#d2f2e3`)| Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Row: Invalid | `INVALID_ROW` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Students"
- **Breadcrumbs:** `PlacementOS > Student Roster`
- **Context Transition:** Approving an academic correction prompts a re-evaluation alert on all affected active drives.

---

## SCREEN 12: Exception Center (`/coordinator/exceptions` and `/coordinator/exceptions/[id]`)

### 1. Screen Identity & Route
- **Screen Name:** Operational Exception Management & Recovery Workspace
- **Route:** `/coordinator/exceptions` (List View) and `/coordinator/exceptions/[id]` (Detail & Recovery View)
- **Primary Audience:** Placement Coordinator, Exception Resolution Specialist

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`exception:view`, `exception:resolve`, `recovery:approve`)
- **Capabilities:** Triage operational exceptions across categories (criteria changes, stale approvals, dispatch failures, schedule conflicts), inspect deterministic impact analyses, review structured recovery plans, and execute bounded recovery steps with human sign-off.

### 3. Core Purpose
Contain, triage, and resolve operational anomalies using strictly bounded deterministic recovery workflows: calculate exact affected candidate scopes, pause affected drives, prepare unsent correction notices, and ensure no recovery step executes without attributable human approval (Invariant INV-04, INV-05).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **List View Layout (`/coordinator/exceptions`):**
  - Top Filter Bar: Category, Severity, and Drive facets.
  - Exception Cards Grid: Responsive grid of Pastel Feature Cards (Peach Wash for High, Cream for Medium).
- **Detail View Layout (`/coordinator/exceptions/[id]`):**
  - Top Case Header with Severity Banner and Drive Link.
  - 2-Column Split Layout (45/55 Split):
    - Left Column (45%): Affected Resources Inspector, Root Cause Revisions Diff, and Audit Evidence (White Product Card `#ffffff`).
    - Right Column (55%): Structured Recovery Plan Stepper, Impact Summary, and Plan Execution Console (Lilac Wash `#fdf0ff` card).

### 5. Key UI Sections & Component Breakdown
1. **Exception List View Components (`/coordinator/exceptions`):**
   - Header: "Operational Exceptions Hub" (DM Sans 32px weight 600, `#0a3922`).
   - Filter Tabs: `All (6)`, `High Severity (2)`, `Medium Severity (3)`, `Low Severity (1)`.
   - Category Filters: `Criteria Changes`, `Stale Approvals`, `Dispatch Failures`, `Schedule Conflicts`, `Malware Detections`.
   - Exception Cards:
     - *Card 1 (Peach Wash `#ffede8`):*
       - Severity Tag: `HIGH SEVERITY` (Coral Pulse `#ff643b` tag).
       - Title: `CRITERIA_CHANGE_AFTER_REGISTRATION`
       - Drive: `Google India — Software Engineer`
       - Summary: Recruiter raised CGPA cutoff from 7.00 to 7.50 after 210 registrations were submitted. 18 registered students now fail criteria.
       - Impact: `18 Registrations Affected` | Status: `RECOVERY_PLAN_DRAFTED` | Owner: `Dr. K. Sharma`.
       - Action: **Open Recovery Workspace →** (Coral Filled Button `#ff643b`, 32px height).
2. **Exception Detail & Recovery Workspace (`/coordinator/exceptions/[id]`):**
   - *Case Header Strip:*
     - Case ID: `#EXC-409` | Severity Pill: `HIGH SEVERITY` | Created: `2026-11-04 15:10:00 IST` | Status: `IN_RECOVERY`.
     - Affected Drive: `Google India — Software Engineer (DRV-8912)`.
   - *Left Column: Affected Resources & Evidence (White Product Card `#ffffff`):*
     - Affected Resources Table: List of 18 students whose eligibility flipped from `Eligible` to `Ineligible`.
       - Columns: Roll Number | Student Name | Branch | CGPA | Prior Status (`Eligible`) | Recalculated Status (`Ineligible`) | Registration (`Eligibility Hold`).
     - Revisions Diff Box:
       - Policy v1.0: `CGPA >= 7.00` → Policy v2.0: `CGPA >= 7.50`
       - Attributed Source: Recruiter memo dated 2026-11-04 (Attached).
   - *Right Column: Structured Recovery Plan Stepper (Lilac Wash `#fdf0ff` card, 24px padding):*
     - Headline: "Deterministic Recovery Plan" (DM Sans 20px weight 600, `#460095`).
     - Ordered Execution Steps:
       - *Step 1: Place Drive on Operational Hold*
         - Precondition: Drive currently active. Status: `COMPLETED ✅` (Executed 2026-11-04 15:12 IST).
       - *Step 2: Place 18 Affected Registrations on Eligibility Hold*
         - Status: `COMPLETED ✅` (Prevents student advancement to scheduling).
       - *Step 3: Stale Pending Schedule Proposals*
         - Status: `COMPLETED ✅` (Invalidated Proposal `#SCHED-014`).
       - *Step 4: Draft Unsent Correction Broadcast Proposal*
         - Explanation: Prepares personalized email informing the 18 students of the recruiter criteria change. Message remains unsent until approved via Communication Approval flow.
         - Status: `PENDING_APPROVAL ⏳` (Proposal `#COMM-PROP-108`).
       - *Step 5: Release Operational Hold on Drive*
         - Precondition: Steps 1 through 4 executed. Status: `BLOCKED (Awaiting Step 4)`.
   - *Plan Authorization Console:*
     - Mandatory Rationale: "Enter recovery approval justification..."
     - Actions:
       - **Approve & Execute Next Step** (Coral Filled Button `#ff643b`, 40px radius, white text).
       - **Cancel Remaining Steps** (Ghost Outline Button with Coral border).

### 6. Interface States & Exact Copy
- **Plan In Execution State:**
  - Progress bar across right pane: "Step 3 of 5 completed. Step 4 awaiting communication approval."
- **Plan Stale State (Registration State Changed):**
  - High-Severity Warning Banner: Cream `#faf7e8` card with 1px solid Coral Pulse `#ff643b` border.
  - Headline: "RECOVERY PLAN STALE: IMPACT RECALCULATION REQUIRED"
  - Copy: "Underlying registration state was modified (1 student voluntarily withdrew). Impact analysis is stale. Re-running deterministic impact calculation..."
  - Action: **Recalculate Impact Analysis** (Coral Filled Button `#ff643b`).
- **Manual Fallback State (AI Resolution Agent Offline):**
  - Info Banner: Sky Wash `#ccf0f8`, Deep Teal `#003642` text.
  - Copy: "AI Exception Resolution Agent unavailable. Bounded manual recovery actions are active below. All recovery operations remain strictly deterministic."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Approve & Execute Next Step** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Recalculate Impact Analysis** (Ghost Outline Button `#000000`, 40px radius).
- **Destructive Action:** **Cancel Remaining Plan Steps** (Ghost Outline Button with Coral border).

### 8. Data Displayed & Visual Formats
- Affected counts formatted in DM Sans Display 32px: `18 Students Affected`.
- Severity badges: `HIGH` (Coral Pulse `#ff643b`), `MEDIUM` (Cream `#faf7e8`), `LOW` (Cloud Gray `#f2f2f2`).
- Policy diffs formatted in code diff syntax with `+` and `-` markers.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Severity: High | `HIGH_SEVERITY` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Severity: Medium | `MEDIUM_SEVERITY` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Status: Drafted | `PLAN_DRAFTED` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Status: In Recovery | `IN_RECOVERY` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |
| Status: Resolved | `RESOLVED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Exceptions"
- **Breadcrumbs:** `PlacementOS > Exceptions Hub > Case #EXC-409`
- **Context Transition:** Executing Step 4 links directly to the Communications Approval Center for message sign-off.

---

## SCREEN 13: Integrations (`/coordinator/integrations`)

### 1. Screen Identity & Route
- **Screen Name:** Google Workspace Connectors & External Integrations Hub
- **Route:** `/coordinator/integrations`
- **Primary Audience:** Placement Coordinator, System Administrator

### 2. User Role & Capabilities
- **Role:** Placement Coordinator / System Admin (`integration:view`, `integration:connect`, `integration:revoke`)
- **Capabilities:** Inspect Google Workspace connector statuses, initiate isolated OAuth flows with narrow scopes, monitor connection health, disconnect or revoke integrations, and verify integration-gating boundaries.

### 3. Core Purpose
Manage external provider boundaries with strict security controls: ensure that Google Workspace connectors (Gmail, Sheets, Calendar) operate in mock sink mode by default, require isolated live acceptance before production use, and strictly prohibit unrestricted inbox access or autonomous email dispatch (Invariants INV-06, INV-07).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Notice Banner:** Integration-Gated Environment Banner (Lilac Wash `#fdf0ff` card with 24px padding).
- **Main Connector Grid:** 3 Large Integration Product Cards (White Product Cards `#ffffff`, 16px radius, 1px Frost Gray `#e0e0e0` border).

### 5. Key UI Sections & Component Breakdown
1. **Environment Gating Notice Banner (Lilac Wash `#fdf0ff`):**
   - Headline: "Google Workspace Connectors (Integration-Gated Architecture)" (DM Sans 20px weight 600, `#460095`).
   - Copy: "Connectors operate in local mock sink mode by default. Real-account synchronization requires institutional Google OAuth credentials, explicit isolated live acceptance, and narrowly bound scopes. Email dispatch strictly uses PlacementOS internal SMTP dispatcher and never requests Gmail-Send authority."
   - Environment Status Tag: `LOCAL_BASELINE_MOCK_ACTIVE` (Mint Wash `#d2f2e3` tag).
2. **Connector Card 1: Google Gmail Connector (Intake Only):**
   - Header: Google Gmail Monogram | "Google Gmail Connector" | Status Badge: `CONNECTED_MOCK` (Leaf Bright tag).
   - Authorized Capabilities:
     - Read selected JD recruitment circular emails.
     - Extract attachments from user-selected email threads.
     - Prohibited: Gmail-Send authority is strictly blocked at the architectural level.
   - Active Scopes: `https://www.googleapis.com/auth/gmail.readonly`
   - Bound Account: `placements-intake@apex.edu` (Revision #2, Last verified: 2026-11-04 10:00 IST).
   - Actions: **Manage Connection** (Ghost Outline Button `#000000`), **Disconnect & Revoke** (Ghost Outline with Coral border).
3. **Connector Card 2: Google Sheets Connector (Roster Read & Export Write):**
   - Header: Google Sheets Monogram | "Google Sheets Connector" | Status Badge: `NOT_CONFIGURED` (Ash tag).
   - Authorized Capabilities:
     - Import student rosters from designated institutional spreadsheets.
     - Export candidate shortlists with formula escaping (`=`, `+`, `-`, `@`).
   - Active Scopes: `https://www.googleapis.com/auth/spreadsheets`
   - Actions: **Connect Google Sheets** (Coral Filled Button `#ff643b`, 40px radius, white text).
4. **Connector Card 3: Google Calendar Connector (Session Sync):**
   - Header: Google Calendar Monogram | "Google Calendar Connector" | Status Badge: `NOT_CONFIGURED` (Ash tag).
   - Authorized Capabilities:
     - Write published interview sessions to coordinator-owned calendar.
     - Watch for schedule conflicts.
     - Prohibited: Does not autonomously invite students or overwrite internal PlacementOS schedules.
   - Active Scopes: `https://www.googleapis.com/auth/calendar.events`
   - Actions: **Connect Google Calendar** (Ghost Outline Button `#000000`, 40px radius).

### 6. Interface States & Exact Copy
- **Mock Baseline Active State:** Cards show `CONNECTED_MOCK`. Subtitle: "Simulated responses enabled for local development and demonstration."
- **OAuth Token Expired / Scope Revoked State:**
  - Card 1 Alert: Cream `#faf7e8` card with Coral Pulse `#ff643b` border.
  - Headline: "OAUTH TOKEN EXPIRED / SCOPE REVOKED"
  - Copy: "The refresh token for `placements-intake@apex.edu` expired or the institutional administrator revoked `gmail.readonly` scope. Ingestion from Gmail is disabled."
  - Action: **Reconnect Institutional Account** (Coral Filled Button `#ff643b`).
- **Gated Environment Alert State:**
  - Notice on Connect Button: "Live account connection disabled in Synthetic Demo mode. Enable LIVE_OAUTH_ACCEPTED in environment configuration to connect production accounts."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Connect Google Sheets** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Manage Connection** (Ghost Outline Button `#000000`, 40px radius).
- **Revoke CTA:** **Disconnect & Revoke Tokens** (Ghost Outline Button with Coral border).

### 8. Data Displayed & Visual Formats
- OAuth scopes displayed in code format DM Sans 12px monospace.
- Connection timestamps: `2026-11-04 10:00:12 IST`.
- Server-side token storage indicator: `Encrypted Server-Side (AES-256-GCM) — Never exposed to browser storage.`

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Status: Connected Mock | `CONNECTED_MOCK` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Status: Live Connected | `CONNECTED_LIVE` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Status: Disconnected | `DISCONNECTED` | Cloud Gray (`#f2f2f2`) | Slate (`#7a7a7a`) | Frost Gray (`#e0e0e0`) |
| Status: Expired | `TOKEN_EXPIRED` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Integrations"
- **Breadcrumbs:** `PlacementOS > External Integrations`
- **Context Transition:** Disconnecting an integration immediately revokes associated background tasks and alerts active drives.

---

## SCREEN 14: Operations / System Health (`/coordinator/operations`)

### 1. Screen Identity & Route
- **Screen Name:** System Health, Production Readiness Gates & Operations
- **Route:** `/coordinator/operations`
- **Primary Audience:** Placement Coordinator, Institutional Administrator, DevOps Lead

### 2. User Role & Capabilities
- **Role:** Placement Coordinator / System Admin (`ops:view`, `config:manage`, `audit:view`)
- **Capabilities:** Inspect real-time operational health of asynchronous services (Celery workers, Redis, outbox dispatch, ClamAV, model provider), verify the 8 Production Readiness Gates, monitor institutional quotas, and inspect immutable system audit logs.

### 3. Core Purpose
Provide transparent, verifiable observability into PlacementOS's runtime infrastructure and compliance posture, guaranteeing that pilot production cannot proceed with unverified security, privacy, or infrastructure components.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Environment Banner:** Full-width Environment & Release Level Banner (Canopy Green `#0a3922` card with Paper White text).
- **2-Column Operational Grid (50/50 Split):**
  - Left Column (50%): 8 Production Readiness Gates Checklist Table (White Product Card `#ffffff`, 16px radius).
  - Right Column (50%): Asynchronous Health Tiles Grid, Institutional Operating Quotas, and Security Audit Stream (White Product Card `#ffffff`).

### 5. Key UI Sections & Component Breakdown
1. **Top Environment Banner (Canopy Green `#0a3922`):**
   - Headline: "ENVIRONMENT: SYNTHETIC DEMO BASELINE (P13 MEASURED EXPANSION)" (DM Sans 24px weight 600, Paper White `#ffffff`).
   - Copy: "Operational with synthetic student records, local ClamAV scanner, Mailpit development sink, and deterministic fixtures. Live student data operation remains gated until all 8 readiness gates are verified."
   - Version Tag: `PlacementOS Core Engine v1.4-p13 (Build: 2026.11.04.14)`
2. **Production Readiness Gates Checklist (Left Column, White Product Card):**
   - Header: "Mandatory Production Readiness Gates (8 Gates)" (DM Sans 18px weight 600, `#0a3922`).
   - Verification Table:
     1. Institutional OIDC / SAML SSO Integration: `❌ PENDING (Local dev identity active)`
     2. ClamAV Antivirus Container: `✅ VERIFIED HEALTHY (Signatures: v2026.11)`
     3. Email Dispatch Service: `✅ VERIFIED (Mailpit Local Sink Connected)`
     4. AI Model Provider (Gemini 1.5 Pro): `✅ VERIFIED (API quota active)`
     5. S3 Private Object Storage: `✅ VERIFIED (MinIO local storage operational)`
     6. Redis Broker & Celery Workers: `✅ VERIFIED (4 workers, concurrency 8)`
     7. Alembic Database Schema Migrations: `✅ VERIFIED (Head: p13_expansion_final)`
     8. Student Data Retention & Privacy Sign-off: `⚠️ PENDING INSTITUTIONAL APPROVAL`
   - Gate Overall Status Pill: `PILOT_GATED (2 Gates Pending)` in Peach Wash `#ffede8` with Coral Pulse `#ff643b` text.
3. **Live Health Tiles Grid (Right Column Top, 4 Pastel Feature Cards):**
   - *Tile 1 (Mint Wash `#d2f2e3`):* Celery Workers. Value: `4 Active` (Display 32px), Subtitle: `0 tasks queued, 0 errors`.
   - *Tile 2 (Sky Wash `#ccf0f8`):* Outbox Dispatcher. Value: `0s Lag` (Display 32px), Subtitle: `100% messages processed`.
   - *Tile 3 (Sage Wash `#e4f7ee`):* Ambiguous Sinks. Value: `0 Unknown` (Display 32px), Subtitle: `Zero unconfirmed sends`.
   - *Tile 4 (Cream `#faf7e8`):* Model Error Rate. Value: `0.0%` (Display 32px), Subtitle: `100 / 100 successful calls`.
4. **Institutional Operating Limits & Quotas (Right Column Middle):**
   - Open Drives Limit: `8 / 25 Maximum Open Drives Active` (Progress bar at 32%).
   - CSV Import Limit: `2,000 Rows per individual import`.
   - Candidate Export Limit: `500 Rows per export operation`.
   - Storage Quarantine Lifetime: `30 Days automatic retention`.
5. **Security & System Audit Trail (Right Column Bottom):**
   - Stream of recent security events:
     - `2026-11-04 15:45:10 IST` | Actor: `Dr. K. Sharma` | Action: `PROPOSAL_APPROVED` | Resource: `PROP-COMM-104` | Correlation ID: `corr_8a91c2`
     - `2026-11-04 15:30:12 IST` | Actor: `System Worker` | Action: `EVALUATION_COMPLETED` | Resource: `DRV-8912` | 312 Eligible
     - `2026-11-04 15:12:00 IST` | Actor: `Dr. K. Sharma` | Action: `OPERATIONAL_HOLD_PLACED` | Resource: `DRV-8912` | Reason: Criteria change

### 6. Interface States & Exact Copy
- **Synthetic Demo Baseline State:**
  - Banner prominently displays Canopy Green `#0a3922` with "SYNTHETIC DEMO" designation.
- **Pilot Ready State (All 8 Gates Passed):**
  - Banner shifts to Leaf Bright `#1dbf73` accent: "ENVIRONMENT: PILOT PRODUCTION READY".
  - Headline: "All 8 Production Readiness Gates Verified". Real student data ingestion authorized.
- **Worker Degraded / Outbox Stall State:**
  - Tile 1 Alert (Peach Wash `#ffede8`): "Celery Worker Lag > 180s. 48 tasks queued. Redis memory pressure detected."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Run Infrastructure Diagnostics** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Export System Audit Log** (Ghost Outline Button `#000000`, 40px radius).
- **Gate Action:** **Inspect Gate Evidence** (Ghost Outline Button, 32px height).

### 8. Data Displayed & Visual Formats
- Health metrics in DM Sans Display 32px.
- Audit Correlation IDs in monospace DM Sans 12px: `corr_8a91c2...`.
- Memory and storage capacities in gigabytes: `14.2 GB / 50.0 GB`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Gate: Verified | `GATE_PASSED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Gate: Pending | `GATE_PENDING` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Service: Active | `SERVICE_ACTIVE` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | None |
| Service: Degraded | `SERVICE_DEGRADED`| Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Operations"
- **Breadcrumbs:** `PlacementOS > System Operations & Health`
- **Context Transition:** Operational alerts link directly to affected drive workspaces or queue recovery handlers.
'''

print("Screens 11 to 14 defined.")
