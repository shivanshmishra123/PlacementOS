# PlacementOS — Screen Specifications (`screens.md`)

> **Status:** Authoritative Screen-by-Screen UI Specification for Google Stitch UI Generation  
> **Target Platform:** Web (Desktop 1280px standard canvas, responsive down to tablet)  
> **Companion Document:** `DESIGN.md` (Visual Style Reference, Color Tokens, Typography, and Components)  
> **Domain Standards:** `PROJ_SPECIFICATION.md`, `Architecture.md`, `UI.md`, `AGENTS.md`  

---

## 1. Introduction and Stitch Generation Guidance

This document defines the comprehensive, production-grade interface specifications for **PlacementOS**, a mission-critical campus recruitment operations platform designed for placement coordinators and university students.

### How to Use with Google Stitch & `DESIGN.md`
1. **Primary Directive:** Pair this file directly with `DESIGN.md`. All visual tokens (colors, font-weights, border-radii, spacing) must reference the canonical token names established in `DESIGN.md`.
2. **Surface Depth Over Drop Shadows:** Elevation in PlacementOS is achieved strictly through flat surface contrast (Lavender Mist canvas `#eee2ff` → Paper White product cards `#ffffff` → Pastel feature cards `#d2f2e3` / `#ccf0f8` / `#e4f7ee` / `#fdf0ff` / `#ffede8` / `#faf7e8` → Deep Canopy Green hero sections `#0a3922`). **Never use drop shadows or outer glows.**
3. **Typography Rule:** Use **DM Sans** exclusively across all scales from 12px captions to 116px display headlines. Apply `font-feature-settings: "ss03"` site-wide. Apply tight tracking (`-0.028em` for >=52px, `-0.019em` for 32–48px, normal for body).
4. **Action Hierarchy:**
   - **Primary CTAs:** Use **Coral Filled Button** (`#ff643b` Coral Pulse, 40px radius, white text). Reserve this for the single most consequential primary forward action on any panel.
   - **Secondary Actions:** Use **Ghost Outline Button** (1px solid border `#000000` on light surfaces or `#ffffff` on dark surfaces, transparent background, 40px radius).
   - **Destructive Actions:** Use **Ghost Outline Button** with `#ff643b` border and text, or filled `#ff643b` with confirmation dialogs.
5. **Separation of Concerns:**
   - AI outputs (JD extraction, draft emails, recovery plans) are always marked with distinct suggestion tags and source evidence locators.
   - Academic eligibility is calculated **strictly deterministically**; no LLM response or free-text override can alter eligibility.
   - Statuses for eligibility, document readiness, registration, schedule assignment, and employer outcomes are **strictly independent** and must never overwrite one another.

---

## 2. Global UI Principles and Token Mapping

### 2.1 Design Token Reference Table

| Token Name | Hex Value | Role in PlacementOS | Approved Usage |
| :--- | :--- | :--- | :--- |
| **Canopy Green** | `#0a3922` | Dominant Brand Surface & Primary Headings | Hero banners, dark section bands, primary typography on light/pastel cards, coordinator active sidebar state |
| **Coral Pulse** | `#ff643b` | Exclusive Primary Action CTA | Primary conversion buttons (e.g., "Submit Registration", "Run Evaluation", "Freeze & Submit Proposal", "Commit Import") |
| **Indigo Bloom** | `#460095` | Secondary Brand Accent & Toolkit Sections | Secondary headings, workflow checkpoint banners, revision lineage indicators |
| **Leaf Bright** | `#1dbf73` | Positive Status & Focused Outlines | `ELIGIBLE`, `READY`, `VERIFIED`, `PASSED`, `CONNECTED` status badge pills and active toggle accents |
| **Deep Teal** | `#003642` | Informational Tag Accents & Secondary Headings | Filter category chips, table column headers, audit metadata labels |
| **Orchid Tint** | `#f3b3fe` | Decorative Tag Accent | Batch cycle chips, special event tags |
| **Sky Signal** | `#00b4dc` | Data Visualization & Chart Elements | Pipeline progress bars, completion meters, queue health dots |
| **Aubergine** | `#47264c` | Body Headings on Lavender Mist | Subheadings on lavender canvas, rich body text pairing with Indigo Bloom |
| **Ink Black** | `#000000` | Primary Typography & Hairline Dividers | 1px dividers, high-contrast table cell text, icon strokes |
| **Paper White** | `#ffffff` | Primary Product Card Surfaces | Data tables, form input containers, code/JSON inspectors, interactive modals |
| **Ash** | `#a6a6a6` | Secondary Borders & Disabled Elements | Form placeholder text, disabled buttons, inactive tab dividers |
| **Slate** | `#7a7a7a` | Metadata & Caption Typography | Timestamps, SHA-256 hashes, subtext footnotes, table row counts |
| **Graphite** | `#3d3d3d` | High-Contrast Secondary Text | Card body copy, predicate labels, list descriptions |
| **Charcoal** | `#333333` | Card Headlines on Pastel Surfaces | H3/H4 card section headers on pastel washes |
| **Frost Gray** | `#e0e0e0` | Subtle Card Separators | Hairline internal borders in White Product Cards |
| **Cloud Gray** | `#f2f2f2` | Neutral Alternating Row Fills | Table stripe alternating rows, disabled background containers |
| **Lavender Mist** | `#eee2ff` | Global Page Canvas Background | Atmospheric page canvas behind all cards in Coordinator and Student portals |
| **Mint Wash** | `#d2f2e3` | Positive Outcome Pastel Card | Success metric cards, `ELIGIBLE` summary cards, verified student profile cards |
| **Sky Wash** | `#ccf0f8` | Informational Pastel Card | Job intake cards, schedule session cards, document upload containers |
| **Sage Wash** | `#e4f7ee` | Operational Audit Pastel Card | Pre-closure checklist cards, document requirements configuration panels |
| **Lilac Wash** | `#fdf0ff` | Workflow & Exception Pastel Card | LangGraph state cards, recovery plan step cards, approval review panels |
| **Peach Wash** | `#ffede8` | Alert & Ineligible Pastel Card | `INELIGIBLE` summary cards, high-severity exception cards, operational hold alerts |
| **Cream** | `#faf7e8` | Review & Warning Pastel Card | `NEEDS_REVIEW` summary cards, unverified evidence cards, draft proposal alerts |

### 2.2 Typography Scale (DM Sans, `ss03` Enabled)

- **Display XL (116px, weight 600, lh 0.89, ls -0.028em):** Large operational dashboard numbers, hero heroics.
- **Display (72px, weight 600, lh 1.05, ls -0.028em):** Major metric summaries (e.g., "312" Eligible students).
- **Heading LG (48px, weight 600, lh 1.14, ls -0.019em):** Portal section titles, modal major headlines.
- **Heading (32px, weight 600, lh 1.20, ls -0.019em):** Screen titles, primary card headers.
- **Heading SM (24px, weight 600, lh 1.30, ls 0):** Subsection titles, panel headers, drawer headers.
- **Subheading (20px, weight 500, lh 1.33, ls 0):** Field group headers, student role headers.
- **Body LG (18px, weight 400, lh 1.40, ls 0):** Hero introductory descriptions, primary banner text.
- **Body (16px, weight 400, lh 1.38, ls 0):** Standard table text, card body copy, form input text.
- **Body SM (14px, weight 500, lh 1.38, ls 0):** Table headers, secondary metadata, breadcrumbs, tab labels.
- **Caption (12px, weight 600, lh 1.20, ls 0):** Pill tag chips, status badges, timestamp labels, hash locators.

---

## 3. Global Navigation Architecture

### 3.1 Coordinator Navigation Shell
The Coordinator Portal uses a dual-structure navigation: a persistent left sidebar paired with a top contextual utility bar.

```
+-------------------------------------------------------------------------------------------------------------+
| SIDEBAR (240px, #ffffff)       | TOP BAR (Height 64px, #ffffff, 1px Frost Gray border-bottom)              |
| [PlacementOS Brand Monogram]   | Apex Institute of Technology | [Cycle: 2026-27] | [SYNTHETIC DEMO Pill]   |
|                                |----------------------------------------------------------------------------|
| * Dashboard (/coordinator)     | MAIN CANVAS (1040px max-width, #eee2ff Lavender Mist)                     |
| * Drives (/coordinator/drives) |                                                                            |
| * Students (/coordinator/stud.)| [Breadcrumb: Drives > Google SWE > Review]                                |
| * Approvals (/coordinator/appr)|                                                                            |
| * Exceptions (/coord./except.) |                                                                            |
| * Integrations (/coord./integr)|                                                                            |
| * Operations (/coord./ops)     |                                                                            |
+--------------------------------+----------------------------------------------------------------------------+
```

- **Sidebar Container:** Fixed 240px width, Paper White `#ffffff` background with 1px Frost Gray `#e0e0e0` right border.
- **Sidebar Links:** Height 44px, 16px horizontal padding, 12px border-radius. Active item receives Canopy Green `#0a3922` fill with Paper White text and Leaf Bright `#1dbf73` left accent bar. Inactive items use Ink Black `#000000` text with `#3d3d3d` iconography.
- **Top Utility Bar:** Full width across canvas, 64px height, Paper White `#ffffff` background. Contains:
  - University Identity: "Apex Institute of Technology" (Heading SM 16px weight 600 in `#0a3922`).
  - Active Placement Cycle Dropdown: "Academic Year 2026–27" (Pill Tag Chip `#ccf0f8`).
  - Environment Gating Pill: "SYNTHETIC DEMO" (Mint Wash `#d2f2e3` background, `#0a3922` text, 9999px radius) or "PRODUCTION" (Canopy Green `#0a3922` with `#ffffff` text).
  - Coordinator Profile & Session: Avatar circle + "Dr. K. Sharma (Placement Chair)" + Logout link.

### 3.2 Student Navigation Shell
The Student Portal uses a streamlined, distraction-free top navigation bar.

```
+-------------------------------------------------------------------------------------------------------------+
| TOP NAVIGATION BAR (Height 72px, Paper White #ffffff, 1280px Centered Container)                            |
| [PlacementOS Logo]  | Opportunities  |  My Schedule & Results  |  My Profile  |  Help  | [2023CS104 - Rahul]|
+-------------------------------------------------------------------------------------------------------------+
| MAIN STUDENT CANVAS (1280px Centered Container, #eee2ff Lavender Mist Background)                           |
+-------------------------------------------------------------------------------------------------------------+
```

- **Sticky Top Bar:** Paper White `#ffffff`, 72px height, full width with 1280px centered content container.
- **Nav Links:** DM Sans 16px weight 500, Ink Black `#000000` text. Active link features a 3px Leaf Bright `#1dbf73` bottom underline.
- **Student Profile Capsule:** Right-aligned pill tag chip (`#d2f2e3` Mint Wash) showing Student Roll Number (`2023CS104`) and Student Name (`Rahul Verma`).

---

## 4. Screen-by-Screen Specifications

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

## SCREEN 6: Participation Management (`/coordinator/drives/[id]/participation`)

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

## SCREEN 11: Student Roster (`/coordinator/students`)

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

---

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

---

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
