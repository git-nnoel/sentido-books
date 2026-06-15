# Sentido — local-dev shortcuts.
#
# All commands are run from the repo root. Most just wrap
# `docker compose ...` with sensible defaults.
#
#   make setup          first-boot: copy backend/.env.example → backend/.env
#   make up             start db + migrate + api
#   make down           stop all services (volumes preserved)
#   make logs           tail api logs
#   make migrate        re-run alembic upgrade head
#   make psql           open a psql shell against the dev database
#   make shell          open a bash shell inside the api container
#   make ps             status of all services
#   make health         curl /v1/health
#   make rebuild        rebuild images without cache + restart
#   make nuke           stop + delete volumes (DESTROYS DATA)

# ─────────────────────────────────────────────────────────────────────────────
# Config — these have safe defaults and can be overridden in the environment.
# ─────────────────────────────────────────────────────────────────────────────

POSTGRES_USER     ?= sentido
POSTGRES_DB       ?= sentido

.PHONY: help setup up down logs migrate psql shell ps health rebuild nuke

help:
	@awk 'BEGIN{FS=":.*##"; print "Sentido — make targets:\n"} \
	      /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' \
	      $(MAKEFILE_LIST)

setup: ## copy backend/.env.example → backend/.env (no-clobber)
	@if [ -f backend/.env ]; then \
	  echo "backend/.env already exists — leaving it alone."; \
	else \
	  cp backend/.env.example backend/.env; \
	  echo "backend/.env created from .env.example."; \
	  echo "→ Edit it and fill in OPENAI_API_KEY + ADMIN_TOKEN before \`make up\`."; \
	fi

up: ## build + start db + migrate + api
	docker compose up -d --build

down: ## stop services (volumes preserved)
	docker compose down

logs: ## tail api logs
	docker compose logs -f api

migrate: ## re-run alembic upgrade head (re-creates the one-shot)
	docker compose run --rm migrate

psql: ## open a psql shell against the dev database
	docker compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

shell: ## open a bash shell inside the api container
	docker compose exec api bash

ps: ## status of all services
	docker compose ps

health: ## curl /v1/health
	@curl -sS http://localhost:8000/v1/health | python3 -m json.tool 2>/dev/null \
	  || curl -sS http://localhost:8000/v1/health || echo "api not reachable"

rebuild: ## rebuild images without cache + restart
	docker compose build --no-cache
	docker compose up -d

nuke: ## stop + DELETE volumes (DESTROYS dev DB)
	@printf "This deletes the dev database. Type YES to confirm: "; \
	read confirm; \
	if [ "$$confirm" = "YES" ]; then \
	  docker compose down -v; \
	  echo "Volumes removed."; \
	else \
	  echo "Aborted."; \
	fi
