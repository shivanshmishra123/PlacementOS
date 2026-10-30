"""P08 durable workflow relay and trusted execution tasks."""

import asyncio
import uuid

from placementos.services.workflows import (
    execute_workflow_command,
    relay_pending_workflow_commands,
)
from placementos.workers.celery_app import celery_app


@celery_app.task(name="placementos.workers.relay_workflow_commands")
def relay_workflow_commands_task() -> int:
    return asyncio.run(relay_pending_workflow_commands())


@celery_app.task(name="placementos.workers.execute_workflow_command")
def execute_workflow_command_task(command_id: str, institution_id: str) -> str:
    return asyncio.run(execute_workflow_command(uuid.UUID(command_id), uuid.UUID(institution_id)))
