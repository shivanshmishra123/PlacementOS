"""Install package-owned LangGraph checkpoint tables in the private workflow schema."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from placementos.services.workflow_checkpoints import setup_workflow_checkpoints

if __name__ == "__main__":
    asyncio.run(setup_workflow_checkpoints())
    print("Workflow checkpoint schema is current.")
