"""Script to export OpenAPI specification from FastAPI application."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from placementos.main import app

def export_openapi():
    output_path = Path(__file__).parent.parent / "packages" / "api-client" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema successfully exported to {output_path}")

if __name__ == "__main__":
    export_openapi()
