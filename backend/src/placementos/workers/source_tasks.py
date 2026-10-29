"""Celery Task for Asynchronous Document Text Extraction."""

import asyncio
import logging
import uuid

from placementos.services.source_jobs import SourceJobService
from placementos.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="placementos.workers.extract_source_text", bind=True, max_retries=3)
def extract_source_text_task(self, source_artifact_id_str: str, institution_id_str: str) -> dict[str, str]:
    """Execute document extraction job in Celery worker process."""
    artifact_id = uuid.UUID(source_artifact_id_str)
    institution_id = uuid.UUID(institution_id_str)

    try:
        extraction = asyncio.run(SourceJobService.run_extraction(artifact_id, institution_id))
        return {
            "status": "completed",
            "extraction_id": str(extraction.id),
            "artifact_id": str(artifact_id),
        }
    except Exception as exc:
        logger.error("Celery extraction task failed for artifact %s: %s", artifact_id, exc)
        # Avoid retry on deterministically failed parse errors (corrupt, encrypted, etc.)
        from placementos.services.parsers import ParseError
        if isinstance(exc, ParseError):
            return {"status": "failed", "error_code": exc.code, "error_message": exc.message}
        raise self.retry(exc=exc, countdown=5) from exc

