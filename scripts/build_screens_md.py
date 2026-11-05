"""
Master builder script to assemble screens.md for PlacementOS.
"""
import os
import sys

# Add script directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "screens_data"))

from coordinator_screens_1_to_5 import get_screens_1_to_5
from coordinator_screens_6_to_10 import get_screens_6_to_10
from coordinator_screens_11_to_14 import get_screens_11_to_14
from student_screens_15_to_20 import get_screens_15_to_20
from badge_dictionary import get_badge_dictionary

OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "screens.md"))

def get_header_and_principles():
    return '''# PlacementOS — Screen Specifications (`screens.md`)

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
'''

def build_screens_md():
    parts = [
        get_header_and_principles(),
        get_screens_1_to_5(),
        get_screens_6_to_10(),
        get_screens_11_to_14(),
        get_screens_15_to_20(),
        get_badge_dictionary()
    ]
    
    full_content = "\n".join(parts)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_content)
        
    print(f"screens.md successfully generated at: {OUTPUT_FILE}")
    print(f"Total characters: {len(full_content)}")
    print(f"Total lines: {full_content.count(chr(10)) + 1}")

if __name__ == "__main__":
    build_screens_md()
