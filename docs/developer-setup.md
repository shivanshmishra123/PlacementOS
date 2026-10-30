# PlacementOS: Local Developer Setup Guide

> Verified local interface for PlacementOS on Windows with Docker Desktop and on Linux/macOS with Docker Compose. Run Celery in a Linux container or WSL on Windows.

---

## 1. Prerequisites

- **Node.js:** v22 LTS
- **Package Manager:** `pnpm` v9+
- **Python:** 3.12+
- **Python Tooling:** `uv`
- **Container Engine:** Docker Desktop with Compose v2+

---

## 2. Quickstart Commands

```bash
# 1. Clone repository and copy environment configuration
copy .env.example .env

# 2. Start local infrastructure (PostgreSQL, Redis, SeaweedFS S3, Mailpit)
docker compose up -d postgres redis object-store mailpit

# 3. Install JavaScript monorepo dependencies
pnpm install

# 4. Sync Python backend environment
uv sync --project backend --all-extras

# 5. Run database migrations
uv run --project backend alembic -c backend/alembic.ini upgrade head

# 6. Start the web frontend (http://localhost:3000)
pnpm dev

# 7. Start the FastAPI backend server (http://localhost:8000)
uv run --project backend uvicorn placementos.main:app --reload --port 8000

# 8. Start the Celery worker from Linux or WSL
uv run --project backend celery -A placementos.workers.celery_app worker --loglevel=info
```

For P07 local dispatch, run Celery beat separately so the durable outbox is relayed:

```text
uv run --project backend celery -A placementos.workers.celery_app beat --loglevel=info
```

Mailpit is available at `http://127.0.0.1:8025`. SMTP acceptance is shown as provider acceptance, not confirmed inbox delivery. The default recipient-domain allowlist is configured with `PLACEMENTOS_EMAIL_RECIPIENT_ALLOWLIST_DOMAINS`.

On Windows, run step 8 inside WSL or a Linux worker container. Native Windows Celery pools are not a supported PlacementOS runtime. The web/API commands may run in PowerShell while the shared infrastructure remains in Docker Desktop.

All backend environment variables use the `PLACEMENTOS_` prefix. `PLACEMENTOS_DATABASE_URL` is the restricted runtime role; only Alembic and administrative migration checks use `PLACEMENTOS_MIGRATION_DATABASE_URL`. The local `development_fixture` scanner and `fixture` interpreter are visibly synthetic and configuration validation rejects them in production.

---

## 3. Running Checks and Verification

```bash
# Frontend lint and typecheck
pnpm lint
pnpm typecheck

# Backend lint, typecheck, and test suite
uv run --project backend ruff check backend/src backend/tests
uv run --project backend mypy backend/src
uv run --project backend pytest backend/tests

# Export OpenAPI schema
uv run --project backend python scripts/export_openapi.py
uv run --project backend python scripts/check_contracts_drift.py
```

---

## 4. Local Service Ports

| Service | Host Port | Internal Port | Web Console / UI |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `55432` | `5432` | `psql -h localhost -p 55432 -U placementos -d placementos` |
| **Redis** | `6379` | `6379` | `redis-cli -p 6379` |
| **SeaweedFS (S3-compatible)** | `4566` | `8333` | Private API endpoint; no local console is exposed. |
| **Mailpit** | `1025` (SMTP), `8025` (UI) | `1025`, `8025` | http://localhost:8025 |
| **FastAPI** | `8000` | `8000` | http://localhost:8000/docs |
| **Next.js Web** | `3000` | `3000` | http://localhost:3000 |

The credentials in `.env.example` are local synthetic defaults. They are not production credentials. The object store is private and application downloads are issued only after authorization through short-lived signed URLs.
