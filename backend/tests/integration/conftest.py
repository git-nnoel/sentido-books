"""Integration-test fixtures.

The shared DB fixtures (``test_engine``, ``test_session``,
``admin_token``) live at ``backend/conftest.py`` so they can be
consumed by both cross-module integration tests under ``tests/`` and
module-level service tests under ``src/sentido/<module>/tests/`` (e.g.
generation's service test in B4 reuses the same ``test_session``).

**Test-DB strategy** (kept here for proximity to integration tests):

We run integration tests against the same Postgres container that
the repo-root ``docker-compose.yml`` starts for development, but in a
**separate database** named ``sentido_test``. Rationale:

- **Why not testcontainers?** It pulls a fresh image per process and
  needs Docker Python bindings, which adds friction for solo-developer
  iteration. The dev container is already running for normal work.
- **Why not the dev DB directly?** Integration tests truncate tables;
  the curator's real data would vanish on every run.
- **Why a separate database, not a separate schema?** pgvector
  extensions are per-database in Postgres. Cleanly tearing down a
  schema would still leave the extension on the dev DB.

Bootstrapping (idempotent, runs once per pytest session):
  1. Connect to the maintenance DB (``postgres``) as the ``sentido``
     role and ``CREATE DATABASE sentido_test`` if missing.
  2. Connect to ``sentido_test`` and ``CREATE EXTENSION IF NOT EXISTS
     vector`` + ``pgcrypto``.
  3. Drop + recreate all ORM tables via ``Base.metadata`` rather than
     running Alembic. Keeps tests fast and removes Alembic from the
     test path; Alembic itself is covered by the ``alembic upgrade
     head`` smoke step.
"""

from __future__ import annotations
