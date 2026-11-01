"""Measure the P10 deterministic cohort and authenticated API latency envelope."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from placementos.core.config import settings
from placementos.services.eligibility_engine import AcademicFacts, evaluate
from placementos.services.session import SessionManager

POLICY = {
    "schema_version": 1,
    "engine_contract": "eligibility-v1",
    "aggregation": "required_unknown_first_then_failure",
    "evidence_revision": "p10-envelope",
    "branch": {"mode": "required", "operator": "in", "values": ["CSE", "IT"]},
    "cgpa": {"mode": "required", "operator": "gte", "minimum": "7.50", "scale": "10.00"},
    "graduation_year": {"mode": "required", "operator": "in", "values": [2027]},
    "active_backlogs": {"mode": "required", "operator": "lte", "maximum": 0},
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction) - 1))
    return ordered[index]


def benchmark_eligibility() -> dict[str, object]:
    cohort = [
        AcademicFacts(
            branch="CSE" if index % 4 else "ECE",
            cgpa=Decimal("8.20") if index % 7 else Decimal("7.20"),
            cgpa_scale=Decimal("10.00"),
            graduation_year=2027,
            active_backlogs=None if index % 31 == 0 else (1 if index % 19 == 0 else 0),
            is_verified=index % 47 != 0,
            academic_revision_id=f"p10-{index}",
        )
        for index in range(5_000)
    ]
    drive_durations: list[float] = []
    outcome_counts = {"eligible": 0, "ineligible": 0, "needs_review": 0}
    for _drive in range(20):
        started = time.perf_counter()
        for record in cohort:
            decision = evaluate(POLICY, record)
            outcome_counts[decision.outcome] += 1
        drive_durations.append((time.perf_counter() - started) * 1000)
    return {
        "students": len(cohort),
        "drives": 20,
        "evaluations": len(cohort) * 20,
        "duration_ms": {
            "min": round(min(drive_durations), 2),
            "median": round(statistics.median(drive_durations), 2),
            "p95": round(percentile(drive_durations, 0.95), 2),
            "max": round(max(drive_durations), 2),
        },
        "outcomes_across_all_drives": outcome_counts,
        "target_each_drive_ms": 60_000,
        "passed": max(drive_durations) < 60_000,
    }


async def benchmark_api(base_url: str, ordinary_concurrency: int) -> dict[str, object]:
    timeout = httpx.Timeout(30)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        tokens: list[str] = []
        for _ in range(100):
            login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
            login.raise_for_status()
            tokens.append(login.json()["session_token"])
        client.cookies.clear()

        async def request_once(token: str) -> tuple[float, int, int]:
            started = time.perf_counter()
            response = await client.get(
                "/api/v1/drives",
                params={"limit": 20},
                headers={"Authorization": f"Bearer {token}"},
            )
            elapsed = (time.perf_counter() - started) * 1000
            total = int(response.json().get("total", 0)) if response.is_success else 0
            return elapsed, response.status_code, total

        semaphore = asyncio.Semaphore(ordinary_concurrency)

        async def ordinary_request(token: str) -> tuple[float, int, int]:
            async with semaphore:
                return await request_once(token)

        ordinary = await asyncio.gather(*(ordinary_request(token) for token in tokens))
        burst = await asyncio.gather(*(request_once(token) for token in tokens))

    for token in tokens:
        await SessionManager.revoke_session(token)

    latencies = [item[0] for item in ordinary]
    statuses = [item[1] for item in ordinary]
    burst_latencies = [item[0] for item in burst]
    burst_statuses = [item[1] for item in burst]
    observed_drives = max(item[2] for item in ordinary)
    return {
        "logical_sessions": 100,
        "ordinary_peak_inflight_requests": ordinary_concurrency,
        "endpoint": "/api/v1/drives?limit=20",
        "observed_drive_count": observed_drives,
        "status_counts": {str(code): statuses.count(code) for code in sorted(set(statuses))},
        "ordinary_latency_ms": {
            "median": round(statistics.median(latencies), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2),
        },
        "synchronized_100_request_burst": {
            "status_counts": {
                str(code): burst_statuses.count(code) for code in sorted(set(burst_statuses))
            },
            "latency_ms": {
                "median": round(statistics.median(burst_latencies), 2),
                "p95": round(percentile(burst_latencies, 0.95), 2),
                "max": round(max(burst_latencies), 2),
            },
            "classification": "stress observation; not the ordinary-load release gate",
        },
        "target_p95_ms": 500,
        "passed": all(code == 200 for code in statuses) and percentile(latencies, 0.95) < 500,
    }


async def run(args: argparse.Namespace) -> int:
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "environment": {
            "release_version": settings.RELEASE_VERSION,
            "model_mode": settings.MODEL_INTERPRETER_MODE,
            "model_call_cap_per_drive": settings.MODEL_MAX_CALLS_PER_DRIVE,
            "model_input_token_cap_per_drive": settings.MODEL_MAX_INPUT_TOKENS_PER_DRIVE,
            "max_upload_bytes": settings.MAX_UPLOAD_BYTES,
            "max_pdf_pages": settings.MAX_PDF_PAGES,
            "max_extracted_text_chars": settings.MAX_EXTRACTED_TEXT_CHARS,
        },
        "eligibility": benchmark_eligibility(),
        "api": await benchmark_api(args.base_url, args.api_concurrency),
        "cost_note": "Eligibility is deterministic and makes zero model calls; model usage is bounded by configuration.",
    }
    report["passed"] = bool(report["eligibility"]["passed"] and report["api"]["passed"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-concurrency", default=2, type=int)
    parser.add_argument("--output", default="docs/evidence/p10-performance.json")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
