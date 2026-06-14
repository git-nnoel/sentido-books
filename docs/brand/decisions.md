# Decisions and anti-patterns

> The non-negotiables. Things that have been deliberately chosen, and things that have been deliberately rejected. When a future design decision feels like it could go either way, the answer lives here.

This file is the **veto book**. If a proposed change conflicts with a decision here, the proposal needs to be raised back to the orchestrator before any implementation. Anti-patterns are not "things we haven't thought of" — they are "things we have considered and chosen against."

---

## 1. Load-bearing decisions

### D1 — Dark canvas is the brand, not a theme

Sentido is dark. There is no light mode in MVP and no light mode planned. The warm near-black canvas (`#0B0A08`) is structural to the brand position — books treated as artifacts in a quiet room.

**Implication:** No `prefers-color-scheme` switching. No theme toggle in the header. No `theme: light` token set. The system only specifies dark values because no other values exist.

**Future option:** If a "reading mode" with a paper-cream canvas is ever introduced, it is a separate experience (e.g., a dedicated `/leitura` view), not a global toggle.

---

### D2 — One accent color

The champagne gold (`#C9A96E`) is the only chromatic accent in the system. There is no secondary color, no success-green, no error-red, no warning-amber.

**Implication:**
- State (success, error, warning) is signaled through copy and through brightness curves of the gold, not through hue.
- Charts and data visualizations in admin use grayscale + the gold for emphasis. They do not use a categorical palette.
- Marketing surfaces (when they exist) follow the same constraint.

**The only exception** is the artwork inside a book cover. Cover art lives on its own island — the system around it stays disciplined.

---

### D3 — Two typefaces, both serifs

Cormorant Garamond (display) and Spectral (body). No sans-serif anywhere in the product surface — including labels, captions, button text, and the admin panel.

**Implication:**
- The frontend team does not introduce Inter, Helvetica, or any geometric/grotesque sans for UI elements.
- Numeric data uses Spectral with tabular figures enabled (`font-feature-settings: "tnum"`).
- Code blocks (if they ever appear) use a monospaced serif like iA Writer Mono or fall back to system monospace.

**Why two serifs is enough:** Cormorant supplies the editorial gravitas of titles; Spectral is a body workhorse with strong italic and small-caps presence. The pairing covers every text role we need.

---

### D4 — Books as posters

Book covers are the primary visual element. They are treated with weight: 2:3 ratio, subtle radius, the only shadow in the system, generous size in heros.

**Implication:**
- We never shrink a cover below 64px wide.
- We never crop a cover to fill space — letterbox onto canvas instead.
- We never overlay text or chrome on a cover (no "NEW" ribbons, no rating stars).
- The fallback embossed-letter cover is treated as carefully as a real cover — no plain rectangles with text.

---

### D5 — The wordmark is the logo

The product has no mark/symbol. The lowercase italic wordmark *sentido* is the entire brand identity. No glyph, no monogram, no app-icon abstraction (the iOS/PWA icon is the wordmark inside a tight frame).

**Implication:**
- Favicon: the letter "s" in Cormorant Garamond italic, gold on near-black.
- PWA icon: the wordmark on canvas, centered, with `space-5` padding.
- Open Graph default image: the wordmark + the page's book cover (when applicable) on a canvas-colored background.

---

### D6 — No popularity surfaces

The product does not display reader counts, view counts, ratings, "trending", "most read", "this week's top". The PRD §8 anti-adjacency to Goodreads/Skoob is enforced here: discovery is by ressonância, not by crowd.

**Implication:**
- No `★ 4.3 (1,247 ratings)` anywhere.
- No "trending" badge.
- No homepage section called "Mais lidos".
- Internal analytics for editorial decisions are admin-only and never surfaced to readers.

---

### D7 — No personalization framing

The product does not say "Recommended for you" or "Based on what you've read". The product is impersonal and editorial — it offers the same room to everyone.

**Implication:**
- "Livros relacionados" is based on semantic similarity, not on user history. The label is "se esse livro ressoou, talvez estes também", not "porque você leu X".
- No user accounts in MVP (PRD §10 confirms). When auth arrives in Phase 3, personalization framing remains disallowed.

---

### D8 — PT-BR only, in PT-BR

The product is in Brazilian Portuguese. There is no language switcher in MVP and no English UI. The catalog covers books in any original language; the interface is monolingual.

**Implication:**
- Strings live in PT-BR directly in components, not behind an i18n key (until Phase 2+ when an i18n system is added for translations of generated content, but the UI remains PT-BR-only).
- The OpenAI `text-embedding-3-small` source text is composed in English internally for embedding quality (PRD §6.4); this **never** surfaces to the user.
- Date and number formatting uses `pt-BR` locale.

---

### D9 — Density is restrained on purpose

The system targets low information density. Whitespace is structural, not decorative.

**Implication:**
- When a page begins to feel cramped, the first response is to remove a section, not to tighten spacing.
- Catalog grids cap at 5 columns on wide desktop — they do not become 8-column posters of covers.
- The admin panel uses tighter density than the public product, but still uses the system's spacing scale.

---

### D10 — No animation that draws attention to itself

Motion supports state transitions and entry/exit. It does not perform.

**Implication:**
- No looping animations on the home page.
- No "Lottie" illustrations.
- No animated emoji.
- The emotion-bar reveal is the most animated element in the product, and it animates once.
- All transitions respect `prefers-reduced-motion`.

---

## 2. Anti-patterns — explicit rejections

These have been considered and rejected. Do not re-propose without raising it back to the orchestrator with a strong product reason.

### A1 — Star ratings, score badges
Sentido is anti-rating. The emotional profile bars are not a rating — they are dimensions of experience. We do not introduce 5-star ratings, percentages, "98% match", or any reductive numeric score.

### A2 — "Save to list" / shelf metaphors
Goodreads, Skoob, and Storygraph all have shelves ("Want to Read", "Currently Reading", "Read"). The MVP does not. When user lists arrive (post-Phase 3), they are framed editorially ("coleções pessoais"), not as shelves.

### A3 — Social proof
No "Maria também leu este livro." No friend graphs, no follow buttons, no activity feeds. If a recommendation engine ever surfaces "users who searched X also looked at Y" — the framing surfaces the **work**, not the **other users**.

### A4 — Gamification
No streaks, no badges, no reading-challenge counters, no XP, no "you read N books this month" celebrations.

### A5 — Notifications and push
The MVP has no notification surface. If/when it does, the volume is very low (e.g., "uma nova coleção foi adicionada") and the tone matches §voice.md.

### A6 — Modal upsells, paywalls, interstitials
The MVP is free and has no paywall. When monetization is introduced (PRD Phase 2+), it is not modal-driven. No "Subscribe to see more results" gates.

### A7 — Carousels with auto-advance
Carousels exist (book-peek, related). None of them auto-advance. The reader controls scroll.

### A8 — Marketing-style hero sections
The home page is a catalog, not a landing page. No "Hero with big headline + CTA button". The product opens directly into the catalog with the search field and editorial collections.

### A9 — Cookie banners with personality
If a cookie banner is required by jurisdiction, it follows the brand: small, bottom-of-page strip in `body-sm`, `--text-muted`, with text like "este site usa cookies para entender uso. [aceitar] [recusar]". No "We value your privacy 💜" framing.

### A10 — Decorative imagery
No stock photos, no hero illustrations, no decorative photography of bookshelves. The only image content the product owns is book covers (and Phase 2 author portraits).

### A11 — Bright colors anywhere outside cover art
No green checkmarks, no red error states, no blue links. Everything chromatic uses the gold.

### A12 — Heavy frames, drop shadows, gradients on chrome
The only shadow is on book covers. The only gradient is inside the emotion-bar fill and inside fallback covers. UI chrome is flat.

### A13 — Pseudo-randomized fortune-cookie copy
No "today's reading mood" widgets, no "your book of the day" surprises. The product is queryable, not whimsical.

### A14 — Modal toasts for routine confirmation
A successful action (admin publishes a book, a user lands on a search page) does not show a toast. The state change is the confirmation.

### A15 — "Login with Google/Apple/etc." in MVP
No auth surface for the public product in MVP (PRD §10 confirms). When auth arrives, the patterns above still apply — no celebratory onboarding flow.

---

## 3. How to escalate a decision

If a future task surfaces a real conflict with any decision above:

1. The frontend specialist **does not work around it**. They report it back to the orchestrator in their Agent return message.
2. The orchestrator reviews against the PRD and this file. If the product genuinely requires breaking a decision, the orchestrator amends `decisions.md` with a dated entry recording the change and the reason.
3. The amendment then propagates: the implementation plan is updated, and the frontend specialist re-dispatched against the new plan.

Decisions are not folklore. They live in this file and they evolve in this file.

---

## 4. Decision log (post-MVP additions)

(Empty in v1. New load-bearing decisions land here with a date and one-paragraph rationale.)
