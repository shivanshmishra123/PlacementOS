"""Private LangGraph PostgreSQL checkpoint lifecycle for trusted workflow code."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from placementos.core.config import settings


def _safe_serializer() -> JsonPlusSerializer:
    # Workflow state is deliberately JSON-like. No arbitrary Python modules may be deserialized.
    return JsonPlusSerializer(pickle_fallback=False, allowed_msgpack_modules=[])


@asynccontextmanager
async def workflow_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """Open the private checkpointer; callers authorize the workflow run before using it."""
    async with AsyncPostgresSaver.from_conn_string(
        settings.WORKFLOW_DATABASE_URL,
        serde=_safe_serializer(),
    ) as saver:
        yield saver


async def setup_workflow_checkpoints() -> None:
    """Run package-owned checkpoint migrations after the P08 schema/role migration."""
    async with workflow_checkpointer() as saver:
        await saver.setup()
