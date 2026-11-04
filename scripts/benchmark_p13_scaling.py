"""Measure the P13 drive-index projection under mixed-institution load."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from placementos.core.config import settings
from placementos.services.session import SessionManager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

INDEXES = {
    "ix_drives_inst_created_id",
    "ix_drives_inst_creator_created",
    "ix_drives_inst_assignee_created",
    "ix_drive_assignments_inst_member_drive",
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction) - 1))
    return ordered[index]


def summarize(samples: list[tuple[float, int, int, bool]]) -> dict[str, Any]:
    latencies = [sample[0] for sample in samples]
    statuses = [sample[1] for sample in samples]
    return {
        "status_counts": {str(code): statuses.count(code) for code in sorted(set(statuses))},
        "latency_ms": {
            "median": round(statistics.median(latencies), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2),
        },
        "median_payload_bytes": round(statistics.median(sample[2] for sample in samples)),
        "tenant_isolation_violations": sum(not sample[3] for sample in samples),
    }


async def index_inventory() -> dict[str, Any]:
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'public' AND indexname = ANY(:names)"
                    ),
                    {"names": sorted(INDEXES)},
                )
            ).scalars()
            present = set(rows)
    finally:
        await engine.dispose()
    return {
        "required": sorted(INDEXES),
        "present": sorted(present),
        "passed": present == INDEXES,
    }


async def benchmark(base_url: str, ordinary_concurrency: int) -> dict[str, Any]:
    timeout = httpx.Timeout(60)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        sessions: list[tuple[str, str]] = []
        for index in range(100):
            persona = "coord_apex" if index % 2 == 0 else "coord_beacon"
            login = await client.post("/api/v1/auth/dev-login", json={"persona": persona})
            login.raise_for_status()
            body = login.json()
            sessions.append((body["session_token"], body["user"]["institution_id"]))
        client.cookies.clear()

        async def request_once(
            endpoint: str, session: tuple[str, str]
        ) -> tuple[float, int, int, bool]:
            token, institution_id = session
            started = time.perf_counter()
            response = await client.get(
                endpoint,
                params={"limit": 20},
                headers={"Authorization": f"Bearer {token}"},
            )
            elapsed = (time.perf_counter() - started) * 1000
            body = response.json() if response.is_success else {}
            isolated = all(
                item.get("institution_id") == institution_id for item in body.get("items", [])
            )
            return elapsed, response.status_code, len(response.content), isolated

        async def sample_endpoint(endpoint: str) -> dict[str, Any]:
            semaphore = asyncio.Semaphore(ordinary_concurrency)

            async def ordinary(session: tuple[str, str]):
                async with semaphore:
                    return await request_once(endpoint, session)

            ordinary_samples = await asyncio.gather(
                *(ordinary(session) for session in sessions)
            )
            burst_samples = await asyncio.gather(
                *(request_once(endpoint, session) for session in sessions)
            )
            return {
                "endpoint": endpoint,
                "ordinary": summarize(ordinary_samples),
                "synchronized_100_request_burst": summarize(burst_samples),
            }

        legacy = await sample_endpoint("/api/v1/drives")
        optimized = await sample_endpoint("/api/v1/drive-summaries")

    for token, _institution_id in sessions:
        await SessionManager.revoke_session(token)

    legacy_p95 = legacy["synchronized_100_request_burst"]["latency_ms"]["p95"]
    optimized_p95 = optimized["synchronized_100_request_burst"]["latency_ms"]["p95"]
    improvement = round((legacy_p95 - optimized_p95) / legacy_p95 * 100, 2)
    endpoints_passed = all(
        measurement["ordinary"]["status_counts"] == {"200": 100}
        and measurement["synchronized_100_request_burst"]["status_counts"] == {"200": 100}
        and measurement["ordinary"]["tenant_isolation_violations"] == 0
        and measurement["synchronized_100_request_burst"]["tenant_isolation_violations"] == 0
        for measurement in (legacy, optimized)
    )
    return {
        "logical_sessions": 100,
        "institution_mix": {"apex-tech": 50, "beacon-state": 50},
        "ordinary_peak_inflight_requests": ordinary_concurrency,
        "before_legacy_full_projection": legacy,
        "after_summary_projection": optimized,
        "burst_p95_improvement_percent": improvement,
        "ordinary_target_p95_ms": 500,
        "passed": bool(
            endpoints_passed
            and optimized["ordinary"]["latency_ms"]["p95"] < 500
            and optimized_p95 < legacy_p95
        ),
    }


async def run(args: argparse.Namespace) -> int:
    api = await benchmark(args.base_url, args.api_concurrency)
    indexes = await index_inventory()
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "release_version": settings.RELEASE_VERSION,
        "scope": "synthetic local mixed-institution drive-index projection",
        "api": api,
        "indexes": indexes,
        "passed": bool(api["passed"] and indexes["passed"]),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-concurrency", default=2, type=int)
    parser.add_argument("--output", default="docs/evidence/p13-scaling.json")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
