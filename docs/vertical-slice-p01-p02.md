# PlacementOS: Next Vertical Slice (P01 & P02 Execution Plan)

> Phase P00 Deliverable: P00-T07  
> Date: 29 October 2026  
> Status: Actionable Roadmap for P01/P02

---

## 1. Overview and Objective

With the contracts, state machines, decision registers, and synthetic fixtures frozen in Phase P00, the implementation pathway transitions to **Milestone M0: Foundations**.

This document outlines:
1. Local runtime constraints on Windows.
2. The ordered task breakdown for Phase P01 (Repository & Infrastructure) and Phase P02 (Identity & Student Records).
3. The concrete acceptance demonstration for the initial vertical slice.

---

## 2. Windows Local Runtime Constraints & Mitigation

The development workstation runs **Windows (PowerShell)**. The following technical constraints are identified and mitigated:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        WINDOWS RUNTIME MATRIX & MITIGATIONS                            │
├────────────────────┬─────────────────────────────┬─────────────────────────────────────┤
│ Component          │ Windows Specific Constraint │ Engineered Mitigation               │
├────────────────────┼─────────────────────────────┼─────────────────────────────────────┤
│ **Celery Workers** │ Celery 5.x dropped native   │ In development on Windows:          │
│                    │ prefork pool support on     │   1. Use `-P solo` or `-P threads`  │
│                    │ Windows without posix fork. │      pool for native local runs, OR │
│                    │                             │   2. Execute worker container in    │
│                    │                             │      Docker Compose / WSL2.         │
├────────────────────┼─────────────────────────────┼─────────────────────────────────────┤
│ **File Paths**     │ Backslash `\` vs Forward `/`│ Use Python `pathlib.Path` and POSIX │
│                    │ across configs and Alembic. │ path formatting in all scripts.     │
├────────────────────┼─────────────────────────────┼─────────────────────────────────────┤
│ **Docker Compose** │ Port collisions on default  │ Pinned port configuration:          │
│                    │ ports (e.g. existing local  │   - PostgreSQL: `5432`              │
│                    │ Postgres).                  │   - Redis: `6379`                   │
│                    │                             │   - MinIO (S3): `9000` (API),       │
│                    │                             │                 `9001` (Console)    │
│                    │                             │   - Mailpit: `1025` (SMTP),         │
│                    │                             │              `8025` (Web UI)        │
├────────────────────┼─────────────────────────────┼─────────────────────────────────────┤
│ **Tooling**        │ PowerShell execution policy │ Use `pnpm` (Node v20+ LTS) and      │
│                    │ for script wrappers.        │ `uv` (Python 3.12+). Lockfiles:     │
│                    │                             │ `pnpm-lock.yaml`, `uv.lock`.        │
└────────────────────┴─────────────────────────────┴─────────────────────────────────────┘
```

---

## 3. Actionable Task Breakdown for Phase P01 (Repository & Infrastructure)

- [ ] **P01-T01: Bootstrap monorepo structure.**  
  Set up root workspace configuration (`pnpm-workspace.yaml`, root `package.json`, `apps/web`, `backend`, `packages/api-client`, `infra/compose`).
- [ ] **P01-T02: Pin dependencies & lockfiles.**  
  Initialize Python 3.12 with `uv` (`pyproject.toml`) and Node 20 LTS with `pnpm`. Configure linters (`ruff`, `eslint`) and test frameworks (`pytest`, `vitest`).
- [ ] **P01-T03: Docker Compose local infrastructure.**  
  Provide `compose.yaml` with PostgreSQL 16, Redis 7, MinIO, and Mailpit with automated health checks.
- [ ] **P01-T04: Settings, database connection, & Alembic setup.**  
  Implement typed configuration (`pydantic-settings`), PostgreSQL connection pool (`SQLAlchemy 2.0`), and Alembic migration directory (`backend/migrations`).
- [ ] **P01-T05: FastAPI & Next.js skeleton shells.**  
  Create FastAPI application entry point with `/health`, `/ready`, correlation ID middleware, error handler, and Next.js App Router base layout.
- [ ] **P01-T06: OpenAPI contract generation.**  
  Generate `openapi.json` from FastAPI and establish automated build for `@placementos/api-client`.
- [ ] **P01-T07: Development checks & scripts.**  
  Add root package scripts for linting, typechecking, and tests.

---

## 4. Actionable Task Breakdown for Phase P02 (Identity & Student Records)

- [ ] **P02-T01: Institution and membership models & migrations.**  
  Relational models for `institutions`, `institution_config_versions`, `users`, `memberships`, `drive_assignments`. Composite foreign keys enforcing tenant isolation.
- [ ] **P02-T02: OIDC session authentication & mock development adapter.**  
  Session management with opaque tokens, secure cookies, CSRF protection, and preconfigured test personas (`coord_apex`, `admin_apex`, `coord_beacon`).
- [ ] **P02-T03: Scoped authorization service & context middleware.**  
  Dependency injection providing authenticated `ActorContext` (user, active institution, capabilities).
- [ ] **P02-T04: Academic record revisions model.**  
  Model `students`, `academic_record_revisions`, tracking immutable verification history and exact decimal CGPA metrics.
- [ ] **P02-T05: Student CSV import with preview and commit.**  
  Implement two-stage import: parse & validate CSV rows without DB mutation, generate preview diff, commit atomically with expected revision checks.
- [ ] **P02-T06: Academic correction proposals & review workflow.**  
  Student proposal submission and coordinator verification endpoints.
- [ ] **P02-T07: Coordinator & student record screens.**  
  Frontend views for coordinator student roster and student profile.
- [ ] **P02-T08: Audit logging & negative authorization suite.**  
  Automated tests verifying cross-institutional isolation (`inst-apex-01` vs `inst-beacon-02`).

---

## 5. Definition of Initial Vertical Slice Acceptance Gate

The completion of P01 and P02 will be demonstrated by the following verifiable end-to-end user scenario:

1. **Service Verification:** Docker Compose starts healthy Postgres, Redis, MinIO, and Mailpit services.
2. **Session Sign-in:** Coordinator Priya Sharma logs into Apex Institute of Technology using the development identity adapter; receives an opaque session cookie.
3. **Tenant-Safe CSV Import:** Priya uploads a CSV containing the Section 10.2 student cohort (10 students). The API returns a validation preview report. Upon confirmation, the 10 students and their initial verified academic revisions are transactionally committed.
4. **Negative Scope Check:** Coordinator Ananya Das (Beacon State University) attempts to fetch student records from Apex Institute of Technology via ID and roster endpoints. All requests are strictly rejected with HTTP 404 / 403.
5. **Collision Demonstration:** Ananya Das imports a student with roll number `2023-CS-001` into Beacon State University. The student is created without collision with Apex's `2023-CS-001`.
