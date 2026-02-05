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