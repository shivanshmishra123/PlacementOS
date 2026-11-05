"""
Screens 15 to 20 (Student Portal) for PlacementOS.
"""

def get_screens_15_to_20():
    return '''---

## SCREEN 15: Student Profile (`/student/portal`)

### 1. Screen Identity & Route
- **Screen Name:** Student Personal Academic Record & Correction Portal
- **Route:** `/student/portal`
- **Primary Audience:** University Student

### 2. User Role & Capabilities
- **Role:** Student (`student_profile:view`, `correction:propose`)
- **Capabilities:** Inspect personal verified academic records, view historical administrative import revisions, track pending correction requests, and submit attributable academic correction proposals with supporting evidence.

### 3. Core Purpose
Empower students to verify their authoritative institutional academic data, understand provenance and verification status, and propose attributable corrections without ever permitting unverified self-edits to directly alter deterministic drive eligibility (Invariant INV-01, INV-02).

### 4. Layout & Surface Structure
- **Container:** Standard Student Shell with sticky 72px Top Navigation Bar and 1280px centered content container on `#eee2ff` Lavender Mist canvas.
- **Top Section:** Student Identity Banner with Roll Monogram and Department details.
- **2-Column Split Layout (50/50 Split):**
  - Left Column (50%): Current Verified Academic Record Card (Mint Wash `#d2f2e3` card, 24px padding, 24px radius).
  - Right Column (50%): Academic Correction Proposals Panel and Administrative Revision History Accordion (White Product Card `#ffffff`, 16px radius).
- **Modal Layer:** Propose Academic Correction Modal (White Product Card `#ffffff`, 24px padding).

### 5. Key UI Sections & Component Breakdown
1. **Student Identity Header:**
   - Monogram Avatar: 64px circle in Canopy Green `#0a3922` with "RV" in Paper White `#ffffff`.
   - Student Name: "Rahul Verma" (DM Sans 32px weight 600, `#0a3922`).
   - Metadata Strip: Roll Number: `2023CS104` | Institutional Email: `rahul.verma@apex.edu` | Department: `Computer Science & Engineering` | Program: `B.Tech (4-Year)`.
   - Verification Status Tag: `RECORD_VERIFIED` (Mint Wash `#d2f2e3` tag with Leaf Bright `#1dbf73` border).
2. **Current Verified Academic Record Card (Mint Wash `#d2f2e3`):**
   - Header: "Authoritative Academic Evidence (Revision #2)" (DM Sans 20px weight 600, `#0a3922`).
   - Verified Fields Grid (2-column layout):
     - *Branch / Program:* `Computer Science and Engineering (CSE)`
     - *Graduation Cohort:* `Batch of 2027`
     - *Cumulative CGPA:* `8.42` (on 10.00 Scale)
     - *Active Backlogs:* `0 Backlogs`
     - *Total Cleared Arrears:* `0`
     - *Academic Standing:* `Regular / In Good Standing`
   - Provenance Box:
     - Verified by: `Office of the Registrar / Exam Cell`
     - Verification Date: `2026-10-15 11:30:00 IST`
     - Source: `Official Semester 6 Batch CSV Import`
     - SHA-256 Digest: `sha256:e9a14...`
3. **Academic Correction Proposals Panel (White Product Card `#ffffff`):**
   - Header: "Correction Proposals" + **Propose Academic Correction** CTA (Coral Filled Button `#ff643b`, 40px radius, white text).
   - Proposals Table:
     - Columns: Field | Current Value | Proposed Value | Status Pill | Reviewer Note | Date.
     - Row 1: `CGPA` | `8.42` | `8.65` | `PENDING_REVIEW` (Sky Wash `#ccf0f8` tag) | "Under verification with Exam Cell" | `2026-11-02`
     - Row 2: `Active Backlogs` | `1` | `0` | `APPROVED` (Mint Wash `#d2f2e3` tag) | "Grade card submitted matches registrar records" | `2026-10-18`
4. **Historical Revisions Accordion (Read-Only):**
   - Collapsible panel showing Revision #1 (`CGPA: 8.20`, imported 2026-08-01).
5. **Propose Academic Correction Modal (Overlaid White Product Card):**
   - Modal Title: "Request Academic Record Correction"
   - Advisory Note: "In accordance with institutional placement policy, corrections must be verified with the Exam Cell before taking effect in drive eligibility evaluations."
   - Inputs:
     - Field Selector Dropdown: `Cumulative CGPA`, `Active Backlogs Count`, `Graduation Year`, `Branch Name`.
     - Proposed Value Input: (e.g., `8.65`).
     - Reason / Explanation Textarea: (e.g., "Semester 6 re-evaluation result declared on Oct 30 revised marks from 78 to 86.").
     - Supporting Document Upload: Drag-and-drop zone for official transcript/marksheet (PDF, Max 5MB).
   - Actions: **Submit Correction Proposal** (Coral Filled Button `#ff643b`), **Cancel** (Ghost Outline Button `#000000`).

### 6. Interface States & Exact Copy
- **Normal Verified State:** All fields show `VERIFIED`; clean record; 1 pending correction proposal.
- **Unverified Profile State (New Batch Setup):**
  - High-Contrast Amber Banner: Cream `#faf7e8` card with 1px solid Coral Pulse `#ff643b` border.
  - Headline: "ACADEMIC EVIDENCE NOT YET VERIFIED" (DM Sans 18px weight 600, `#ff643b`).
  - Copy: "Your academic records have not yet been imported or verified by the University Placement Office. Deterministic eligibility evaluations will mark unverified fields as 'Needs Review'. Contact your department placement representative if this is an error."
- **Correction Approved State (Toast Notification):**
  - "Academic correction approved. Academic Revision #3 generated. Active drive eligibility evaluations are being updated."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Propose Academic Correction** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Modal Action:** **Submit Correction Proposal** (Coral Filled Button `#ff643b`).
- **Secondary Action:** **Download Verified Transcript** (Ghost Outline Button `#000000`, 40px radius).

### 8. Data Displayed & Visual Formats
- Academic scores formatted to two decimal places: `8.42 / 10.00`.
- Dates formatted as `YYYY-MM-DD HH:mm:ss IST`.
- Verification badges in Leaf Bright `#1dbf73`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Profile: Verified | `RECORD_VERIFIED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Profile: Unverified | `RECORD_UNVERIFIED`| Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Correction: Pending | `PENDING_REVIEW` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Correction: Approved | `APPROVED_VERIFIED`| Mint Wash (`#d2f2e3`)| Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Correction: Rejected | `REJECTED` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Top Nav Active Item:** "My Profile" (Leaf Bright `#1dbf73` bottom underline).
- **Navigation Links:** Opportunities (`/student/drives`), Schedule & Results (`/student/schedule-results`), My Profile (`/student/portal`).

---

## SCREEN 16: Drive Opportunities (`/student/drives`)

### 1. Screen Identity & Route
- **Screen Name:** Student Drive Opportunities Directory
- **Route:** `/student/drives`
- **Primary Audience:** University Student

### 2. User Role & Capabilities
- **Role:** Student (`drives:browse_published`, `registration:view`)
- **Capabilities:** Browse approved student-visible recruitment drives, filter by personal deterministic eligibility status, inspect approved job facts, and access registration workspaces.

### 3. Core Purpose
Serve as the official student directory of published campus recruitment drives, providing immediate, transparent visibility into personal eligibility status, compensation breakdowns, registration deadlines, and document requirements.

### 4. Layout & Surface Structure
- **Container:** Standard Student Shell with sticky 72px Top Navigation Bar and 1280px centered content container on `#eee2ff` Lavender Mist canvas.
- **Top Ribbon:** Page Title, Search input, and Eligibility Filter Tabs.
- **Main Canvas:** 3-column responsive grid of Drive Opportunity Cards (Pastel Feature Cards cycling through Mint, Sky, Sage, Lilac, Peach, Cream).

### 5. Key UI Sections & Component Breakdown
1. **Header & Filter Ribbon:**
   - Title: "Campus Recruitment Opportunities" (DM Sans 32px weight 600, `#0a3922`).
   - Subtitle: "Official drives approved by the Placement Cell for the Batch of 2027."
   - Search Bar: "Search by company name, role title, or location..."
   - Filter Tabs:
     - `All Opportunities (8)`
     - `Eligible for Me (5)` (Leaf Bright badge)
     - `Needs Review (1)` (Amber badge)
     - `Ineligible for Me (2)` (Gray badge)
2. **Drive Opportunity Cards Grid (Pastel Feature Cards cycling every 6 cards):**
   - *Card Anatomy (Example: Google India - Mint Wash `#d2f2e3`):*
     - Top Row: Company Monogram/Logo (48px square, Paper White background) | Company Name: `Google India` | Personal Eligibility Badge.
     - *Prominent Eligibility Badge:*
       - `YOU ARE ELIGIBLE` (Mint Wash `#d2f2e3` pill, Leaf Bright `#1dbf73` border, Canopy Green `#0a3922` text).
     - Role Title: `Software Engineer - Campus Graduate` (DM Sans 24px weight 600, `#0a3922`).
     - Key Highlights Grid:
       - Compensation: `₹18.0 LPA Base (₹32.0 LPA Gross CTC)`
       - Location: `Bengaluru / Hyderabad (Hybrid)`
       - Employment Type: `Full-Time Employment (FTE)`
     - Registration Window Countdown Strip (Paper White Card inside pastel surface, 12px padding):
       - Clock Icon + "Registration Closes: 2026-11-15 23:59:00 IST (4 days remaining)".
     - Required Documents Tag: `Resume (Required at Reg) · Marksheet (Required by Nov 17)`.
     - Registration Status Pill: `NOT REGISTERED` or `REGISTERED (Nov 11)`.
     - Card Action: **View Details & Register →** (Coral Filled Button `#ff643b`, 40px radius, white text).
   - *Card Anatomy (Example: Texas Instruments - Peach Wash `#ffede8`):*
     - Personal Eligibility Badge: `NOT ELIGIBLE` (Peach Wash `#ffede8` pill, Coral Pulse `#ff643b` text).
     - Reason Snippet: "Branch 'CSE' is not permitted for this Hardware role."
     - Card Action: **View Eligibility Details** (Ghost Outline Button `#000000`, 40px radius).
   - *Card Anatomy (Example: Deloitte - Cream `#faf7e8`):*
     - Personal Eligibility Badge: `ELIGIBILITY NEEDS REVIEW` (Cream `#faf7e8` pill, Charcoal text).
     - Reason Snippet: "Active Backlogs evidence is unverified in your profile."
     - Card Action: **Resolve Evidence Review** (Ghost Outline Button `#000000`, 40px radius).

### 6. Interface States & Exact Copy
- **Normal State:** Grid displays 8 published drive cards with clear personal eligibility badges.
- **Empty Filter State (Zero Results):**
  - Container: White Product Card `#ffffff`, 48px padding, centered.
  - Headline: "No recruitment opportunities match your filter" (DM Sans 20px weight 600, `#0a3922`).
  - Copy: "You currently have no drives matching 'Needs Review'. Check 'All Opportunities' to view active drives."
  - Action: **Reset All Filters** (Ghost Outline Button `#000000`).
- **All Drives Closed State:**
  - Notice Banner: "No recruitment drives are currently accepting registrations. Upcoming drives for the next cycle will be published here."

### 7. Primary & Secondary Actions
- **Primary CTA (On Eligible Cards):** **View Details & Register →** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA (On Ineligible/Review Cards):** **View Eligibility Details** (Ghost Outline Button `#000000`, 40px radius).
- **Filter Action:** **Reset Filters** (Ghost Outline Button).

### 8. Data Displayed & Visual Formats
- CTC amounts displayed in Indian Lakhs per Annum: `₹18.0 LPA Base (₹32.0 LPA Gross CTC)`.
- Deadlines formatted with exact 24-hour time and timezone: `2026-11-15 23:59:00 IST`.
- Company logos rendered as clean SVG monograms on Paper White `#ffffff` squares.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Personal: Eligible | `YOU ARE ELIGIBLE` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Personal: Ineligible | `NOT ELIGIBLE` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Personal: Review | `NEEDS_REVIEW` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Registration: Open | `REGISTRATION_OPEN`| Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Registration: Closed | `REGISTRATION_CLOSED`| Cloud Gray (`#f2f2f2`) | Slate (`#7a7a7a`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Top Nav Active Item:** "Opportunities" (Leaf Bright `#1dbf73` bottom underline).
- **Context Transition:** Clicking any card routes to the Drive Detail Hub for that drive, default landing on `/student/drives/[id]/eligibility`.

---

## SCREEN 17: Student Eligibility Detail (`/student/eligibility` or within drive detail)

### 1. Screen Identity & Route
- **Screen Name:** Student Deterministic Eligibility Breakdown & Explanation
- **Route:** `/student/drives/[id]/eligibility` (and `/student/eligibility`)
- **Primary Audience:** University Student

### 2. User Role & Capabilities
- **Role:** Student (`eligibility:view_self`, `review:request_evidence`)
- **Capabilities:** Transparently inspect personal deterministic eligibility results, review line-by-line predicate requirements against verified personal records, understand exact failure or missing-evidence reasons, and submit evidence review requests.

### 3. Core Purpose
Demystify placement eligibility for students through radical explainability: display exact deterministic predicate comparisons, explain why an outcome is Eligible, Ineligible, or Needs Review, and prevent arbitrary override requests by rooting all decisions in verified evidence (Invariant INV-01).

### 4. Layout & Surface Structure
- **Container:** Standard Student Shell with sticky 72px Top Navigation Bar and 1280px centered content container on `#eee2ff` Lavender Mist canvas.
- **Top Banner:** Drive context header with Company Monogram, Role Title, and Overall Eligibility Outcome Banner.
- **Central Explanation Card:** White Product Card `#ffffff` (24px padding, 16px radius, no shadow) hosting the Predicate Breakdown Table.
- **Bottom Section:** Evidence Review Request Box (Sage Wash `#e4f7ee` card, 24px padding).

### 5. Key UI Sections & Component Breakdown
1. **Drive Context & Master Outcome Banner:**
   - Company Monogram & Role: "Google India — Software Engineer - Campus Graduate"
   - *Master Outcome Banner (Mint Wash `#d2f2e3` for Eligible / Peach Wash `#ffede8` for Ineligible / Cream `#faf7e8` for Needs Review):*
     - Headline: "YOU MEET ALL ELIGIBILITY CRITERIA FOR THIS DRIVE" (DM Sans 28px weight 600, Canopy Green `#0a3922`).
     - Subtitle: "Calculated deterministically by the PlacementOS Policy Engine against approved Policy v1.0 on 2026-11-04 15:30:12 IST."
     - Icon: Check-Circle (Leaf Bright `#1dbf73`).
2. **Predicate Breakdown Table (White Product Card `#ffffff`):**
   - Header: "Academic Predicates Evaluation Breakdown" (DM Sans 18px weight 600, `#0a3922`).
   - Table Columns: Recruitment Requirement | Required Company Criteria | Your Verified Record | Predicate Result | Source Evidence.
   - Row 1 (Branch):
     - Requirement: `Permitted Engineering Branches`
     - Required: `CSE, IT, ECE, EE`
     - Your Record: `CSE`
     - Predicate Result: `PASSED` (Leaf Bright `#1dbf73` tag)
     - Evidence: Verified by Registrar (Revision #2)
   - Row 2 (Graduation Year):
     - Requirement: `Graduation Cohort`
     - Required: `Batch of 2027`
     - Your Record: `2027`
     - Predicate Result: `PASSED` (Leaf Bright tag)
     - Evidence: Verified by Registrar
   - Row 3 (Minimum CGPA):
     - Requirement: `Cumulative Grade Point Average`
     - Required: `>= 7.50 on 10.00 Scale`
     - Your Record: `8.42 / 10.00`
     - Predicate Result: `PASSED` (Leaf Bright tag)
     - Evidence: Verified Semester 6 Batch CSV
   - Row 4 (Active Backlogs):
     - Requirement: `Maximum Active Backlogs Allowed`
     - Required: `<= 0 Backlogs (Strict Cutoff)`
     - Your Record: `0 Backlogs`
     - Predicate Result: `PASSED` (Leaf Bright tag)
     - Evidence: Verified Exam Cell Clearance
3. **Ineligible Scenario Breakdown (When Student Fails Predicates):**
   - *Example: Roll 2023ME045 (Mechanical Engineering Student):*
     - Row 1 (Branch): Required: `CSE, IT, ECE, EE` | Your Record: `ME` | Result: `FAILED (ERR_BRANCH_NOT_PERMITTED)` [Red Tag].
     - Row 3 (CGPA): Required: `>= 7.50` | Your Record: `7.10` | Result: `FAILED (ERR_CGPA_BELOW_MIN)` [Red Tag].
     - Explanatory Notice: "Recruiter criteria strictly limits registration to listed branches and minimum CGPA. Placement coordinators cannot grant exceptions or overrides for academic criteria."
4. **Needs Review Scenario Breakdown (Missing Evidence):**
   - *Example: Roll 2023EC089:*
     - Row 4 (Backlogs): Required: `<= 0` | Your Record: `null (Unverified)` | Result: `UNDER REVIEW (EVID_MISSING)` [Amber Tag].
     - Explanatory Notice: "Your backlog standing has not been verified by the Exam Cell. Conservative Aggregation Rule: Unverified evidence prevents an automatic pass. Propose an academic correction on your profile to resolve."
5. **Evidence Review Request Drawer (Bottom Card):**
   - Headline: "Believe your verified academic record contains an error?"
   - Copy: "PlacementOS calculates eligibility strictly from your verified academic profile. If your Exam Cell grade card differs from the values above, submit an academic correction request."
   - Action: **Go to My Profile to Propose Correction →** (Coral Filled Button `#ff643b`, 40px radius).

### 6. Interface States & Exact Copy
- **Eligible State:** Master banner green (Mint Wash `#d2f2e3`); all 4 rows show `PASSED`; action CTA **Proceed to Registration →** active.
- **Ineligible State:** Master banner red (Peach Wash `#ffede8`); failing rows highlighted in red; explanation states that overrides are prohibited.
- **Needs Review State:** Master banner amber (Cream `#faf7e8`); missing rows highlighted; CTA directs student to profile correction flow.
- **Stale Evaluation Alert State:**
  - Amber Notification Banner above table:
  - Copy: "Notice: An academic correction was recently approved on your profile. Eligibility for this drive is currently being recalculated by the system."

### 7. Primary & Secondary Actions
- **Primary CTA (When Eligible):** **Proceed to Registration & Documents →** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Go to My Profile to Propose Correction** (Ghost Outline Button `#000000`, 40px radius).
- **Download Action:** **Download Eligibility Summary (PDF)** (Ghost Outline Button, 32px height).

### 8. Data Displayed & Visual Formats
- Predicate values explicitly typed: Decimals (`8.42`), Integers (`0`), Sets (`[CSE, IT, ECE, EE]`).
- Status tags: `PASSED` (Leaf Bright `#1dbf73`), `FAILED` (Coral Pulse `#ff643b`), `UNDER_REVIEW` (Cream `#faf7e8`).
- Reason codes in monospace: `ERR_CGPA_BELOW_MIN`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Predicate: Passed | `PASSED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Predicate: Failed | `FAILED` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Predicate: Review | `UNDER_REVIEW` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Engine: Deterministic | `STRICT_DETERMINISTIC`| Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Top Nav Active Item:** "Opportunities"
- **Breadcrumbs:** `Opportunities > Google India - SWE > Eligibility Explanation`
- **Next Logical Route:** `/student/drives/[id]/documents` (Upload Required Documents).

---

## SCREEN 18: Document Checklist & Upload (Within drive detail for student)

### 1. Screen Identity & Route
- **Screen Name:** Student Drive Document Checklist, Upload & Validation
- **Route:** `/student/drives/[id]/documents`
- **Primary Audience:** University Student

### 2. User Role & Capabilities
- **Role:** Student (`document:upload`, `document:replace`, `document:view_self`)
- **Capabilities:** Inspect drive-specific document requirements, upload personal PDFs/DOCXs, monitor asynchronous antivirus quarantine and PDF structure parsing in real time, inspect safe validation findings, and replace outdated files.

### 3. Core Purpose
Guide students through document readiness compliance: validate file formats, sanitize uploads through an isolated antivirus quarantine, and maintain complete independence between document readiness and academic eligibility.

### 4. Layout & Surface Structure
- **Container:** Standard Student Shell with sticky 72px Top Navigation Bar and 1280px centered content container on `#eee2ff` Lavender Mist canvas.
- **Top Summary Strip:** Overall Document Readiness Status Banner with deadline notice.
- **Checklist Area:** Vertical stack of Document Requirement Cards (White Product Cards `#ffffff`, 16px radius, 24px padding).
- **Upload Modal Layer:** Quarantined File Upload Dialog with progress bar and scan status spinner.

### 5. Key UI Sections & Component Breakdown
1. **Document Readiness Summary Banner (Mint Wash `#d2f2e3` or Peach Wash `#ffede8`):**
   - Headline: "DOCUMENT READINESS: 1 OF 2 REQUIRED DOCUMENTS READY" (DM Sans 20px weight 600, `#0a3922`).
   - Copy: "You have successfully uploaded your Resume. Your 6th Semester Marksheet is missing and must be submitted before interview scheduling closes on 2026-11-17 18:00:00 IST."
   - Overall Readiness Tag: `DOCS_INCOMPLETE` (Cream `#faf7e8` tag).
2. **Document Requirement Cards Stack:**
   - *Card 1: Resume / Curriculum Vitae (Stage: Required at Registration):*
     - Format: `PDF Format Only` | Max Size: `5 MB` | Status: `READY` (Leaf Bright tag).
     - Uploaded File Info: `Rahul_Verma_Resume_2026.pdf` (1.4 MB)
     - Upload Timestamp: `2026-11-10 10:15:22 IST`
     - Security & Validation Findings:
       - Antivirus Scan: `ClamAV Scanned Clean ✅`
       - PDF Structure: `Valid PDF v1.6 (Linearized, Unencrypted) ✅`
     - Actions: **Download My File** (Ghost Outline Button, 32px height), **Replace Resume** (Ghost Outline Button).
   - *Card 2: 6th Semester Marksheet (Stage: Required before Round 1 Scheduling):*
     - Format: `PDF Format Only` | Max Size: `10 MB` | Status: `BLOCKED_CORRUPT` (Peach Wash tag).
     - Deadline: `2026-11-17 18:00:00 IST (6 days remaining)`
     - Security & Validation Findings:
       - Antivirus Scan: `Clean ✅`
       - PDF Structure: `FAILED ❌ (File header corrupt or password-protected)`
     - Safe Student Error Notice: "The uploaded file could not be parsed. Please ensure the PDF is unencrypted, does not require a password, and was generated directly from your university exam portal."
     - Actions: **Upload New Marksheet** (Coral Filled Button `#ff643b`, 40px radius, white text).
   - *Card 3: Institutional College ID Card (Stage: Optional / Identity Verification):*
     - Format: `PDF, JPEG, or PNG` | Max Size: `2 MB` | Status: `NOT_UPLOADED_OPTIONAL` (Cloud Gray tag).
     - Action: **Upload ID Card** (Ghost Outline Button `#000000`).
3. **Upload Dialog Modal (When clicking Upload/Replace):**
   - Modal Header: "Upload 6th Semester Marksheet"
   - Dropzone Container: 2px dashed Ink Black `#000000` border on Sky Wash `#ccf0f8` surface.
   - Text: "Drag and drop your PDF here or **Browse Files**"
   - Processing States during upload:
     1. Client MIME/Extension Check: "Verifying file is a valid PDF..."
     2. Upload to Quarantine Bucket: "Uploading 2.1 MB..." (Progress bar).
     3. Asynchronous Security Scan: "Scanning for malware with ClamAV..." (Spinner).
     4. PDF Structure Verification: "Checking page count and unencrypted header..."
   - Action: **Confirm & Save Document** (Coral Filled Button `#ff643b`).

### 6. Interface States & Exact Copy
- **All Documents Ready State:**
  - Banner: Mint Wash `#d2f2e3`, Leaf Bright `#1dbf73` border.
  - Headline: "ALL REQUIRED DOCUMENTS READY"
  - Copy: "Your resume and marksheet have passed security and structure validation. You meet all document prerequisites for interview scheduling."
- **Quarantined Malware State (Upload Modal):**
  - High-Severity Red Warning inside modal: Peach Wash `#ffede8`, Coral Pulse `#ff643b` border.
  - Headline: "SECURITY SCAN FAILED: FILE QUARANTINED"
  - Copy: "The file you uploaded triggered an antivirus signature alert. The file has been quarantined and isolated in accordance with institutional security policy. Document preview and acceptance are disabled. Please scan your device and upload a clean copy."
- **Upload in Progress State:**
  - Spinner with animated progress bar: "Uploading and scanning document... Please do not close this window."

### 7. Primary & Secondary Actions
- **Primary CTA (On Blocked/Missing Cards):** **Upload New File** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Replace Resume** (Ghost Outline Button `#000000`, 40px radius).
- **Download Action:** **Download My File** (Ghost Outline Button, 32px height).

### 8. Data Displayed & Visual Formats
- File sizes formatted in megabytes: `1.4 MB`.
- Validation checks displayed as checklist with green checkmarks or red X icons.
- Deadlines formatted with explicit timezone: `2026-11-17 18:00:00 IST`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Document: Ready | `READY` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Document: Missing | `MISSING_REQUIRED` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Ash (`#a6a6a6`) |
| Document: Blocked | `BLOCKED_CORRUPT` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Document: Scanning | `SCANNING_QUARANTINE`| Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Document: Optional | `NOT_UPLOADED` | Cloud Gray (`#f2f2f2`) | Slate (`#7a7a7a`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Top Nav Active Item:** "Opportunities"
- **Breadcrumbs:** `Opportunities > Google India - SWE > Document Checklist`
- **Next Logical Route:** `/student/drives/[id]/register` (Submit Drive Registration).

---

## SCREEN 19: Registration (Within drive detail for student)

### 1. Screen Identity & Route
- **Screen Name:** Student Drive Registration, Status & Withdrawal
- **Route:** `/student/drives/[id]/register`
- **Primary Audience:** University Student

### 2. User Role & Capabilities
- **Role:** Student (`registration:submit`, `registration:withdraw`, `registration:view_self`)
- **Capabilities:** Inspect registration window status, verify prerequisite fulfillment (academic eligibility and submission-time documents), submit formal drive registration, track confirmation tokens, and execute self-service withdrawal before cutoff.

### 3. Core Purpose
Provide students with an authoritative, immutable registration submission flow: enforce strict prerequisite gating, generate durable registration tokens, and handle post-registration lifecycle events such as eligibility holds and pre-cutoff withdrawals.

### 4. Layout & Surface Structure
- **Container:** Standard Student Shell with sticky 72px Top Navigation Bar and 1280px centered content container on `#eee2ff` Lavender Mist canvas.
- **Top Section:** Registration Window Timer & Server Synchronization Strip.
- **Central Action Canvas (Centered Container, 800px width):**
  - Prerequisite Checklist Card (Sage Wash `#e4f7ee` card, 24px padding).
  - Main Registration Submission / Confirmation Card (White Product Card `#ffffff` or Mint Wash `#d2f2e3` card, 32px padding).
  - Withdrawal Policy Notice & Action Box (Paper White Card `#ffffff`, 16px radius).

### 5. Key UI Sections & Component Breakdown
1. **Registration Window Status Strip:**
   - Registration Window Banner: "REGISTRATION WINDOW OPEN" (Mint Wash `#d2f2e3`, Canopy Green `#0a3922` text).
   - Window Parameters: Opens: `2026-11-10 09:00:00 IST` | Closes: `2026-11-15 23:59:00 IST` (Explicit server clock synchronization).
   - Real-Time Informational Countdown: `04 Days : 08 Hours : 14 Minutes : 32 Seconds Remaining`.
2. **Prerequisites Checklist Card (Sage Wash `#e4f7ee`):**
   - Header: "Mandatory Registration Prerequisites" (DM Sans 18px weight 600, `#0a3922`).
   - Prerequisites List:
     - [x] Deterministic Academic Eligibility: `ELIGIBLE (Passed all 4 predicates)`
     - [x] Registration-Time Documents: `READY (Resume uploaded and scanned clean)`
     - [x] Drive Operational Status: `ACTIVE (No operational holds)`
   - Status Note: "All prerequisites verified. You are authorized to submit your registration."
3. **Registration Action & Confirmation Card (Center Container):**
   - *State A: Not Yet Registered (Submission Mode):*
     - Headline: "Confirm Registration for Google India — Software Engineer" (DM Sans 24px weight 600, `#0a3922`).
     - Student Declaration Checkbox: "I confirm my availability for all rounds of the recruitment drive on 2026-11-18. I understand that withdrawal after the deadline requires coordinator approval."
     - Primary Action CTA: **Submit Formal Registration** (Coral Filled Button `#ff643b`, 40px radius, DM Sans 18px weight 600, white text).
     - Idempotency Note: Repeated clicks or retries safely return the existing registration token without creating duplicate records.
   - *State B: Successfully Registered (Confirmed State):*
     - Container shifts to Mint Wash `#d2f2e3` with Leaf Bright `#1dbf73` border.
     - Headline: "YOU ARE REGISTERED FOR THIS DRIVE" (DM Sans 28px weight 600, Canopy Green `#0a3922`).
     - Registration Token Capsule: `REGISTRATION TOKEN: #REG-90812` (Monospace DM Sans 14px).
     - Submission Timestamp: `2026-11-11 14:22:18 IST`
     - Bound Policy & Evaluation Reference: `Policy v1.0 (Hash: sha256:91bc74...)`
     - Post-Registration Requirement Notice: "Reminder: Your 6th Semester Marksheet is due before 2026-11-17 18:00 IST to participate in interview scheduling."
4. **Withdrawal Console (Paper White Card `#ffffff`):**
   - Headline: "Registration Withdrawal Policy" (DM Sans 16px weight 600, `#0a3922`).
   - Copy: "You may withdraw your registration at any time before the registration cutoff (2026-11-15 23:59:00 IST). After this deadline, withdrawals can only be processed by the Placement Office."
   - Action: **Withdraw Registration** (Ghost Outline Button with Coral Pulse `#ff643b` border and confirmation dialog).

### 6. Interface States & Exact Copy
- **Prerequisite Unmet State (Registration Blocked):**
  - Red Warning Box inside submission card:
    - Headline: "REGISTRATION BLOCKED: PREREQUISITES UNMET"
    - Copy: "You cannot submit registration because your document readiness status is 'BLOCKED_CORRUPT' for your 6th Sem Marksheet. Resolve all required documents before submitting."
    - Primary Button **Submit Formal Registration** is disabled (Ash `#a6a6a6` background).
- **Eligibility Hold State (After Submission):**
  - Prominent Warning Banner: Cream `#faf7e8` card with 1px solid Coral Pulse `#ff643b` border.
  - Headline: "REGISTRATION STATUS: ELIGIBILITY HOLD" (DM Sans 20px weight 600, `#ff643b`).
  - Copy: "Your registration has been placed on temporary hold because the recruiter updated academic criteria. Your verified record is being re-evaluated against Policy v2.0. You will be notified automatically once evaluation concludes."
- **Registration Window Closed State:**
  - Banner: Cloud Gray `#f2f2f2`, Charcoal text.
  - Headline: "REGISTRATION CLOSED"
  - Copy: "The deadline for this recruitment drive closed on 2026-11-15 23:59:00 IST. New registrations are no longer accepted."
- **Withdrawn State:**
  - Notice Card: Sand `#f4ece9` surface.
  - Copy: "You successfully withdrew your registration on 2026-11-12 16:04:00 IST. The registration window remains open until Nov 15 if you wish to re-register."
  - Action: **Re-Register for Drive** (Coral Filled Button `#ff643b`).

### 7. Primary & Secondary Actions
- **Primary CTA:** **Submit Formal Registration** (Coral Filled Button `#ff643b`, 40px radius, white text).
- **Secondary CTA:** **Withdraw Registration** (Ghost Outline Button with Coral border and confirmation prompt).
- **Re-Register CTA:** **Re-Register for Drive** (Coral Filled Button `#ff643b`).

### 8. Data Displayed & Visual Formats
- Registration token: `#REG-90812` in monospace DM Sans 14px.
- Timestamps with second precision: `2026-11-11 14:22:18 IST`.
- Countdown timers formatted as `DDd : HHh : MMm : SSs`.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Status: Registered | `REGISTERED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Status: Not Registered | `NOT_REGISTERED` | Cloud Gray (`#f2f2f2`) | Slate (`#7a7a7a`) | None |
| Status: Withdrawn | `WITHDRAWN` | Sand (`#f4ece9`) | Slate (`#7a7a7a`) | None |
| Status: On Hold | `ELIGIBILITY_HOLD` | Peach Wash (`#ffede8`)| Coral Pulse (`#ff643b`) | Coral Pulse (`#ff643b`) |
| Status: Closed | `WINDOW_CLOSED` | Cloud Gray (`#f2f2f2`) | Charcoal (`#333333`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Top Nav Active Item:** "Opportunities"
- **Breadcrumbs:** `Opportunities > Google India - SWE > Registration`
- **Next Logical Route:** `/student/schedule-results` (Track Interview Sessions & Results).

---

## SCREEN 20: Schedule & Results (`/student/schedule-results`)

### 1. Screen Identity & Route
- **Screen Name:** Student Interview Schedule & Official Recruitment Results
- **Route:** `/student/schedule-results`
- **Primary Audience:** University Student

### 2. User Role & Capabilities
- **Role:** Student (`schedule:view_self`, `results:view_self`)
- **Capabilities:** View personal published interview session assignments, inspect venue/virtual meeting links, follow rescheduling correction notices, and view official published employer round outcomes and final offers.

### 3. Core Purpose
Serve as the authoritative student destination for interview schedules and employer outcomes: guarantee that students only see officially published assignments, display clear correction history when sessions are rescheduled, and prevent premature leaks of draft internal coordinator results.

### 4. Layout & Surface Structure
- **Container:** Standard Student Shell with sticky 72px Top Navigation Bar and 1280px centered content container on `#eee2ff` Lavender Mist canvas.
- **Top Section:** Page Header with Tab Toggle: `[My Upcoming Schedule]` and `[Official Selection Results]`.
- **Schedule Section:** Vertical stack of Published Session Cards (Sky Wash `#ccf0f8` and Mint Wash `#d2f2e3` cards, 24px padding).
- **Results Section:** Full-width Official Outcomes Table (White Product Card `#ffffff`, 16px radius).

### 5. Key UI Sections & Component Breakdown
1. **Header & View Toggle:**
   - Title: "My Schedule & Recruitment Results" (DM Sans 32px weight 600, `#0a3922`).
   - Subtitle: "Official interview assignments and verified employer results published by the Placement Office."
   - Tab Bar:
     - `My Upcoming Schedule (1 Active Session)` (Pill Tag `#ccf0f8`)
     - `Official Drive Results (3 Drives)` (Pill Tag `#d2f2e3`)
2. **Upcoming Interview Sessions Stack (Sky Wash `#ccf0f8` cards, 24px radius):**
   - *Session Card Anatomy (Google India — Technical Interview 1):*
     - Company & Round Header: `Google India — Software Engineer` | `Round 2: Technical Interview (Panel A)`
     - Status Pill: `OFFICIALLY_PUBLISHED` (Leaf Bright tag).
     - Date & Time Capsule:
       - Date: `Wednesday, 18 November 2026`
       - Time: `10:30:00 IST – 11:30:00 IST` (Explicit timezone).
     - Location / Virtual Link Box (Paper White Card inside pastel surface, 16px padding):
       - Venue Type: `Virtual Google Meet`
       - Link: `https://meet.google.com/xyz-qwer-abc` (Link activates 15 minutes prior to session).
       - Meeting Passcode: `SEC-9081`
     - Instructions: "Please have your institutional ID card ready and ensure stable internet connectivity. Code pairing will take place in Google Docs."
     - Assigned Panel: `Google Systems Engineering Panel A`
     - Action: **Add to Google Calendar** (Ghost Outline Button `#000000`, 32px height), **Download Hall Ticket** (Ghost Outline Button).
   - *Rescheduled Session Notice (If session was moved):*
     - Amber Warning Ribbon inside card: Cream `#faf7e8` surface, 1px solid Coral Pulse `#ff643b` border.
     - Headline: `SCHEDULE REVISED: TIME UPDATED`
     - Copy: "This session was rescheduled from 09:00:00 IST to 10:30:00 IST by the Placement Office on 2026-11-16. Reason: Recruiter panel flight delay."
3. **Official Selection Results Table (White Product Card `#ffffff`):**
   - Header: "Verified Recruitment Outcomes" (DM Sans 20px weight 600, `#0a3922`).
   - Notice: "Results displayed here are published exclusively for your record following formal employer confirmation."
   - Table Columns: Recruitment Drive | Round Evaluated | Employer Outcome Status | CTC Offered | Published Date | Official Memo.
   - Row 1 (Selection / Final Offer):
     - Drive: `Google India — Software Engineer`
     - Round: `Round 4: Googliness & Final HR`
     - Status Badge: `OFFER_EXTENDED` (Mint Wash `#d2f2e3` pill, Leaf Bright `#1dbf73` border, Canopy Green `#0a3922` text).
     - CTC: `₹32.0 LPA Gross (₹18.0 LPA Base)`
     - Published: `2026-11-20 18:30:00 IST`
     - Memo: `Official Letter of Intent issued by Placement Office`
   - Row 2 (Advanced to Next Round):
     - Drive: `Microsoft — Systems Engineer`
     - Round: `Round 1: Online Coding Test`
     - Status Badge: `ADVANCED_TO_NEXT_ROUND` (Sky Wash `#ccf0f8` tag).
     - Published: `2026-11-14 12:00:00 IST`
   - Row 3 (Not Selected):
     - Drive: `Deloitte — Technology Analyst`
     - Round: `Round 2: Technical Interview`
     - Status Badge: `NOT_SELECTED` (Cloud Gray `#f2f2f2` tag with Slate text).
     - Published: `2026-11-08 17:00:00 IST`

### 6. Interface States & Exact Copy
- **Normal Scheduled State:** Active session card displayed with clear time, Google Meet link, and preparation instructions.
- **No Scheduled Sessions State:**
  - Replacement Container: White Product Card `#ffffff`, 48px padding, centered.
  - Headline: "No upcoming interview sessions" (DM Sans 20px weight 600, `#0a3922`).
  - Copy: "You currently have no scheduled interview slots. Schedules are published by coordinators after registration and shortlisting rounds conclude."
- **Internal Draft Results Invisible State:**
  - Clarification notice: "Evaluations currently underway by employer panels remain internal drafts and are not displayed until formally published by the Placement Chair."
- **Session Cancelled State:**
  - Notice on Card: Peach Wash `#ffede8` surface.
  - Headline: "SESSION CANCELLED BY PLACEMENT OFFICE"
  - Copy: "Interview Panel A has been cancelled. A rescheduled slot will be assigned and published shortly."

### 7. Primary & Secondary Actions
- **Primary CTA:** **Join Virtual Interview** (Coral Filled Button `#ff643b`, 40px radius, white text — enabled 15 mins prior to slot).
- **Secondary CTA:** **Download Official Selection Memo** (Ghost Outline Button `#000000`, 40px radius).
- **Calendar Action:** **Add to Personal Calendar** (Ghost Outline Button, 32px height).

### 8. Data Displayed & Visual Formats
- Time intervals: `10:30:00 IST – 11:30:00 IST`.
- Gross CTC formatted in Lakhs: `₹32.0 LPA Gross`.
- Selection status badges rendered with high contrast.

### 9. Status Badges & Color Tokens
| Status Concept | Badge Text | Surface Fill (Token) | Text Color (Token) | Border Token |
| :--- | :--- | :--- | :--- | :--- |
| Schedule: Published | `OFFICIALLY_PUBLISHED`| Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Schedule: Rescheduled | `SESSION_RESCHEDULED` | Cream (`#faf7e8`) | Charcoal (`#333333`) | Coral Pulse (`#ff643b`) |
| Outcome: Selected | `OFFER_EXTENDED` | Mint Wash (`#d2f2e3`) | Canopy Green (`#0a3922`) | Leaf Bright (`#1dbf73`) |
| Outcome: Advanced | `ADVANCED` | Sky Wash (`#ccf0f8`) | Deep Teal (`#003642`) | None |
| Outcome: Rejected | `NOT_SELECTED` | Cloud Gray (`#f2f2f2`) | Slate (`#7a7a7a`) | Frost Gray (`#e0e0e0`) |
| Outcome: Waitlisted | `WAITLISTED` | Lilac Wash (`#fdf0ff`) | Indigo Bloom (`#460095`) | None |

### 10. Navigation, Breadcrumbs & Workflow Context
- **Top Nav Active Item:** "My Schedule & Results" (Leaf Bright `#1dbf73` bottom underline).
- **Context Transition:** Selection results link to institutional placement records and offer acceptance paperwork.
'''

print("Screens 15 to 20 defined.")
