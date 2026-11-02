"""Run a non-destructive smoke gate against a running release candidate."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx


async def run(base_url: str) -> dict[str, object]:
    checks: dict[str, bool] = {}
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        health = await client.get("/health", headers={"X-Correlation-ID": "p10-release-smoke"})
        checks["liveness"] = health.status_code == 200 and health.json()["version"] == "0.12.0"
        checks["correlation_id"] = health.headers.get("x-correlation-id") == "p10-release-smoke"

        ready = await client.get("/ready")
        checks["dependencies_ready"] = ready.status_code == 200 and ready.json()["status"] == "ready"

        login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
        checks["synthetic_coordinator_login"] = login.status_code == 200
        readiness = await client.get("/api/v1/operations/pilot-readiness")
        checks["honest_pilot_gate"] = (
            readiness.status_code == 200
            and readiness.json()["status"] == "synthetic_demo_only"
            and readiness.json()["real_data_pilot_ready"] is False
        )
        checks["private_cache_control"] = readiness.headers.get("cache-control") == "private, no-store, max-age=0"
        operations = await client.get("/api/v1/operations/health")
        checks["operational_projection"] = operations.status_code == 200 and "alerts" in operations.json()

        await client.post("/api/v1/auth/dev-login", json={"persona": "student_a_apex"})
        denied = await client.get("/api/v1/operations/health")
        checks["student_operations_denied"] = denied.status_code == 403

    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", default="docs/evidence/p10-release-smoke.json")
    args = parser.parse_args()
    report = asyncio.run(run(args.base_url))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
