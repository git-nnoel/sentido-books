# Multi-stage Python image for the sentido api service.
# Stage 1 (deps): build a virtualenv from pyproject.toml.
# Stage 2 (runtime): copy the venv + source.
#
# B1 (this task) only requires the image to build successfully; B2 wires
# in the real entrypoint (uvicorn/gunicorn).
#
# Lockfile follow-on (post-B1): for reproducible builds, run locally
#   `pip-compile pyproject.toml -o requirements.lock.txt`
# then switch the install command in stage 1 to
#   `pip install -r requirements.lock.txt`
# pip-compile requires pip-tools, which is in pyproject.toml [dev] extras
# but cannot be generated from the agent sandbox or this orchestrator env.

# ---------- Stage 1: deps ----------
FROM python:3.12-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build-time deps for asyncpg / pgvector wheels. Slim image lacks gcc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Install from pyproject.toml. Switch to `pip install -r requirements.lock.txt`
# once the lockfile is generated locally with pip-compile (see header comment).
# `src/` is copied here because pyproject.toml declares `packages.find:
# where = ["src"]` — setuptools needs the source present at install time to
# discover the package. Once requirements.lock.txt exists this whole stage
# can install dependencies directly without needing the source.
COPY pyproject.toml /build/pyproject.toml
COPY README.md /build/README.md
COPY src /build/src
RUN pip install --upgrade pip \
 && pip install /build

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Runtime-only system deps (libpq for asyncpg's runtime symbols).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=deps /opt/venv /opt/venv

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY src /app/src

EXPOSE 8000

# Production-style entrypoint. The dev compose overrides this with
# `--reload` so source-tree edits hot-reload (see docker-compose.yml).
CMD ["uvicorn", "sentido.main:app", "--host", "0.0.0.0", "--port", "8000"]
