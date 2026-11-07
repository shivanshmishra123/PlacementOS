"""Verify live Google Gemini 2.0 Flash extraction on a sample campus recruitment JD.

This script executes exactly 1 real API call to test connectivity, structured output,
and provenance citations, and records the response for future zero-token replay.
"""

import os
import sys
import time
import uuid
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from placementos.core.config import settings
from placementos.models.storage import TextExtraction
from placementos.services.models.gemini_adapter import GeminiModelInterpreter
from placementos.services.models.cached_adapter import CachedModelInterpreter

SAMPLE_CAMPUS_JD = """Nexora Dynamics - Campus Recruitment 2026-2027

Position: Associate Software Engineer (Platform & AI Systems)
Location: Bengaluru / Hyderabad (Hybrid: 3 days in office, 2 days remote)
Employment Type: Full-time

About the Role:
We are seeking high-caliber engineering graduates to join our Core Platform engineering group. You will develop distributed cloud systems and AI orchestration pipelines using Python, TypeScript, and Go.

Eligibility & Academic Requirements:
- Permitted Engineering Disciplines: B.Tech / B.E. in Computer Science Engineering (CSE), Information Technology (IT), or Electronics & Communication Engineering (ECE).
- Academic Cutoff: Minimum aggregate CGPA of 7.50 out of 10.0 (or equivalent percentage) across all completed semesters.
- Backlog Policy: Maximum 0 active backlogs at the time of campus assessment and joining.
- Target Cohort: Class of 2027 graduating batch only.

Compensation & Benefits:
- Fixed Compensation: INR 16,50,000 per annum
- Performance Variable / Joining Bonus: INR 2,00,000
- Total CTC: 18.5 LPA (Eighteen Lakh Fifty Thousand per annum)

Important Dates & Instructions:
- Campus Registration Deadline: 2026-11-25
- Online Assessment Schedule: First week of December 2026
"""


def main():
    print("=" * 60)
    print("PlacementOS: Live Google Gemini 2.0 Flash Extraction Verification")
    print("=" * 60)

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("ERROR: PLACEMENTOS_GEMINI_API_KEY is not configured in .env")
        sys.exit(1)

    print(f"Provider: Google Gemini ({settings.MODEL_ID or 'gemini-2.0-flash'})")
    print(f"Key configured: {'*' * (len(api_key) - 6) + api_key[-6:]}")

    # Prepare extraction text with paragraphs
    paragraphs = [p.strip() for p in SAMPLE_CAMPUS_JD.split("\n\n") if p.strip()]
    locators = []
    cursor = 0
    for idx, p in enumerate(paragraphs):
        start = SAMPLE_CAMPUS_JD.index(p, cursor)
        end = start + len(p)
        locators.append({
            "locator_type": "paragraph",
            "paragraph_index": idx,
            "page_number": 1,
            "char_offset_start": start,
            "char_offset_end": end,
            "preview": p[:80],
        })
        cursor = end

    extraction = TextExtraction(
        id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        institution_id=uuid.uuid4(),
        parser_version="test-v1",
        extraction_method="pypdf",
        text_hash_sha256="sample_campus_jd_hash_123",
        extracted_text=SAMPLE_CAMPUS_JD,
        page_count=1,
        is_empty_or_scanned=False,
        status="completed",
        locators=locators,
    )

    interpreter = GeminiModelInterpreter(api_key=api_key)

    print("\nSending 1 structured extraction request to Gemini 2.0 Flash...")
    start_time = time.time()
    draft = interpreter.interpret(extraction)
    elapsed_ms = (time.time() - start_time) * 1000

    print(f"\n[OK] Response received in {elapsed_ms:.1f} ms!")
    print("-" * 60)
    print("Extracted Structured Facts:")
    print(f"  Company Name:    {draft.facts.get('company_name')}")
    print(f"  Role Title:      {draft.facts.get('role_title')}")
    print(f"  Location:        {draft.facts.get('location')}")
    print(f"  Work Mode:       {draft.facts.get('work_mode')}")
    print(f"  Compensation:    {draft.facts.get('compensation', {}).get('source_wording')} (INR {draft.facts.get('compensation', {}).get('annual_ctc_minor_units')})")

    elig = draft.facts.get("eligibility_draft", {})
    print(f"  Allowed Branches:{elig.get('allowed_branches')}")
    print(f"  Minimum CGPA:    {elig.get('minimum_cgpa')} (Scale: {elig.get('cgpa_scale')})")
    print(f"  Graduation Years:{elig.get('graduation_years')}")
    print(f"  Max Backlogs:    {elig.get('maximum_active_backlogs')}")
    print(f"  Deadline:        {draft.facts.get('registration_deadline')}")

    print("-" * 60)
    print(f"Traceable Evidence Citations ({len(draft.evidence)}):")
    for ev in draft.evidence:
        print(f"  • [{ev.get('field_path')}] §{ev.get('paragraph_index')}: \"{ev.get('excerpt')}\"")

    print("-" * 60)
    print(f"Clarifications ({len(draft.clarifications)}):")
    for cl in draft.clarifications:
        print(f"  • [{cl.get('reason_code')}] {cl.get('field_path')}: {cl.get('detail')}")

    # Record response to cache for zero-token future replays
    cached_adapter = CachedModelInterpreter()
    cached_adapter.record(extraction, draft)
    print(f"\n[OK] Successfully recorded golden response to local cache for 0-token replay.")
    print("=" * 60)


if __name__ == "__main__":
    main()
