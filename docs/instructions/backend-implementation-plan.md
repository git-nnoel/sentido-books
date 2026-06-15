# Backend implementation plan — Sentido (v1, lean)

> Source of truth for the backend specialist. Do not read the product spec or the brand reference directly — everything you need is here. If something is missing or contradictory, stop and report it back to the orchestrator.

This plan covers **Phase 0 (foundation)** and **Phase 1 (MVP public)**. Later phases are out of scope until the orchestrator extends this document.

---

## 1. Mission

Build a Python service that:

1. Stores books, authors, editions, and editorial collections in PostgreSQL.
2. Generates and persists, lazily and on curator command, three artifacts per book: a PT-BR synopsis, an emotional profile (JSON), and an OpenAI embedding.
3. Answers semantic search queries by embedding the query in real time and running cosine-similarity in pgvector.
4. Exposes a small REST API consumed by a Next.js frontend (deployed separately on Vercel).
5. Provides admin endpoints for curators to ingest books from Open Library / Google Books and approve generated artifacts.

That's the whole product surface for v1. Resist scope creep.

---

## 2. Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Framework | FastAPI | async by default; Pydantic v2 |
| ASGI server | Uvicorn (dev) · Gunicorn + UvicornWorker (prod) | |
| DB | PostgreSQL 16 + `pgvector` extension | Self-hosted via docker-compose |
| ORM | SQLAlchemy 2.x (async) | `asyncpg` driver |
| Migrations | Alembic | |
| LLM / embeddings | OpenAI Python SDK | Models: `gpt-4o-mini`, `text-embedding-3-small` |
| External APIs | `httpx` (async) | For Open Library + Google Books |
| Config | `pydantic-settings` | `.env` driven |
| Tests | `pytest` + `pytest-asyncio` + `httpx.AsyncClient` | |
| Deps | `uv` (preferred) or `pip-tools` | |
| Container | Docker (multi-stage) + docker-compose | |
| Reverse proxy | Caddy | Out-of-process; not configured by backend code |

No Redis, no Celery, no background workers in v1. Generation is synchronous from the admin endpoint (curator sees the result of the call). If a generation takes > 30 seconds we revisit.

---

## 3. Project layout

**Modular monolith** organized by feature, with **functional core + imperative shell** discipline inside each module. The architecture rejects layered/clean-architecture ceremony (no repository protocols, no use-case classes per verb) in favor of feature-shaped modules that each have a small, predictable internal structure.

See `decisions §D7` for the rationale and §3.4 for what this rejects.

### 3.1 Top-level structure

Note: `docker-compose.yml` lives at the **repo root** (one level above the
tree below) — it orchestrates the backend services (`db` + `api`) and references
`backend/docker/Dockerfile` as the build target. The `backend/docker/` subfolder
holds the Dockerfile and is where the production compose + Caddyfile land in
Phase 1.

```
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   └── versions/
├── docker/
│   └── Dockerfile
├── src/
│   └── sentido/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory; mounts module routers
│       │
│       ├── shared/                 # cross-module infrastructure
│       │   ├── config.py           # pydantic-settings
│       │   ├── db.py               # async session factory + FastAPI dependency
│       │   ├── auth.py             # admin token guard (FastAPI dependency)
│       │   ├── errors.py           # ApiError + exception handlers
│       │   └── http.py             # shared httpx client factory (timeouts, UA)
│       │
│       ├── catalog/                # books, authors, editions, collections
│       │   ├── routes.py
│       │   ├── service.py
│       │   ├── logic.py
│       │   ├── models.py           # SQLAlchemy ORM (BookORM, AuthorORM, ...)
│       │   ├── schemas.py          # Pydantic DTOs
│       │   └── tests/
│       │
│       ├── search/                 # semantic search + resonance cache
│       │   ├── routes.py           # POST /v1/search
│       │   ├── service.py
│       │   ├── logic.py            # query normalization, hash, ranking helpers
│       │   ├── models.py           # ResonanceCacheORM
│       │   ├── schemas.py
│       │   └── tests/
│       │
│       ├── ingestion/              # Open Library + Google Books
│       │   ├── service.py          # ingest_by_isbn — orchestrates lookups + writes via catalog
│       │   ├── logic.py            # response normalization (pure)
│       │   ├── clients.py          # OpenLibraryClient, GoogleBooksClient (thin httpx wrappers)
│       │   ├── schemas.py          # external response shapes
│       │   └── tests/
│       │
│       ├── generation/             # OpenAI orchestration
│       │   ├── service.py          # generate_artifacts — synopsis + profile + embedding
│       │   ├── logic.py            # compose embedding source string, validate profile JSON
│       │   ├── clients.py          # OpenAI wrapper with retry + timeouts
│       │   ├── prompts.py          # voice-locked prompt strings (mirror brand/voice §4)
│       │   ├── schemas.py
│       │   └── tests/
│       │
│       └── admin/                  # admin routes — composes ingestion, generation, catalog
│           ├── routes.py
│           ├── service.py          # workflow coordination (ingest → generate → publish)
│           ├── schemas.py
│           └── tests/
│
├── tests/
│   ├── integration/                # cross-module DB tests
│   └── e2e/                        # FastAPI AsyncClient end-to-end
└── README.md
```

### 3.2 Inside a module — functional core + imperative shell

Every module follows the same internal shape:

| File | Role | I/O? |
|---|---|---|
| `routes.py` | FastAPI router. Parses request DTOs, calls service, returns response DTOs. **No business logic.** | HTTP only |
| `service.py` | **Imperative shell.** Opens transactions, calls external services, calls `logic.py` for pure transforms, persists. | All I/O lives here |
| `logic.py` | **Functional core.** Pure functions: data → data. Slug generation, validation, ranking, hashing, string composition. | None — no DB, no httpx, no OpenAI SDK |
| `models.py` | SQLAlchemy ORM. Persistence schema only. | None directly |
| `schemas.py` | Pydantic request/response DTOs. | None |
| `prompts.py` *(generation only)* | LLM prompt strings, verbatim from `brand/voice.md §4`. | None |
| `clients.py` *(when the module integrates external APIs/SDKs)* | Thin external wrappers (httpx, openai). Called by `service.py`. | HTTP / SDK out |

A useful sanity check: if a function in `logic.py` needs to be patched with `mock.patch('...')` to test, it does not belong in `logic.py`. Move the I/O up to `service.py`.

### 3.3 Module dependency rules

Cross-module imports follow strict direction. **A module imports another module's `service.py` and `schemas.py` only.** Never `logic.py` (private), never `routes.py` (HTTP-only).

```
       ┌──────────┐
       │  admin   │
       └─┬─┬───┬──┘
         │ │   │
   ┌─────┘ │   └─────┐
   ▼       ▼         ▼
┌──────┐ ┌────────┐ ┌──────────┐
│search│ │ingest. │ │generation│
└──┬───┘ └───┬────┘ └────┬─────┘
   │         │           │
   └────┬────┴─────┬─────┘
        ▼          ▼
     ┌────────────────┐
     │    catalog     │
     └───────┬────────┘
             ▼
     ┌────────────────┐
     │     shared     │
     └────────────────┘
```

These rules mirror the skill's Mode B rules (`backend-system-architecture §3.4 M1–M8`); the project-level wording below is the operational form.

| Rule | Applies to |
|---|---|
| M1 — `shared/` imports from nothing in `sentido/` | every module |
| M2 — `catalog/` imports only from `shared/` | catalog |
| M3 — `search/`, `ingestion/`, `generation/` may import from `catalog/` and `shared/` only | spokes |
| M4 — `admin/` may import from `catalog/`, `ingestion/`, `generation/`, `shared/` | admin |
| M5 — No module imports another module's `routes.py` or `logic.py` | all |
| M6 — `logic.py` imports nothing from `sentido/` outside its own module | all |
| M7 — ORM models in `catalog.models` are the shared persistence schema; other modules may import `BookORM`/`AuthorORM` for queries. This is the conscious pragmatic exception to "service.py is the only public surface" — wrapping every cross-module DB query in a service call would reintroduce repository ceremony. | all |
| M8 — `service.py` is the only place HTTP clients, OpenAI SDK calls, and DB transactions appear | every module that does I/O |

If a circular import appears, the architecture is broken. Move the shared piece down to `shared/` or invert the dependency. Do not break M1–M8.

### 3.4 What this rejects

These were considered and explicitly rejected for v1:

- **Repository protocols + implementations.** Each `IBookRepository` / `BookRepository` pair adds two files per entity for zero v1 benefit. We use ORM models + SQLAlchemy sessions directly inside `service.py`. If we later need to swap persistence, we extract repositories then.
- **Use-case-per-verb classes** (`SearchBooksUseCase`, `IngestBookUseCase`). Replaced by module-level service functions: `search.service.semantic_search(query, limit)`, `ingestion.service.ingest_by_isbn(isbn)`.
- **A `domain/` layer with pure entity dataclasses parallel to ORM models.** We use SQLAlchemy ORM models as the persistence representation and Pydantic schemas for the API DTOs. No third "domain entity" shape. If a business invariant needs to be enforced, it lives as a pure function in `logic.py` and is called from `service.py`.
- **A `usecases/` layer.** Collapsed into module `service.py`.
- **Hexagonal ports/adapters terminology.** Same shape, different name; we use "imperative shell".

### 3.5 Naming

| Kind | Convention | Example |
|---|---|---|
| Module | lowercase noun | `catalog`, `ingestion` |
| Service function | `verb_noun` snake_case | `catalog.service.get_book_by_slug(slug)` |
| Logic function | pure verb_noun | `catalog.logic.slugify(name)` |
| ORM model | `NounORM` | `BookORM`, `ResonanceCacheORM` |
| Pydantic DTO | `NounRequest` / `NounResponse` / `NounSummary` | `SearchRequest`, `BookDetailResponse` |
| Client class | `ExternalServiceClient` | `OpenLibraryClient`, `OpenAIClient` |
| Custom exception | `XxxError` | `IsbnNotFoundError`, `GenerationFailedError` |

### 3.6 File-size discipline

When a file passes ~250 lines, split it before adding more. Common splits:

- `service.py` → `service/` package with one file per workflow (`service/ingest.py`, `service/publish.py`).
- `logic.py` → `logic/` package by concern (`logic/slug.py`, `logic/profile.py`).
- `routes.py` → `routes/` package by route group (`routes/public.py`, `routes/admin.py`).

We do not pre-split. The fact that something is 80 lines is not an excuse to make it three files.

---

## 4. Data model

This mirrors the schema in PRD §7.4 with light normalization. The backend specialist implements this in Alembic migrations + SQLAlchemy models.

### 4.1 Tables

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

CREATE TABLE authors (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  bio           TEXT,                          -- LLM, PT-BR
  nationality   TEXT,
  born          DATE,
  awards        JSONB NOT NULL DEFAULT '[]',
  ol_id         TEXT,                          -- Open Library
  wiki_url      TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE books (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug               TEXT UNIQUE NOT NULL,
  title              TEXT NOT NULL,
  original_title     TEXT,
  author_id          UUID NOT NULL REFERENCES authors(id) ON DELETE RESTRICT,
  year_published     INT,
  synopsis           TEXT,                     -- LLM, PT-BR
  emotional_profile  JSONB,                    -- see §4.2
  atmosphere_tags    TEXT[] NOT NULL DEFAULT '{}',
  narrative_pace     TEXT,                     -- 'slow' | 'progressive' | 'frenetic'
  cover_url          TEXT,
  ol_id              TEXT,
  embedding          vector(1536),
  embedding_status   TEXT NOT NULL DEFAULT 'pending',    -- 'pending' | 'done'
  profile_status     TEXT NOT NULL DEFAULT 'pending',    -- 'pending' | 'approved' | 'rejected'
  published          BOOLEAN NOT NULL DEFAULT false,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX books_published_idx ON books (published) WHERE published = true;
CREATE INDEX books_author_idx ON books (author_id);
CREATE INDEX books_embedding_idx
  ON books USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;

CREATE TABLE editions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id    UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  publisher  TEXT,
  language   TEXT,
  year       INT,
  isbn       TEXT,
  cover_url  TEXT
);

CREATE INDEX editions_book_idx ON editions (book_id);
CREATE INDEX editions_isbn_idx ON editions (isbn) WHERE isbn IS NOT NULL;

CREATE TABLE collections (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         TEXT UNIQUE NOT NULL,
  title        TEXT NOT NULL,
  description  TEXT,
  published    BOOLEAN NOT NULL DEFAULT false,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE collection_books (
  collection_id  UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  book_id        UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  position       INT NOT NULL,
  PRIMARY KEY (collection_id, book_id)
);
```

### 4.2 `emotional_profile` JSON shape

Strict shape. Validated by Pydantic in the domain layer; rejected if any key is missing or out of range.

```json
{
  "anguish": 0.0,
  "melancholy": 0.0,
  "hope": 0.0,
  "violence": 0.0,
  "tenderness": 0.0,
  "strangeness": 0.0
}
```

All values: float, range `[0.0, 10.0]`, one decimal of significance (no enforcement at DB level; enforced in domain validation).

### 4.3 Slug strategy

- `authors.slug` = ASCII-folded, lowercased, hyphenated `name`. Collision → append `-2`, `-3`, etc.
- `books.slug` = ASCII-folded, lowercased, hyphenated `title`. Collisions resolved with `-{author_lastname}`, then `-2`, `-3`.
- `collections.slug` = ASCII-folded, lowercased, hyphenated `title`.

Slugs are generated server-side on insert and never user-edited.

---

## 5. API contract — the source of truth

This is the boundary the frontend consumes. Every endpoint listed here is binding. **The frontend implementation plan mirrors this exact shape.** Any change to a response body or status code is a contract change and updates both plans atomically.

Base URL (dev): `http://localhost:8000`. Prod: `https://api.sentido.app` (placeholder domain).

All responses are JSON. All timestamps are ISO-8601 UTC. All IDs are UUIDs.

### 5.1 Public endpoints (no auth)

#### POST `/v1/search`

Semantic search. Embeds the query, runs pgvector cosine similarity over published books with `embedding_status = 'done'`.

Request:
```json
{
  "q": "solidão que não dói",
  "limit": 12
}
```
- `q`: string, 1–500 chars, required
- `limit`: int, 1–50, default 12

Response `200`:
```json
{
  "query": "solidão que não dói",
  "results": [
    {
      "slug": "o-estrangeiro",
      "title": "O Estrangeiro",
      "author_name": "Albert Camus",
      "year_published": 1942,
      "cover_url": "https://...",
      "resonance_line": "Meursault não chora; a recusa de sentir é a sua forma de existir.",
      "similarity": 0.83
    }
  ]
}
```

- `resonance_line` is generated by LLM per `(query, book)` pair on first ask and cached. Cache key: `sha256(query || book_id)`.
- `similarity` is included for debug; the frontend may hide it.

Errors:
- `400` — invalid `q` or `limit`.
- `503` — OpenAI embedding service down. Body: `{"detail": "search temporarily unavailable"}`.

#### GET `/v1/books/{slug}`

Returns the full book detail for the public page.

Response `200`:
```json
{
  "slug": "o-estrangeiro",
  "title": "O Estrangeiro",
  "original_title": "L'Étranger",
  "year_published": 1942,
  "author": {
    "slug": "albert-camus",
    "name": "Albert Camus"
  },
  "synopsis": "Meursault não chora no funeral da mãe…",
  "emotional_profile": {
    "anguish": 6.0,
    "melancholy": 4.0,
    "hope": 1.0,
    "violence": 5.0,
    "tenderness": 1.0,
    "strangeness": 8.5
  },
  "atmosphere_tags": ["apatia", "absurdo", "sol como violência"],
  "narrative_pace": "progressive",
  "cover_url": "https://...",
  "editions": [
    {"publisher": "Record", "language": "pt-BR", "year": 2014, "isbn": "9788501062451"}
  ],
  "related_books": [
    {
      "slug": "norwegian-wood",
      "title": "Norwegian Wood",
      "author_name": "Haruki Murakami",
      "cover_url": "https://...",
      "year_published": 1987
    }
  ]
}
```

- Only books with `published = true` are returned. Unpublished slugs return `404`.
- `related_books` is computed via pgvector similarity against the book's own embedding, limited to 8.
- `404` body: `{"detail": "book not found"}`.

#### GET `/v1/authors/{slug}`

Phase 1 returns a minimal payload; Phase 2 enriches.

Response `200`:
```json
{
  "slug": "albert-camus",
  "name": "Albert Camus",
  "bio": null,
  "books": [
    {"slug": "o-estrangeiro", "title": "O Estrangeiro", "cover_url": "...", "year_published": 1942}
  ]
}
```

- `bio` is `null` in Phase 1 (filled in Phase 2 via Wikipedia integration).
- Only published books appear in `books`.

#### GET `/v1/collections` *(Phase 1, minimal)*

Returns a list of published collections. Phase 2 extends with collection detail endpoints.

Response `200`:
```json
{
  "collections": [
    {"slug": "livros-que-ficam-no-corpo", "title": "Livros que ficam no corpo", "description": "…"}
  ]
}
```

#### GET `/v1/collections/{slug}`

Response `200`:
```json
{
  "slug": "livros-que-ficam-no-corpo",
  "title": "Livros que ficam no corpo",
  "description": "…",
  "books": [
    {"slug": "...", "title": "...", "author_name": "...", "cover_url": "...", "year_published": 0}
  ]
}
```

### 5.2 Admin endpoints (auth: `Authorization: Bearer {ADMIN_TOKEN}`)

The admin token is a single static value loaded from `ADMIN_TOKEN` env var. No user accounts in v1. Wrong/missing token → `401 {"detail": "unauthorized"}`.

#### The admin book object

All admin endpoints that return a book return the **admin book shape**: every field from `GET /v1/books/{slug}` plus:

```jsonc
{
  // ...all public fields...
  "id": "uuid",
  "embedding_status": "pending" | "done",
  "profile_status": "pending" | "approved" | "rejected",
  "published": true | false,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

This shape is the contract the frontend's admin pages mirror. Public endpoints never expose these fields.

#### POST `/v1/admin/books/ingest`

Adds a book to the catalog using ISBN lookup. Creates author if not yet present. Does NOT generate LLM artifacts; the book lands in `embedding_status=pending, profile_status=pending, published=false`.

Request:
```json
{"isbn": "9788501062451"}
```

Response `201`: full book object (same shape as `GET /v1/books/{slug}` but including admin-only fields `embedding_status`, `profile_status`, `published`).

Errors:
- `404` — ISBN not found in Open Library nor Google Books.
- `409` — book already exists (returns existing book in body).

#### POST `/v1/admin/books/{id}/generate`

Triggers LLM generation: synopsis + emotional_profile + embedding, in that order. Synchronous.

Request body: `{"regenerate": false}` (optional; defaults false. If `true`, overwrites existing artifacts and sets `profile_status` back to `pending`.)

Response `200`: full admin book object with generated fields filled, `profile_status=pending` (curator approval still required).

Errors:
- `404` — book id not found.
- `409` — book already has artifacts and `regenerate` is false. Body: `{"detail": "already generated; pass regenerate=true to overwrite"}`.
- `502` — OpenAI failure. Body includes upstream error message truncated to 200 chars.

#### PUT `/v1/admin/books/{id}`

Edits arbitrary fields on a book. Used by curators to clean up generated content before publishing.

Request: any subset of `{title, original_title, synopsis, emotional_profile, atmosphere_tags, narrative_pace, cover_url, year_published, profile_status, published}`. Other fields rejected with `422`.

Response `200`: updated book object.

Setting `published=true` requires `profile_status=approved` and `embedding_status=done`. Otherwise `422 {"detail": "cannot publish: profile not approved or embedding missing"}`.

#### POST `/v1/admin/books/{id}/publish`

Convenience endpoint equivalent to `PUT` with `{"profile_status": "approved", "published": true}`. Same validation rules.

Response `200`: updated book object.

#### GET `/v1/admin/books`

Lists books with admin filters. Used by the admin panel queue view.

Query params:
- `status`: one of `pending_generation`, `pending_approval`, `published`, `all`. Default: `pending_generation`.
- `limit`: 1–100, default 50.
- `offset`: ≥ 0, default 0.

Response `200`:
```json
{"books": [/* admin book objects */], "total": 137}
```

### 5.3 Health

`GET /v1/health` → `200 {"status": "ok", "version": "1.0.0"}`. No auth.

---

## 6. Lazy generation flow

The single most important flow in the backend. The curator triggers it from the admin panel; the system never auto-generates without a request.

```
admin → POST /v1/admin/books/{id}/generate
            │
            ▼
   admin.service.generate_artifacts(book_id)
   └─► generation.service.generate_artifacts(book)
            │
            ├─► load BookORM by id (via catalog query), fail 404 if missing
            │
            ├─► (1) generate synopsis
            │        └─► OpenAI gpt-4o-mini, prompt from voice §4.1
            │            (orchestrator-controlled; copied verbatim
            │             into generation/prompts.py)
            │
            ├─► (2) generate emotional_profile
            │        └─► OpenAI gpt-4o-mini, prompt from voice §4.2
            │            response_format=json_object
            │            validated by generation.logic.parse_profile() (pure)
            │
            ├─► (3) generate embedding
            │        └─► generation.logic.compose_embedding_text(book) — pure
            │             returns `{title} — {author_name}. {synopsis}
            │             Atmosfera: {atmosphere_tags joined by ", "}.
            │             Ritmo: {narrative_pace}.`
            │        └─► OpenAI text-embedding-3-small
            │
            ├─► persist all three in one transaction (single session.commit())
            │        embedding_status='done'
            │        profile_status='pending'    ← awaits curator approval
            │
            └─► return admin book object
```

Then:

```
curator reviews → PUT /v1/admin/books/{id}
                  with {"profile_status": "approved"}
                  (and optional edits to synopsis / emotional_profile)
            │
            ▼
curator publishes → POST /v1/admin/books/{id}/publish
                    sets published=true
            │
            ▼
   book is now visible to public search + book page
```

Search-time:
```
public → POST /v1/search {"q": "..."}
            │
            ▼
   search.service.semantic_search(query, limit)
            │
            ├─► search.logic.normalize_query(q) — pure
            ├─► embed normalized query (OpenAI text-embedding-3-small) — no cache
            │
            ├─► SELECT ... FROM books
            │   WHERE published = true AND embedding IS NOT NULL
            │   ORDER BY embedding <=> :query_embedding
            │   LIMIT :limit
            │
            ├─► for each result, fetch or generate resonance_line
            │   (lazy + cached by search.logic.cache_key(query, book_id))
            │
            └─► return results
```

Resonance lines are cached in a small table:
```sql
CREATE TABLE resonance_cache (
  query_hash CHAR(64) NOT NULL,
  book_id    UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  line       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (query_hash, book_id)
);
```

---

## 7. External integrations

### 7.1 OpenAI

| Use | Model | Notes |
|---|---|---|
| Synopsis | `gpt-4o-mini` | temperature 0.7, max_tokens 400, system prompt from `voice §4.1` |
| Emotional profile | `gpt-4o-mini` | temperature 0.3, `response_format={"type": "json_object"}`, prompt from `voice §4.2` |
| Resonance line | `gpt-4o-mini` | temperature 0.6, max_tokens 80, prompt from `voice §4.3` |
| Book embedding | `text-embedding-3-small` | input: composed English text (see §6) |
| Query embedding | `text-embedding-3-small` | per request, no cache |

The three voice prompts live in **`docs/brand/voice.md §4`**. The backend specialist copies them verbatim into `generation/prompts.py`. Any change to wording is a brand change — escalate to orchestrator.

Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s) on `RateLimitError` / `APIConnectionError`. Other errors propagate.

### 7.2 Open Library

- ISBN lookup: `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data`
- Author detail: `https://openlibrary.org{ol_author_key}.json`
- Cover image: `https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg` (URL only — we store the URL, we do not proxy)

Fields we extract: title, authors[*].name, publish_date, publishers[*].name, identifiers.isbn, cover URL.

User-Agent header is mandatory and configurable in `.env` (default: `Sentido/1.0 (https://sentido.app)`).

### 7.3 Google Books

Fallback only, when Open Library returns no result.

- Endpoint: `https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_BOOKS_API_KEY}`
- Quota: 1,000 req/day on free tier — fine for MVP.

### 7.4 Wikipedia / Wikidata

**Out of scope for v1.** Author bios remain `null` until Phase 2.

---

## 8. Configuration & secrets

All config via env vars, loaded by `pydantic-settings`. `.env.example` is committed; `.env` is gitignored.

| Var | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | — | `postgresql+asyncpg://...` |
| `OPENAI_API_KEY` | yes | — | |
| `OPENAI_BASE_URL` | no | `https://api.openai.com/v1` | for proxying / mocking in tests |
| `ADMIN_TOKEN` | yes | — | static bearer token for admin endpoints |
| `GOOGLE_BOOKS_API_KEY` | yes | — | even free tier requires a key |
| `OPEN_LIBRARY_USER_AGENT` | no | `Sentido/1.0` | |
| `CORS_ORIGINS` | yes | — | comma-separated list of allowed Vercel origins |
| `LOG_LEVEL` | no | `INFO` | |
| `ENV` | no | `development` | `development` \| `production` |

### 8.1 CORS

Allow `CORS_ORIGINS` for `GET, POST, PUT` and headers `Authorization, Content-Type`. Public endpoints are CORS-permissive to the frontend origin; admin endpoints share the same CORS config since the admin panel ships from the same Vercel domain.

---

## 9. Phase 0 — Foundation

Goal: a working backend skeleton with one happy-path manually-curated book end-to-end. **No frontend integration yet.**

### Deliverables

- [ ] `docker-compose.yml` running `db` + `api` (Caddy excluded from local dev; only added in prod compose).
- [ ] PostgreSQL 16 image with `pgvector` and `pgcrypto` extensions enabled.
- [ ] Alembic initialized; one migration that creates all tables in §4.
- [ ] FastAPI app skeleton with the modular structure per §3 (`shared/`, `catalog/`, `admin/` at minimum; other modules scaffolded as `service.py` stubs).
- [ ] Health endpoint `/v1/health` returning OK.
- [ ] Admin auth dependency wired and tested.
- [ ] Open Library client implemented with happy-path ISBN lookup.
- [ ] `POST /v1/admin/books/ingest` working end-to-end against Open Library.
- [ ] `POST /v1/admin/books/{id}/generate` working end-to-end against OpenAI for one book.
- [ ] `POST /v1/admin/books/{id}/publish` working with validation gates.
- [ ] `GET /v1/books/{slug}` returning the published book.
- [ ] `POST /v1/search` returning the published book when queried with a relevant phrase.

### Exit criteria
- All endpoints above respond in <500ms p50 for a catalog of 5 books.
- One end-to-end test in `tests/e2e/` walks the full ingest → generate → publish → search flow with mocked OpenAI + Open Library responses.

**Status:** not started

---

## 10. Phase 1 — MVP public

Goal: a complete admin curation flow + a public catalog of 200–500 books that the frontend can fully render.

### Deliverables (delta over Phase 0)

- [ ] `GET /v1/admin/books` with filters per §5.2.
- [ ] `PUT /v1/admin/books/{id}` with full field validation.
- [ ] `GET /v1/authors/{slug}` returning published books.
- [ ] `GET /v1/collections` + `GET /v1/collections/{slug}`.
- [ ] Google Books fallback in ISBN ingest when Open Library is silent.
- [ ] `related_books` in `GET /v1/books/{slug}` (top 8 by similarity, excluding the book itself).
- [ ] Resonance-line caching (`resonance_cache` table) + on-demand generation.
- [ ] CORS configured per §8.1.
- [ ] Production docker-compose with Caddy + HTTPS via Let's Encrypt.
- [ ] Error responses standardized (always `{"detail": "..."}`).
- [ ] Structured request logging (JSON) with request ID.

### Exit criteria
- Catalog of ≥ 200 books, all with `published=true`.
- Search p50 < 500ms over 200 books.
- Generation p50 < 15s per book (one synopsis + one profile + one embedding).
- E2E test suite covering all endpoints with mocked externals.
- Unit-test coverage for `logic.py` files ≥ 90% and `service.py` files ≥ 70% (per §12).

**Status:** not started

---

## 11. Decisions

Date format: `YYYY-MM-DD`. Each entry: rationale and what it locks down.

### D1 — Synchronous generation (2026-06-14)
Generation endpoints (`/generate`) are synchronous. No Celery, no Redis. If a generation exceeds 30 seconds (rare; gpt-4o-mini is fast), the curator retries. Async job queue is deferred to Phase 2+.
**Locks down:** no background worker in v1; admin UI shows a spinner during generation and reports the final state in the response body.

### D2 — Embedding source text in v1 (2026-06-14)
Embedding source is a deterministic PT-BR string composed at generation time: `{title} — {author_name}. {synopsis} Atmosfera: {atmosphere_tags joined by ", "}. Ritmo: {narrative_pace}.`. `text-embedding-3-small` is multilingual and performs well on PT-BR; the PRD's English-source recommendation is deferred to Phase 2 where we measure retrieval quality before adding a translation step. No extra LLM call is needed for embedding composition.
**Locks down:** if the curator edits the synopsis after generation, the embedding is **stale** until a curator-triggered regenerate. Acceptable for v1; flagged for Phase 2.

### D3 — Single admin token (2026-06-14)
No user accounts. One static bearer token in `ADMIN_TOKEN`. Sufficient for solo curator MVP. Real auth (per PRD Phase 3) replaces this surface entirely.
**Locks down:** no users table, no sessions, no roles in v1.

### D4 — Public endpoints only return published books (2026-06-14)
Unpublished books are invisible to the public — they don't appear in search, can't be loaded by slug, and aren't reachable as related books. Curator review is the publish gate.
**Locks down:** the frontend never has to handle an "unpublished book" state on public pages.

### D5 — UUIDs in URLs only for admin (2026-06-14)
Public URLs use slugs (`/v1/books/{slug}`); admin URLs use UUIDs (`/v1/admin/books/{id}`). Slugs are stable across edits; UUIDs are stable across re-slugging. Curators can rename a book in admin without breaking external links because the slug machinery handles redirects (post-MVP).
**Locks down:** any future redirect logic targets slugs.

### D6 — `pgvector` ivfflat index with lists=100 (2026-06-14)
Starting parameter for a catalog of < 5,000 books. We tune `lists` and consider HNSW if recall or speed degrades. Documented in Phase 1 exit criteria as a measurable threshold.
**Locks down:** indexing strategy is reviewed when catalog grows past 2,000 books.

### D7 — Modular monolith with functional core + imperative shell (2026-06-14)
**Declared mode for the `backend-system-architecture` skill: `modular-monolith` (Mode B).**

We reject Clean Architecture / four-layer split for this service. The product has ~11 endpoints, one core entity (books with related authors/editions/collections), a thin business-rules surface, and most of the actual complexity lives in **orchestration of external services** (OpenAI generation, Open Library lookup, Google Books fallback). For that shape, layered architecture imposes ceremony (repository protocols, use-case-per-verb classes, parallel domain entities + ORM models + DTOs) without proportional payoff.

The chosen structure: feature-shaped modules (`catalog`, `search`, `ingestion`, `generation`, `admin`, `shared`), each with `routes.py / service.py / logic.py / models.py / schemas.py`. Inside every module, pure functions (`logic.py`) carry the business transforms; the imperative shell (`service.py`) carries the I/O. This keeps the orchestration code legible — which is where most bugs will be — and keeps the business transforms trivially testable without mocks.

This declaration activates Mode B in the `backend-system-architecture` skill (the skill defaults to `clean-architecture` if no mode is declared). The specialist follows the skill's §3 (Mode B) for structure, §4 for cross-mode rules (R1–R20), and uses §3.4 M1–M8 for module boundaries (mirrored in §3.3 above).

Considered and rejected: Clean Architecture (overhead too high), vertical slice (too granular at 11 endpoints), CQRS (premature; revisit if reads outgrow writes by a wide margin in Phase 2+), service-oriented split (distribution before we have a distribution problem).

**Locks down:** module boundary rules (§3.3 M1–M8); no repository abstractions in v1; no per-verb use case classes; ORM models are the shared persistence schema, not encapsulated per module.
**Revisit if:** any single module exceeds ~1,500 lines of service.py code, or if a clear bounded context emerges that justifies extraction.

---

## 12. Testing

Tests live next to the code that owns them: each module has a `tests/` folder for its own unit + small-integration tests. Cross-module integration and end-to-end tests live in `backend/tests/` at the project root.

| Where | What | When it runs |
|---|---|---|
| `src/sentido/{module}/tests/` | **logic.py** tested directly (pure, no mocks). **service.py** tested with a real test DB (`db_test`) and httpx/OpenAI mocked at the module's client boundary. | every commit; <30s total |
| `tests/integration/` | Cross-module workflows (e.g., admin orchestrating ingestion → generation → publish) against the real test DB with external clients mocked. | every commit; <30s total |
| `tests/e2e/` | FastAPI `AsyncClient` exercising endpoints end to end with the same external mocks. | every commit; <30s total |

We do not call real OpenAI or Open Library in tests. Recorded responses live in `tests/fixtures/`.

Coverage targets: ≥ 90% for `logic.py` files (trivial — they're pure), ≥ 70% for `service.py` files, no target for `routes.py` (exercised by e2e), no target for `models.py` / `schemas.py` (declarative).

If a `logic.py` function ever requires a mock to test, it has I/O in it and belongs in `service.py`. Fix the placement, not the test.

---

## 13. Open items routed back to orchestrator

The backend specialist does not resolve these — they require orchestrator decisions and (in some cases) PRD clarifications:

1. **Cover image hosting.** PRD §6.3 says we store the Open Library cover URL. If Open Library rate-limits the frontend or covers move, we have no plan. Acceptable for v1 (URLs are stable in practice); flagged for Phase 2.
2. **Resonance-line cache eviction.** No eviction in v1. Cache grows monotonically. Acceptable for v1; flagged if the table exceeds 1M rows.
3. **Embedding regeneration semantics.** D2 says synopsis edits don't rebuild the embedding. If editorial decides synopsis is meaningful for retrieval, D2 changes — and Phase 2 reopens.

When a Phase 2 question becomes load-bearing, the specialist reports back; the orchestrator amends this plan.
