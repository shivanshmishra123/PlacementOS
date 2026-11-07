"""Zero-token cached response adapter for regression testing and offline verification."""

from __future__ import annotations

import json
from pathlib import Path

from placementos.models.storage import TextExtraction
from placementos.services.jd_intelligence import (
    DeterministicFixtureJDInterpreter,
    InterpretationDraft,
    validate_evidence,
)

CACHE_DIR = Path(__file__).parent / "recordings"


class CachedModelInterpreter:
    """Zero-token replaying interpreter that reads previously recorded model responses."""

    adapter_id = "cached-gemini-v1"
    prompt_version = "jd-intelligence-cached-v1"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fallback = DeterministicFixtureJDInterpreter()

    def _get_cache_key(self, extraction: TextExtraction) -> str:
        return extraction.text_hash_sha256[:16]

    def interpret(self, extraction: TextExtraction) -> InterpretationDraft:
        key = self._get_cache_key(extraction)
        file_path = self.cache_dir / f"{key}.json"

        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            draft = InterpretationDraft(
                facts=data["facts"],
                evidence=data["evidence"],
                clarifications=data["clarifications"],
                findings=data.get("findings", []),
                usage={"adapter_id": self.adapter_id, "cached": True, "tokens_used": 0},
            )
            validate_evidence(extraction, draft.evidence)
            return draft

        # Fallback to deterministic fixture when no recording exists
        draft = self.fallback.interpret(extraction)
        draft.usage["cached_fallback"] = True
        draft.usage["tokens_used"] = 0
        return draft

    def record(self, extraction: TextExtraction, draft: InterpretationDraft) -> None:
        """Persist a live Gemini model response for future zero-token replay."""
        key = self._get_cache_key(extraction)
        file_path = self.cache_dir / f"{key}.json"
        data = {
            "facts": draft.facts,
            "evidence": draft.evidence,
            "clarifications": draft.clarifications,
            "findings": draft.findings,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
