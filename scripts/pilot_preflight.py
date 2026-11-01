"""Fail closed unless the selected environment satisfies every real-data pilot gate."""

from __future__ import annotations

import json

from placementos.core.config import settings
from placementos.services.operations import pilot_readiness_snapshot


def main() -> int:
    snapshot = pilot_readiness_snapshot(settings)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["real_data_pilot_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
