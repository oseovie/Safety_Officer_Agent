# SentinelSafe

AI-powered Safety Management and Risk Automation SaaS platform for construction, manufacturing, logistics, and oil and gas teams.

## What Is Included

- FastAPI backend with Swagger docs at `/docs`
- PostgreSQL multi-tenant schema using tenant-scoped records
- SQLAlchemy models for incidents, hazards, inspections, corrective actions, documents, employees, audits, notifications, and users
- JWT authentication and role-based permissions
- Celery and Redis for notifications, audit packs, and scheduled automation
- S3-compatible secure document uploads
- PDF and Excel risk register exports
- Next.js mobile-first dashboard
- Docker Compose for API, worker, frontend, Postgres, Redis, and MinIO
- Unit tests for security and AI risk scoring

## Architecture

```text
frontend/          Next.js enterprise operations UI
backend/app/api    REST routes and auth dependencies
backend/app/core   settings, security, RBAC, Celery config
backend/app/models SQLAlchemy database schema
backend/app/services risk AI, storage, reporting, notifications
backend/app/tasks  background workers
backend/tests      unit tests
```

Tenant isolation is enforced through JWT `tenant_id`, `X-Tenant-Id` validation, and tenant-scoped database queries. For production, add PostgreSQL row-level security policies and an Alembic migration chain before onboarding customers.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open the API docs at `http://localhost:8000/docs`.
4. Open the frontend at `http://localhost:3000`.

Register a tenant:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"organization":"Acme Construction","slug":"acme","admin_name":"Safety Lead","admin_email":"safety@example.com","admin_password":"S@ferPass12345"}'
```

Use the returned bearer token for API calls.

## Core API Areas

- `POST /api/v1/incidents`
- `POST /api/v1/hazards`
- `POST /api/v1/inspections`
- `POST /api/v1/actions`
- `POST /api/v1/documents`
- `POST /api/v1/employees`
- `POST /api/v1/audits`
- `GET /api/v1/dashboard`
- `GET /api/v1/reports/risk-register.pdf`
- `GET /api/v1/reports/risk-register.xlsx`

## Offline Inspection Support

Inspection payloads accept `offline_sync_id`, checklist data, and response maps. Mobile clients can store drafts locally, then submit once connectivity returns. The API keeps the sync identifier indexed for dedupe and reconciliation workflows.

## Production Notes

- Replace `JWT_SECRET` with a long random value and rotate it through your secrets manager.
- Add Alembic migrations before the first production deployment.
- Configure S3 lifecycle, object encryption, malware scanning, and signed URL download routes.
- Put the API behind a TLS reverse proxy or managed load balancer.
- Enable Postgres backups, Redis persistence where needed, and structured logs.
- Connect `AI_PROVIDER` to your preferred LLM provider after legal review of safety data handling.

## Tests

```bash
cd backend
pytest
```
