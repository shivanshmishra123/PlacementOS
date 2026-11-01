"""P11 integration outbox relay and controlled provider execution tasks."""

import asyncio
import uuid

from placementos.services.integrations import (
    execute_integration_operation,
    relay_pending_integration_operations,
)
from placementos.workers.celery_app import celery_app


@celery_app.task(name="placementos.workers.relay_integration_operations")
def relay_integration_operations_task() -> int:
    return asyncio.run(relay_pending_integration_operations())


@celery_app.task(name="placementos.workers.execute_integration_operation")
def execute_integration_operation_task(operation_id: str, institution_id: str) -> str:
    return asyncio.run(
        execute_integration_operation(uuid.UUID(operation_id), uuid.UUID(institution_id))
    )
