"""
Screens 1 to 5 for PlacementOS.
"""

def get_screens_1_to_5():
    return '''## 4. Screen-by-Screen Specifications

---

## SCREEN 1: Coordinator Dashboard (`/coordinator`)

### 1. Screen Identity & Route
- **Screen Name:** Coordinator Operations Dashboard
- **Route:** `/coordinator`
- **Primary Audience:** Campus Placement Coordinator, Head of Placements, Records Reviewer

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`ops:view`, `drive:view`, `proposal:view`, `exception:view`)
- **Capabilities:** Inspect current institutional placement metrics, triage pending approvals across all active drives, review approaching deadlines, monitor asynchronous background service health, and launch new drive workspaces.

### 3. Core Purpose
Provide placement coordinators with an immediate, high-contrast operational snapshot of all active recruitment drives, pending consequential approvals, open operational exceptions, and time-critical student participation deadlines.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Section:** Full-bleed institution header strip with active placement cycle selector and environment readiness pill.
- **Metrics Section:** 4-column Pastel Feature Card grid (24px gap, 24px padding, 24px border-radius, no shadow).
- **Core Operations Area:** 60/40 two-column split:
  - Left Column (60%): Live Recruitment Drives Pipeline Table (White Product Card `#ffffff`, 16px radius).
  - Right Column (40%): Stacked operational widgets: Pending Consequential Approvals Panel (White Product Card) and Approaching Operational Deadlines Strip (Sage Wash `#e4f7ee` card).
- **Footer Section:** System Health & Infrastructure Dock (Cloud Gray `#f2f2f2` card with Leaf Bright `#1dbf73` status indicators).

### 5. Key UI Sections & Component Breakdown
1. **Header Ribbon:**
   - University Monogram & Name: "Apex Institute of Technology — Training & Placement Cell" (DM Sans 20px weight 600, `#0a3922`).
   - Cycle Pill Tag: "Academic Cycle 2026–27" (`#ccf0f8` Sky Wash, 9999px radius, DM Sans 12px weight 600).
   - Environment Badge: "SYNTHETIC DEMO" (Mint Wash `#d2f2e3` background, `#0a3922` text, 9999px radius).
   - Quick Action: **Create New Drive** (Coral Filled Button, `#ff643b`, 40px radius, white text).
2. **Top Metric Strip (4 Pastel Feature Cards):**
   - *Card 1 (Mint Wash `#d2f2e3`):* Active Drives metric. Value: "8 Active" (Display 48px `#0a3922`), Subtext: "2 on Operational Hold", Icon: Briefcase.
   - *Card 2 (Sky Wash `#ccf0f8`):* Pending Approvals. Value: "5 Pending" (Display 48px `#003642`), Subtext: "3 Policy, 2 Communications", Icon: Shield-Check.
   - *Card 3 (Peach Wash `#ffede8`):* Open Exceptions. Value: "3 Open" (Display 48px `#ff643b`), Subtext: "1 High Severity (Criteria change)", Icon: Alert-Triangle.
   - *Card 4 (Lilac Wash `#fdf0ff`):* Upcoming Deadlines. Value: "4 Today" (Display 48px `#460095`), Subtext: "Next: Google Reg closes 23:59 IST", Icon: Clock.
3. **Live Drive Pipeline Table (White Product Card `#ffffff`):**
   - Header: "Active Recruitment Drives" + "View All Drives (14) →" link.
   - Table columns: Company & Role | Stage Pill | Eligibility Funnel (Eligible / Ineligible / Review) | Registrations | Operational Status | Workspace Action.
   - Row items with company avatars (Google, Microsoft, Texas Instruments, Deloitte).
4. **Pending Approvals Quick Panel (White Product Card `#ffffff`):**
   - Header: "Awaiting Coordinator Decision (5)" (DM Sans 18px weight 600, `#0a3922`).
   - List of proposals: Type badge (`POLICY`, `COMMUNICATION`, `PUBLICATION`), Drive Name, Target Hash, Submitted by, Age.
   - Direct action per item: **Review & Decide** (Ghost Outline Button, 32px height, 14px DM Sans).
5. **Approaching Deadlines Strip (Sage Wash `#e4f7ee` Card):**
   - Chronological list of deadlines with explicit timezones:
     - "Google SWE: Student Registration Closes today at 23:59:00 IST (Countdown: 06h 42m)"
     - "Microsoft SDE: Marksheet Submission Cutoff tomorrow at 18:00:00 IST"
     - "Deloitte Analyst: Round 1 Online Aptitude starts 2026-11-06 10:00:00 IST"
6. **System Health & Worker Dock (Cloud Gray `#f2f2f2`):**
   - Real-time service pulses: Celery Worker: `ACTIVE (4 workers)`, Redis Broker: `CONNECTED`, Mail Sink: `MAILPIT CONNECTED`, Malware Scanner: `CLAMAV HEALTHY`, AI Model: `GEMINI 1.5 PRO READY`.

### 6. Interface States & Exact Copy
- **Normal State:** Pipeline table populated with 4 active drives; approvals panel shows 5 pending items; health dock indicates all green.
- **Empty State (Initial Setup):**
  - Table Replacement Container: White Product Card `#ffffff`, 48px vertical padding, centered layout.
  - Headline: "No recruitment drives currently active" (DM Sans 24px weight 600, `#0a3922`).
  - Body Copy: "Get started for the 2026–27 placement season by uploading a company Job Description or importing the verified student roster."
  - Primary Action: **Create New Drive** (Coral Filled Button `#ff643b`).
  - Secondary Action: **Import Student Roster (CSV)** (Ghost Outline Button `#000000`).
- **Operational Hold Alert State:**
  - Banner displayed at top of pipeline table on Cream `#faf7e8` surface with `#000000` 1px border.
  - Copy: "Operational Hold Active on 2 Drives (Google SWE, Texas Instruments). Automated communications and round scheduling are suspended pending coordinator review."
- **Model Offline / Fallback State:**
  - System Dock Warning Pill: `MODEL PROVIDER OFFLINE (FALLBACK MANUAL)` in Peach Wash `#ffede8` with `#ff643b` text.
  - Toast alert: "Model extraction provider unreachable. Manual JD review workflows remain fully functional."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Create New Drive** (Coral Filled Button `#ff643b`, 40px radius, DM Sans 16px weight 600, white text).
- **Secondary CTA:** **Review Pending Approvals** (Ghost Outline Button, 1px solid `#000000`, 40px radius, 14px weight 500).
- **Inline Row Actions:** **Open Workspace** (Ghost Outline Button), **Inspect Exceptions** (Ghost Outline Button).

### 8. Data Displayed & Visual Formats
- Metric numbers rendered in DM Sans Display (48px) with tight tracking `-0.019em`.
- Dates and deadlines strictly formatted with 24-hour time and explicit timezone: `YYYY-MM-DD HH:mm:ss [TIMEZONE]` (e.g., `2026-11-04 23:59:00 IST`).
- Hash indicators: SHA-256 strings truncated with copy-to-clipboard: `sha256:d4f18a...e91b` in Slate `#7a7a7a` DM Sans 12px monospace.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Lifecycle: Intake | `INTAKE` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Lifecycle: Review | `IN_REVIEW` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |
| Lifecycle: Published | `PUBLISHED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Operational Hold | `ON_HOLD` | Peach Wash (`#ffede8`) | Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| System Health | `HEALTHY` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Dashboard" highlighted with Canopy Green `#0a3922` fill and Leaf Bright `#1dbf73` left accent bar.
- **Breadcrumbs:** `PlacementOS > Dashboard` (DM Sans 14px, Slate `#7a7a7a`).
- **Context Transition:** Clicking any drive row transitions directly to `/coordinator/drives/[id]/workflow`.

---

## SCREEN 2: Drive Roster (`/coordinator/drives`)

### 1. Screen Identity & Route
- **Screen Name:** Recruitment Drives Roster & Management
- **Route:** `/coordinator/drives`
- **Primary Audience:** Placement Coordinator, Placement Chair

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`drive:create`, `drive:view`, `drive:archive`)
- **Capabilities:** Browse, search, and filter all campus recruitment drives across lifecycle stages, inspect operational hold statuses, view real-time participation metrics, and instantiate new recruitment drives.

### 3. Core Purpose
Serve as the central directory for all company recruitment drives within the institution, enabling coordinators to track progress from draft intake through drive closure.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Ribbon:** Page title, search bar, active filter pills, and primary **Create Drive** CTA.
- **Main Canvas:** 2-column responsive grid of Drive Cards (Pastel Feature Cards cycling through Mint, Sky, Sage, Lilac, Peach, Cream).
- **Modal Layer:** Create Drive Slide-over / Modal (White Product Card `#ffffff` with 24px padding and 1px Frost Gray `#e0e0e0` border).

### 5. Key UI Sections & Component Breakdown
1. **Header & Search Strip:**
   - Title: "Campus Recruitment Drives" (DM Sans 32px weight 600, `#0a3922`).
   - Search Input: Full-width search bar with magnifying glass icon: "Search by company name, role title, batch, or coordinator..."
   - Create Drive Button: **Create Drive** (Coral Filled Button `#ff643b`, 40px radius).
2. **Lifecycle Filter Pills Bar:**
   - Interactive pill filters: `All (14)`, `Draft / Intake (2)`, `Policy Review (3)`, `Published / Active (5)`, `In Progress (2)`, `Completed (1)`, `Cancelled (1)`.
   - Toggle switch: "Show On-Hold Drives Only (2)".
3. **Drive Cards Grid (Pastel Feature Cards cycling every 6 cards):**
   - *Card Anatomy:*
     - Header Row: Company Monogram/Logo (48px square, Paper White `#ffffff` background, 8px radius) | Company Name & Role Title | Lifecycle Stage Pill Tag.
     - Drive Cycle Pill: "Batch of 2027 · B.Tech" (Tag Chip `#ffffff`).
     - Key Dates Block: Registration Deadline: `2026-11-15 23:59:00 IST` | Drive Date: `2026-11-20`.
     - Mini Funnel Metrics (3-segment strip):
       - Eligible: `312` | Registered: `210` | Offers: `14`
     - Operational Hold Indicator (if active): Coral border with warning banner: "Hold: Recruiter criteria revision requested".
     - Action Footer: **Open Drive Workspace** (Coral Filled Button or Ghost Outline Button), **Quick Review** link.
4. **Create Drive Modal (Overlaid White Product Card `#ffffff`):**
   - Modal Header: "Create New Recruitment Drive" (DM Sans 24px weight 600, `#0a3922`).
   - Quota Notice: "Institution Quota: 8 of 25 open drives active" (DM Sans 14px, Slate `#7a7a7a`).
   - Input Fields:
     - Company Name (Typeahead dropdown with "+ Add New Institutional Company").
     - Role / Job Title (e.g., "Software Engineer - Systems").
     - Employment Type Dropdown: Full-Time Employment (FTE), 6-Month Internship, 2-Month Summer Internship, FTE + Internship.
     - Placement Cycle / Batch: "Batch 2027 (2026–27 Season)".
     - Lead Coordinator Assignment: Dropdown of certified coordinators.
     - Internal Notes (Optional textarea).
   - Actions: **Create Draft Drive** (Coral Filled Button `#ff643b`), **Cancel** (Ghost Outline Button `#000000`).

### 6. Interface States & Exact Copy
- **Normal State:** Grid displays 8 active drive cards with dynamic pastel backgrounds.
- **Empty Filter State (Zero Results):**
  - Container: White Product Card `#ffffff`, 40px padding.
  - Headline: "No recruitment drives match your filter criteria" (DM Sans 20px weight 600, `#0a3922`).
  - Body Copy: "No drives found matching the selected stage and search query. Try clearing filters or checking spelling."
  - Action: **Reset All Filters** (Ghost Outline Button `#000000`).
- **Quota Exceeded State (Modal):**
  - Warning Alert inside modal: "Institution open-drive quota reached (25/25). To launch a new drive, complete or archive inactive recruitment drives in accordance with institutional policy."
  - Primary button **Create Draft Drive** is disabled (Ash `#a6a6a6` background).

### 7. Primary & Secondary Actions
- **Primary CTA:** **Create Drive** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Card CTA:** **Open Workspace** (Ghost Outline Button `#000000`, 40px radius, 14px DM Sans weight 600).
- **Secondary Action:** **Reset Filters** (Ghost Outline Button).

### 8. Data Displayed & Visual Formats
- Card backgrounds cycle deterministically: Mint Wash `#d2f2e3` → Sky Wash `#ccf0f8` → Sage Wash `#e4f7ee` → Lilac Wash `#fdf0ff` → Peach Wash `#ffede8` → Cream `#faf7e8`.
- Metric numbers displayed in DM Sans 20px weight 600 in Charcoal `#333333`.
- Timestamps formatted with explicit timezone: `2026-11-15 23:59:00 IST`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Stage: Draft | `DRAFT` | Cloud Gray (`#f2f2f2`) | Graphite (`#3d3d3d`) | Frost Gray (`#e0e0e0`) |
| Stage: Policy Approval | `POLICY_PENDING` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |
| Stage: Published | `REGISTRATION_OPEN`| Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Stage: Closed | `REGISTRATION_CLOSED`| Cream (`#faf7e8`) | Graphite (`#3d3d3d`) | None |
| Operational Hold | `HOLD_ACTIVE` | Peach Wash (`#ffede8`) | Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `PlacementOS > Drives`
- **Context Transition:** Clicking any card routes to `/coordinator/drives/[id]/intake` (if draft) or `/coordinator/drives/[id]/review` or `/coordinator/drives/[id]/workflow`.

---

## SCREEN 3: Drive Intake Workspace (`/coordinator/drives/[id]/intake`)

### 1. Screen Identity & Route
- **Screen Name:** Drive Source Intake & Parsing Workspace
- **Route:** `/coordinator/drives/[id]/intake`
- **Primary Audience:** Placement Coordinator, Intake Specialist

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`drive:intake`, `source:upload`, `source:extract`)
- **Capabilities:** Ingest raw JD documents (PDF/DOCX), paste circular text, connect authorized Gmail sources, monitor quarantine and malware scanning, and review parsed text with page/paragraph source locators.

### 3. Core Purpose
Ingest raw recruiter job descriptions through safe, quarantined multi-channel ingestion, ensuring that original files are cryptographically fingerprinted, scanned for malware, and parsed into structured text with source locators before policy extraction.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Banner:** Drive Breadcrumb, Company Context, and Intake Stage Progress Stepper.
- **Main Workspace Split (50/50 Split Pane):**
  - Left Pane (50%): Source Ingestion Dropzone, Pasted Text Tab, Integration-Gated Gmail Capture, and Uploaded Sources Table (White Product Card `#ffffff`).
  - Right Pane (50%): Interactive Source Viewer & Paragraph Locator Inspector (White Product Card `#ffffff`, 16px radius, full height scrollable).

### 5. Key UI Sections & Component Breakdown
1. **Drive Context Header:**
   - Company Monogram & Drive Title: "Google India — Software Engineer (Campus 2026–27)" (DM Sans 24px weight 600, `#0a3922`).
   - Breadcrumb: `Drives > Google - SWE > Intake Workspace`.
   - Drive ID Pill: `DRV-8912` | SHA-256 Hash: `sha256:4a9f...`
2. **Source Ingestion Controls (Left Pane):**
   - *Tab Bar:* `[Upload File (PDF/DOCX)]`, `[Paste Text / Email Body]`, `[Gmail Ingestion (Gated)]`.
   - *File Dropzone:*
     - Drag-and-drop container: 2px dashed Ink Black `#000000` border on Sky Wash `#ccf0f8` surface, 32px padding, 16px radius.
     - Icon: Document upload icon (Leaf Bright `#1dbf73`).
     - Text: "Drag and drop Job Description PDF or DOCX here, or **Browse Files**"
     - Subtext: "Maximum file size: 10MB. Executable binaries and password-protected files are strictly rejected."
   - *Gmail Integration Ribbon (Integration-Gated):*
     - Pill: "GMAIL INTEGRATION GATED" (`#faf7e8` Cream with `#000000` text).
     - Notice: "Requires isolated live acceptance in Integrations Hub before reading production inbox."
     - Action: **Capture from Selected Gmail Thread** (Ghost Outline Button, disabled in local demo mode).
3. **Uploaded Sources Table (Left Pane Bottom):**
   - Table columns: Source File | Format & Size | Cryptographic Hash | Malware Scan | Parser Status | Actions.
   - Row Example:
     - File: `Google_Campus_JD_2026.pdf` (1.8 MB, PDF v1.6)
     - Hash: `sha256:e3b0c44...` (Truncated, copyable)
     - Scan Status: `SCANNED_CLEAN` (Mint Wash `#d2f2e3` tag)
     - Extraction Status: `PARSED_SUCCESS` (Leaf Bright `#1dbf73` tag)
     - Actions: **View Extracted Text** (Ghost Outline), **Re-Extract**, **Download Quarantined Source** (Audited).
4. **Source Locator & Extracted Text Viewer (Right Pane):**
   - Viewer Toolbar: Source Selector Dropdown, Extractor Version Tag: `Textract/PyMuPDF Engine v2.4`, Search in Document box.
   - Scrollable Extracted Text Area:
     - Document paragraphs rendered in high-contrast DM Sans 14px weight 400 on Paper White `#ffffff`.
     - Paragraph Locator Anchor Chips: Each paragraph carries an interactive badge: `[Page 1, Para 2]`, `[Page 2, Para 5: Eligibility Criteria]`.
     - Clicking an anchor highlights the text in Cream `#faf7e8` and displays the exact locator string for downstream attribution (Invariant INV-03).

### 6. Interface States & Exact Copy
- **Uploading / Scanning State:**
  - Progress Card inside dropzone: Sky Wash `#ccf0f8`, animated pulse.
  - Text: "Uploading `Google_JD_2026.pdf` (1.8 MB)... Performing ClamAV antivirus quarantine scan..."
- **Malware Quarantined Failure State:**
  - High-Severity Red Warning Container inside dropzone: Peach Wash `#ffede8`, 1px solid Coral Pulse `#ff643b` border.
  - Headline: "SECURITY ALERT: Upload Quarantined" (DM Sans 16px weight 600, `#ff643b`).
  - Copy: "File `JD_Malicious.pdf` failed security verification: Trojan signature detected by ClamAV scanner. The file has been quarantined and isolated. Document access and parsing are disabled."
- **Extraction Failed / OCR Required State:**
  - Amber Warning Box: Cream `#faf7e8` surface.
  - Headline: "Text Extraction Incomplete: Scanned Image PDF Detected"
  - Copy: "No selectable text found in `Scan_JD.pdf`. File appears to be a flat raster scan. Trigger OCR extraction or manually transcribe the job description facts."
  - Action CTAs: **Trigger OCR Extraction** (Coral Filled Button `#ff643b`), **Manual Structured Entry** (Ghost Outline Button `#000000`).
- **Empty State:**
  - Dropzone idle: "No source documents ingested for this drive yet. Upload the company JD PDF or paste email text to begin."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Proceed to JD Fact Review** (Coral Filled Button `#ff643b`, 40px radius, white text — enabled once at least 1 source is clean & parsed).
- **Secondary CTA:** **Upload Additional Attachment** (Ghost Outline Button `#000000`, 40px radius).
- **Tertiary Action:** **Manual Entry Fallback** (Ghost Outline Button `#000000`).

### 8. Data Displayed & Visual Formats
- SHA-256 hash displayed in 12px monospace DM Sans.
- Page and paragraph locators formatted as `[p.{page_num}:para.{para_num}]`.
- Document sizes displayed in normalized megabytes: `1.8 MB`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Scan: Clean | `SCANNED_CLEAN` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Scan: Scanning | `SCANNING_QUARANTINE`| Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Scan: Quarantined | `QUARANTINED_INFECTED`| Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Parser: Success | `PARSED_OK` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | None |
| Parser: Needs OCR | `NEEDS_OCR` | Cream (`#faf7e8`) | Graphite (`#3d3d3d`) | Ash (`#a6a6a6`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > Intake Workspace`
- **Next Logical Route:** `/coordinator/drives/[id]/review` (JD Fact Review & Policy Compilation).

---

## SCREEN 4: JD Review & Policy Approval (`/coordinator/drives/[id]/review`)

### 1. Screen Identity & Route
- **Screen Name:** JD Fact Review, Clarifications & Policy Approval
- **Route:** `/coordinator/drives/[id]/review`
- **Primary Audience:** Placement Coordinator, Faculty Reviewer, Placement Approver

### 2. User Role & Capabilities
- **Role:** Placement Coordinator / Approver (`policy:review`, `policy:approve`, `clarification:resolve`)
- **Capabilities:** Review AI-extracted JD facts, inspect paragraph-level source evidence, answer blocking clarifications, resolve ambiguous criteria, compile deterministic eligibility policy, and freeze policy proposals for attributable sign-off.

### 3. Core Purpose
Bridge unstructured recruiter JDs and deterministic eligibility execution: enable coordinators to verify every extracted fact against exact source text, resolve institutional ambiguities, compile a formal policy revision, and execute an attributable approval.

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Bar:** Drive context header with Active Policy Revision Pill (`Policy v1.0 Draft`), Dependency Fingerprint, and Review Progress Indicator.
- **3-Column Workspace Layout:**
  - Column 1 (45% Width): Structured Reviewed Facts & Criteria Form (White Product Card `#ffffff` with collapsible field groups).
  - Column 2 (30% Width): Interactive Source Evidence Locator & Document Excerpt Viewer (Paper White Card `#ffffff` with Leaf Bright `#1dbf73` anchor highlights).
  - Column 3 (25% Width): Blocking Clarifications Drawer, Policy Compilation Summary, and Attributable Approval Box (Lilac Wash `#fdf0ff` card).

### 5. Key UI Sections & Component Breakdown
1. **Header & Proposal Bar:**
   - Drive: "Google India — Software Engineer" | Revision: `Rev 3 (Draft)` | Source Hash: `sha256:e3b0c4...`
   - Actions: **Compile Policy Draft** (Ghost Outline Button), **Freeze & Submit Policy** (Coral Filled Button).
2. **Reviewed Facts Form (Column 1):**
   - *Field Group A: Company & Position Metadata:*
     - Company Name: `Google India Pvt. Ltd.` (Verified chip)
     - Role Title: `Software Engineer - Campus Graduate`
     - Employment Type: `Full-Time (FTE)`
     - Work Location & Mode: `Bengaluru / Hyderabad (Hybrid - 3 days in office)`
     - Compensation Breakdown: Base CTC: `₹18,00,000`, Stock Grants: `₹12,00,000 / 4 yrs`, Joining Bonus: `₹2,00,000`, Gross CTC: `₹32,00,000`.
   - *Field Group B: Academic Eligibility Criteria (Strict Deterministic Mapping):*
     - Allowed Branches: Multi-select pill chips: `[CSE]`, `[IT]`, `[ECE]`, `[EE]`.
     - Graduation Cohort: `2027` (Batch of 2027 B.Tech / Dual Degree).
     - Minimum CGPA & Scale: `7.50` on `10.00` Scale (Aggregate across all completed semesters).
     - Maximum Active Backlogs Allowed: `0 Backlogs` (Strict cutoff).
     - History of Arrears Allowed: `Yes (Must be cleared before joining)`.
   - *Field Group C: Dates & Recruitment Process:*
     - Registration Deadline: `2026-11-15 23:59:00 IST` (Explicit timezone mandatory).
     - Document Deadline: `2026-11-16 18:00:00 IST`.
     - Recruitment Rounds: Round 1: Online Coding (90 min) → Round 2: Technical Interview 1 → Round 3: Technical Interview 2 → Round 4: Googliness & Leadership.
   - *Provenance Tagging per Field:* Every field displays an evidence pill:
     - `AI EXTRACTED (Conf: 96%)` in Mint Wash `#d2f2e3` with locator link.
     - `HUMAN OVERRIDDEN (Prof. Sharma)` in Cream `#faf7e8` with timestamp and reason link.
3. **Source Evidence Viewer (Column 2):**
   - Live synchronization: Clicking any field in Column 1 scrolls the viewer to the exact source paragraph.
   - Document Excerpt Card:
     - Header: `Source: Google_Campus_JD_2026.pdf (Page 2, Paragraph 4)`
     - Highlighted Excerpt Text: `"Candidates must possess a minimum CGPA of 7.5 on a 10-point scale or 70% aggregate across all semesters with no active backlogs at the time of interview."`
     - Excerpt background: Cream `#faf7e8` with 2px solid Leaf Bright `#1dbf73` left border.
4. **Blocking Clarifications & Approval Drawer (Column 3):**
   - *Clarifications Box:*
     - Alert: `1 BLOCKING CLARIFICATION OPEN` (Peach Wash `#ffede8` card).
     - Item: "Ambiguity in CGPA Conversion: Recruiter specifies '7.5 CGPA or 70%'. Apex University uses formula `Percentage = CGPA * 9.5` (7.5 CGPA = 71.25%). Does 70% percentage cut off apply or strictly 7.5 CGPA?"
     - Resolution Action: Coordinator input field + **Resolve Clarification** button.
   - *Compiled Human-Readable Policy Rule Statement:*
     - Text Box (Sage Wash `#e4f7ee` card):
       `"STUDENTS ARE ELIGIBLE IF: Branch IN [CSE, IT, ECE, EE] AND Graduation_Year == 2027 AND Verified_CGPA >= 7.50 (Scale 10.0) AND Active_Backlogs <= 0."`
     - Evaluates against: `480 Verified Students in Cohort 2027`.
   - *Attributable Approval Controls:*
     - Reviewer Rationale Field: Mandatory textarea: "Enter approval rationale for institutional audit..."
     - Action Buttons:
       - **Approve Policy (v1.0)** (Coral Filled Button `#ff643b`, 40px radius).
       - **Reject Policy Proposal** (Ghost Outline Button `#000000`, 40px radius).
       - **Request Policy Revision** (Ghost Outline Button with revision notes).

### 6. Interface States & Exact Copy
- **Blocking Clarification Active State:**
  - Approval Box buttons are disabled (Ash `#a6a6a6` background).
  - Notice Banner: "Approval Blocked: 1 unresolved blocking clarification requires coordinator confirmation before policy can be compiled and approved."
- **Invalid Policy State (Validation Errors):**
  - Red Error Strip inside Column 3:
    - "Validation Error: Registration deadline time is missing an explicit institutional timezone."
    - "Validation Error: Allowed branches cannot be empty. Select at least one branch or toggle 'All Verified Branches'."
- **Stale Proposal State (Source Modified):**
  - High-Contrast Alert Banner: Cream `#faf7e8` with Coral Pulse `#ff643b` border.
  - Copy: "PROPOSAL INVALIDATED: A newer version of the JD source was uploaded after this draft was compiled. Dependency fingerprint mismatch. Re-compilation required."
  - Action: **Re-Compile Policy Draft** (Coral Filled Button `#ff643b`).
- **Policy Approved State (Locked & Immutable):**
  - Green Success Banner: Mint Wash `#d2f2e3`, Leaf Bright `#1dbf73` border.
  - Copy: "Policy v1.0 successfully approved by Dr. K. Sharma on 2026-11-04 14:10:22 IST. Policy is locked and immutable (Fingerprint: `sha256:91bc74...`). Ready for deterministic evaluation."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Approve Policy (v1.0)** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Compile Policy Draft** (Ghost Outline Button `#000000`, 40px radius).
- **Revision CTA:** **Request Revision** (Ghost Outline Button).

### 8. Data Displayed & Visual Formats
- Academic cutoffs formatted with explicit decimal precision: `7.50` (two decimal places, never rounded to single digit).
- Currency amounts formatted in Indian numbering: `₹18,00,000` (Base) and `₹32,00,000` (Gross CTC).
- Source locators formatted as `[Doc_Name, p.X, para.Y]`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Extraction: AI | `AI_SUGGESTION` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Extraction: Human | `HUMAN_CORRECTED` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Clarification: Open | `CLARIFICATION_OPEN` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Policy: Draft | `POLICY_DRAFT` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |
| Policy: Approved | `POLICY_APPROVED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > JD Review & Policy`
- **Next Logical Route:** `/coordinator/drives/[id]/eligibility` (Run Deterministic Evaluation).

---

## SCREEN 5: Eligibility Evaluation (`/coordinator/drives/[id]/eligibility`)

### 1. Screen Identity & Route
- **Screen Name:** Deterministic Cohort Eligibility Evaluation
- **Route:** `/coordinator/drives/[id]/eligibility`
- **Primary Audience:** Placement Coordinator, Academic Verification Officer

### 2. User Role & Capabilities
- **Role:** Placement Coordinator (`eligibility:evaluate`, `eligibility:view`, `cohort:filter`)
- **Capabilities:** Execute deterministic batch cohort eligibility evaluation against the immutable approved policy, inspect aggregate metrics, filter candidate cohorts by outcome, expand line-by-line predicate evaluations, and detect stale evaluation runs.

### 3. Core Purpose
Calculate and display strictly deterministic, rule-based academic eligibility for all cohort students, guaranteeing zero hallucination, explicit evidence verification, and transparent predicate-level explainability (Invariants INV-01, INV-02).

### 4. Layout & Surface Structure
- **Container:** Standard Coordinator Shell with 240px persistent left sidebar and 1040px content canvas on `#eee2ff` Lavender Mist.
- **Top Control Ribbon:** Approved Policy Reference, Cohort Scope Selector, and **Run Deterministic Evaluation** CTA.
- **Summary Metrics Strip:** 3 Large Pastel Feature Cards displaying the conservative aggregation outcomes: Eligible (Mint Wash `#d2f2e3`), Ineligible (Peach Wash `#ffede8`), Needs Review (Cream `#faf7e8`).
- **Main Evaluation Roster Table:** Full-width filterable data table (White Product Card `#ffffff`, 16px radius) with expandable predicate detail rows.

### 5. Key UI Sections & Component Breakdown
1. **Evaluation Control Ribbon:**
   - Active Policy Capsule: "Approved Policy v1.0 (Hash: `sha256:91bc74...`)" (DM Sans 14px weight 600, Canopy Green `#0a3922`).
   - Cohort Scope Dropdown: "Batch of 2027 — B.Tech All Branches (480 Verified Students)".
   - Historical Evaluation Runs Dropdown: "Run #4 — 2026-11-04 15:30:12 IST (Current)" | "Run #3 — 2026-11-03 11:20:00 IST".
   - Primary Execution Action: **Run Deterministic Evaluation** (Coral Filled Button `#ff643b`, 40px radius).
2. **Summary Metric Cards Strip (3 Pastel Feature Cards):**
   - *Card 1: ELIGIBLE (Mint Wash `#d2f2e3`):*
     - Headline: "ELIGIBLE" (DM Sans 14px weight 600, Canopy Green `#0a3922`).
     - Value: "312" (Display 72px `#0a3922`).
     - Subtitle: "65.0% of cohort meets all academic predicates".
     - Icon: Check-Circle.
   - *Card 2: INELIGIBLE (Peach Wash `#ffede8`):*
     - Headline: "INELIGIBLE" (DM Sans 14px weight 600, Coral Pulse `#ff643b`).
     - Value: "142" (Display 72px `#ff643b`).
     - Subtitle: "29.6% failed one or more verified predicates".
     - Icon: X-Circle.
   - *Card 3: NEEDS REVIEW (Cream `#faf7e8`):*
     - Headline: "NEEDS REVIEW" (DM Sans 14px weight 600, Charcoal `#333333`).
     - Value: "26" (Display 72px `#333333`).
     - Subtitle: "5.4% contain unverified, missing, or contradictory evidence".
     - Icon: Alert-Circle.
3. **Filter & Search Ribbon:**
   - Search: "Search by student roll number, student name, or branch..."
   - Filter Tabs: `All (480)`, `Eligible (312)`, `Ineligible (142)`, `Needs Review (26)`.
   - Branch Filter: Multi-select: `CSE`, `IT`, `ECE`, `EE`, `ME`, `CE`.
4. **Cohort Evaluation Master Table (White Product Card `#ffffff`):**
   - Table Columns: Roll Number | Student Name | Branch | Verified CGPA | Backlogs | Overall Outcome Badge | Failed / Missing Predicates Summary | Action.
   - Row Example:
     - Roll: `2023CS104` | Name: `Rahul Verma` | Branch: `CSE` | CGPA: `8.42` | Backlogs: `0`
     - Overall Badge: `ELIGIBLE` (Mint Wash `#d2f2e3` pill, Leaf Bright `#1dbf73` border)
     - Summary: `All 4 predicates satisfied`
     - Action: **Expand Predicates ↓** (Ghost Outline Button, 32px height)
5. **Expandable Predicate Breakdown Row (Expands below selected student):**
   - Container: Lavender Mist `#eee2ff` drawer with 16px padding.
   - Predicate Table:
     - *Predicate 1 (Branch):* Expected: `IN [CSE, IT, ECE, EE]` | Actual: `CSE` | Evidence Status: `VERIFIED` | Result: `PASS` (Leaf Bright `#1dbf73` tag).
     - *Predicate 2 (Graduation Year):* Expected: `== 2027` | Actual: `2027` | Evidence Status: `VERIFIED` | Result: `PASS` (Leaf Bright tag).
     - *Predicate 3 (Minimum CGPA):* Expected: `>= 7.50` | Actual: `8.42` | Evidence Status: `VERIFIED` | Result: `PASS` (Leaf Bright tag).
     - *Predicate 4 (Active Backlogs):* Expected: `<= 0` | Actual: `0` | Evidence Status: `VERIFIED` | Result: `PASS` (Leaf Bright tag).
   - *Ineligible Example (Roll: `2023ME045` - Vikram Singh):*
     - Predicate 1 (Branch): Expected: `IN [CSE, IT, ECE, EE]` | Actual: `ME` | Result: `FAIL` (Peach Wash `#ffede8` tag: `ERR_BRANCH_NOT_PERMITTED`).
     - Predicate 3 (CGPA): Expected: `>= 7.50` | Actual: `7.10` | Result: `FAIL` (`ERR_CGPA_BELOW_MIN`).
   - *Needs Review Example (Roll: `2023EC089` - Priya Nair):*
     - Predicate 4 (Backlogs): Expected: `<= 0` | Actual: `null (Unverified)` | Evidence Status: `UNVERIFIED_EVIDENCE` | Result: `UNKNOWN` (Cream `#faf7e8` tag: `EVID_MISSING`).
     - Notice: "Conservative Aggregation Rule: Unknown required evidence forces overall outcome to Needs Review. Cannot mark Eligible or Ineligible."

### 6. Interface States & Exact Copy
- **Evaluation Running State:**
  - Full-width Progress Bar across table header: Sky Signal `#00b4dc` bar.
  - Text: "Evaluating 480 student records against Policy v1.0... 72% completed (345/480). Non-blocking background worker."
- **Stale Evaluation State:**
  - Prominent Warning Banner above metrics: Cream `#faf7e8` card with 1px solid Coral Pulse `#ff643b` border.
  - Headline: "EVALUATION RESULTS ARE STALE" (DM Sans 16px weight 600, `#ff643b`).
  - Copy: "Academic records for 4 students were updated and verified since Run #4 was completed. Current results do not reflect the latest authoritative institutional evidence."
  - Action: **Re-Evaluate Cohort Now** (Coral Filled Button `#ff643b`).
- **Initial State (Zero Evaluations Run):**
  - Container: White Product Card `#ffffff`, 48px padding, centered.
  - Headline: "Policy Approved: Ready for Cohort Evaluation" (DM Sans 24px weight 600, `#0a3922`).
  - Body Copy: "Policy v1.0 is approved and immutable. Click below to execute the deterministic eligibility calculation across the 480 verified cohort students."
  - Action: **Run Deterministic Evaluation** (Coral Filled Button `#ff643b`).

### 7. Primary & Secondary Actions
- **Primary CTA:** **Run Deterministic Evaluation** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Export Evaluated Cohort** (Ghost Outline Button `#000000`, 40px radius).
- **Table Action:** **Expand Predicate Breakdown** (Ghost Outline Button).

### 8. Data Displayed & Visual Formats
- Academic percentages and CGPAs rendered strictly as decimals: `8.42 / 10.00`.
- Predicate statuses: `PASS` (Leaf Bright `#1dbf73`), `FAIL` (Coral Pulse `#ff643b`), `UNKNOWN` (Cream `#faf7e8` with Charcoal text).
- Reason codes displayed in code format: `ERR_CGPA_BELOW_MIN`, `ERR_BRANCH_NOT_PERMITTED`, `EVID_UNVERIFIED`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Outcome: Eligible | `ELIGIBLE` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Outcome: Ineligible | `INELIGIBLE` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Outcome: Review | `NEEDS_REVIEW` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Evidence: Verified | `EVID_VERIFIED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | None |
| Evidence: Missing | `EVID_MISSING` | Cream (`#faf7e8`) | Coral Pulse (`#ff643b`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Sidebar Active Item:** "Drives"
- **Breadcrumbs:** `Drives > Google - SWE > Eligibility Evaluation`
- **Next Logical Route:** `/coordinator/drives/[id]/participation` (Participation & Document Management).
'''

print("Screens 1 to 5 defined.")
