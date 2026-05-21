# Truuth Worker Demo Architecture

This prototype is a demo-first FastAPI backend for adverse media and PEP/sanctions orchestration.

It is intentionally built with mocks and extension points so future real integrations can be added without changing the core business flow.

## Design Principles

### Vendor Agnostic

Business services do not depend on a specific vendor response shape.

Vendor-specific behavior lives behind adapter interfaces:

- `VendorAdapter`
- `MockAdverseMediaAdapter`
- `MockPepSanctionsAdapter`

Future production vendors should be added by implementing the same adapter contract.

### Internal System Of Record

The service treats internal collections as authoritative:

- candidates
- employees
- payload runs
- payload entries
- screening runs
- screening results
- vendor executions
- task runs
- schedules
- webhook events
- audit logs
- error logs

Vendor systems are treated as external data sources only. Normalized results are persisted internally before being returned to dashboard-facing APIs.

### Dynamic Payloads

Payloads are generated per execution.

Each `PayloadRun` captures:

- selected candidates
- selected employees
- whitelist exclusions
- batch ID
- chunk size
- chunk count

This keeps every screening execution reproducible for audit and demo walkthroughs.

### Candidate And Employee Lifecycles Are Separate

Candidates and employees are distinct documents.

A candidate can be promoted into an employee, and the link is tracked through:

- `CandidateDocument.promoted_employee_id`
- `EmployeeDocument.candidate_id`

This supports the recruitment-to-monitoring lifecycle without collapsing the two concepts.

### Extensible Integration Hooks

External integration points are represented as interfaces and mock implementations:

- resume parsing hook
- AI extraction hook
- vendor adapter hook
- webhook hook
- task/retry hook
- scheduler trigger hook

The demo avoids real external credentials while preserving the shape of future integration work.

Current hook classes:

- `ResumeParser`
- `MockResumeParser`
- `AIExtractionProvider`
- `MockAIExtractionProvider`
- `VendorAdapter`

### Clean Architecture

Framework concerns are kept in API route modules.

Business logic lives in service classes:

- `CandidateService`
- `PayloadService`
- `ScreeningService`
- `TaskService`
- `WebhookService`
- `AuditService`

Persistence lives behind repository abstractions with in-memory, MongoDB-ready, and Postgres/Supabase-ready implementations.

The current deployable demo uses Postgres JSONB tables through Supabase. MongoDB remains available as an alternate repository backend, but Supabase/Postgres is the preferred free demo persistence path.

## Non-Goals

This prototype does not implement:

- frontend UI
- authentication
- RBAC
- production cloud deployment
- Kubernetes
- real OCR
- real AI extraction
- real vendor credentials
- production queue workers
- production schedulers

Instead, it provides:

- interfaces
- hooks
- placeholders
- mock implementations
- demo-ready API flows
- repeatable demo reset flow
- extensible architecture

## Current Demo Flow

```text
Seed candidates
-> optionally promote candidates into employees
-> build dynamic payload
-> submit payload to mock vendor adapters
-> normalize vendor responses
-> persist internal screening results
-> return dashboard-facing results
-> write audit/error/task/webhook records where relevant
```

## Production Evolution Notes

A production version would likely add:

- real database provisioning and migrations
- typed relational tables where stronger reporting/querying is needed
- real vendor API adapters
- real resume parser implementation
- real AI extraction provider
- queue workers
- scheduler worker
- authentication and RBAC
- observability export
- production deployment target such as AWS ECS/Fargate
