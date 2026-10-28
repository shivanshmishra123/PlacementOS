# PlacementOS: Synthetic Acceptance Fixtures Inventory

> Phase P00 Deliverable: P00-T05  
> Date: 29 October 2026  
> Status: Frozen Fixture Inventory (No Real Personal Data)

---

## 1. Overview and Privacy Guarantee

This inventory defines the canonical synthetic test dataset for PlacementOS. In compliance with Invariant `INV-10` and Section 22.1 of the Product Specification, **no real personal or institutional data is used**. All names, email addresses, student IDs, and company names are purely fictional.

---

## 2. Institutional Fixtures & Isolation Boundary

```
┌─────────────────────────────────────────────────────────────┐
│                 SYNTHETIC INSTITUTIONS                      │
├──────────────────────────────┬──────────────────────────────┤
│ Apex Institute of Technology │ Beacon State University      │
│ ID: inst-apex-01             │ ID: inst-beacon-02           │
│ Slug: apex-tech              │ Slug: beacon-state           │
│ Timezone: Asia/Kolkata       │ Timezone: Asia/Kolkata       │
│ Domain: @apex.edu            │ Domain: @beacon.edu          │
└──────────────────────────────┴──────────────────────────────┘
```

### Institutional Personas:
1. **Apex Placement Coordinator (`coord_apex`):**
   - Name: `Priya Sharma`
   - Email: `priya.sharma@apex.edu`
   - Role: `placement_coordinator`
   - Capabilities: `[drive_create, drive_edit, rule_approve, proposal_decide, schedule_publish, result_publish, export_generate]`
2. **Apex Administrator (`admin_apex`):**
   - Name: `Rajesh Verma`
   - Email: `rajesh.verma@apex.edu`
   - Role: `institution_admin`
   - Capabilities: `[member_manage, config_manage, audit_view]`
3. **Beacon Placement Coordinator (`coord_beacon`):**
   - Name: `Ananya Das`
   - Email: `ananya.das@beacon.edu`
   - Role: `placement_coordinator`
   - Test Purpose: Negative testing of cross-institutional object access (`INV-06`).

---

## 3. Section 10.2 Synthetic Cohort Dataset

This cohort tests every path of the deterministic eligibility aggregation engine. All records have verified graduation year `2027` and grading scale `10.00` unless explicitly annotated.

### Approved Test Policy:
- **Allowed Branches:** `["CSE", "IT"]`
- **Minimum CGPA:** `7.50` (on 10.00 scale)
- **Graduation Year:** `2027`
- **Max Active Backlogs:** `0`

### Cohort Evaluation Truth Table:

| Student ID | Roll Number | Student Name | Branch | CGPA | Scale | Active Backlogs | Verification State | Expected Outcome | Expected Predicate Finding Codes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `stu-001` | `2023-CS-001` | `Student A` | `CSE` | `8.20` | `10.00` | `0` | `verified` | **`eligible`** | All predicates pass |
| `stu-002` | `2023-EC-002` | `Student B` | `ECE` | `8.80` | `10.00` | `0` | `verified` | **`ineligible`** | `BRANCH_NOT_ALLOWED` |
| `stu-003` | `2023-IT-003` | `Student C` | `IT` | `7.20` | `10.00` | `0` | `verified` | **`ineligible`** | `CGPA_BELOW_MINIMUM` |
| `stu-004` | `2023-CS-004` | `Student D` | `CSE` | `8.00` | `10.00` | `1` | `verified` | **`ineligible`** | `ACTIVE_BACKLOGS_EXCEED_LIMIT` |
| `stu-005` | `2023-IT-005` | `Student E` | `IT` | `7.90` | `10.00` | `null` | `verified` | **`needs_review`** | `REQUIRED_VALUE_MISSING: active_backlogs` |
| `stu-006` | `2023-CS-006` | `Student F` | `CSE` | `7.50` | `10.00` | `0` | `verified` | **`eligible`** | Exact equality passes |
| `stu-007` | `2023-IT-007` | `Student G` | `IT` | `7.49` | `10.00` | `0` | `verified` | **`ineligible`** | `CGPA_BELOW_MINIMUM` (no rounding) |
| `stu-008` | `2023-EC-008` | `Student H` | `ECE` | `8.80` | `10.00` | `null` | `verified` | **`needs_review`** | `BRANCH_NOT_ALLOWED` + `REQUIRED_VALUE_MISSING` |
| `stu-009` | `2023-CS-009` | `Student I` | `CSE` | `8.20` | `10.00` | `0` | `unverified` | **`needs_review`** | `RECORD_UNVERIFIED` |
| `stu-010` | `2023-CS-010` | `Student J` | `CSE` | `3.80` | `4.00` | `0` | `verified` | **`needs_review`** | `SCALE_UNSUPPORTED` |

### Cross-Institution Collision Test Case:
- **Beacon Student (`stu-beacon-001`):** Roll number `2023-CS-001` in institution `inst-beacon-02`. Must coexist without collision with Apex Student A (`2023-CS-001` in `inst-apex-01`).

---

## 4. Job Description (JD) Fixtures

### 4.1 Normal JD Fixture (`jd-normal-nexora.txt` / `.pdf`)
```text
Company: Nexora Technologies Pvt. Ltd.
Role: Software Development Engineer (SDE-1)
Employment Type: Full-time
Location: Bengaluru, India (Hybrid)
Compensation: CTC INR 14.50 LPA (Fixed: 12.00 LPA, Performance Bonus: 2.50 LPA)
Eligibility Criteria:
- Degree: B.Tech graduating in 2027
- Eligible Branches: Computer Science and Engineering (CSE), Information Technology (IT)
- Academic Threshold: Minimum 7.50 CGPA on a 10-point scale
- Backlog Policy: No active backlogs allowed at the time of registration
Selection Process:
1. Online Coding Assessment (90 mins)
2. Technical Interview Round 1
3. Technical Interview Round 2
4. HR & Culture Fit Interview
Registration Deadline: 2026-11-05 23:59:59 IST (Asia/Kolkata)
Required Documents: Updated Resume (PDF), Semester Marksheets (PDF), College ID Card (PDF)
```
- **Expected Outcome:** Clean extraction, zero blocking clarifications, valid policy draft compilation.

### 4.2 Ambiguous JD Fixture (`jd-ambiguous-strata.txt` / `.pdf`)
```text
Company: StrataCloud Systems
Role: Graduate Systems Engineer
Compensation: Up to 18 LPA depending on performance
Branches: Circuit branches or equivalent computing disciplines
Cutoff: 7.0 CGPA or 65% aggregate; candidates with 7.5 CGPA preferred
Backlogs: Active backlogs will be reviewed case by case
Registration Deadline: 5th November 2026
```
- **Ambiguities Identified:**
  1. `Cutoff`: Ambiguous dual cutoff (7.0 vs 7.5 preferred, percentage conversion missing).
  2. `Branches`: "Circuit branches or equivalent" requires explicit branch mapping review.
  3. `Backlogs`: "Case by case" backlog rule is unsupported by baseline predicates.
  4. `Registration Deadline`: Date only provided; missing cutoff time and timezone.
- **Expected Outcome:** Blocks rule approval (`requires_clarification: true`), creates explicit clarification tasks for coordinator.

---

## 5. Document Validation & Attack Fixtures

| Fixture Name | Characteristics | Target Validation Check | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `valid-resume.pdf` | Clean, 1-page PDF, 150 KB, readable text stream, valid PDF header `%PDF-1.7` | Standard validation (`FR-DOC-04`) | `DocumentValidationStatus.passed` |
| `corrupt-header.pdf` | Truncated byte stream, missing EOF marker `%%EOF` | Integrity & structural validation | `DocumentValidationStatus.failed` (`PDF_CORRUPT`) |
| `encrypted-password.pdf`| Valid PDF encrypted with standard user password | Password-protection check | `DocumentValidationStatus.failed` (`PDF_ENCRYPTED`) |
| `fake-extension.pdf` | ELF/PE executable file renamed to `.pdf` (magic bytes `MZ...` or `\x7fELF`) | Sniffed MIME / magic signature check | `DocumentValidationStatus.quarantined` (`MIME_MISMATCH_SUSPICIOUS`) |
| `oversized-file.pdf` | Valid PDF inflated to 25 MiB (exceeding 10 MiB limit) | Payload size guard | HTTP 413 / `DocumentValidationStatus.failed` (`SIZE_EXCEEDED`) |
| `decompression-bomb.docx`| Small 50 KB ZIP file containing XML that expands to 10 GB | Safe parser container bounds | `DocumentValidationStatus.failed` (`RESOURCE_LIMIT_EXCEEDED`) |
