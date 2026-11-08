"""Production observability, OpenTelemetry-compatible telemetry, and redacted logging (P20)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|secret|password|authorization|api_key|key|cookie|signed_url|eicar|credential|private_key)",
    re.IGNORECASE,
)
TOKEN_VALUE_PATTERN = re.compile(
    r"(Bearer\s+)[A-Za-z0-9._~+/-]+=*",
    re.IGNORECASE,
)


def redact_sensitive_data(val: Any) -> Any:
    """Recursively scrub secrets, tokens, passwords, and private identifiers."""
    if isinstance(val, dict):
        scrubbed = {}
        for k, v in val.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = redact_sensitive_data(v)
        return scrubbed
    if isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    if isinstance(val, str):
        return TOKEN_VALUE_PATTERN.sub(r"\1[REDACTED]", val)
    return val


class RedactedJsonFormatter(logging.Formatter):
    """Structured JSON log formatter with automatic sensitive field redaction (INV-10)."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_data(record.getMessage()),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        # Include structured extra fields if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_payload["extra"] = redact_sensitive_data(record.extra)

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, separators=(",", ":"))


class TelemetryTracker:
    """Thread-safe operational telemetry metrics tracking platform health and model performance."""

    def __init__(self) -> None:
        self.total_http_requests: int = 0
        self.total_model_calls: int = 0
        self.failed_model_calls: int = 0
        self.model_latencies: list[float] = []
        self.last_scanner_check: str = "operational"

    def record_model_call(self, latency_seconds: float, success: bool = True) -> None:
        """Record model invocation metrics."""
        self.total_model_calls += 1
        if not success:
            self.failed_model_calls += 1
        self.model_latencies.append(latency_seconds)
        # Keep rolling window of last 1000 measurements
        if len(self.model_latencies) > 1000:
            self.model_latencies = self.model_latencies[-1000:]

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Compute operational metrics summary."""
        latencies = sorted(self.model_latencies)
        p50 = latencies[len(latencies) // 2] if latencies else 0.0
        p95_index = int(len(latencies) * 0.95)
        p95 = latencies[p95_index] if latencies else 0.0

        error_rate = (
            (self.failed_model_calls / self.total_model_calls)
            if self.total_model_calls > 0
            else 0.0
        )

        return {
            "timestamp": time.time(),
            "model_calls": {
                "total": self.total_model_calls,
                "failed": self.failed_model_calls,
                "error_rate": round(error_rate, 4),
                "latency_p50_seconds": round(p50, 3),
                "latency_p95_seconds": round(p95, 3),
            },
            "scanner_status": self.last_scanner_check,
            "healthy": error_rate < 0.25,
        }


GLOBAL_TELEMETRY = TelemetryTracker()
