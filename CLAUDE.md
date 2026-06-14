# Sentido — project orientation for Claude

> Read this before doing anything in this repository. It tells you what this project is, where the canonical docs live, and which docs you read vs. which docs you do not.

---

## What this is

**Sentido** is a semantic catalog of books indexed by feeling, atmosphere, and resonance — not by genre or popularity. Users query in natural language ("solidão que não dói") and the system returns books that match the experience of reading them, via OpenAI embeddings + pgvector.

Stack: Next.js 14 (frontend on Vercel) + FastAPI (Python, backend on a VPS) + PostgreSQL with pgvector + OpenAI (`gpt-4o-mini` for generation, `text-embedding-3-small` for embeddings).

---

## Roles

This project uses a **three-role orchestration model** built on top of the `developers-orchestration` skill:

| Role | Who | What they read | What they write |
|---|---|---|---|
| **Orchestrator** | You (default Claude session) | All four canonical artifacts (§Artifacts below) | The two implementation plans + this file. **Never writes code in backend or frontend code territory.** |
| **Backend specialist** | `backend-developer-specialist` sub-agent | `docs/instructions/backend-implementation-plan.md` only | Backend code under the path the plan declares |
| **Frontend specialist** | `frontend-developer-specialist` sub-agent | `docs/instructions/frontend-implementation-plan.md` only + `docs/brand/` | Frontend code under the path the plan declares |

**Specialists DO NOT read the product specification (`docs/product/prd.md`).** The orchestrator paraphrases relevant requirements into the implementation plans. This is a load-bearing rule from the orchestration skill — it forces the orchestrator to do the translation work and keeps specialists focused on a single source.

---

## Artifacts

The four canonical artifacts that govern this project:

| Artifact | Path | Owner | Mutability |
|---|---|---|---|
| **Product specification** | `docs/product/prd.md` | User (Pedro) | Mutated only by Pedro |
| **Brand reference** | `docs/brand/` (6 files) | Orchestrator + Pedro | Mutated deliberately; treated as immutable input for the visual system |
| **Backend implementation plan** | `docs/instructions/backend-implementation-plan.md` | Orchestrator | Updated when scope, contract, or decisions change |
| **Frontend implementation plan** | `docs/instructions/frontend-implementation-plan.md` | Orchestrator | Same as backend — atomic updates when the contract changes |

The canonical mobile mockup lives at `docs/assets/book_overview_mobile.jpg`. It is the visual reference for the book detail page and the rhythm of the system.

---

## Skills in play

| Skill | When |
|---|---|
| `developers-orchestration` | Orchestrator session — coordinates backend + frontend specialists, owns the plans, mediates contract changes |
| `backend-system-architecture` | Backend specialist — declared mode is **`modular-monolith` (Mode B)** per backend plan D7 |
| `frontend-system-pattern` | Frontend specialist — declared mode is **`ssr-rsc` (Mode B, Next.js App Router)** per frontend plan F1 |
| `superpowers:*` | Process disciplines (brainstorming, TDD, verification-before-completion, etc.) |

The CTG-Brasil-specific frontend skill (`frontend-ctg-system-pattern`) does NOT apply here — Sentido is not a CTG product. The generalist `frontend-system-pattern` skill is the correct one.

---

## Code territory

When specialists are dispatched with `isolation: "worktree"`, they work in a copy of the repo and their diff is reviewed before merging. The orchestrator owns:

| Territory | Owner | Orchestrator may | Orchestrator may NOT |
|---|---|---|---|
| `docs/product/` | Pedro (user) | Read | Edit (except on explicit Pedro instruction) |
| `docs/brand/` | Orchestrator | Edit | Modify visual decisions without surfacing to Pedro |
| `docs/instructions/` | Orchestrator | Edit, restructure | — |
| `backend/` (future) | Backend specialist | Read for audit · diff for review | Edit code directly |
| `frontend/` (future) | Frontend specialist | Read for audit · diff for review | Edit code directly |
| `CLAUDE.md`, `.gitignore`, repo-root config | Orchestrator | Edit | — |

---

## Phase status

| Phase | Backend | Frontend |
|---|---|---|
| Phase 0 — Foundation | not started | not started |
| Phase 1 — MVP public | not started | not started |
| Phase 2+ | out of scope until plans extended | out of scope until plans extended |

When phases progress, update the **`Status:`** line inside each plan's phase section. Do not maintain phase status here — this file is for orientation, not state.

---

## Conventions

- **Language for user-facing copy:** PT-BR (Brazilian Portuguese). The voice canon lives in `docs/brand/voice.md`.
- **Language for internal docs and code:** English.
- **Generated content (LLM):** PT-BR for synopses and emotional profiles; English for the embedding source text is **not used in v1** (see backend plan D2 — embedding source is composed in PT-BR).
- **Date format in plan decisions:** `YYYY-MM-DD` (ISO).
- **Commit messages:** present-tense imperative, English, conventional-commits-style where it adds clarity (`feat:`, `fix:`, `docs:`, `chore:`). No co-authoring lines in this project — the orchestrator commits on its own behalf.

---

## First-time setup expectations

When a backend specialist is dispatched for Phase 0, expect them to create `backend/` with the structure declared in the backend plan §3.1. When a frontend specialist is dispatched, expect `frontend/` with the structure declared in the frontend plan §3. Neither has been created yet — Phase 0 begins with that scaffolding.

The orchestrator dispatches Phase 0 in waves (declared in the orchestrator's working notes, not committed here):

- Wave 1: backend `B1` (repo skeleton + db + Alembic) ⇆ frontend `F1` (Next.js scaffold + tokens) — parallel.
- Wave 2: backend `B2` (FastAPI skeleton) ⇆ frontend `F2` (Phase 0 brand components) — parallel.
- Wave 3: backend `B3` (ingestion) ⇆ backend `B4` (generation) — parallel within backend.
- Wave 4: backend `B5` (publish + book detail + search + e2e).
- Wave 5: frontend `F3` (API client + book page + admin login + ISBN form) against the real backend.

Phase 0 exit: one book added via admin → generated → published → renders at `/livro/{slug}` matching the canonical mockup.
