"""Celery task for durable P05 deterministic cohort evaluation."""

import asyncio
import logging
import uuid

from placementos.services.eligibility_runs import EligibilityRunService
from placementos.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="placementos.workers.evaluate_eligibility", bind=True, max_retries=3)
def evaluate_eligibility_task(self, run_id_str: str, institution_id_str: str) -> dict[str, str | int]:
    run_id = uuid.UUID(run_id_str)
    institution_id = uuid.UUID(institution_id_str)
    try:
        run = asyncio.run(EligibilityRunService.execute_run(run_id, institution_id))
        return {
            "status": run.status,
            "run_id": str(run.id),
            "total_count": run.total_count,
        }
    except Exception as exc:
        logger.error("Eligibility run %s failed: %s", run_id, exc)
        raise self.retry(exc=exc, countdown=5) from exc
