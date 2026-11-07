"""Model interpreter factory for PlacementOS."""

from __future__ import annotations

import logging

from placementos.core.config import settings
from placementos.core.errors import ConflictException
from placementos.services.jd_intelligence import (
    DeterministicFixtureJDInterpreter,
    ModelInterpreter,
)
from placementos.services.models.cached_adapter import CachedModelInterpreter
from placementos.services.models.gemini_adapter import GeminiModelInterpreter

logger = logging.getLogger(__name__)


def get_model_interpreter() -> ModelInterpreter:
    """Return the configured model interpreter adapter based on environment and settings."""
    mode = settings.MODEL_INTERPRETER_MODE

    if mode == "disabled":
        raise ConflictException("Model interpretation is disabled; use attributed manual coordinator entry")

    if mode == "provider":
        if not settings.GEMINI_API_KEY:
            logger.warning("Gemini API key is not set; falling back to deterministic fixture.")
            return DeterministicFixtureJDInterpreter()
        return GeminiModelInterpreter()

    if mode == "cached":
        return CachedModelInterpreter()

    # Default: "fixture"
    return DeterministicFixtureJDInterpreter()
