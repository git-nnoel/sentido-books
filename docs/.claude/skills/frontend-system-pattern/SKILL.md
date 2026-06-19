---
name: frontend-system-pattern
description: Use when writing, reviewing, or refactoring React/TypeScript frontend code — pages, routes, components, hooks, API clients, design tokens, forms, tables, i18n, accessibility, performance. Brand-agnostic — the project's brand reference (e.g., `docs/brand/`) is the canonical source for visual tokens and voice. Supports two architecture modes — SPA-layered (default) and SSR/RSC (Next.js App Router). The project's frontend implementation plan declares the mode in its decisions section. Do NOT use for projects that have a brand-specific skill (e.g., `frontend-ctg-system-pattern` for CTG Brasil).
---

# Frontend System Pattern

You are building a React/TypeScript frontend. Every architectural, structural, and code-quality decision must follow the rules below. Visual decisions follow the **project's brand reference**, not this skill.

This skill is **brand-agnostic by design**. It does not define colors, type stacks, copy tone, or component anatomy. Those live in the project's brand reference (typically `docs/brand/`). This skill defines the **system around the brand**: layering, data flow, contract handling, accessibility, performance, testing, and the rules that keep a frontend codebase legible at scale.

For brand-locked projects (e.g., CTG Brasil), use the matching brand-specific skill instead — it bundles both the brand canon and these structural rules into one place.

---

## 0. Brand reference contract — required

Before writing any frontend code, you MUST locate the project's brand reference. The reference defines the visual and verbal system the frontend implements.

| Where to look | What you expect |
|---|---|
| `docs/brand/` or `frontend/brand/` | A folder with markdown files describing tokens, components, layout, voice, decisions |
| Project's frontend implementation plan | A "Brand reference" section pointing at the canonical path |
| Project's PRD | A brand section, design references, or mockup attachments |

If no brand reference exists, **stop and report to the orchestrator**. Do not invent tokens. Do not infer brand from a screenshot. Visual decisions made without a brand reference will be wrong, and rolling them back is expensive.

A complete brand reference typically provides:

- Color tokens (canvas, surface, accent, text, divider) with hex values and contrast notes
- Type stack (display + body families) and a documented type scale
- Spacing scale (4px or 8px base; tokens `space-1`..`space-10` or similar)
- Component anatomies (buttons, cards, inputs, list items, dialogs) with prop tables
- Layout patterns (page rhythm, headers, footers, breakpoints, content widths)
- Voice (copy tone, microcopy library, what to avoid)
- Decisions (anti-patterns and explicit "do not do this")

If the reference is missing pieces, raise them to the orchestrator before guessing.

This skill assumes the reference is the source of truth. **Where this skill and the brand reference conflict, the brand reference wins** for visual/verbal matters; this skill wins for structural matters.

---

## 1. Architecture mode selection

Identify the mode declared by the project's **frontend implementation plan**. The plan's decisions section names the active mode.

| Mode | When chosen | Section |
|---|---|---|
| **spa-layered** (default) | SPAs without server-side rendering needs. Vite + React Router. Auth via JWT in HTTP client. | §3 |
| **ssr-rsc** | Server-rendered apps that benefit from SEO and fast first paint. Next.js App Router with React Server Components by default; client components opt-in. | §4 |

If the plan does not name a mode, the default is `spa-layered`. A plan that wants `ssr-rsc` records the decision explicitly with rationale (typically SEO, social previews, or first-paint performance).

**Sections labeled "(Mode A)" apply only in SPA-layered mode. Sections labeled "(Mode B)" apply only in SSR/RSC mode. Everything else applies to both.**

---

## 2. SOLID applied to React (Both modes)

**Single Responsibility.** A component renders one concept. A hook returns one resource. A page composes; it does not implement business logic.

**Open/Closed.** Adding a new page or feature must not require editing shared primitives. New routes plug into the existing layout; new components plug into the existing token system.

**Liskov Substitution.** A `<Button>` and a `<Button variant="ghost">` are substitutable. A `<DataTable>` works for any row shape because the row renderer is injected.

**Interface Segregation.** A read-only consumer of a hook depends on a read-only signature. Do not bundle `useResources` and `useCreateResource` into one hook just because both touch the same resource.

**Dependency Inversion.** Pages depend on hook signatures, not on the HTTP client. Hooks depend on API endpoint signatures, not on `fetch`. The HTTP client lives in `lib/api/client.ts` (or `api/client.ts`) and is the single seam to the backend.

---

## 3. Mode A — SPA layered (Vite + React Router)

The default mode. Choose this for client-rendered applications: dashboards, admin panels, authenticated SPAs.

### 3.1 Layer diagram

```
+------------------------------------------------------------------+
|                            PAGES                                 |
|  src/pages/ — route-level composition. No business logic.        |
|  One file per logical screen. Receives URL params + nothing else.|
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                            HOOKS                                 |
|  src/hooks/ — React Query wrappers + derived state.              |
|  useResource(), useCreateResource(), useDuplicateCheck()         |
|  Sorting, filtering, validation rules — live here, not in pages. |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                      API ENDPOINTS                               |
|  src/api/endpoints/<resource>.ts — typed CRUD operations         |
|  list, get, create, update, remove. Mirrors backend DTOs 1:1.    |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                       HTTP CLIENT                                |
|  src/api/client.ts — single typed fetch wrapper.                 |
|  Owns: base URL, auth header, refresh-on-401, error mapping.     |
|  Schema validation (zod) happens here on every response.         |
+------------------------------------------------------------------+
```

Pages call hooks. Hooks call endpoints. Endpoints call the client. The client is the only place `fetch` is called.

### 3.2 Layer responsibilities (Mode A)

**Pages** (`src/pages/`)
- Route-level composition. One file per logical area of the app.
- Reads URL params, calls hooks, renders components, handles in-page UI state (filter values, active tab).
- No business logic, no `fetch`, no sorting or filtering arithmetic — push those into hooks.
- Renders loading, empty, and error states (see §5.6).

**Hooks** (`src/hooks/`)
- React Query wrappers for each resource: `useResources(params)`, `useResource(id)`, `useCreateResource()`, etc.
- Derived state: `useTableSort`, `useDuplicateCheck`, `useFilteredList`.
- Encapsulate query keys, cache invalidation, optimistic updates.
- One hook per concept; do not bundle reads and mutations into one hook unless they share a meaningful state machine.

**API endpoints** (`src/api/endpoints/<resource>.ts`)
- Typed CRUD operations for one backend resource. Functions take typed input and return typed output.
- The endpoint module is the **TS contract surface** for that resource.
- Mirrors backend DTOs 1:1; types live in `src/api/types/`.

**HTTP client** (`src/api/client.ts`)
- Single typed wrapper over native `fetch`.
- Owns: `VITE_API_BASE_URL`, JWT `Authorization` header, refresh-on-401 logic, JSON parsing, status-code → error mapping.
- Validates every response against a Zod schema before returning. Validation failures throw `ApiContractError` loudly.

**Components** (`src/components/`)
- `components/ui/` — generic primitives (Button, Card, Dialog, Input). The brand reference governs their visual specs.
- `components/<feature>/` or `components/<domain>/` — domain-specific compositions (e.g., `OrderRow`, `MetricCard`).
- `components/layout/` — app-level chrome (AppLayout, Sidebar, Topbar).

### 3.3 Directory structure (Mode A)

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts                # if Tailwind is the styling layer
├── src/
│   ├── main.tsx
│   ├── App.tsx                       # <Router><QueryClientProvider><AuthProvider><ThemeProvider>
│   ├── index.css                     # brand tokens as CSS vars + base reset
│   │
│   ├── api/
│   │   ├── client.ts                 # typed fetch wrapper
│   │   ├── endpoints/                # one file per resource
│   │   └── types/                    # TS types mirroring backend DTOs
│   │
│   ├── hooks/                        # React Query wrappers
│   │
│   ├── contexts/                     # AuthContext, ThemeContext, I18nContext
│   │
│   ├── components/
│   │   ├── layout/                   # AppLayout, Sidebar, Topbar
│   │   ├── ui/                       # generic primitives (Button, Card, ...)
│   │   └── <feature>/                # domain-specific compositions
│   │
│   ├── pages/                        # one file per logical area
│   └── lib/
│       ├── i18n.ts                   # if i18n is in scope
│       └── utils.ts                  # formatters, helpers
└── tests/
    ├── unit/
    └── e2e/
```

### 3.4 Routing (Mode A)

- React Router v6+ with data loaders disabled (loaders re-fetch on every navigation and conflict with React Query). Use React Query as the single data layer.
- Route definitions live in `App.tsx` or a dedicated `routes.tsx`.
- Protected routes wrap an `<AuthGuard>` component that redirects to `/login` if the auth context has no session.
- 404s are handled by a wildcard `*` route rendering a `<NotFoundPage>` from `pages/`.

### 3.5 Auth (Mode A)

- Access token in memory (React context); refresh token in `httpOnly` cookie or refresh endpoint.
- `api/client.ts` attaches `Authorization: Bearer <access>` to every request. On `401`, it calls `POST /auth/refresh` once, retries the original request, and on second failure clears auth and redirects to `/login`.
- No tokens in `localStorage` or `sessionStorage`. Theme and language preferences are fine in `localStorage`.

---

## 4. Mode B — SSR/RSC (Next.js App Router)

Choose this when the product needs SEO, social-preview metadata, or sub-second first paint on cold loads. Examples: marketing sites, public catalogs, content-heavy products.

### 4.1 Layer diagram

```
+------------------------------------------------------------------+
|                        APP ROUTES                                |
|  src/app/ — file-based routing. Server Components by default.    |
|  page.tsx fetches via `lib/api/*` (server-side cache).           |
|  Client components only for interactivity (`'use client'`).      |
+------------------------------------------------------------------+
                |                                |
                v                                v
+----------------------+         +-------------------------------+
|     COMPONENTS       |         |     CLIENT ISLANDS            |
|  Server-rendered     |         |  'use client' — interactivity |
|  No state, no events |         |  TanStack Query for mutations |
+----------------------+         +-------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     API CLIENT LAYER                             |
|  src/lib/api/ — typed functions used by Server Components        |
|  AND by client islands. Same surface, same Zod schemas.          |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                   BACKEND API (HTTP)                             |
+------------------------------------------------------------------+
```

### 4.2 Layer responsibilities (Mode B)

**App routes** (`src/app/`)
- File-based routing. `page.tsx`, `layout.tsx`, `error.tsx`, `not-found.tsx`, `loading.tsx`.
- `page.tsx` is a Server Component by default. It calls typed functions from `lib/api/*` and renders the result.
- Server Components have no `useState`, no `useEffect`, no event handlers. They are pure render functions over fetched data.
- Client components live in `components/` (or co-located) and are marked with `'use client'` at the top. They handle clicks, forms, controlled inputs, animations.

**API client layer** (`src/lib/api/`)
- One file per resource: `lib/api/books.ts`, `lib/api/search.ts`, `lib/api/admin.ts`.
- Each function is a typed wrapper around `fetch` with explicit `cache:`/`next:` options.
- The same functions are imported by Server Components AND by client islands (via server actions or route handlers). Single source of truth for the contract.
- Zod schemas validate every response. Contract drift fails loudly in dev.

**Components** (`src/components/`)
- `components/brand/` — atoms from the brand reference (Button, Card, Wordmark, etc.). Server-renderable by default; mark `'use client'` only if they need interactivity.
- `components/layout/` — Header, Footer, page-shell wrappers.
- `components/<feature>/` — feature-specific compositions.

**Server actions** (Mode B preferred over route handlers for mutations)
- Mutations (POST/PUT/DELETE) go through server actions defined in `app/<route>/actions.ts` or co-located.
- Server actions attach auth tokens server-side; the browser never sees the token.
- Client mutation hooks (TanStack Query `useMutation`) call the server action and invalidate query cache on success.

### 4.3 Directory structure (Mode B)

```
frontend/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx                # root layout: fonts, providers, header
│   │   ├── page.tsx                  # home (Server Component)
│   │   ├── globals.css               # brand tokens as CSS vars
│   │   ├── (public)/
│   │   │   ├── <route>/page.tsx
│   │   │   └── <route>/[slug]/page.tsx
│   │   ├── admin/
│   │   │   ├── layout.tsx            # auth gate
│   │   │   └── <route>/page.tsx
│   │   ├── api/                      # route handlers (rare; prefer server actions)
│   │   ├── not-found.tsx
│   │   └── error.tsx                 # required: catches render errors
│   │
│   ├── components/
│   │   ├── brand/                    # 1:1 with brand reference
│   │   ├── layout/                   # Header, Footer, PageColumn
│   │   └── <feature>/
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts             # fetch wrapper (server + client)
│   │   │   ├── types.ts              # Zod schemas mirroring backend
│   │   │   └── <resource>.ts         # typed functions per resource
│   │   ├── auth/                     # cookie helpers, guards
│   │   ├── format.ts                 # locale-aware formatters
│   │   └── utils.ts
│   │
│   └── styles/
│       └── tokens.ts                 # tokens consumed by tailwind.config
└── tests/
    ├── unit/
    └── e2e/
```

### 4.4 Data fetching (Mode B)

- **Server Components** call `lib/api/*` directly. Use `cache: 'no-store'` for per-request fresh data, `next: { revalidate: N }` for ISR.
- **Client islands** that read data (rare in SSR mode — usually a Server Component fetches and passes props) use TanStack Query with the same `lib/api/*` functions.
- **Mutations** use server actions invoked from TanStack Query `useMutation` in the client island. Server actions attach cookies/tokens server-side.

### 4.5 Auth (Mode B)

- Tokens never reach the browser JS. They live in `httpOnly`, `secure`, `sameSite=lax` cookies set by Next.js route handlers or server actions.
- Server Components read the cookie via `cookies()` from `next/headers` and pass the token to `lib/api/client.ts`.
- Client islands cannot read the token. Their mutations go through server actions that attach the token server-side.
- Admin layouts use a server-side guard in `app/admin/layout.tsx` that redirects to `/admin/login?next=...` when the cookie is missing or invalid.

### 4.6 Routes vs server actions

| Use route handler (`app/api/<route>/route.ts`) when | Use server action when |
|---|---|
| The endpoint must be called from outside the app (webhooks, third parties) | The mutation is part of the app's own flow |
| You need a stable public URL | The action is co-located with the page that calls it |
| The response is consumed as raw JSON by external systems | TanStack Query mutation invokes it |

Default to server actions. Route handlers add a routing layer and don't get the type safety of imports.

---

## 5. Cross-mode rules (Both modes)

### 5.1 API client and contract

- **R1.** **One HTTP client module.** `api/client.ts` (Mode A) or `lib/api/client.ts` (Mode B) is the SINGLE place `fetch` is called. Components, hooks, pages, server actions — they all route through this module.
- **R2.** **Typed responses via Zod.** Every API function validates the response with a Zod schema before returning. Schemas live in `api/types.ts` or `lib/api/types.ts`. Contract drift between frontend and backend fails loudly in dev/preview.
- **R3.** **Backend DTOs mirror 1:1.** Field names match the backend's response shape exactly. No camelCase translation layer in the schema; if a translation is desired, do it in a derived selector, not in the schema.
- **R4.** **No business logic in components.** Sorting, filtering, validation rules, derived metrics — these live in hooks (Mode A) or in pure helpers in `lib/` (Mode B). Components compose; they do not compute.

### 5.2 State

- **R5.** **No global state libraries** (Redux, Zustand, Jotai). Server state goes through React Query / RSC fetch; UI state goes through `useState` / Context. If a real cross-component state need emerges, raise it back to the orchestrator before introducing a library.
- **R6.** **Browser storage holds only preferences.** Theme, language, "remember me" toggle — yes. Auth tokens — never (use `httpOnly` cookies in Mode B; in-memory access token + refresh cookie in Mode A). User profile data — never; fetch it from the API.
- **R7.** **Query keys are tuples** in stable order: `['resource', id]`, `['resources', { page, search }]`. Spreading params into a single object is fine; mutating params and re-fetching is not — replace the object instead.

### 5.3 Styling — defer to the brand reference

- **R8.** **Tokens come from the brand reference.** `globals.css` (Mode B) or `index.css` (Mode A) declares CSS custom properties for every brand token. Components reference tokens via Tailwind classes mapped to `var(...)` or via CSS Modules referencing the variables.
- **R9.** **No raw color values in components.** No `bg-slate-900`, no `#0B0A08`, no inline hex. If a needed value is not in the brand reference, raise it back to the orchestrator before inventing.
- **R10.** **No inline styles for layout or color.** Spacing, color, typography go through tokens. Inline `style={{}}` is acceptable only for dynamic values driven by data (e.g., a progress bar width).
- **R11.** **No `!important`.** Specificity conflicts indicate the component or the token usage is wrong — fix the structure, not the cascade.

### 5.4 Forms

- **R12.** All forms use `react-hook-form` + a `zod` schema co-located with the page or component. Server errors surface via the form's `setError` after the mutation rejects.
- **R13.** Validation messages are i18n keys when i18n is in scope; otherwise they are constants in a single file, not inline strings sprinkled across components.
- **R14.** Required fields show the visual marker the brand reference specifies (typically `*`). `aria-required` is set on the input, and the Zod schema's `.min(1)` enforces it.

### 5.5 Internationalization

- **R15.** When the project is multi-language, every user-facing string is a `t()` key. Keys are flat, scoped by page: `<page>.title`, `<page>.actions.save`, `common.<concept>`.
- **R16.** Backend error responses with an `error.code` field resolve via `` t(`errors.${code}`) ``. If the backend doesn't return error codes, fall back to a generic friendly message — do not surface stack traces or raw upstream text.
- **R17.** Single-language projects (e.g., PT-BR only) may skip the `t()` layer for v1 and use strings directly in JSX. The frontend implementation plan declares whether i18n is in scope.

### 5.6 Loading, empty, error states

Every data-bound surface implements all four states. The brand reference defines what each looks like.

| State | Mode A | Mode B |
|---|---|---|
| **Loading** | `useResources().isLoading` → skeleton | `loading.tsx` next to `page.tsx` for route-level; skeletons for component-level |
| **Empty** | `data?.length === 0` → empty-state component with copy from brand voice | Same; render inside the Server Component |
| **Error** | `useResources().isError` → inline error component | `error.tsx` next to `page.tsx`; inline errors for component-level |
| **Success** | render the data | render the data |

No `<Spinner />` without a layout shift. Reserve the space the loaded UI will occupy with a skeleton.

### 5.7 Accessibility

- **R18.** **Every interactive element has a visible focus ring.** The ring color comes from the brand reference (typically the accent color or a focus-specific token).
- **R19.** **Status colors are paired with text or icon — never color alone.** A red badge must also have a label or icon that conveys "error" / "overdue" / etc. for color-blind users.
- **R20.** **Charts include `aria-label`** describing the data so screen readers can hear the chart's content. The label is generated from the data, not hard-coded.
- **R21.** **Tables use semantic markup.** `<th scope="col">` on column headers. Sortable headers expose `aria-sort="ascending|descending|none"`.
- **R22.** **Lighthouse accessibility score ≥ 90** on the three primary surfaces in CI. Drops below 90 block merge.

### 5.8 Performance

- **R23.** **List pages paginate.** Sensible defaults: 25 per page, max 100. Never fetch unbounded lists into memory.
- **R24.** **Filter / search inputs debounce 300ms** before triggering refetches.
- **R25.** **Charts and overlay panels are code-split** via `React.lazy` (Mode A) or dynamic import (Mode B) when the chunk exceeds ~50 KB.
- **R26.** **Lighthouse mobile performance ≥ 90** on the three primary surfaces. Drops below 90 block merge.

### 5.9 Testing

- **R27.** **Component unit tests** for every primitive in `components/ui/` (Mode A) or `components/brand/` (Mode B). At minimum, assert the right tokens are applied and the right props change behavior.
- **R28.** **Hook tests** for every hook with derived logic (sorting, filtering, validation). Pure logic is preferred — extract derivations into pure functions and test them directly.
- **R29.** **API client schema tests** with valid + invalid fixtures, asserting Zod validation passes on valid responses and throws on invalid.
- **R30.** **E2E smoke flow** in Playwright covering the primary user path of the product (e.g., `home → search → detail page → related item → another detail page`). One flow at MVP; do not chase coverage.
- **R31.** Visual regression is not required at MVP. Lighthouse + manual review against the brand reference is the gate.

### 5.10 General

- **R32.** **No feature flags or compatibility shims** for code that has not yet shipped.
- **R33.** **No speculative abstractions.** If there is only one caller of a hook or one consumer of a component, that is fine.
- **R34.** **Breaking changes to inbound or outbound contracts** require a new schema version, not a mutation of the existing one.

---

## 6. Technology baseline (Both modes)

Use ONLY these packages unless explicitly approved.

### Runtime — required
| Package | Purpose |
|---|---|
| `react` | UI library |
| `react-dom` | DOM bindings |
| `typescript` | Strict mode required (`"strict": true`) |
| `zod` | Schema validation for API responses |
| `@tanstack/react-query` | Server state (Mode A all data; Mode B mutations + admin) |

### Mode A only
| Package | Purpose |
|---|---|
| `vite` | Bundler / dev server |
| `react-router-dom` | Routing |

### Mode B only
| Package | Purpose |
|---|---|
| `next` | App Router framework |

### Conditionally allowed
| Package | When |
|---|---|
| `tailwindcss` | Default styling layer; map utilities to brand tokens via CSS vars |
| `react-hook-form` | Forms with non-trivial validation |
| `lucide-react` or `phosphor-react` | Icon set (pick one) |
| `framer-motion` | Animation (sparingly; only for non-essential transitions) |
| `@radix-ui/react-*` | Headless primitives where accessibility is non-trivial (Dialog, Menu, Tooltip) |
| `recharts` | Charts (Mode A or Mode B client islands) |
| `i18next` + `react-i18next` | When the project is multi-language |
| `date-fns` or native `Intl` | Date formatting (prefer native `Intl` where possible) |

### NOT allowed
| Package | Why |
|---|---|
| `redux`, `@reduxjs/toolkit` | Use React Query + Context instead |
| `zustand`, `jotai`, `valtio`, `recoil` | Same — no global state libraries |
| `axios` | Use native `fetch` via the typed client wrapper |
| `moment` | Bloated; use `date-fns` or `Intl` |
| `lodash` (full package) | Cherry-pick functions if needed; prefer native or write a small util |
| `styled-components`, `@emotion/*` | Pick one styling approach per project; runtime CSS-in-JS adds bundle cost |
| `mui`, `antd`, `chakra` | Component libraries with strong opinions that fight the brand reference. Hand-roll primitives from the brand reference; use Radix for accessibility-hard cases |

### Provisional
| Package | Note |
|---|---|
| `shadcn/ui` | Acceptable when the brand reference's primitives align closely with shadcn's defaults. Reject when the brand is distinctive enough that de-themeing shadcn costs more than hand-rolling — raise to orchestrator. |

---

## 7. Mode selection checklist

When the implementation plan declares a mode, verify the choice with this checklist. If a plan declares one mode but the project's needs strongly suggest the other, raise the concern back to the orchestrator before building.

**Indicators that Mode A (SPA-layered) is the right choice:**
- The product is behind authentication and SEO is not a goal.
- The audience is internal or invited (admin panels, dashboards, customer portals).
- Cold-load performance is secondary to dev velocity and simplicity.
- The team is small and prefers a single rendering model.

**Indicators that Mode B (SSR/RSC) is the right choice:**
- The product has public pages that need SEO, social previews, or share links with rich metadata.
- Cold-load time-to-content matters (catalogs, marketing surfaces, content sites).
- Some pages are nearly static while others need full interactivity — the SSR/RSC split lets each pay only its cost.
- The team is comfortable with the Server / Client component split.

A plan that picks the wrong mode creates either over-complexity (Mode B for a private dashboard) or under-performance (Mode A for a public catalog). When in doubt, default to Mode A and revisit if SEO or first-paint becomes a real constraint.

---

## 8. What this skill does NOT cover

These belong elsewhere:

| Concern | Where |
|---|---|
| Brand visuals, voice, copy library | The project's brand reference (`docs/brand/`) |
| Backend architecture and contracts | The `backend-system-architecture` skill |
| Orchestration between teams | The `developers-orchestration` skill |
| Deployment, hosting, CI/CD | The project's infrastructure plan |
| Specific brand canon (CTG Brasil) | The `frontend-ctg-system-pattern` skill |
| Visual one-offs without a brand | The `frontend-design` skill (use only when the project genuinely has no brand reference and is exploratory) |

If a question crosses domains, address each in its proper skill rather than expanding the scope here.
