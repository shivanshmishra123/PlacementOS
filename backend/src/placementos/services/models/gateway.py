"""Provider-neutral model gateway and token budgeting controls for PlacementOS."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from placementos.core.config import settings
from placementos.core.errors import BadRequestException
from placementos.models.storage import TextExtraction
from placementos.services.jd_intelligence import InterpretationDraft

logger = logging.getLogger(__name__)


class TokenBudgetExceededError(BadRequestException):
    """Raised when client-side token or request caps are reached to protect provider quota."""

    pass


@dataclass
class UsageTracker:
    """In-memory rate and budget tracking to strictly safeguard free-tier limits."""

    calls_today: int = 0
    calls_per_drive: dict[str, int] = None  # drive_id -> count

    def __post_init__(self):
        if self.calls_per_drive is None:
            self.calls_per_drive = {}

    def check_and_increment(self, drive_id: str | None = None) -> None:
        """Enforce strict client-side ceilings before issuing an external model request."""
        if self.calls_today >= settings.MODEL_DAILY_REQUEST_CAP:
            msg = (
                f"Client safety ceiling reached: daily model call limit ({settings.MODEL_DAILY_REQUEST_CAP}) "
                "reached to protect free-tier quota. Coordinator manual entry activated."
            )
            logger.warning(msg)
            raise TokenBudgetExceededError(msg)

        if drive_id:
            count = self.calls_per_drive.get(drive_id, 0)
            if count >= settings.MODEL_MAX_CALLS_PER_DRIVE:
                msg = (
                    f"Per-drive extraction limit ({settings.MODEL_MAX_CALLS_PER_DRIVE}) reached for drive {drive_id}. "
                    "Use coordinator field corrections to modify criteria."
                )
                logger.warning(msg)
                raise TokenBudgetExceededError(msg)
            self.calls_per_drive[drive_id] = count + 1

        self.calls_today += 1
        logger.info(
            "Model call budgeted. Usage today: %d/%d calls. Drive calls: %s",
            self.calls_today,
            settings.MODEL_DAILY_REQUEST_CAP,
            self.calls_per_drive.get(drive_id, 1) if drive_id else "N/A",
        )


GLOBAL_USAGE_TRACKER = UsageTracker()


class ModelGateway(Protocol):
    """Protocol for provider-neutral model execution."""

    adapter_id: str
    prompt_version: str

    def interpret(self, extraction: TextExtraction) -> InterpretationDraft:
        """Extract candidate facts from document extraction with verbatim source citations."""
        ...
