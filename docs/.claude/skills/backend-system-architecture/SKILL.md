---
name: backend-system-architecture
description: Use when writing, reviewing, or refactoring Python backend services — FastAPI routes, Pydantic DTOs, application logic, persistence, external integrations, dependency injection, configuration, and tests. Supports two architecture modes — Clean Architecture (default) and Modular Monolith with functional core + imperative shell. The project's backend implementation plan declares the mode in its decisions section. Do NOT use for one-off scripts, data analysis notebooks, frontend code, ML training pipelines, or non-Python services.
---

# Backend System Architecture

You are building a Python backend service. Every decision must follow the patterns below. These are load-bearing rules — code that violates them blocks merge.

This skill supports **two architecture modes**. Cross-cutting rules (SOLID, configuration, errors, testing, tech baseline) apply to both modes. The mode-specific sections govern structure, naming, and the canonical example.

---

## 0. Architecture mode selection

Before writing any code, identify the mode declared by the project's **backend implementation plan**. The plan's decisions section names the active mode.

| Mode | When chosen | Section |
|---|---|---|
| **clean-architecture** (default) | Services with rich domain models, multi-team contributions, or where strict layer testability outweighs ceremony cost. | §2 |
| **modular-monolith** | Single-team services with thin business rules where most complexity is orchestration of external services. Smaller scope (≲ 20 endpoints), no expected domain explosion. | §3 |

If the plan does not name a mode, the default is `clean-architecture`. A plan that wants modular-monolith records the decision explicitly with rationale.

**Sections below labeled "(Mode A)" apply only in Clean Architecture mode. Sections labeled "(Mode B)" apply only in Modular Monolith mode. Everything else applies to both.**

---

## 1. SOLID Principles — Non-Negotiable (Both modes)

**Single Responsibility.** Each class, module, or service function has one reason to change. One use case per file (Mode A) or one feature per module (Mode B). One mapper per data transformation. One client per external service.

**Open/Closed.** Adding a new operation must not require editing existing code. New behavior plugs in through existing interfaces (Mode A) or by adding a new service function or module (Mode B).

**Liskov Substitution.** Any adapter implementing an interface must be substitutable for any other. Test fakes and production adapters interchangeable.

**Interface Segregation.** Interfaces and module surfaces are small and purpose-specific. A consumer that needs reads must not depend on a surface that also exposes writes.

**Dependency Inversion.** High-level components depend on abstractions, not on concrete infrastructure. In Mode A, abstractions are `Protocol`s in `domain/`. In Mode B, abstractions are service function signatures with explicit dependency parameters — the caller passes them in; the service does not construct them.

---

## 2. Mode A — Clean Architecture

Four layers with inward dependencies. Choose this when no mode is declared or the plan explicitly declares `clean-architecture`.

### 2.1 Layer diagram

```
+------------------------------------------------------------------+
|                         API LAYER                                |
|  FastAPI routes, DTOs, dependency injection                      |
|  Handles HTTP, serialization, input validation                   |
+------------------------------------------------------------------+
        |                                         |
        v                                         v
+------------------------------------------------------------------+
|                     APPLICATION LAYER                            |
|  Use Cases — one class per operation                             |
|  Orchestrates domain work, framework-agnostic                    |
+------------------------------------------------------------------+
        |
        v
+------------------------------------------------------------------+
|                       DOMAIN LAYER                               |
|  Entities, Repository Interfaces (Protocols)                     |
|  Pure business models, no framework, no I/O                      |
+------------------------------------------------------------------+
        ^
        | (infrastructure implements domain interfaces;
        |  this arrow points up because infra depends on
        |  domain, not the reverse)
+------------------------------------------------------------------+
|                    INFRASTRUCTURE LAYER                          |
|  API clients, repository implementations, mappers, database      |
|  Implements domain interfaces, handles external communication    |
+------------------------------------------------------------------+
```

Dependencies flow inward ONLY. Outer layers depend on inner layers, never the reverse. Domain never imports from infrastructure or API.

### 2.2 Layer responsibilities (Mode A)

**API layer** (`api/`)
- FastAPI routes, Pydantic DTOs, dependency wiring via `Depends()`.
- Validates input, calls use case, maps result to HTTP response.
- No business logic. No direct calls to repositories or external APIs.
- Error translation: `None` returns → 502, `ValueError` → 400, unhandled → 500.

**Application layer** (`application/`)
- One use case class per meaningful operation (e.g., `CreateOrderUseCase`).
- Each use case exposes a single `execute()` method.
- Orchestrates domain work by calling repository interfaces. Does not implement transport or persistence.
- Framework-agnostic — no FastAPI, no HTTP, no SQL.

**Domain layer** (`domain/`)
- Pure entities (`domain/entities/`) — Pydantic models with no framework dependencies beyond Pydantic for validation.
- Repository interfaces (`domain/repositories/`) — Python `Protocol`s defining the contract.
- No I/O, no imports from infrastructure or api.

**Infrastructure layer** (`infrastructure/`)
- Concrete implementations of domain interfaces.
- API clients for external services.
- Mappers that transform external data formats into domain entities.
- Database adapters, ORM models, session factories.

### 2.3 Directory structure (Mode A)

```
service/
└── src/
    ├── core/                         App initialization & config
    │   ├── app.py                    FastAPI app + router registration
    │   └── config.py                 Pydantic Settings (single env reader)
    │
    ├── api/                          API layer
    │   ├── dependencies.py           DI wiring (Depends() providers)
    │   ├── dtos/                     Pydantic request/response models
    │   └── routes/                   FastAPI route handlers
    │
    ├── application/                  Use cases (one file per operation)
    │
    ├── domain/                       Pure core
    │   ├── entities/                 Business models (Pydantic, no I/O)
    │   └── repositories/             Interface contracts (Protocols)
    │
    ├── infrastructure/               External integrations
    │   ├── clients/                  API clients per external service
    │   ├── repositories/             Repository implementations
    │   ├── mappers/                  Data transformation (external → entity)
    │   └── database/                 ORM models, session factory (if needed)
    │
    └── tests/
        ├── unit/                     Per-layer unit tests with fakes
        └── integration/              Cross-layer tests (DB, real adapters)
```

### 2.4 Boundary rules (Mode A)

- **B1.** External clients may only call the API layer. No direct calls to use cases, repositories, or infrastructure.
- **B2.** Only infrastructure adapters talk to external services. No other layer holds URLs, credentials, or SDK clients.
- **B3.** Domain code is pure. No network calls, no file I/O, no framework imports (except Pydantic for validation).
- **B4.** Use cases orchestrate — they do not implement transport, persistence, or data mapping.

### 2.5 Request flow (Mode A)

```
HTTP request
   → Route handler (api/routes/)
   → DTO validates input (api/dtos/)
   → Use case injected via Depends() (application/)
   → Use case calls repository interface (domain/repositories/)
   → Repository implementation calls API client / DB (infrastructure/)
   → Mapper converts external response → domain entity (infrastructure/mappers/)
   → Entity returned up the stack (or None on infra failure)
   → Route maps entity → response DTO
   → HTTP response
```

A route never calls an API client directly. A use case never imports `httpx`.

### 2.6 Canonical example (Mode A)

A minimal end-to-end slice. Use this as the template for new operations in Mode A.

#### `domain/entities/order.py`
```python
from pydantic import BaseModel

class Order(BaseModel):
    id: str
    customer_id: str
    total_cents: int
    status: str
```

#### `domain/repositories/order_repository.py`
```python
from typing import Protocol
from domain.entities.order import Order

class IOrderRepository(Protocol):
    async def get(self, order_id: str) -> Order | None: ...
```

#### `application/get_order.py`
```python
from domain.entities.order import Order
from domain.repositories.order_repository import IOrderRepository

class GetOrderUseCase:
    def __init__(self, orders: IOrderRepository) -> None:
        self._orders = orders

    async def execute(self, order_id: str) -> Order | None:
        return await self._orders.get(order_id)
```

#### `infrastructure/clients/orders_api_client.py`
```python
import httpx
import structlog

log = structlog.get_logger()

class OrdersAPIClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url

    async def fetch_order(self, order_id: str) -> dict | None:
        try:
            r = await self._http.get(f"{self._base_url}/orders/{order_id}")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            log.warning("orders_api_fetch_failed", order_id=order_id, error=str(e))
            return None
```

#### `infrastructure/mappers/order_mapper.py`
```python
from domain.entities.order import Order

def to_order(payload: dict) -> Order:
    return Order(
        id=payload["id"],
        customer_id=payload["customerId"],
        total_cents=payload["totalCents"],
        status=payload["status"],
    )
```

#### `infrastructure/repositories/order_repository.py`
```python
from domain.entities.order import Order
from infrastructure.clients.orders_api_client import OrdersAPIClient
from infrastructure.mappers.order_mapper import to_order

class OrderRepository:
    def __init__(self, client: OrdersAPIClient) -> None:
        self._client = client

    async def get(self, order_id: str) -> Order | None:
        payload = await self._client.fetch_order(order_id)
        return to_order(payload) if payload else None
```

#### `api/dtos/order_dtos.py`
```python
from pydantic import BaseModel

class OrderResponse(BaseModel):
    id: str
    customer_id: str
    total_cents: int
    status: str
```

#### `api/dependencies.py`
```python
from fastapi import Depends, Request
from application.get_order import GetOrderUseCase
from infrastructure.repositories.order_repository import OrderRepository

def get_order_repository(request: Request) -> OrderRepository:
    return OrderRepository(client=request.app.state.orders_client)

def get_order_use_case(
    repo: OrderRepository = Depends(get_order_repository),
) -> GetOrderUseCase:
    return GetOrderUseCase(orders=repo)
```

#### `api/routes/orders.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from api.dtos.order_dtos import OrderResponse
from application.get_order import GetOrderUseCase
from api.dependencies import get_order_use_case

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    use_case: GetOrderUseCase = Depends(get_order_use_case),
) -> OrderResponse:
    order = await use_case.execute(order_id)
    if order is None:
        raise HTTPException(status_code=502, detail="Upstream order service unavailable")
    return OrderResponse(**order.model_dump())
```

#### `tests/unit/application/test_get_order.py`
```python
import pytest
from domain.entities.order import Order
from application.get_order import GetOrderUseCase

class FakeOrderRepo:
    def __init__(self, order: Order | None) -> None:
        self._order = order
    async def get(self, order_id: str) -> Order | None:
        return self._order

@pytest.mark.asyncio
async def test_returns_order_when_found():
    order = Order(id="o1", customer_id="c1", total_cents=999, status="paid")
    use_case = GetOrderUseCase(orders=FakeOrderRepo(order))
    assert await use_case.execute("o1") == order

@pytest.mark.asyncio
async def test_returns_none_when_missing():
    use_case = GetOrderUseCase(orders=FakeOrderRepo(None))
    assert await use_case.execute("o1") is None
```

---

## 3. Mode B — Modular Monolith (Functional Core + Imperative Shell)

Feature-shaped modules with strict role separation inside each module. Choose this when the implementation plan explicitly declares `modular-monolith`.

### 3.1 Module diagram

```
       ┌──────────┐
       │  admin   │   composes the others
       └─┬─┬───┬──┘
   ┌─────┘ │   └─────┐
   ▼       ▼         ▼
┌──────┐ ┌────────┐ ┌──────────┐
│ ...  │ │  ...   │ │   ...    │   feature modules (spokes)
└──┬───┘ └───┬────┘ └────┬─────┘
   └────┬────┴─────┬─────┘
        ▼          ▼
     ┌────────────────┐
     │  core module   │   owns shared ORM models for core entities
     └───────┬────────┘
             ▼
     ┌────────────────┐
     │     shared     │   config, db, auth, errors, http
     └────────────────┘
```

Dependency direction is one-way. The hub-and-spoke shape keeps the graph acyclic and lets you delete or extract a spoke later.

### 3.2 Inside a module — functional core + imperative shell

Every module follows the same internal shape:

| File | Role | I/O? |
|---|---|---|
| `routes.py` | FastAPI router. Parses request DTOs, calls service, returns response DTOs. **No business logic.** | HTTP only |
| `service.py` | **Imperative shell.** Opens transactions, calls external services, calls `logic.py` for pure transforms, persists. | All I/O lives here |
| `logic.py` | **Functional core.** Pure functions: data → data. Slug generation, validation, ranking, hashing, string composition. | None — no DB, no httpx, no SDKs |
| `models.py` | SQLAlchemy ORM. Persistence schema. | Declarative |
| `schemas.py` | Pydantic request/response DTOs. | None |
| `clients.py` (when applicable) | Thin external API wrappers (httpx). Called by `service.py`. | HTTP out |
| `prompts.py` (LLM modules) | LLM prompt strings, verbatim from brand voice / spec. | None |

Sanity check: if a function in `logic.py` needs to be patched with `mock.patch('...')` to test, it has I/O and belongs in `service.py`. Move the I/O up; do not weaken `logic.py`.

### 3.3 Directory structure (Mode B)

```
service/
└── src/
    └── {service_name}/
        ├── main.py                  FastAPI app factory; mounts module routers
        │
        ├── shared/                  Cross-module infrastructure
        │   ├── config.py            pydantic-settings
        │   ├── db.py                Async session factory + FastAPI dependency
        │   ├── auth.py              Auth dependencies (e.g., admin token guard)
        │   ├── errors.py            ApiError + exception handlers
        │   └── http.py              Shared httpx client factory
        │
        ├── {core_module}/           Owns core entities and ORM models
        │   ├── routes.py
        │   ├── service.py
        │   ├── logic.py
        │   ├── models.py            SQLAlchemy ORM (shared persistence schema)
        │   ├── schemas.py
        │   └── tests/
        │
        ├── {feature_module}/        Each feature module follows the same shape
        │   ├── routes.py            (omit if module is internal-only)
        │   ├── service.py
        │   ├── logic.py
        │   ├── clients.py           (when integrating an external API)
        │   ├── prompts.py           (when calling an LLM)
        │   ├── schemas.py
        │   └── tests/
        │
        └── admin/                   Admin module composes feature modules
            ├── routes.py
            ├── service.py
            ├── schemas.py
            └── tests/

tests/
├── integration/                     Cross-module DB tests
└── e2e/                             FastAPI AsyncClient end-to-end
```

The core module owns the ORM models for shared entities (e.g., a `catalog` module owns `BookORM`, `AuthorORM`). Feature modules may import those ORM classes for queries — see M7.

### 3.4 Module dependency rules (Mode B)

A module imports another module's `service.py` and `schemas.py` only. Never `logic.py` (private), never `routes.py` (HTTP-only).

- **M1.** `shared/` imports from nothing within the service.
- **M2.** The core module imports only from `shared/`.
- **M3.** Feature modules (spokes) may import from the core module and `shared/`. They do not import from each other.
- **M4.** The admin module may import from any other module + `shared/`.
- **M5.** No module imports another module's `routes.py` or `logic.py`.
- **M6.** `logic.py` imports nothing from sibling modules — it depends only on stdlib, Pydantic, and its own module.
- **M7.** ORM models in the core module's `models.py` are the **shared persistence schema**. Other modules may import the ORM classes for queries directly. This is the conscious pragmatic exception to "service.py is the only public surface": wrapping every cross-module DB query in a service call would reintroduce repository ceremony. Use this exception for reads/writes that are genuinely persistence-shaped; use the service surface for anything that involves orchestration.
- **M8.** `service.py` is the only place HTTP clients, SDK calls, and DB transactions appear.

If a circular import appears, the architecture is broken. Move the shared piece down to `shared/`, or invert the dependency. Do not break M1–M8.

### 3.5 What this mode rejects

These layered-architecture patterns are explicitly rejected in modular-monolith mode:

- **Repository protocols + implementations.** Use ORM models + sessions directly inside `service.py`. If we later need to swap persistence, we extract repositories then.
- **Use-case-per-verb classes.** Replaced by module-level service functions: `catalog.service.get_book_by_slug(slug)`, `ingestion.service.ingest_by_isbn(isbn)`.
- **A `domain/` layer with pure entity dataclasses parallel to ORM models.** ORM models are the persistence representation; Pydantic schemas are the API DTOs; pure invariants live in `logic.py` and are called from `service.py`.
- **An `application/` or `usecases/` layer.** Collapsed into module `service.py`.

If a project genuinely needs any of these, the implementation plan should be re-evaluated against §0 — likely it should declare `clean-architecture`, not graft layers onto modular-monolith.

### 3.6 Request flow (Mode B)

```
HTTP request
   → Route handler ({module}/routes.py)
   → DTO validates input ({module}/schemas.py)
   → Service function called ({module}/service.py)
   → service.py opens a transaction, calls pure functions ({module}/logic.py),
     calls external clients ({module}/clients.py or another module's service),
     persists via ORM (own models.py or the core module's)
   → service.py returns a domain-shaped result (ORM object, dict, or Pydantic)
   → Route maps result → response DTO
   → HTTP response
```

The route never runs SQL or calls an external SDK. `service.py` is the orchestration spine.

### 3.7 File-size discipline (Mode B)

When a file passes ~250 lines, split it before adding more. Common splits:

- `service.py` → `service/` package, one file per workflow (`service/ingest.py`, `service/publish.py`).
- `logic.py` → `logic/` package by concern (`logic/slug.py`, `logic/profile.py`).
- `routes.py` → `routes/` package by route group (`routes/public.py`, `routes/admin.py`).

Do not pre-split. An 80-line file is fine.

### 3.8 Canonical example (Mode B)

A minimal end-to-end slice in modular-monolith mode. Use this as the template for new endpoints in Mode B.

#### `{service_name}/shared/db.py`
```python
from collections.abc import AsyncIterator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True)

async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session
```

#### `{service_name}/orders/models.py`
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class OrderORM(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str]
    total_cents: Mapped[int]
    status: Mapped[str]
```

#### `{service_name}/orders/schemas.py`
```python
from pydantic import BaseModel

class OrderResponse(BaseModel):
    id: str
    customer_id: str
    total_cents: int
    status: str
```

#### `{service_name}/orders/logic.py` (functional core — pure)
```python
def is_payable(status: str) -> bool:
    return status in {"pending", "awaiting_payment"}

def total_in_brl(total_cents: int) -> str:
    return f"R$ {total_cents / 100:.2f}"
```

#### `{service_name}/orders/service.py` (imperative shell — all I/O)
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from orders.models import OrderORM
from orders.schemas import OrderResponse

async def get_order(session: AsyncSession, order_id: str) -> OrderResponse | None:
    order = await session.scalar(select(OrderORM).where(OrderORM.id == order_id))
    if order is None:
        return None
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        total_cents=order.total_cents,
        status=order.status,
    )
```

Service functions take their dependencies (the session) as parameters. No DI provider class — composition happens at the route boundary via `Depends()`.

#### `{service_name}/orders/routes.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db import get_session
from orders import service
from orders.schemas import OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
) -> OrderResponse:
    order = await service.get_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order
```

The route is thin: parse path, call service, raise HTTP error if needed, return DTO.

#### `{service_name}/orders/tests/test_logic.py` (no fixtures, no mocks)
```python
from orders.logic import is_payable, total_in_brl

def test_is_payable():
    assert is_payable("pending") is True
    assert is_payable("paid") is False

def test_total_in_brl():
    assert total_in_brl(12345) == "R$ 123.45"
```

#### `{service_name}/orders/tests/test_service.py` (real test DB)
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from orders import service

@pytest.mark.asyncio
async def test_get_order_returns_none_when_missing(test_session: AsyncSession):
    assert await service.get_order(test_session, "missing") is None
```

This slice demonstrates the mode: pure logic in `logic.py`, all I/O in `service.py`, thin routes, ORM as the persistence representation, no repository abstraction, dependencies passed as parameters.

---

## 4. Cross-mode rules (Both modes)

These rules apply regardless of mode.

### 4.1 Configuration
- **R1.** All config is read from environment variables via a single Pydantic Settings class (Mode A: `core/config.py`; Mode B: `shared/config.py`). No other file imports `os.environ` or `os.getenv`.
- **R2.** Secrets never land in source code. No hardcoded API keys, passwords, or tokens.
- **R3.** No YAML or TOML config files. Env vars only (with `.env` file support via `pydantic-settings`).

### 4.2 Dependency wiring
- **R4 (Mode A).** DI is wired in one place: `api/dependencies.py`. Provider chains build the use case bottom-up: client → repository → use case.
- **R4 (Mode B).** Cross-request dependencies (sessions, HTTP clients, settings) are exposed via FastAPI `Depends()` factories in `shared/` (e.g., `shared/db.py::get_session`, `shared/auth.py::require_admin`). Service functions take dependencies as parameters (not through a `Depends()` chain inside the service). Composition happens at the route boundary.
- **R5.** Each dependency factory builds at most one resource. Composition happens at the call site.
- **R6.** Dependencies expensive to construct (HTTP clients, DB engines, settings) are built **once at app startup** using FastAPI's `lifespan` handler and stored on `app.state`. Dependency providers retrieve them from `app.state`; they do not construct new instances per request. Misconfiguration must fail at startup, not at first request.

### 4.3 Error Handling
- **R7.** Infrastructure exceptions (e.g., `HTTPStatusError`, `OperationalError`) never leak into the route layer. The orchestration layer (use cases in Mode A; `service.py` in Mode B) catches them, logs them, and either returns `None`/a domain-shaped result or raises a domain-defined error.
- **R8.** API layer translates: `None` (where it means "upstream said nothing") → HTTP 502; missing-resource semantics → HTTP 404; `ValueError` → HTTP 400; unhandled → HTTP 500.
- **R9.** Adding error handling, fallbacks, or retries requires a documented failure mode. Speculative `try/except` is not acceptable.
- **R10.** No retry libraries (`tenacity`, etc.). When retry logic is needed, write it explicitly with a bounded loop, fixed or exponential backoff, and a maximum attempt count — and document why retry is justified at that call site.

### 4.4 Data Transformation
- **R11.** External data formats (XML, JSON from third parties) stay in the integration boundary (Mode A: `infrastructure/`; Mode B: the module's `clients.py`). Internal layers never see raw external shapes.
- **R12 (Mode A).** Dedicated mapper files in `infrastructure/mappers/` transform external formats → domain entities. No raw dicts in domain code.
- **R12 (Mode B).** Pure functions in `logic.py` transform external responses → domain shape. Dedicated `mappers.py` files are not required unless a `logic.py` exceeds 250 lines.
- **R13.** API-layer DTOs are separate from the persistence representation (entities in Mode A; ORM models in Mode B). No bidirectional coupling — a Pydantic DTO never inherits from an ORM model or vice versa.

### 4.5 Testing
- **R14.** Every use case (Mode A) and every service function (Mode B) has at least one unit or service-level test using `pytest`.
- **R15 (Mode A).** External dependencies are tested with hand-written fakes implementing the domain `Protocol`. Prefer fakes over `MagicMock(spec=...)`.
- **R15 (Mode B).** Pure `logic.py` functions are tested directly without mocks or fixtures — they take data and return data. `service.py` functions are tested against a real test database (testcontainers or local) with external clients faked at the HTTP boundary (`httpx.MockTransport`) or the SDK boundary.
- **R16.** LLM-dependent logic is tested with deterministic fakes. Real-LLM tests are opt-in and excluded from default `pytest` runs (e.g., marked `@pytest.mark.llm` and gated behind an env flag).
- **R17 (Mode A).** Tests live in `tests/unit/` and `tests/integration/`, mirroring the source tree.
- **R17 (Mode B).** Module-internal tests live in `{module}/tests/`. Cross-module integration tests and e2e tests live in `tests/integration/` and `tests/e2e/` at the project root.

### 4.6 General
- **R18.** No feature flags or compatibility shims for code that has not yet shipped.
- **R19.** No speculative abstractions. If there is only one implementation of an interface (Mode A) or only one caller of a service function (Mode B), that is fine.
- **R20.** Breaking changes to inbound or outbound contracts require a new version (e.g., `v2/` DTO folder or `routes/v2/`), not a mutation of the existing one.

---

## 5. Technology Baseline (Both modes)

Use ONLY these packages unless explicitly approved.

### Runtime
| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server (dev) |
| `gunicorn` | Process manager (prod) |
| `pydantic` | Validation, entities, DTOs |
| `pydantic-settings` | Env var loading |
| `httpx` | Async HTTP client |
| `structlog` | Structured JSON logging |

### Conditionally allowed (only if the service needs them)
| Package | When |
|---|---|
| `sqlalchemy` + `alembic` | Service has a database |
| `psycopg2-binary` or `asyncpg` | PostgreSQL adapter |
| `redis[hiredis]` | Service uses Redis |
| `openai` | Service calls OpenAI or Azure OpenAI |
| `defusedxml` + `xmltodict` | Service parses XML (XXE prevention) |
| `requests` | Only for maintaining existing sync code; new code uses `httpx` |
| `pgvector` | Service uses vector similarity in Postgres |

### NOT allowed
| Package | Why |
|---|---|
| `langchain`, `langchain-*`, `langgraph` | Unnecessary abstraction over LLM SDKs |
| `crewai`, `autogen`, `swarm` | No agent frameworks |
| `celery`, `dramatiq` | No background job queues by default — if needed, raise to orchestrator |
| `tenacity` | No retry decorator libraries |
| `pyyaml` | No YAML config |

---

## 6. Mode selection checklist

When the implementation plan declares a mode, verify the choice with this checklist. If a plan declares `modular-monolith` but the project answers "yes" to most Mode A indicators, raise the concern back to the orchestrator before building.

**Indicators that Mode A (Clean Architecture) is the right choice:**
- The service has > 20 distinct operations / endpoints.
- The domain has rich invariants enforced across multiple entities (e.g., financial, healthcare, multi-tenant authorization).
- Multiple teams contribute, and the layered split protects independent evolution.
- The service is expected to extract one or more bounded contexts into independent services within 12 months.

**Indicators that Mode B (Modular Monolith) is the right choice:**
- The service has ≤ 20 endpoints organized into 3–7 natural feature areas.
- Most complexity lives in orchestrating external services (HTTP APIs, SDKs, queues), not in domain invariants.
- A single team owns the service.
- The product surface is stable; no near-term plan to split.

A plan that picks the wrong mode for the shape of the work creates either over-engineering (Mode A on a small service) or under-structure (Mode B on a complex domain). When in doubt, default to Mode A.
