# Sentido backend

This file is a developer pointer — **not** the spec. The full plan
(architecture, data model, API contract, phasing) lives at:

> `docs/instructions/backend-implementation-plan.md`

The backend is a Python 3.12 + FastAPI + SQLAlchemy (async) + pgvector
modular monolith.

## Quick start (local dev)

### 1. Bring up Postgres

The dev database runs in Docker on host port **5433** to avoid clashing
with any locally-installed Postgres.

```bash
cd backend
docker compose -f docker/docker-compose.yml up -d db
```

The `pgvector/pgvector:pg16` image bundles the `vector` extension;
`pgcrypto` ships with stock Postgres. Both are enabled by the first
Alembic migration.

### 2. Install the Python package (editable + dev tools)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### 3. Generate the lockfile (recommended before deploying)

`pip-tools` produces a deterministic lock for reproducible Docker builds.
The B1 commit ships **without** `requirements.lock.txt` because the agent
sandbox lacks pip-tools — generate it locally and commit it:

```bash
cd backend
pip-compile pyproject.toml -o requirements.lock.txt
git add requirements.lock.txt && git commit -m "chore: lock backend dependencies"
```

Re-run whenever `pyproject.toml` dependencies change.

After the lockfile exists, switch the Dockerfile install line from
`pip install /build` back to `pip install -r requirements.lock.txt` for
reproducible image builds (see the Dockerfile header comment).

### 4. Apply migrations

```bash
cd backend
cp .env.example .env   # then edit secrets
export $(grep -v '^#' .env | xargs)   # or use a tool like direnv
alembic upgrade head
```

### 5. Verify the database

```bash
psql "postgresql://sentido:sentido@localhost:5433/sentido" \
  -c "\dt" \
  -c "SELECT 1 FROM books;" \
  -c "SELECT 1 FROM authors;" \
  -c "SELECT 1 FROM resonance_cache;" \
  -c "\d books"
```

You should see all five tables (`authors`, `books`, `editions`,
`collections`, `collection_books`, `resonance_cache`) and the
`books_embedding_idx` ivfflat index on `books.embedding`.

## Layout

See plan §3.1. Top level under `src/sentido/`:

- `shared/` — config, db session factory, auth, errors, http
- `catalog/` — books/authors/editions/collections (owns the persistence schema)
- `search/` — semantic search + resonance-line cache
- `ingestion/` — Open Library + Google Books clients
- `generation/` — OpenAI orchestration (synopsis, profile, embedding)
- `admin/` — composes the above behind the admin-token guard

## Phase status

- **B1 — infrastructure scaffold (this commit).** `pyproject.toml`,
  module skeleton, ORM models, initial Alembic migration, Docker setup.
  The api service does not yet run.
- **B2 — running FastAPI app + admin auth + health endpoint.** Next.
- See plan §9 for the rest of Phase 0.
