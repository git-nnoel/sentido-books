# Sentido — Frontend

Next.js 14 (App Router) application for the Sentido book catalog.

The canonical spec lives in `../docs/instructions/frontend-implementation-plan.md`. The visual + voice system lives in `../docs/brand/` (start with `foundations.md`).

This package is at Phase 0 task F1: the design-token wiring (CSS variables, Tailwind theme, font loading) is in place; brand components and pages land in F2.

## Run locally

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 — the smoke-test page renders the wordmark in champagne gold (Cormorant Garamond italic) and confirms the tokens are wired.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Next.js dev server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint via `next lint` |
| `npm run format` | Prettier write across `src/` |
| `npm run typecheck` | `tsc --noEmit` |

## Stack

- Next.js 14 (App Router, RSC by default — see plan §12 F1)
- TypeScript, `strict: true`
- Tailwind CSS, theme extended with brand tokens (plan §4.2)
- `next/font/google` for Cormorant Garamond + Spectral (plan §4.3)

## Conventions

- Brand tokens are CSS custom properties declared in `src/app/globals.css`. Tailwind references them via `var(...)`. Do not introduce a token value that is not in `docs/brand/foundations.md`.
- The default font family is `--font-body` (Spectral). Use `font-display` for the wordmark, page titles, and book titles.
