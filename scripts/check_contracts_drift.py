"""Script to detect drift between FastAPI OpenAPI schema and api-client/openapi.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from placementos.main import app

def check_drift() -> int:
    contract_path = Path(__file__).parent.parent / "packages" / "api-client" / "openapi.json"
    if not contract_path.exists():
        print(f"Contract file missing: {contract_path}. Run export_openapi.py first.")
        return 1

    with open(contract_path, encoding="utf-8") as f:
        existing_schema = json.load(f)

    current_schema = json.loads(json.dumps(app.openapi()))

    if existing_schema == current_schema:
        print("Contract check passed: zero schema drift detected.")
        return 0
    else:
        print("Contract drift detected! OpenAPI schema has changed. Run export_openapi.py to update.")
        return 1

if __name__ == "__main__":
    sys.exit(check_drift())
