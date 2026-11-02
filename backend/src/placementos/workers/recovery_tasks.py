"""P12 recovery-plan outbox relay and bounded execution tasks."""

import asyncio
import uuid

from placementos.services.recovery import (
    execute_recovery_plan,
    relay_pending_recovery_executions,
)
from placementos.workers.celery_app import celery_app


@celery_app.task(name="placementos.workers.relay_recovery_executions")
def relay_recovery_executions_task() -> int:
    return asyncio.run(relay_pending_recovery_executions())


@celery_app.task(name="placementos.workers.execute_recovery_plan")
def execute_recovery_plan_task(execution_id: str, institution_id: str) -> str:
    return asyncio.run(execute_recovery_plan(uuid.UUID(execution_id), uuid.UUID(institution_id)))
