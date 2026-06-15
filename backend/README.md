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

- **B1 — infrastructure scaffold.** `pyproject.toml`, module skeleton,
  ORM models, initial Alembic migration, Docker setup. Done.
- **B2 — running FastAPI app + admin auth + health endpoint.** Done.
  `main.py` factory + lifespan, `/v1/health`, `require_admin`
  dependency, exception handlers, CORS, and the `api` service in
  docker-compose.
- **B3 — ingestion.** Done. `OpenLibraryClient`, ISBN normalization,
  catalog DTOs, `find_or_create_author` + `create_book_from_normalized`
  with slug-collision handling, `POST /v1/admin/books/ingest`. Google
  Books fallback is deferred to Phase 1.
- **B4 — generation.** Done. Voice-locked prompts in
  `generation/prompts.py` (mirror `docs/brand/voice.md §4`), pure
  `parse_profile` + `compose_embedding_text` helpers, `OpenAIClient`
  wrapper with the plan §7.1 retry policy, and `generate_artifacts`
  service composing synopsis → emotional profile → embedding in a
  single transaction. Exposed via `POST /v1/admin/books/{id}/generate`
  (admin auth). Books land with `embedding_status='done'` and
  `profile_status='pending'` for curator approval.
- **B5 — publish + curator approval + public reads + semantic search.**
  Done. `PUT /v1/admin/books/{id}` (partial update with `extra="forbid"`),
  `POST /v1/admin/books/{id}/publish` (single-call approve + publish
  with the embedding/profile gates), public `GET /v1/books/{slug}`
  (with pgvector-similarity `related_books`), and `POST /v1/search`
  (query embedding + pgvector cosine ranking + lazy
  `resonance_cache` lookup keyed by `sha256(normalized_query || book_id)`).
  Resonance lines are generated via the lone
  `generation.service.generate_resonance_line` seam so the M3 boundary
  stays clean.
- **Phase 0 complete; Phase 1 next.** See plan §10 for the deltas
  over Phase 0 (admin list endpoint, author pages, collections, Google
  Books fallback, structured logging).
