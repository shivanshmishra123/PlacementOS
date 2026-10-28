# PlacementOS: Local Developer Setup Guide

> Comprehensive instructions for setting up and running PlacementOS on Windows and Linux/macOS.

---

## 1. Prerequisites

- **Node.js:** v20+ LTS
- **Package Manager:** `pnpm` (v9+)
- **Python:** 3.12+
- **Python Tooling:** `uv`
- **Container Engine:** Docker Desktop with Compose v2+

---

## 2. Quickstart Commands

```bash
# 1. Clone repository and copy environment configuration
copy .env.example .env

# 2. Start local infrastructure containers (PostgreSQL, Redis, MinIO, Mailpit)
docker compose up -d

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

# 8. Start Celery worker (Windows requires -P solo or -P threads)
uv run --project backend celery -A placementos.workers.celery_app worker -P solo --loglevel=info
```

---

## 3. Running Checks and Verification

```bash
# Frontend lint and typecheck
pnpm lint
pnpm typecheck

# Backend lint, typecheck, and test suite
uv run --project backend ruff check src tests
uv run --project backend pytest

# Export OpenAPI schema
uv run --project backend python scripts/export_openapi.py
```

---

## 4. Local Service Ports

| Service | Host Port | Internal Port | Web Console / UI |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `55432` | `5432` | `psql -h localhost -p 55432 -U placementos -d placementos` |
| **Redis** | `6379` | `6379` | `redis-cli -p 6379` |
| **MinIO (S3)** | `4566` (API), `9001` (UI) | `9000`, `9001` | http://localhost:9001 (`dev_access_key` / `dev_secret_key`) |
| **Mailpit** | `1025` (SMTP), `8025` (UI) | `1025`, `8025` | http://localhost:8025 |
| **FastAPI** | `8000` | `8000` | http://localhost:8000/docs |
| **Next.js Web** | `3000` | `3000` | http://localhost:3000 |
