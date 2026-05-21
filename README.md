# Truuth Worker Demo API

FastAPI backend prototype for adverse media, PEP, and sanctions screening orchestration.

This repository is intended to be deployed as the backend API for the separate `truuth-screening-dashboard` frontend repository.

## Overview

The service demonstrates a vendor-agnostic worker architecture:

```text
candidate / employee records
-> dynamic payload generation
-> mock vendor adapter execution
-> normalized screening results
-> analyst review actions
-> audit, task, schedule, webhook evidence
```

The implementation is demo-first. It uses mock vendors and placeholder hooks instead of real vendor credentials, real OCR, or real AI extraction.

## Key Features

- Candidate and employee lifecycle separation
- Candidate promotion into employee monitoring
- Dynamic payload generation per screening run
- Mock adverse media vendor adapter
- Mock PEP and sanctions vendor adapter
- Normalized internal results independent of vendor response shape
- Dashboard-facing screening run API
- Analyst review action API
- Audit and error logs
- Schedule, task, retry, and webhook placeholders
- Request and correlation ID middleware
- In-memory, Mongo-ready, and Postgres/Supabase repository modes
- JSONB-backed Postgres document tables for fast demo persistence
- Demo reset endpoint for repeatable stakeholder walkthroughs

## Architecture Notes

The service follows the prototype brief principles:

- **Vendor agnostic:** vendor logic lives behind adapter interfaces.
- **Internal system of record:** internal datasets are authoritative.
- **Dynamic payloads:** payloads are generated per execution.
- **Candidate and employee lifecycles are separate:** they are distinct records but can be linked.
- **Extensible integration hooks:** future providers can plug into the adapter layer.
- **Clean architecture:** routes, schemas, services, repositories, and adapters are separated.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design principles, non-goals, and production evolution notes.

## Project Structure

```text
app/
  adapters/          # vendor adapter interface and mock adapters
  api/               # FastAPI route modules and dependencies
  core/              # config, logging, request context, error codes
  data/              # seed dataset
  repositories/      # memory, Mongo, and Postgres repository implementations
  schemas/           # Pydantic domain documents and request/response models
  services/          # orchestration/business logic
  main.py            # FastAPI app factory
tests/
  smoke_test.py      # end-to-end API smoke test
vercel.json          # Vercel FastAPI deployment config
```

## Local Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Environment Variables

Copy the example file if you want local env config:

```bash
cp .env.example .env
```

Default local mode:

```env
REPOSITORY_BACKEND=memory
```

Postgres/Supabase mode:

```env
REPOSITORY_BACKEND=postgres
DATABASE_URL=postgresql://...
```

Mongo mode:

```env
REPOSITORY_BACKEND=mongo
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=truuth_worker_demo
```

Do not commit `.env`. It is ignored by `.gitignore`.

## Supabase Setup

Use the Supabase transaction pooler connection string:

```text
postgresql://postgres.<project-ref>:<password>@aws-1-<region>.pooler.supabase.com:6543/postgres
```

Set it as `DATABASE_URL`.

The code accepts the copied `postgresql://` URL and internally normalizes it to SQLAlchemy's asyncpg driver. It also configures asyncpg for Supabase's transaction pooler by disabling statement cache and using unique prepared statement names.

Tables are created automatically on API startup. The current demo creates these JSONB-backed tables:

```text
candidates
employees
payload_runs
payload_entries
screening_runs
screening_results
vendor_executions
task_runs
schedules
webhook_events
audit_logs
error_logs
```

Each table uses this shape:

```sql
id TEXT PRIMARY KEY
data JSONB NOT NULL
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## API Demo Flow

Health check:

```text
GET /health
```

Seed demo candidates:

```text
POST /seed
```

Reset persistent demo state and reseed:

```text
POST /demo/reset
```

List candidates:

```text
GET /candidates
```

Run screening:

```json
POST /screening/runs
{
  "build_payload": true,
  "candidate_ids": ["<candidate-id-1>", "<candidate-id-2>"],
  "chunk_size": 2
}
```

View dashboard data for a run:

```text
GET /dashboard/runs/{run_id}
```

Review a result:

```json
POST /results/{result_id}/review
{
  "action": "accept",
  "reviewer": "demo-analyst",
  "note": "Verified for demo"
}
```

Operational evidence endpoints:

```text
GET /vendors/executions
POST /schedules
GET /schedules
POST /schedules/{schedule_id}/trigger
GET /tasks
GET /tasks/retryable
POST /tasks/{task_id}/execute
POST /tasks/{task_id}/fail
POST /tasks/{task_id}/retry
POST /webhooks/vendors/{vendor_name}
GET /audit/logs
GET /errors
```

Every response includes:

```text
x-request-id
x-correlation-id
```

## Validation

Run the backend smoke test:

```bash
python tests/smoke_test.py
```

The smoke test covers:

- health
- seed
- reset demo
- screening run
- dashboard run
- review action
- audit logs
- schedules
- tasks
- vendor executions
- webhooks

To test against Supabase locally:

```bash
REPOSITORY_BACKEND=postgres DATABASE_URL='<supabase-pooler-url>' python tests/smoke_test.py
```

## Vercel Deployment

Create a new Vercel project using this repository as the project root.

Recommended settings:

```text
Framework Preset: Other
Build Command: empty/default
Output Directory: empty/default
Install Command: pip install -r requirements.txt
```

The included [vercel.json](vercel.json) routes all requests to `app/main.py` using `@vercel/python`.

Set environment variables in Vercel:

```env
REPOSITORY_BACKEND=postgres
DATABASE_URL=<supabase-transaction-pooler-url>
```

After deployment, verify:

```text
https://<backend-domain>/health
```

Then initialize demo data:

```text
POST https://<backend-domain>/demo/reset
```

## Connecting The Frontend

Deploy the separate `truuth-screening-dashboard` repository and set:

```env
VITE_API_BASE_URL=https://<backend-domain>
```

The dashboard also has a runtime API URL field in the header. During demos, confirm it points to the deployed backend and click **Save**.

## Non-Goals

The demo intentionally does not implement:

- frontend UI in this repo
- authentication
- RBAC
- production cloud architecture
- Kubernetes
- real OCR
- real AI extraction
- real vendor credentials
- production queue workers
- production scheduler

Instead, it provides hooks, mocked implementations, and an extensible architecture for future phases.

## Troubleshooting

If `/health` fails on Vercel, check `REPOSITORY_BACKEND` and `DATABASE_URL`.

If Supabase returns prepared statement errors, confirm the backend includes the current `PostgresDocumentRepository` pooler config.

If data disappears between requests, check whether the backend is running with `REPOSITORY_BACKEND=memory`.

If the frontend cannot call the API, confirm the frontend `VITE_API_BASE_URL` matches the deployed backend domain and does not include a trailing path.
