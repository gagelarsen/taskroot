# TaskRoot

TaskRoot is an open-source friendly project tracking application aimed at keeping work visible, organized, and actionable.
It’s designed to be lightweight for in-house use while remaining easy for others to adopt and extend.
This repository currently contains the tooling and CI foundation; application code will land in subsequent PRs.

## Local development

### Requirements
- Python 3.13
- pip

### Setup

```bash
git clone <repo-url>
cd taskroot

python -m venv .venv
source .venv/bin/activate
```

```bash
pip install -r requirements/dev.txt
cp .env.example .env
```

### Initialize the database
```bash
python manage.py migrate
Run the server
python manage.py runserver
```
The API health endpoint should be available at:
http://127.0.0.1:8000/api/v1/health/

### Run tests

```bash
pytest
```

### Lint and format
```bash
ruff check .
black --check .
```

## Pre-commit hooks (optional but recommended)

This project uses `pre-commit` to run linting and formatting checks automatically before each commit.

To enable it locally:

```bash
pip install pre-commit
pre-commit install
```
Once installed, Ruff and Black will run on each commit.
CI will still enforce the same checks even if you choose not to use pre-commit locally.

## Roles

TaskRoot authorization is based on `Staff.role`:

- `admin`: full read/write access across the API, including managing staff roles
- `manager`: read everything; write access to contracts/deliverables/assignments/tasks/time entries/status updates (per policy)
- `staff`: read everything; limited write access to tasks (self/unassigned rules) and time entries (own entries only)

## API (v1)

The API is available under the `/api/v1/` prefix.

### Authentication

All API endpoints (except `/api/v1/health/` and `/api/v1/auth/*`) require JWT authentication.

#### Creating test users

To create test users with different roles:

```bash
python manage.py create_test_users
```

This creates three users:
- **Admin**: `username=admin`, `password=admin123`
- **Manager**: `username=manager`, `password=manager123`
- **Staff**: `username=staff`, `password=staff123`

To reset and recreate test users:

```bash
python manage.py create_test_users --reset
```

#### Obtaining a JWT token

To authenticate, first obtain a JWT token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Response:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Making authenticated requests

Use the `access` token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://127.0.0.1:8000/api/v1/staff/
```

#### Refreshing a token

When the access token expires, use the refresh token to get a new one:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

Response:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Verifying a token (optional)

To verify if a token is valid:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

### Health check

```bash
curl -s http://127.0.0.1:8000/api/v1/health/
```

## Filtering & Query Parameters (canonical)

All list endpoints support a stable, integration-friendly set of **canonical** query parameters.

### Canonical rules
- IDs use `*_id` (e.g. `contract_id`, `deliverable_id`, `staff_id`)
- Date ranges use `<field>_from` / `<field>_to`
- Booleans use `true|false`
- Text search uses `q`
- Ordering uses `order_by=<field>&order_dir=asc|desc`
- **Django-style query params are not supported** (e.g. `field__gte`, `field__lte`)

### Examples

**Note**: All examples below require authentication. Set your token as an environment variable for convenience:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Deliverables for a contract:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?contract_id=1"
```

Deliverables assigned to a staff member:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?staff_id=1"
```

Lead-only deliverables:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?lead_only=true"
```

Unassigned tasks for a contract:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/tasks/?contract_id=1&unassigned=true"
```

Order deliverables by due date ascending:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?order_by=due_date&order_dir=asc"
```

## Rollups & Burn Metrics

TaskRoot automatically computes rollup metrics for contracts and deliverables to help track progress and identify issues.

### Metrics Overview

#### Expected vs Actual Hours

- **Expected hours**: Sum of all assignment `expected_hours` for a deliverable (or all deliverables for a contract)
- **Actual hours**: Sum of all time entry `hours` for a deliverable (or all deliverables for a contract)
- **Variance**: `actual_hours - expected_hours` (positive means over, negative means under)

#### Per-Week Metrics

All per-week metrics use consistent weeks calculations:

- **Planned weeks**: `max(1, ceil((end_date - start_date + 1) / 7))`
  - For deliverables: uses deliverable dates if present, else falls back to contract dates
  - For contracts: uses contract `start_date` and `end_date`
  - Minimum is always 1 week

- **Elapsed weeks**: `max(1, ceil((min(today, end_date) - start_date + 1) / 7))`
  - Counts weeks from start to today, capped at the planned end date
  - If the project hasn't started yet, returns 1
  - Minimum is always 1 week

- **Expected hours per week**: `expected_hours_total / planned_weeks`
- **Actual hours per week**: `actual_hours_total / elapsed_weeks`

#### Health Flags

**Deliverable-level:**
- `is_over_expected`: True if actual hours exceed expected hours
- `is_missing_estimate`: True if expected hours is 0 but has assignments
- `is_missing_lead`: True if no assignment has `is_lead=True`

**Contract-level:**
- `is_over_budget`: True if actual hours exceed budget
- `is_over_expected`: True if actual hours exceed expected hours

### API Response Examples

#### Deliverable with Rollups

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/1/"
```

Response:
```json
{
  "id": 1,
  "contract": 1,
  "name": "API Development",
  "start_date": "2024-01-01",
  "due_date": "2024-01-28",
  "status": "in_progress",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z",

  "expected_hours_total": 80.0,
  "actual_hours_total": 45.5,
  "planned_weeks": 4,
  "elapsed_weeks": 2,
  "expected_hours_per_week": 20.0,
  "actual_hours_per_week": 22.75,
  "variance_hours": -34.5,

  "is_over_expected": false,
  "is_missing_estimate": false,
  "is_missing_lead": false,

  "latest_status_update": {
    "id": 5,
    "period_end": "2024-01-14",
    "status": "on_track",
    "summary": "Making good progress on core features",
    "created_by": 2,
    "created_at": "2024-01-14T17:00:00Z"
  }
}
```

#### Contract with Rollups

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/contracts/1/"
```

Response:
```json
{
  "id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-03-31",
  "budget_hours_total": 1000.0,
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z",

  "expected_hours_total": 850.0,
  "actual_hours_total": 245.5,
  "planned_weeks": 13,
  "elapsed_weeks": 2,
  "expected_hours_per_week": 65.38,
  "actual_hours_per_week": 122.75,
  "remaining_budget_hours": 754.5,

  "is_over_budget": false,
  "is_over_expected": false
}
```

### Health Query Filters

You can filter deliverables and contracts by health indicators:

**Deliverables over expected:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?over_expected=true"
```

**Deliverables missing a lead:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?missing_lead=true"
```

**Deliverables missing estimates:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/deliverables/?missing_estimate=true"
```

**Contracts over budget:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/contracts/?over_budget=true"
```

**Contracts over expected:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/contracts/?over_expected=true"
```

### Notes

- All rollup metrics are **computed on-the-fly** (not stored in the database)
- Metrics are **read-only** and cannot be set via the API
- The API uses efficient queries to avoid N+1 problems where possible
- Per-week calculations are consistent across deliverables and contracts