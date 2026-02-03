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

## API (v1)

The API is available under the `/api/v1/` prefix.

### Health check

```bash
curl -s http://127.0.0.1:8000/api/v1/health/
```
