# Frontend implementation plan — Sentido (v1, lean)

> Source of truth for the frontend specialist. Do not read the product spec or the backend plan — everything you need is here. The brand reference in `docs/brand/` is the canonical visual + voice source; read it before starting.
>
> If something is missing or contradictory, stop and report it back to the orchestrator. Do not invent contract shapes — they live in §5.

This plan covers **Phase 0 (foundation)** and **Phase 1 (MVP public)**. Later phases are out of scope until the orchestrator extends this document.

---

## 1. Mission

Build a Next.js application that:

1. Renders a public catalog where readers can search by feeling, open a book page, browse authors and editorial collections.
2. Renders an admin panel at `/admin` where curators ingest books by ISBN, trigger LLM generation, edit drafts, and publish.
3. Consumes the backend REST API (single base URL, defined in §5).
4. Embodies the visual and verbal system described in `docs/brand/` — exactly.
5. Deploys to Vercel as a single Next.js 14 app.

That's the whole product surface for v1. Resist scope creep.

---

## 2. Stack

| Concern | Choice | Notes |
|---|---|---|
| Framework | Next.js 14 (App Router) | React Server Components by default; client components opt-in |
| Language | TypeScript 5.x, `strict: true` | |
| Styling | Tailwind CSS 3.x | Configured against tokens from `docs/brand/foundations.md` |
| Fonts | `next/font/google` for Cormorant Garamond + Spectral | Self-hosted, CLS-prevention |
| Icons | `lucide-react` | Per `brand/foundations.md §7` |
| Data fetching (server) | Native `fetch` with Next.js cache controls | |
| Data fetching (client) | TanStack Query v5 | Mutations + admin queue |
| Forms (admin) | `react-hook-form` + `zod` | One-row alignment: schema = validation = type |
| Carousels | Native CSS `scroll-snap` + `overflow-x-auto` | No carousel library. Chevrons are plain buttons. |
| Animation | Framer Motion (sparingly) | Only for emotion-bar reveal and route transitions |
| Test (unit) | Vitest + React Testing Library | |
| Test (e2e) | Playwright | Smoke flow only in v1 |
| Linting | ESLint with `next/core-web-vitals`, Prettier | |
| Package manager | `npm` | Default Node tooling; `package-lock.json` committed |
| Deploy | Vercel | |

No state library beyond TanStack Query. No Redux, no Zustand, no Jotai. Server components carry most state.

No `shadcn/ui`. The components are too generic for this aesthetic — we hand-roll against the brand spec. Use Radix primitives only where accessibility is non-trivial (Dialog for admin confirmations).

---

## 3. Project layout

```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── .env.local.example
├── public/
│   ├── favicon.svg                  # the wordmark 's'
│   └── og-default.png
├── src/
│   ├── app/
│   │   ├── layout.tsx               # root layout: fonts, providers, header
│   │   ├── page.tsx                 # home — catalog + search
│   │   ├── globals.css              # tokens as CSS vars
│   │   ├── (public)/
│   │   │   ├── buscar/page.tsx
│   │   │   ├── livro/[slug]/page.tsx
│   │   │   ├── autor/[slug]/page.tsx
│   │   │   ├── colecoes/page.tsx
│   │   │   └── colecoes/[slug]/page.tsx
│   │   ├── admin/
│   │   │   ├── layout.tsx           # admin shell (auth gate + sidebar)
│   │   │   ├── page.tsx             # queue: pending generation
│   │   │   ├── revisao/page.tsx     # queue: pending approval
│   │   │   ├── publicados/page.tsx
│   │   │   ├── novo/page.tsx        # ISBN ingest form
│   │   │   ├── livro/[id]/page.tsx  # edit + generate + publish
│   │   │   └── login/page.tsx
│   │   ├── api/
│   │   │   └── auth/route.ts        # cookie-set route for admin token
│   │   ├── not-found.tsx
│   │   └── error.tsx
│   │
│   ├── components/
│   │   ├── brand/                   # 1:1 with brand/components.md
│   │   │   ├── Wordmark.tsx
│   │   │   ├── PillChip.tsx
│   │   │   ├── EmotionBar.tsx
│   │   │   ├── SectionLabel.tsx
│   │   │   ├── HairlineDivider.tsx
│   │   │   ├── QuoteBlock.tsx
│   │   │   ├── BookCover.tsx
│   │   │   ├── BookCard.tsx
│   │   │   ├── SearchField.tsx
│   │   │   ├── Button.tsx
│   │   │   └── CarouselChevron.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── PageColumn.tsx       # centered content wrapper
│   │   │   ├── BookPeekCarousel.tsx
│   │   │   └── RelatedCarousel.tsx
│   │   └── admin/
│   │       ├── AdminShell.tsx
│   │       ├── BookEditForm.tsx
│   │       ├── EmotionProfileEditor.tsx
│   │       ├── GenerationPanel.tsx
│   │       └── BookQueueTable.tsx
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts            # fetch wrapper (server + client)
│   │   │   ├── types.ts             # zod schemas mirroring backend DTOs
│   │   │   ├── search.ts
│   │   │   ├── books.ts
│   │   │   ├── authors.ts
│   │   │   ├── collections.ts
│   │   │   └── admin.ts
│   │   ├── auth/
│   │   │   ├── cookies.ts           # server-only cookie helpers
│   │   │   └── guard.ts             # admin route guard
│   │   ├── format.ts                # PT-BR locale helpers
│   │   └── slug.ts                  # client-side slug helpers (read-only)
│   │
│   └── styles/
│       └── tokens.ts                # tokens consumed by tailwind.config
└── tests/
    ├── unit/
    └── e2e/
```

### 3.1 Folder rules

- **`app/`** holds routes only. No business logic. Pages compose components from `components/` and call functions from `lib/`.
- **`components/brand/`** is 1:1 with the brand reference. One file per documented component. No drift.
- **`components/layout/`** holds composition primitives (Header, Footer, carousels). They use only `components/brand/` parts and tokens.
- **`components/admin/`** is admin-only. Public pages never import from here.
- **`lib/api/`** is the only place that talks to the backend. Pages and components import typed functions, not raw fetch calls.

### 3.2 Naming

| Kind | Convention | Example |
|---|---|---|
| Component file | `PascalCase.tsx` | `BookCard.tsx` |
| Hook file | `useCamelCase.ts` | `useAdminBook.ts` |
| Lib function | `camelCase` | `searchBooks(query)` |
| Zod schema | `XxxSchema` | `BookDetailSchema` |
| Inferred type | `Xxx` | `BookDetail = z.infer<typeof BookDetailSchema>` |

---

## 4. Design token wiring

The brand reference owns the tokens. The Tailwind config translates them. **The frontend specialist does not invent tokens.** If a value is needed that isn't in `brand/foundations.md`, raise it back to the orchestrator.

### 4.1 `globals.css` — CSS custom properties

Every token from `brand/foundations.md` is declared once at `:root`:

```css
:root {
  /* color — from brand/foundations.md §1.1 */
  --bg-canvas: #0B0A08;
  --bg-elevated: #14110D;
  --bg-overlay: rgba(11, 10, 8, 0.85);
  --accent: #C9A96E;
  --accent-hover: #D7BA82;
  --accent-dim: #8A7A5E;
  --text-primary: #E8DFD2;
  --text-muted: #8A7A5E;
  --text-subtle: #4A4338;
  --divider: rgba(201, 169, 110, 0.20);
  --focus-ring: rgba(215, 186, 130, 0.45);

  /* spacing — from brand/foundations.md §3 */
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;
  --space-7: 3rem;
  --space-8: 4rem;
  --space-9: 6rem;
  --space-10: 8rem;

  /* width — from brand/layout.md §2.1 */
  --width-prose: 38rem;
  --width-content: 42rem;
  --width-wide: 64rem;
  --width-edge: 90rem;

  /* motion — from brand/foundations.md §4 */
  --motion-fast: 120ms;
  --motion-base: 200ms;
  --motion-slow: 360ms;
  --motion-glacial: 600ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-entry: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-exit: cubic-bezier(0.4, 0, 1, 1);

  /* radius — from brand/foundations.md §6 */
  --radius-none: 0;
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-full: 9999px;
}

html { background-color: var(--bg-canvas); color: var(--text-primary); }
body { font-family: var(--font-body); }
```

### 4.2 `tailwind.config.ts` — theme extension

Tailwind theme is **extended only**, never replaced. The default scale stays available but the project convention is to use the brand tokens:

```ts
theme: {
  extend: {
    colors: {
      canvas: 'var(--bg-canvas)',
      elevated: 'var(--bg-elevated)',
      overlay: 'var(--bg-overlay)',
      accent: { DEFAULT: 'var(--accent)', hover: 'var(--accent-hover)', dim: 'var(--accent-dim)' },
      text: { primary: 'var(--text-primary)', muted: 'var(--text-muted)', subtle: 'var(--text-subtle)' },
      divider: 'var(--divider)',
      'focus-ring': 'var(--focus-ring)',
    },
    spacing: { /* 1..10 mapped from --space-* */ },
    maxWidth: { prose: 'var(--width-prose)', content: 'var(--width-content)', wide: 'var(--width-wide)', edge: 'var(--width-edge)' },
    fontFamily: { display: 'var(--font-display)', body: 'var(--font-body)' },
    fontSize: {
      'display-xl': ['2.75rem', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
      'display-lg': ['2.25rem', { lineHeight: '1.1',  letterSpacing: '-0.015em' }],
      'display-md': ['1.75rem', { lineHeight: '1.15', letterSpacing: '-0.01em' }],
      'title-lg':   ['1.375rem',{ lineHeight: '1.3' }],
      'title-md':   ['1.125rem',{ lineHeight: '1.35' }],
      'body-lg':    ['1.0625rem',{ lineHeight: '1.6' }],
      'body-md':    ['1rem',     { lineHeight: '1.6' }],
      'body-sm':    ['0.875rem', { lineHeight: '1.55' }],
      'label':      ['0.75rem',  { lineHeight: '1.4', letterSpacing: '0.15em' }],
      'label-sm':   ['0.6875rem',{ lineHeight: '1.4', letterSpacing: '0.18em' }],
    },
    borderRadius: { none: '0', sm: '2px', md: '4px', full: '9999px' },
    transitionDuration: { fast: '120ms', base: '200ms', slow: '360ms', glacial: '600ms' },
    transitionTimingFunction: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)',
      entry:    'cubic-bezier(0.16, 1, 0.3, 1)',
      exit:     'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
},
```

Desktop overrides for `fontSize` happen at component level via responsive classes (`md:text-display-xl`); the base scale is the mobile values from `brand/foundations.md §2.2`.

### 4.3 Fonts

```ts
// app/layout.tsx
import { Cormorant_Garamond, Spectral } from 'next/font/google';

const display = Cormorant_Garamond({
  subsets: ['latin', 'latin-ext'],
  weight: ['300', '400', '500'],
  style: ['normal', 'italic'],
  variable: '--font-display',
});
const body = Spectral({
  subsets: ['latin', 'latin-ext'],
  weight: ['300', '400', '500', '600'],
  style: ['normal', 'italic'],
  variable: '--font-body',
});
```

The `variable` names match the CSS vars; `<html className={`${display.variable} ${body.variable}`}>` makes them resolve.

---

## 5. API contract (mirrored from backend)

This is the boundary the backend exposes. **Every shape here mirrors `backend-implementation-plan.md §5` exactly.** If the backend plan changes, this section changes in the same orchestrator pass. The frontend never invents fields.

All requests target the env-configured base URL (`NEXT_PUBLIC_API_BASE_URL`).

### 5.1 Zod schemas (single source of truth in TS)

```ts
// lib/api/types.ts
import { z } from 'zod';

export const EmotionalProfileSchema = z.object({
  anguish: z.number().min(0).max(10),
  melancholy: z.number().min(0).max(10),
  hope: z.number().min(0).max(10),
  violence: z.number().min(0).max(10),
  tenderness: z.number().min(0).max(10),
  strangeness: z.number().min(0).max(10),
});

export const SearchResultSchema = z.object({
  slug: z.string(),
  title: z.string(),
  author_name: z.string(),
  year_published: z.number().nullable(),
  cover_url: z.string().nullable(),
  resonance_line: z.string(),
  similarity: z.number(),
});

export const RelatedBookSchema = z.object({
  slug: z.string(),
  title: z.string(),
  author_name: z.string(),
  year_published: z.number().nullable(),
  cover_url: z.string().nullable(),
});

export const EditionSchema = z.object({
  publisher: z.string().nullable(),
  language: z.string().nullable(),
  year: z.number().nullable(),
  isbn: z.string().nullable(),
});

export const BookDetailSchema = z.object({
  slug: z.string(),
  title: z.string(),
  original_title: z.string().nullable(),
  year_published: z.number().nullable(),
  author: z.object({ slug: z.string(), name: z.string() }),
  synopsis: z.string().nullable(),
  emotional_profile: EmotionalProfileSchema.nullable(),
  atmosphere_tags: z.array(z.string()),
  narrative_pace: z.enum(['slow', 'progressive', 'frenetic']).nullable(),
  cover_url: z.string().nullable(),
  editions: z.array(EditionSchema),
  related_books: z.array(RelatedBookSchema),
});

export const AuthorDetailSchema = z.object({
  slug: z.string(),
  name: z.string(),
  bio: z.string().nullable(),
  books: z.array(z.object({
    slug: z.string(), title: z.string(),
    cover_url: z.string().nullable(),
    year_published: z.number().nullable(),
  })),
});

export const CollectionSummarySchema = z.object({
  slug: z.string(),
  title: z.string(),
  description: z.string().nullable(),
});

export const CollectionDetailSchema = CollectionSummarySchema.extend({
  books: z.array(RelatedBookSchema),
});

export const AdminBookSchema = BookDetailSchema.extend({
  id: z.string().uuid(),
  embedding_status: z.enum(['pending', 'done']),
  profile_status: z.enum(['pending', 'approved', 'rejected']),
  published: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});
```

### 5.2 Endpoints

| Method | Path | Returns | Where called |
|---|---|---|---|
| `POST` | `/v1/search` | `{ query: string, results: SearchResult[] }` | `lib/api/search.ts → searchBooks(q, limit?)` |
| `GET` | `/v1/books/{slug}` | `BookDetail` | `lib/api/books.ts → getBookBySlug(slug)` |
| `GET` | `/v1/authors/{slug}` | `AuthorDetail` | `lib/api/authors.ts → getAuthorBySlug(slug)` |
| `GET` | `/v1/collections` | `{ collections: CollectionSummary[] }` | `lib/api/collections.ts → listCollections()` |
| `GET` | `/v1/collections/{slug}` | `CollectionDetail` | `lib/api/collections.ts → getCollectionBySlug(slug)` |
| `GET` | `/v1/health` | `{ status, version }` | `lib/api/client.ts → healthCheck()` |
| `POST` | `/v1/admin/books/ingest` | `AdminBook` | `lib/api/admin.ts → ingestByISBN(isbn)` |
| `POST` | `/v1/admin/books/{id}/generate` | `AdminBook` | `lib/api/admin.ts → generateArtifacts(id, regenerate?)` |
| `PUT` | `/v1/admin/books/{id}` | `AdminBook` | `lib/api/admin.ts → updateBook(id, patch)` |
| `POST` | `/v1/admin/books/{id}/publish` | `AdminBook` | `lib/api/admin.ts → publishBook(id)` |
| `GET` | `/v1/admin/books?status=...` | `{ books: AdminBook[], total: number }` | `lib/api/admin.ts → listAdminBooks(filter)` |

### 5.3 Client wrapper

A single `apiFetch<T>(path, options, schema)` function in `lib/api/client.ts`:

- Prefixes `NEXT_PUBLIC_API_BASE_URL`.
- Adds `Authorization: Bearer {token}` automatically for `/v1/admin/*` paths (reads from server cookie via `next/headers` when called from a server component, or from a TanStack Query mutation context on the client).
- Validates every response with the provided Zod schema. Validation failures throw `ApiContractError` with the failing path — these get surfaced loudly in dev.
- Maps `4xx` / `5xx` to `ApiError` with `{status, detail}`.
- Sets `cache: 'no-store'` for admin paths; uses `next: { revalidate: 60 }` for public reads by default. Caller can override.

### 5.4 Error UI conventions

| Backend response | Frontend behavior |
|---|---|
| `404` on book/author/collection | Render `not-found.tsx` with copy `esse livro ainda não vive aqui` (per voice §3.4) |
| `503` on search (OpenAI down) | Inline message in results area: `algo ficou em silêncio. tente de novo em um instante.` |
| `5xx` elsewhere | Trigger `error.tsx` with copy `o catálogo se recolheu por um momento. volte logo.` |
| `401` on admin | Redirect to `/admin/login`, preserve `?next={path}` |
| Network failure | Same as `5xx` |

---

## 6. Routes

### 6.1 Public route map

| Path | Page file | Render mode | Notes |
|---|---|---|---|
| `/` | `app/page.tsx` | RSC | Home — hero search + curated collections + a sample of the catalog |
| `/buscar?q=...` | `app/(public)/buscar/page.tsx` | RSC | Server-rendered first paint; client component handles input |
| `/livro/[slug]` | `app/(public)/livro/[slug]/page.tsx` | RSC | Full book detail — the canonical mockup |
| `/autor/[slug]` | `app/(public)/autor/[slug]/page.tsx` | RSC | Minimal Phase 1 author page |
| `/colecoes` | `app/(public)/colecoes/page.tsx` | RSC | List of editorial collections |
| `/colecoes/[slug]` | `app/(public)/colecoes/[slug]/page.tsx` | RSC | Collection detail |
| `*` | `app/not-found.tsx` | static | 404 with brand voice copy |

All public pages have `<Header>` and `<Footer>` from `components/layout/`. The footer per `brand/components.md §12`.

### 6.2 Admin route map

| Path | Page file | Notes |
|---|---|---|
| `/admin/login` | login form, sets cookie via `app/api/auth/route.ts` |
| `/admin` | redirects to `/admin?status=pending_generation` queue |
| `/admin?status=pending_generation` | books awaiting first artifact generation |
| `/admin/revisao` | books with `profile_status=pending` and artifacts generated — curator review |
| `/admin/publicados` | published books — search + edit |
| `/admin/novo` | ISBN ingest form |
| `/admin/livro/[id]` | one-book editor: edit fields, trigger generate, publish |

Admin routes are protected by `lib/auth/guard.ts` (server-side) that reads the cookie and 302s to `/admin/login?next=...` if missing. The cookie is `httpOnly`, `secure`, `sameSite=lax`, lifetime 7 days.

### 6.3 Metadata

Every route exports a `generateMetadata()` for SEO:
- `/livro/[slug]` → title `{book.title} — {author}` and `og:image` set to the book cover.
- Home → title `sentido — um catálogo afetivo de livros`.
- Author / collection pages → mirror the visible label.
- Admin routes → `noindex, nofollow`.

---

## 7. Component build order

The components in `components/brand/` are 1:1 with `brand/components.md`. Build them first; everything else composes from them.

### 7.1 Phase 0 — components

In this order:

1. `Wordmark` — `brand/components.md §1`
2. `BookCover` — §7 (including the embossed-letter fallback — deterministic from slug hash)
3. `SectionLabel` — §4
4. `HairlineDivider` — §5
5. `Button` — §10 (Primary, Ghost, TextLink)
6. `Header` (layout) + `Footer` (layout) — `brand/layout.md §4 + §12`

Each component:
- Has a TypeScript prop type.
- Composes only Tailwind classes mapped to brand tokens.
- Includes a Storybook-style page route under `/dev/components` (gated by `NODE_ENV !== 'production'`) showing every variant. No Storybook dependency — just an unstyled showcase page.
- Has at least one unit test asserting the right tokens are applied (smoke).

### 7.2 Phase 1 — components

7. `PillChip` — §2
8. `EmotionBar` — §3 (with the reveal animation gated by `prefers-reduced-motion`)
9. `QuoteBlock` — §6
10. `BookCard` — §8
11. `SearchField` — §9 (controlled, fires on Enter)
12. `CarouselChevron` — §11
13. `BookPeekCarousel` (layout) — `brand/layout.md §6`
14. `RelatedCarousel` (layout) — `brand/layout.md §7`
15. `PageColumn` (layout) — centered column wrapper using `--width-content`

Then the page-level compositions in `app/`.

### 7.3 Admin components (Phase 1)

16. `AdminShell` — sidebar + breadcrumb + curator/logout
17. `BookQueueTable` — see `brand/layout.md §10`
18. `EmotionProfileEditor` — six number inputs (or sliders 0–10, step 0.1) styled as emotion bars
19. `BookEditForm` — title, original_title, synopsis (textarea, monospace? no — Spectral), atmosphere_tags (chip input), narrative_pace (radio)
20. `GenerationPanel` — single button per artifact (synopsis, profile, embedding) — but for v1 a single "gerar perfil emocional" button triggers all three via `/generate`. See backend §6.

---

## 8. State management & data fetching

### 8.1 Public reads

Server components fetch via `lib/api/*` functions. Next.js cache headers per the client wrapper §5.3.

- `searchBooks` — `cache: 'no-store'` (every query is fresh). The search results page is dynamic.
- `getBookBySlug` — `next: { revalidate: 300 }` (5 min ISR). Editorial changes go live within 5 min without a full deploy.
- `getAuthorBySlug` / `getCollectionBySlug` / `listCollections` — `next: { revalidate: 600 }`.

### 8.2 Client interactivity

Three small client islands on public pages:

| Island | Purpose | State |
|---|---|---|
| `SearchField` in header | Take input → `router.push('/buscar?q=' + encoded)` | local |
| `EmotionBar` reveal | Trigger CSS animation on first viewport entry via `IntersectionObserver` | local |
| `BookPeekCarousel` controls | Track scroll-snap position + chevron handlers | local |

No global state. No context providers beyond a `QueryClientProvider` for the admin tree.

### 8.3 Admin

All admin pages are client components or compose client islands. State managed by TanStack Query.

- `useAdminBookQueue({ status })` — `useQuery` with key `['admin', 'books', status]`.
- `useGenerateArtifacts(bookId)` — `useMutation`; on success, invalidates `['admin', 'books']` queues.
- `usePublishBook(bookId)` — `useMutation`; on success, invalidates queues + redirects.
- `useUpdateBook(bookId)` — `useMutation`; on success, updates cache for `['admin', 'book', bookId]`.

Optimistic updates only for `useUpdateBook` (text edits); generate and publish go through pending → success states because their server side-effects are heavy.

---

## 9. Authentication

### 9.1 Public

None in v1. Per backend §11 D3.

### 9.2 Admin

Single-token bearer.

**Flow (Phase 0 — deferred validation):**
1. Curator visits `/admin/something` without cookie.
2. `lib/auth/guard.ts` (called in admin route `layout.tsx` from server) redirects to `/admin/login?next=/admin/something`.
3. Login page: a single password input. On submit, `POST` to `/api/auth` (Next.js route handler).
4. Route handler sets the `httpOnly` cookie `sentido_admin` with the submitted token **without upfront validation**. Bad tokens fail on first real action — any admin endpoint returns `401 {"detail": "unauthorized"}` from the backend. The frontend catches that 401, clears the cookie, and redirects back to `/admin/login?next=...&error=token%20inv%C3%A1lido`.
5. Subsequent requests: server components read the cookie and pass it to `apiFetch`.

**Why deferred:** the original Phase-0 plan was to probe `GET /v1/admin/books?limit=1` on login, but that endpoint is a Phase 1 backend deliverable. Rather than add a Phase 0 probe endpoint just for upfront validation, we accept first-action failure as the validation signal. Phase 1 reintroduces upfront validation against the now-existing admin listing endpoint.

**Logout:** `DELETE /api/auth` clears the cookie and redirects to `/admin/login`.

The admin token is never exposed to the browser JS — it only lives in the `httpOnly` cookie and is attached server-side. Client mutations call `lib/api/admin.ts` functions which either:
- Run inside a server action (preferred), or
- Hit a Next.js route handler that proxies to the backend with the cookie attached server-side.

For v1 we use **server actions** for all admin mutations. The TanStack Query mutation function calls the server action; cache invalidation happens on success in the React layer.

---

## 10. Phase 0 — Foundation

Goal: a working frontend skeleton with the brand system wired and one happy-path book renderable end-to-end against a real backend running Phase 0.

### Deliverables

- [ ] `npx create-next-app@14` with App Router + TypeScript + Tailwind + src dir + npm + manual ESLint setup.
- [ ] `tailwind.config.ts` + `globals.css` wired with **all** tokens per §4.
- [ ] `next/font` configured for Cormorant Garamond + Spectral; variables wired to CSS vars.
- [ ] `lib/api/` client + Zod schemas for the endpoints used by Phase 0.
- [ ] Phase 0 brand components (§7.1): Wordmark, BookCover, SectionLabel, HairlineDivider, Button, Header, Footer.
- [ ] `/dev/components` showcase page rendering all built components (dev only).
- [ ] `app/page.tsx` — home shell with `Header`, `Footer`, page title, no search yet.
- [ ] `app/(public)/livro/[slug]/page.tsx` — renders a real book from the Phase 0 backend with cover, title, author, sinopse, perfil emocional. No related books yet.
- [ ] `/admin/login` and admin cookie flow against Phase 0 backend's static token.
- [ ] `app/admin/novo/page.tsx` — ISBN form posting to `/v1/admin/books/ingest`.
- [ ] Vercel preview deploy succeeds.

### Exit criteria
- One real book added via the admin ingest + generate flow shows correctly on `/livro/{slug}` and matches the canonical mockup.
- Lighthouse mobile score ≥ 90 on `/livro/{slug}` (perf, a11y, SEO).
- All Phase 0 components rendered on `/dev/components` match the brand spec on visual inspection.

**Status:** not started

---

## 11. Phase 1 — MVP public

Goal: full public catalog + complete admin curation flow against the Phase 1 backend.

### Deliverables (delta over Phase 0)

- [ ] All Phase 1 brand + layout components (§7.2).
- [ ] `app/page.tsx` — home with `SearchField`, editorial collections, sample catalog.
- [ ] `/buscar?q=...` — results grid with `BookCard`s, `resonance_line` rendered, empty state copy.
- [ ] `/livro/[slug]` — full mockup parity: book-peek carousel (mobile), emotion bars with reveal, related carousel.
- [ ] `/autor/[slug]` — minimal author page.
- [ ] `/colecoes` + `/colecoes/[slug]`.
- [ ] Admin: queue tables (`/admin`, `/admin/revisao`, `/admin/publicados`), `BookEditForm`, `EmotionProfileEditor`, `GenerationPanel`, publish gate.
- [ ] `not-found.tsx` and `error.tsx` with brand-voice copy.
- [ ] OG metadata for `/livro/[slug]`.
- [ ] `prefers-reduced-motion` handling for emotion-bar reveal and route transitions.
- [ ] Mobile-first verified: 360px width works without horizontal scroll on every page.

### Exit criteria
- Visual parity with the canonical mockup on a real book: matches on a side-by-side at 390px width.
- Lighthouse mobile ≥ 90 (perf, a11y, SEO, best-practices) on the three primary surfaces: `/`, `/buscar?q=...`, `/livro/{slug}`.
- Admin can take a fresh book from ISBN ingest to published in under 3 minutes.
- E2E Playwright smoke: home → search → click first result → book page → click a related book → another book page. All steps pass.

**Status:** not started

---

## 12. Decisions

### F1 — App Router with Server Components by default (2026-06-14)
**Declared mode for the `frontend-system-pattern` skill: `ssr-rsc` (Mode B).**

Public catalog pages need SEO (search by feeling is meaningless without indexable book pages), social-preview metadata for share links, and fast cold-paint on `/livro/{slug}` deep links. That's the exact shape the skill describes as the Mode B indicator set. RSC for public reads; client components only where interactivity demands it (search input, carousel scroll-snap controls, emotion-bar reveal, admin mutations). No `getServerSideProps`-style pages.

The frontend specialist follows the skill's §4 (Mode B) for structure, §5 for cross-mode rules (R1–R34), and §6 for the technology baseline.

**Locks down:** no Pages Router. No `next-i18next`. No `next-auth` (custom token cookie suffices for the single admin).

### F2 — No `shadcn/ui`; hand-rolled brand components (2026-06-14)
shadcn components are designed against a generic aesthetic that fights this brand. We hand-roll the small set in `brand/components.md` and use Radix only where accessibility demands it (Dialog for admin confirmations). Cheaper than de-themeing shadcn back to our system.
**Locks down:** no shadcn imports; no Headless UI; no other component library.

### F3 — Tailwind tokens as CSS variables, not config values (2026-06-14)
Tokens live in `globals.css` as `:root` custom properties; Tailwind references them via `var(...)`. This lets the brand reference's token names map 1:1 to CSS and lets us swap themes in a future Phase 4+ if it ever happens without rebuilding Tailwind.
**Locks down:** changing a brand token does not require a Tailwind rebuild — it's a CSS edit.

### F4 — Server actions for admin mutations (2026-06-14)
All admin mutations go through Next.js server actions that attach the cookie-stored token server-side. The browser never sees the token. Simpler than a separate API proxy route.
**Locks down:** the admin token is `httpOnly` and stays in the Next.js process.

### F5 — Zod schemas validate every API response (2026-06-14)
The TS API client validates every response against a Zod schema before returning. Contract drift between backend and frontend fails loudly in dev/preview instead of silently in prod.
**Locks down:** schema files in `lib/api/types.ts` are the single TS truth for backend shapes; any change in backend §5 propagates here in the same orchestrator pass.

### F6 — Native CSS scroll-snap for carousels (2026-06-14)
No Swiper, no Embla, no Keen. CSS scroll-snap + `scroll-snap-align: center` + custom chevrons covers both the book-peek and related carousels. Lighter, more performant, and the snap behavior is what the brand specifies.
**Locks down:** if a future surface needs free-form drag/inertia beyond what native scroll provides, raise it back to the orchestrator.

### F7 — Mobile-first, desktop is an enhancement (2026-06-14)
The canonical mockup is mobile. Desktop unlocks the two-column hero on `/livro/[slug]` and wider catalog grids — that's it. We don't design two products.
**Locks down:** default styles target mobile; `md:` and above add the desktop deltas.

---

## 13. Testing

### 13.1 Unit (Vitest + RTL)
- Every `components/brand/` component has at least one render test verifying the brand-token classes resolve.
- `lib/api/*` functions have schema-validation tests with valid + invalid fixtures.
- Slug / format helpers have edge-case tests.

Target: 60% line coverage. We do not chase 80% on the App Router page files (they're thin compositions).

### 13.2 E2E (Playwright)
v1 ships ONE smoke flow (the exit criterion in §11) running in CI on every PR. We do not write granular Playwright tests in v1.

### 13.3 Visual regression
**Not in v1.** Lighthouse + manual review against the canonical mockup is the gate.

---

## 14. Configuration

`.env.local`:

| Var | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | yes | e.g. `https://api.sentido.app` |
| `SENTIDO_ADMIN_COOKIE_SECRET` | yes | for cookie signing (Next.js `cookies()` API) |
| `NODE_ENV` | auto | |

The admin token itself is **never** in env — curators type it on the login page.

CORS is configured server-side (backend §8.1); the frontend doesn't manage it.

---

## 15. Open items routed back to orchestrator

The frontend specialist does not resolve these:

1. **Admin "edit emotional profile" UX** — sliders vs. number inputs? The brand mandates the bar visualization; the editor will need its own treatment. Will be revisited in Phase 1 once a real curator tests the flow.
2. **Cover image source** — backend stores Open Library URLs. If those load slowly or break CORS for hot-linking, the frontend may need to proxy through `next/image`. Decided in Phase 1 against real data.
3. **Logged-out admin UX for shared links** — what happens when a curator shares an `/admin/livro/{id}` URL with a colleague? Currently: they're redirected to login and back. That's fine; flagged in case it becomes annoying.

When any of these becomes load-bearing, the specialist reports back; the orchestrator amends this plan and (if needed) the backend plan.
