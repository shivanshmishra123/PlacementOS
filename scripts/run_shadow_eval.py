#!/usr/bin/env python
"""P21 Shadow Mode Evaluation Script.

Runs the AI model interpreter against synthetic JD fixtures and compares
output with coordinator ground truth — in read-only shadow mode only.
Model suggestions are NEVER written to live drives.

Usage (from project root):
    uv run --project backend python scripts/run_shadow_eval.py

The script uses the CACHED model interpreter by default (zero live tokens).
Set PLACEMENTOS_MODEL_INTERPRETER_MODE=provider to use real Gemini API.
"""

from __future__ import annotations

import json
import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

os.environ.setdefault("PLACEMENTOS_MODEL_INTERPRETER_MODE", "cached")
os.environ.setdefault("PLACEMENTOS_ENVIRONMENT", "development")


def build_synthetic_extraction() -> object:
    """Build a minimal synthetic TextExtraction-like fixture for shadow eval."""
    from placementos.models.storage import TextExtraction

    jd_text = (
        "TechCorp Solutions – Campus Hiring 2027\n\n"
        "Role: Software Development Engineer (Full-Time)\n\n"
        "Location: Bangalore / Hyderabad (On-site)\n\n"
        "Compensation: 18.5 LPA (Cost to Company)\n\n"
        "Eligibility Criteria:\n"
        "- Branches: CSE, IT, ECE, EEE\n"
        "- Minimum CGPA: 7.0 on a 10-point scale\n"
        "- Graduation Year: 2027\n"
        "- Active Backlogs: 0\n\n"
        "Registration Deadline: 2026-12-15\n\n"
        "Selection Process: Online Assessment → Technical Interview → HR Interview"
    )

    return TextExtraction(
        id=None,
        source_artifact_id="shadow-eval-fixture-001",
        drive_id=None,
        extracted_text=jd_text,
        extraction_method="pdf_text_layer",
        extractor_version="pdfminer-v1",
        source_hash="shadow_fixture_hash",
        parser_version="1.0.0",
        locators=[
            {"locator_type": "paragraph", "paragraph_index": 0, "char_offset_start": 0, "char_offset_end": 40, "page_number": 1},
            {"locator_type": "paragraph", "paragraph_index": 4, "char_offset_start": 180, "char_offset_end": 320, "page_number": 1},
        ],
    )


# Coordinator-reviewed ground truth for this synthetic JD
GROUND_TRUTH: dict = {
    "company_name": "TechCorp Solutions",
    "role_title": "Software Development Engineer",
    "employment_type": "full_time",
    "location": "Bangalore / Hyderabad",
    "work_mode": "on_site",
    "registration_deadline": "2026-12-15",
    "eligibility_draft": {
        "minimum_cgpa": "7.0",
        "cgpa_scale": "10.0",
        "maximum_active_backlogs": 0,
        "allowed_branches": ["CSE", "IT", "ECE", "EEE"],
        "graduation_years": [2027],
    },
    "compensation": {
        "annual_ctc_minor_units": 185_000_000,
    },
}


def main() -> None:
    from placementos.services.models.factory import get_model_interpreter
    from placementos.services.shadow_mode import ShadowModeRunner, shadow_mode_active

    print("=" * 70)
    print("PlacementOS – P21 Shadow Mode Evaluation")
    print("=" * 70)

    mode = os.environ.get("PLACEMENTOS_MODEL_INTERPRETER_MODE", "cached")
    print(f"Model Interpreter Mode : {mode}")
    print(f"Shadow Mode Active     : {shadow_mode_active()}")
    print()

    # 1. Run model interpreter
    extraction = build_synthetic_extraction()
    interpreter = get_model_interpreter()
    print(f"Adapter ID             : {interpreter.adapter_id}")
    print(f"Prompt Version         : {interpreter.prompt_version}")
    print()

    print("Running model interpretation... ", end="", flush=True)
    draft = interpreter.interpret(extraction)
    print("done.")
    print()

    # 2. Run shadow comparison (read-only — never writes to any drive)
    runner = ShadowModeRunner(
        adapter_id=interpreter.adapter_id,
        prompt_version=interpreter.prompt_version,
    )
    result = runner.compare(
        model_facts=draft.facts,
        ground_truth=GROUND_TRUTH,
        source_text=extraction.extracted_text,
    )

    # 3. Print results
    print(f"Status                 : {result.status.value}")
    print(f"Precision              : {result.precision:.1%}")
    print(f"Recall                 : {result.recall:.1%}")
    print(f"Model hash             : {result.model_extraction_hash}")
    print(f"Ground truth hash      : {result.ground_truth_hash}")
    print()

    print("Field-level comparison:")
    print(f"  {'Field':<45} {'Match':<8} Detail")
    print(f"  {'-'*45} {'-'*7} {'-'*30}")
    for fc in result.field_comparisons:
        match_str = "✓ YES" if fc.matched else "✗ NO "
        detail = fc.discrepancy_detail or ""
        print(f"  {fc.field_path:<45} {match_str:<8} {detail[:60]}")

    if result.notes:
        print()
        print("Notes:")
        for note in result.notes:
            print(f"  ⚠  {note}")

    print()
    correction_summary = runner.correction_tracker.get_summary()
    print(f"Total corrections recorded : {correction_summary['total_corrections']}")
    if correction_summary["field_correction_rates"]:
        print("Per-field correction rates:")
        for fp, rate in correction_summary["field_correction_rates"].items():
            print(f"  {fp:<45} {rate:.1%}")

    print()
    print("Shadow evaluation output (JSON):")
    print(json.dumps(result.to_dict(), indent=2, default=str))

    print()
    print("=" * 70)
    if result.precision >= 0.70 and result.recall >= 0.70:
        print("✅  SHADOW EVALUATION PASSED — precision and recall meet 70%% thresholds.")
    else:
        print("⚠️  SHADOW EVALUATION: metrics below threshold — review prompt/model config.")
    print(
        "\nReminder: These results are shadow-only. No suggestions were written to any drive.\n"
        "Coordinator adoption requires explicit review and approval (INV-04)."
    )


if __name__ == "__main__":
    main()
