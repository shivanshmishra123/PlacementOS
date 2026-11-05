"""
Screens 6 to 10 for PlacementOS.
"""

def get_screens_6_to_10():
    return '''## SCREEN 6: Participation Management (`/coordinator/drives/[id]/participation`)

### 1. Screen Identity & Route
- **Screen Name:** Student Participation & Document Readiness Management
- **Route:** `/coordinator/drives/[id]/participation`
- **Primary Audience:** Placement Coordinator, Student Operations Manager

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`participation:view`, `participation:export`, `document:review`, `hold:manage`)
- **Capabilities:** Monitor student registrations, inspect independent document readiness states, configure drive document requirements, place individual registrations on eligibility hold, and export candidate shortlists with formula escaping.

### 3. Core Purpose
Provide unified visibility into student participation by maintaining strict independence between academic eligibility, document validation readiness, and registration status, ensuring no student is improperly blocked or registered without meeting prerequisites.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Bar:** Drive context header with Registration Countdown, Total Registrations Metric, and Candidate Export CTA.
- **Config Section:** Collapsible Document Requirements Strip (Sage Wash `#e4f7ee` card, 16px radius).
- **Filter Ribbon:** Multi-dimensional filter strip (Eligibility × Document Readiness × Registration State).
- **Main Participation Table:** Full-width high-contrast data table (White Product Card `#ffffff`, 16px radius) with slide-over Student Detail Inspector.

### 5. Key UI Sections & Component Breakdown
1. **Header & Participation Metrics:**
   - Drive: "Google India — Software Engineer"
   - Registration Window Status Pill: "REGISTRATION OPEN" (Mint Wash `#d2f2e3`, Leaf Bright `#1dbf73` border) | Closes: `2026-11-15 23:59:00 IST (4 days remaining)`.
   - Metrics Capsule: `210 Registered / 312 Eligible (67.3% Participation Rate)`.
   - Export Action: **Export Candidate List (CSV)** (Ghost Outline Button `#000000`, 40px radius).
2. **Document Requirements Config Ribbon (Sage Wash `#e4f7ee`):**
   - Header: "Drive Document Requirements & Deadlines" (DM Sans 16px weight 600, `#0a3922`).
   - Defined Requirements:
     - *Resume / CV:* PDF format only, max 5MB, Stage: `Required at Registration`.
     - *6th Sem Marksheet:* PDF format, max 10MB, Stage: `Required before Round 1 Scheduling (Deadline: 2026-11-17 18:00 IST)`.
     - *College ID Card:* PDF/JPEG, Stage: `Optional`.
   - Action: **Edit Requirements** (Ghost Outline Button, 32px height).
3. **Multi-Dimensional Filter Bar:**
   - Search: "Search by student name or roll number..."
   - Filter Dimensions (Interactive Pill Tags):
     - *Eligibility:* `All (480)`, `Eligible (312)`, `Ineligible (142)`, `Needs Review (26)`.
     - *Document Readiness:* `All`, `Ready (188)`, `Pending (18)`, `Blocked (4)`.
     - *Registration State:* `All`, `Submitted (210)`, `Draft (14)`, `Withdrawn (6)`, `Eligibility Hold (4)`.
4. **Participation Master Table (White Product Card `#ffffff`):**
   - Columns: Roll Number | Student Name | Branch | Eligibility Pill | Doc Readiness Pill | Registration State Pill | Registered At | Actions.
   - Row Example 1 (Standard Complete):
     - `2023CS104` | Rahul Verma | CSE | `ELIGIBLE` [Green] | `DOCS_READY` [Green] | `REGISTERED` [Green] | `2026-11-11 14:22 IST` | Actions: **Inspect**, **Audit Log**.
   - Row Example 2 (Document Blocked):
     - `2023IT022` | Ananya Rao | IT | `ELIGIBLE` [Green] | `DOC_BLOCKED` [Red] | `REGISTERED` [Green] | `2026-11-11 16:04 IST` | Notice: `Corrupted Marksheet PDF` | Actions: **Request Replacement**.
   - Row Example 3 (Eligibility Hold Active):
     - `2023EC078` | Rohan Patel | ECE | `NEEDS_REVIEW` [Amber] | `DOCS_READY` [Green] | `ELIGIBILITY_HOLD` [Peach] | `2026-11-10 12:00 IST` | Notice: `Criteria revision in review` | Actions: **Release Hold**.
5. **Student Detail Inspector (Slide-over Drawer from Right, 420px width):**
   - Header: Student Name (`Rahul Verma`), Roll (`2023CS104`), Department (`CSE`).
   - Academic Snapshot: CGPA: `8.42`, Active Backlogs: `0`, Verified by Exam Cell.
   - Document Checklist Review:
     - Resume: `Rahul_Verma_Resume.pdf` (1.4MB) — `SCANNED_CLEAN`, Format: PDF v1.6 — Status: `READY`.
     - Marksheet: `Sem6_Marksheet.pdf` (2.1MB) — Status: `READY`.
   - Registration Audit Trail: Submitted `2026-11-11 14:22:18 IST` under Policy v1.0.

### 6. Interface States & Exact Copy
- **Normal State:** Master table displaying 210 registered candidates with clear distinction between eligibility, document readiness, and registration.
- **Eligibility Hold Highlight State:**
  - Rows on eligibility hold feature a Peach Wash `#ffede8` background with an alert icon.
  - Notice text inside row: "Student placed on Eligibility Hold following academic revision. Cannot advance to interview scheduling until re-evaluated."
- **Zero Search Results State:**
  - Table replacement message: "No students match the filter combination: Eligibility [Eligible] × Doc Readiness [Blocked]."
  - Action: **Clear Filter Selection** (Ghost Outline Button `#000000`).
- **Exporting State:**
  - Spinner modal: "Generating cryptographically fingerprinted candidate export... Sanitizing formula characters (=, +, -, @)..."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Export Candidate List (CSV)** (Ghost Outline Button `#000000`, 40px radius, white background).
- **Table Actions:** **Inspect Student** (Ghost Outline Button, 32px height), **Request Document Replacement** (Coral Filled Button `#ff643b`, 32px height).
- **Secondary Action:** **Place Selected on Hold** (Ghost Outline Button with Peach border).

### 8. Data Displayed & Visual Formats
- Timestamps: `YYYY-MM-DD HH:mm:ss IST` (e.g., `2026-11-11 14:22:18 IST`).
- Document statuses: `READY` (Leaf Bright), `PENDING` (Ash), `BLOCKED` (Coral Pulse), `NEEDS_REVIEW` (Cream).
- Registration states: `SUBMITTED`, `DRAFT`, `WITHDRAWN`, `ELIGIBILITY_HOLD`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Registration: Submitted | `REGISTERED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Registration: Draft | `REG_DRAFT` | Cloud Gray (`#f2f2f2`) | Graphite (`#3d3d3d`) | Frost Gray (`#e0e0e0`) |
| Registration: Withdrawn | `WITHDRAWN` | Sand (`#f4ece9`) | Slate (`#7a7a7a`) | None |
| Registration: Hold | `ELIGIBILITY_HOLD` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Doc Readiness: Ready | `DOCS_READY` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Doc Readiness: Blocked | `DOC_BLOCKED` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > Participation & Documents`
- **Next Logical Route:** `/coordinator/drives/[id]/communications` (Draft & Dispatch Targeted Communications).

---

## SCREEN 7: Communications Workspace (`/coordinator/drives/[id]/communications`)

### 1. Screen Identity & Route
- **Screen Name:** Controlled Communications & Broadcast Workspace
- **Route:** `/coordinator/drives/[id]/communications`
- **Primary Audience:** Placement Coordinator, Communications Lead

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`communication:draft`, `communication:freeze`, `communication:propose`)
- **Capabilities:** Draft notification campaigns using controlled templates or AI assistance, select deterministic target audiences, freeze recipient snapshots, preview exact rendered individual messages, and submit immutable communication proposals for approval.

### 3. Core Purpose
Manage high-stakes student recruitment communications with strict approval boundaries: guarantee that message content uses only approved facts, freeze exact recipient lists to prevent stale audience dispatch, and submit proposals for human sign-off (Invariants INV-04, INV-05).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Ribbon:** Drive context header with Communication Intent Selector and Proposal Status Badge.
- **2-Column Split Workspace (50/50 Split):**
  - Left Column (50%): Audience Rule Builder, Template Editor, Merge Variable Palette, and Content Validation Checklist (White Product Card `#ffffff`).
  - Right Column (50%): Frozen Recipient Snapshot Inspector, Live Single-Recipient Rendered Preview, and Approval Submission Box (Lilac Wash `#fdf0ff` card).

### 5. Key UI Sections & Component Breakdown
1. **Header & Intent Selector:**
   - Drive: "Google India — Software Engineer"
   - Intent Dropdown (Mandatory selection):
     - `Drive Announcement` (Eligible students)
     - `Registration Deadline Reminder` (Eligible not yet registered)
     - `Missing Document Remediation Notice` (Registered with blocked/pending docs)
     - `Interview Session Schedule Notice` (Shortlisted candidates)
     - `Official Result Announcement` (Published round outcomes)
     - `Schedule Correction Notice` (Rescheduled participants)
2. **Left Pane: Audience & Template Editor (White Product Card `#ffffff`):**
   - *Target Audience Selector:* Dropdown of deterministic audience rules:
     - "Eligible Students Not Yet Registered (102 Students)"
     - "All Registered Candidates (210 Students)"
     - "Registered Candidates Missing Marksheet (18 Students)"
   - *Channel Selector:* Email (`SMTP Dispatcher / Mailpit Sink`).
   - *Subject Line Input:* `[Action Required] Registration Deadline Approaching: {{company_name}} {{role_title}}`
   - *Message Body Editor:* Markdown / Rich text editor with auto-populated approved drive facts:
     ```markdown
     Dear {{student_name}},

     This is an official reminder that the registration window for **{{company_name}}** (Role: **{{role_title}}**) will close strictly on **{{registration_deadline_at}}**.

     **Key Details:**
     - CTC: {{gross_compensation}}
     - Location: {{work_location}}
     - Required at Registration: {{document_requirements}}

     To participate, complete your submission at: {{registration_portal_link}}
     ```
   - *Merge Tags Palette:* Clickable chips inserting validated placeholders: `{{student_name}}`, `{{roll_number}}`, `{{registration_deadline_at}}`, `{{gross_compensation}}`, `{{company_name}}`, `{{support_contact}}`.
   - *Strict Content Validation Checklist:*
     - [x] Company & Role match approved facts
     - [x] Deadline includes explicit timezone (`IST`)
     - [x] Actionable portal registration link included
     - [x] Zero unresolved / invalid placeholders
3. **Right Pane: Audience Snapshot & Rendered Preview:**
   - *Frozen Audience Snapshot Card (Lilac Wash `#fdf0ff`):*
     - Headline: "Audience Snapshot (Frozen)" (DM Sans 16px weight 600, `#460095`).
     - Total Recipients: `102 Students`.
     - Inclusions: `102 Eligible non-registered students in Batch 2027`.
     - Exclusions: `0 Students (0 opt-outs, 0 bounced)`.
     - Dependency Fingerprint: `sha256:7c9e12...` (Evaluated under Policy v1.0).
   - *Live Single-Recipient Rendered Preview (Paper White Card `#ffffff`, 16px radius):*
     - Header: "Sample Preview: Recipient 1 of 102 (`Rahul Verma - 2023CS104`)"
     - Rendered HTML Email view displaying actual merged values:
       - Recipient: `rahul.verma@apex.edu`
       - Subject: `[Action Required] Registration Deadline Approaching: Google India Software Engineer - Campus Graduate`
       - Rendered Date: `2026-11-15 23:59:00 IST`
       - Rendered CTC: `₹32,00,000`
   - *Approval Submission Console:*
     - Proposal Identifier: `#COMM-PROP-104`
     - Action Buttons:
       - **Freeze & Submit for Approval** (Coral Filled Button `#ff643b`, 40px radius, white text).
       - **Save Draft** (Ghost Outline Button `#000000`, 40px radius).

### 6. Interface States & Exact Copy
- **Normal Drafting State:** Editor active, live preview renders instantaneous merge tag replacement.
- **Validation Failure State:**
  - Red Warning Box inside editor:
    - "Cannot submit proposal: Deadline reference '2026-11-15 23:59' is missing the mandatory institutional timezone."
    - "Primary CTA button **Freeze & Submit for Approval** is disabled until all validation rules pass."
- **Audience Stale State:**
  - Amber Warning Banner across preview pane: Cream `#faf7e8` card with Coral Pulse `#ff643b` border.
  - Headline: "AUDIENCE SNAPSHOT STALE" (DM Sans 16px weight 600, `#ff643b`).
  - Copy: "Underlying student cohort changed (3 students completed academic verification and became eligible). The recipient list must be refreshed before submission."
  - Action: **Refresh Audience Snapshot** (Coral Filled Button `#ff643b`).
- **Proposal Submitted & Frozen State:**
  - Success Banner: Mint Wash `#d2f2e3`, Leaf Bright `#1dbf73` border.
  - Copy: "Communication Proposal #COMM-PROP-104 frozen and submitted. Content and 102 recipients are locked. Awaiting approval by Placement Chair."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Freeze & Submit for Approval** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Save Draft** (Ghost Outline Button `#000000`, 40px radius).
- **Preview Navigation:** **Next Sample Recipient →** (Ghost Outline Button, 32px height).

### 8. Data Displayed & Visual Formats
- Recipient count rendered in DM Sans Display 32px: `102 Recipients`.
- Timezone explicit on all dates: `2026-11-15 23:59:00 IST`.
- Proposal hash displayed in monospace DM Sans 12px: `sha256:7c9e12...`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Intent: Reminder | `DEADLINE_REMINDER` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Audience: Frozen | `AUDIENCE_FROZEN` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |
| Audience: Stale | `AUDIENCE_STALE` | Cream (`#faf7e8`) | Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Proposal: Pending | `AWAITING_APPROVAL`| Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > Communications Workspace`
- **Next Logical Route:** `/coordinator/approvals` (Review & Authorize Consequential Proposal).

---

## SCREEN 8: Workflow Status (`/coordinator/drives/[id]/workflow`)

### 1. Screen Identity & Route
- **Screen Name:** Durable Workflow Orchestration & Checkpoint Inspector
- **Route:** `/coordinator/drives/[id]/workflow`
- **Primary Audience:** Placement Coordinator, System Administrator

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`workflow:view`, `workflow:hold`, `workflow:resume`)
- **Capabilities:** Monitor the durable LangGraph state machine execution, inspect checkpoint transitions, review current workflow wait conditions, place or release operational holds, and safely resume interrupted execution paths.

### 3. Core Purpose
Provide end-to-end transparency and operational control over the background LangGraph workflow engine, ensuring that every drive checkpoint is durable in PostgreSQL and that consequential transitions pause safely for human authorization (Invariant INV-08).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Visual Stepper:** Horizontal full-width Stage Stepper (Paper White `#ffffff` card, 16px radius).
- **Status & Control Banner:** Prominent Operational State Banner (Mint Wash `#d2f2e3` or Peach Wash `#ffede8` card with 24px padding).
- **2-Column Execution Grid (50/50 Split):**
  - Left Column (50%): Checkpoint Metadata, State Schema Version, and Thread Parameters (White Product Card `#ffffff`).
  - Right Column (50%): Checkpoint Transition Log & Audit Timeline (White Product Card `#ffffff`, full height).

### 5. Key UI Sections & Component Breakdown
1. **Drive Context & Workflow Stepper:**
   - Drive: "Google India — Software Engineer"
   - Horizontal Stepper (8 Stages):
     1. `Intake` (Completed ✅)
     2. `Source Review` (Completed ✅)
     3. `Policy Approval` (Completed ✅)
     4. `Eligibility Evaluation` (Completed ✅)
     5. `Drive Publication` (Active 🔵)
     6. `Registration & Docs` (Pending ⏳)
     7. `Rounds & Scheduling` (Pending ⏳)
     8. `Results & Closure` (Pending ⏳)
2. **Current Operational Status Banner:**
   - Headline: `WORKFLOW PAUSED: WAITING FOR ACTION APPROVAL` (DM Sans 24px weight 600, Indigo Bloom `#460095`).
   - Wait Condition Description: "The workflow reached node `PublishDriveNode` and safely paused for human authorization. Proposal `#PUB-042` is pending approval by the Placement Chair."
   - Action Link: **Inspect Pending Publication Proposal →** (DM Sans 16px weight 600, `#460095`).
   - Operational Hold Controls:
     - If Normal: **Place Operational Hold** (Ghost Outline Button `#000000`, 40px radius with mandatory reason prompt).
     - If On Hold: Coral Warning Banner + **Release Operational Hold** (Coral Filled Button `#ff643b`).
3. **Left Column: Checkpoint & State Machine Metadata:**
   - Checkpoint Identifier: `chk_langgraph_pg_98214a_step18`
   - Orchestration Framework: `LangGraph Python Engine (PostgreSQL Checkpointer)`
   - State Schema Version: `v1.4.2`
   - Active Thread ID: `drive_f891a27e`
   - Active Graph Node: `Node: AwaitPublicationApproval`
   - Bound Dependency Revisions:
     - Approved Policy: `Policy v1.0 (Hash: sha256:91bc74...)`
     - Evaluated Cohort: `Run #4 (312 Eligible, Hash: sha256:a14f92...)`
   - Retry / Idempotency Key: `op_resume_pub_8921`
4. **Right Column: Checkpoint Transition Timeline:**
   - Chronological log of durable state transitions:
     - *Step 18 (2026-11-04 15:45:10 IST):* `InterruptNode` triggered by `Node: PreparePublicationProposal`. State persisted to PostgreSQL.
     - *Step 17 (2026-11-04 15:30:12 IST):* `Node: BatchEligibilityEvaluator` completed. 480 students evaluated (312 eligible).
     - *Step 16 (2026-11-04 14:10:22 IST):* `ResumeNode` executed following attributable approval of Policy v1.0 by Dr. K. Sharma.
     - *Step 15 (2026-11-04 13:40:00 IST):* `InterruptNode` paused for human policy approval.

### 6. Interface States & Exact Copy
- **State: Running (`running`):**
  - Banner: Sky Wash `#ccf0f8`, Blue pulse dot.
  - Copy: "Workflow executing node `EvaluateEligibilityCohort`. Running non-blocking background workers..."
- **State: Waiting for Rule Approval (`waiting_for_rule_approval`):**
  - Banner: Lilac Wash `#fdf0ff`, Indigo Bloom `#460095` text.
  - Copy: "Workflow safely paused at policy compilation checkpoint. Awaiting coordinator review and policy approval."
- **State: Waiting for Clarification (`waiting_for_clarification`):**
  - Banner: Cream `#faf7e8`, Charcoal `#333333` text.
  - Copy: "Workflow blocked: 1 unresolved ambiguity in job description requires coordinator clarification."
- **State: Operational Hold Active (`operational_hold`):**
  - Banner: Peach Wash `#ffede8`, 1px solid Coral Pulse `#ff643b` border.
  - Copy: "OPERATIONAL HOLD ACTIVE: Drive paused by Dr. K. Sharma on 2026-11-04 16:00 IST. Reason: Recruiter requested criteria revision. Consequential actions and dispatches suspended."
  - Action: **Release Operational Hold** (Coral Filled Button `#ff643b`).
- **State: Failed Retryable (`failed_retryable`):**
  - Red Warning Banner: "Checkpoint execution error: Database transaction timeout during evaluation batch. State safely rolled back."
  - Action: **Retry Workflow from Last Checkpoint** (Coral Filled Button `#ff643b`).

### 7. Primary & Secondary Actions
- **Primary CTA (When On Hold):** **Release Operational Hold** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary Action:** **Place Operational Hold** (Ghost Outline Button `#000000`, 40px radius).
- **Resume Action:** **Resume from Checkpoint** (Coral Filled Button `#ff643b`).

### 8. Data Displayed & Visual Formats
- Graph nodes and checkpoint IDs in monospace DM Sans 12px.
- Timestamps with second precision and timezone: `2026-11-04 15:45:10 IST`.
- Stepper stages: Completed (Leaf Bright `#1dbf73`), Active (Sky Signal `#00b4dc`), Pending (Ash `#a6a6a6`).

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| State: Running | `WORKFLOW_RUNNING` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| State: Waiting Approval | `WAITING_APPROVAL` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |
| State: On Hold | `OPERATIONAL_HOLD` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| State: Completed | `WORKFLOW_COMPLETED`| Mint Wash (`#d2f2e3`)| Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| State: Failed | `CHECKPOINT_FAILED` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > Workflow Engine`
- **Context Transition:** Clicking wait conditions links directly to `/coordinator/approvals` or `/coordinator/drives/[id]/review`.

---

## SCREEN 9: Lifecycle (Scheduling, Results, Closure) (`/coordinator/drives/[id]/lifecycle`)

### 1. Screen Identity & Route
- **Screen Name:** Drive Lifecycle: Rounds, Scheduling, Attendance, Results & Closure
- **Route:** `/coordinator/drives/[id]/lifecycle`
- **Primary Audience:** Placement Coordinator, Interview Operations Lead

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`schedule:manage`, `results:manage`, `drive:close`)
- **Capabilities:** Configure ordered recruitment rounds and sessions, detect scheduling conflicts with half-open intervals, record student attendance, record employer outcomes, verify pre-closure audit checklists, and execute drive closure.

### 3. Core Purpose
Orchestrate post-registration interview operations through strict deterministic execution: schedule sessions without conflicts, record attendance independently from outcomes, manage internal vs published results, and close the drive only when all prerequisites are verified.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Bar:** Drive context header with Stage Stepper and 4 Master Operational Tabs:
  - `[Tab 1: Rounds & Sessions]`, `[Tab 2: Attendance]`, `[Tab 3: Employer Results]`, `[Tab 4: Pre-Closure & Report]`.
- **Content Area:** Dynamic full-width panels based on selected tab (White Product Cards `#ffffff` and Pastel Feature Cards).

### 5. Key UI Sections & Component Breakdown
1. **Tab 1: Rounds & Sessions Configuration:**
   - *Ordered Rounds Header:* Round 1: Online Coding Test → Round 2: Technical Interview 1 → Round 3: Technical Interview 2 → Round 4: HR Interview.
   - *Add Session CTA:* **Add Interview Session** (Coral Filled Button `#ff643b`, 40px radius).
   - *Active Sessions Grid (Pastel Feature Cards cycling Sky and Lilac):*
     - *Session Card Anatomy:*
       - Header: "Round 2 — Technical Panel A (Systems)"
       - Timing: `2026-11-18 09:00:00 IST – 13:00:00 IST` (Explicit `[start, end)` half-open interval).
       - Venue / Link: "Computer Lab 4, Desks 1–12" or "Google Meet (Link generated)".
       - Capacity: `12 / 12 Candidates Assigned` (Full).
       - Conflict Engine Check: `NO CONFLICTS DETECTED` (Leaf Bright `#1dbf73` tag).
       - Actions: **Manage Participants**, **Publish Schedule** (Ghost Outline Button).
   - *Candidate Assignment & Conflict Checker (Drawer / Modal):*
     - Eligible and registered candidates listed with real-time interval conflict detector.
     - Half-open interval rule: A student assigned to a session ending at 11:00:00 IST can be assigned to a session starting at 11:00:00 IST without conflict.
     - Conflict Warning (if overlapping): Coral text: "Conflict: Student Rahul Verma is already scheduled in Panel B from 10:00 to 11:30 IST."
2. **Tab 2: Attendance Recording:**
   - Session Selector Dropdown: "Round 2 — Technical Panel A (2026-11-18 09:00 IST)".
   - Attendance Roster Table (White Product Card `#ffffff`):
     - Columns: Roll Number | Student Name | Branch | Scheduled Slot | Attendance Radio Group | Notes | Action.
     - Radio Options per student: `(•) Present  ( ) Absent  ( ) Excused  ( ) Not Recorded`.
     - Action: **Save Attendance Snapshot** (Coral Filled Button `#ff643b`).
3. **Tab 3: Employer Outcomes & Results:**
   - Round Selector: "Round 2 — Technical Interview 1".
   - Draft vs Published Toggle: "Status: Internal Draft (Invisible to students)".
   - Results Table (White Product Card `#ffffff`):
     - Columns: Roll Number | Student Name | Attendance | Employer Outcome Selector | Offered CTC (Final round only) | Coordinator Notes.
     - Outcome Dropdown: `Advanced to Round 3`, `Rejected`, `Waitlisted`, `Pending Decision`.
     - Selection is independent of attendance (Attendance does not infer outcome).
   - Action: **Submit Results for Publication Approval** (Coral Filled Button `#ff643b`).
4. **Tab 4: Pre-Closure Audit Checklist & Final Report:**
   - Pre-Closure Audit Checklist Card (Sage Wash `#e4f7ee`, 24px padding):
     - [x] All 4 recruitment rounds concluded (100% complete)
     - [x] All candidate outcomes recorded and published (210/210 verified)
     - [x] Zero pending consequential approval proposals (0 open)
     - [x] Zero unresolved dispatch outbox messages (0 unknown/stalled)
     - [x] All operational exceptions acknowledged or resolved (0 blocking)
   - Funnel Performance Snapshot:
     - Evaluated: `480` → Eligible: `312` → Registered: `210` → Shortlisted R1: `84` → Shortlisted R2: `32` → Offers Extended: `14`.
   - Closure Execution Controls:
     - **Freeze Report & Close Drive** (Coral Filled Button `#ff643b`, 40px radius, white text).
     - **Cancel Recruitment Drive** (Ghost Outline Button with Coral border and confirmation prompt).

### 6. Interface States & Exact Copy
- **Conflict Detected State (Tab 1):**
  - High-Contrast Alert inside session card: Peach Wash `#ffede8`, 1px solid Coral Pulse `#ff643b` border.
  - Copy: "SCHEDULING CONFLICT: Student `2023CS104` assigned to overlapping session `Panel B` (10:00–11:00 IST). Resolve conflict before publishing."
- **Draft Session Label:**
  - Status Tag on Session: `DRAFT (INTERNAL ONLY)` in Ash `#a6a6a6` background with Charcoal text.
  - Notice: "Draft sessions and student assignments remain completely invisible in the Student Portal until approved and published."
- **Pre-Closure Blocked State (Tab 4):**
  - Closure Button is disabled (Ash `#a6a6a6` background).
  - Amber Warning Banner: "Drive Closure Blocked: 2 outbox dispatch messages remain in 'UNKNOWN' status. Reconcile provider delivery confirmation before closing drive."

### 7. Primary & Secondary Actions
- **Primary CTA (Tab 1):** **Publish Session Schedule** (Coral Filled Button `#ff643b`, 40px radius).
- **Primary CTA (Tab 3):** **Submit Results for Publication Approval** (Coral Filled Button `#ff643b`).
- **Primary CTA (Tab 4):** **Freeze Report & Close Drive** (Coral Filled Button `#ff643b`).
- **Secondary Action:** **Add Session** (Ghost Outline Button `#000000`, 40px radius).

### 8. Data Displayed & Visual Formats
- Schedule intervals: `[2026-11-18 09:00:00, 2026-11-18 13:00:00) IST`.
- Final offer CTC displayed in Indian numbering: `₹32,00,000`.
- Funnel metrics formatted in DM Sans Display 32px.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Session: Draft | `SESSION_DRAFT` | Cloud Gray (`#f2f2f2`) | Slate (`#7a7a7a`) | Frost Gray (`#e0e0e0`) |
| Session: Published | `SESSION_PUBLISHED`| Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Attendance: Present | `ATTENDANCE_PRESENT`| Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | None |
| Outcome: Advanced | `OUTCOME_ADVANCED` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Outcome: Selected | `OFFER_EXTENDED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Drive: Closed | `DRIVE_CLOSED` | Paper White (`#ffffff`)| Canopy Green (`#0a3922`) | Canopy Green (`#0a3922`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > Lifecycle Operations`
- **Context Transition:** Concluding drive routes to final institutional summary at `/coordinator/drives`.

---

## SCREEN 10: Approval Center (`/coordinator/approvals`)

### 1. Screen Identity & Route
- **Screen Name:** Central Consequential Approval Center
- **Route:** `/coordinator/approvals`
- **Primary Audience:** Placement Chair, Authorized Approving Coordinator

### 2. User Role & Capabilities
- **Role:** Placement Approver (`proposal:view`, `proposal:approve`, `proposal:reject`, `proposal:request_revision`)
- **Capabilities:** Triage and inspect all pending consequential proposals across all drives (policies, publications, communications, schedules, results, recovery plans), inspect cryptographic fingerprints and dependency staleness, and record attributable decisions with mandatory rationale.

### 3. Core Purpose
Serve as the single institutional checkpoint for all actions carrying consequential external side effects, ensuring no communication, drive publication, schedule release, or policy rule can execute without explicit, attributable human authorization (Invariants INV-04, INV-05).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Filter Ribbon:** Multi-category proposal type filters and status facets.
- **Master-Detail 2-Pane Split (40/60 Split):**
  - Left Pane (40% Width): Scrollable Proposals Master List (White Product Cards `#ffffff`).
  - Right Pane (60% Width): Comprehensive Proposal Inspector, Content Diff Viewer, Dependency Fingerprint Monitor, and Attributable Decision Console (Lilac Wash `#fdf0ff` card).

### 5. Key UI Sections & Component Breakdown
1. **Master Filter & Facets Ribbon:**
   - Filter Tabs: `Pending Review (5)`, `Approved (28)`, `Rejected (3)`, `Stale / Invalidated (2)`, `All (38)`.
   - Category Dropdown: `All Types`, `Eligibility Policy`, `Communication Broadcast`, `Drive Publication`, `Interview Schedule`, `Employer Results`, `Exception Recovery Plan`.
2. **Proposals List (Left Pane):**
   - List of proposals sorted by submission timestamp:
     - *Item 1:* `#PROP-COMM-104` | Pill: `COMMUNICATION` (Sky Wash `#ccf0f8`) | Drive: `Google - SWE` | Target: `102 Students (Deadline Reminder)` | Submitter: `Prof. Sharma` | Submitted: `12m ago` | Status: `PENDING`.
     - *Item 2:* `#PROP-POL-082` | Pill: `POLICY` (Lilac Wash `#fdf0ff`) | Drive: `Microsoft - SDE` | Target: `Policy v1.0 Compilation` | Submitter: `Dr. Verma` | Submitted: `1h ago` | Status: `PENDING`.
     - *Item 3:* `#PROP-PUB-042` | Pill: `PUBLICATION` (Mint Wash `#d2f2e3`) | Drive: `Google - SWE` | Target: `Drive Publication (Student Portal)` | Submitter: `Prof. Sharma` | Submitted: `2h ago` | Status: `PENDING`.
3. **Proposal Inspector & Content Diff (Right Pane):**
   - *Header Box:*
     - Proposal Title: `Approval Request: Communication Broadcast #PROP-COMM-104`
     - Proposal ID: `#PROP-COMM-104` | Version: `Rev 1`
     - Submitter: `Dr. K. Sharma (2026-11-04 15:45:10 IST)`
     - Dependency Fingerprint: `sha256:7c9e12...` (Verified current & active ✅).
   - *Exact Proposed Payload Viewer (White Product Card `#ffffff`):*
     - For Communications: Shows exact sender (`placements@apex.edu`), channel (`SMTP`), subject line, full message body, and frozen recipient count (`102 recipients`).
     - For Policies: Shows human-readable rule expression, branch whitelist, CGPA cutoff (`7.50`), backlog limit (`0`), and evaluated cohort size (`480 students`).
     - For Schedules: Shows session start/end, timezone, venue, capacity, and candidate roster.
   - *Dependency Freshness Monitor:*
     - Status: `DEPENDENCIES CURRENT: No underlying source, policy, or student evidence changes detected.`
4. **Attributable Decision Console (Lilac Wash `#fdf0ff` card, 24px padding):**
   - Reviewer Rationale Box:
     - Label: "Decision Rationale (Mandatory for institutional audit compliance)" (DM Sans 14px weight 600, `#0a3922`).
     - Textarea: "Enter detailed review notes and justification..." (Required before buttons become active).
   - Attributable Decision Actions:
     - **Approve Proposal** (Coral Filled Button `#ff643b`, 40px radius, white text).
     - **Reject Proposal** (Ghost Outline Button with Coral Pulse `#ff643b` border).
     - **Request Revision** (Ghost Outline Button `#000000`, 40px radius).

### 6. Interface States & Exact Copy
- **Normal Review State:** Proposal selected; dependencies verified; rationale input enabled.
- **Stale Proposal State (Dependencies Modified):**
  - High-Severity Warning Banner across Right Pane: Cream `#faf7e8` card with 1px solid Coral Pulse `#ff643b` border.
  - Headline: "PROPOSAL STALE: DECISION DISABLED" (DM Sans 18px weight 600, `#ff643b`).
  - Copy: "Underlying dependencies changed since this proposal was submitted (3 student records updated). The proposal fingerprint `sha256:7c9e...` is invalid. In accordance with Invariant INV-05, stale approvals are prohibited. The coordinator must re-freeze and submit a new revision."
  - Action buttons **Approve** and **Reject** are permanently disabled.
- **Decision Successfully Recorded State:**
  - Green Success Banner: Mint Wash `#d2f2e3`, Leaf Bright `#1dbf73` border.
  - Copy: "Proposal #PROP-COMM-104 Approved by Dr. K. Sharma on 2026-11-04 16:15:20 IST. Cryptographic execution token issued. Workflow node resumed."
- **Empty State (Zero Pending Approvals):**
  - Left Pane Replacement: White Product Card `#ffffff`, 48px padding, centered.
  - Headline: "Inbox Zero: All Proposals Decided" (DM Sans 20px weight 600, Canopy Green `#0a3922`).
  - Body Copy: "No consequential proposals currently awaiting review. New proposals from policy drafts, communications, and publications will appear here."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Approve Proposal** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Request Revision** (Ghost Outline Button `#000000`, 40px radius).
- **Destructive Action:** **Reject Proposal** (Ghost Outline Button with Coral border and required reason).

### 8. Data Displayed & Visual Formats
- Cryptographic proposal hash and dependency fingerprint in monospace DM Sans 12px.
- Timestamps with second precision: `2026-11-04 16:15:20 IST`.
- Reviewer attribution: `Name, Institutional ID, Role, Timestamp`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Proposal: Pending | `PENDING_REVIEW` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Proposal: Approved | `APPROVED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Proposal: Rejected | `REJECTED` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Proposal: Revision | `REVISION_REQUESTED`| Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Proposal: Stale | `PROPOSAL_STALE` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Approvals"
- **Breadcrumbs:** `PlacementOS > Approval Center`
- **Context Transition:** Deciding a proposal returns the reviewer to the list and updates downstream drive workflow status.
'''

print("Screens 6 to 10 defined.")
