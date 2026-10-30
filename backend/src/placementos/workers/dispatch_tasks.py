"""P07 outbox relay and controlled dispatch worker tasks."""

import asyncio
import uuid

from placementos.services.dispatch import execute_dispatch_operation, relay_pending_outbox
from placementos.workers.celery_app import celery_app


@celery_app.task(name="placementos.workers.relay_dispatch_outbox")
def relay_dispatch_outbox_task() -> int:
    return asyncio.run(relay_pending_outbox())


@celery_app.task(name="placementos.workers.dispatch_operation")
def dispatch_operation_task(operation_id: str, institution_id: str) -> str:
    return asyncio.run(
        execute_dispatch_operation(uuid.UUID(operation_id), uuid.UUID(institution_id))
    )
