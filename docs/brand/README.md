# Brand reference — Sentido

> Canonical visual and verbal identity. Source of truth for every page, component, and string in the product.

Sentido is a catalog of books treated as **emotional objects**. The brand reflects the product premise: a book is not a product to be sold but a presence to be encountered. The interface gets out of the way so that books — their covers, their titles, their feelings — can dominate the field of attention.

---

## Brand essence

| | |
|---|---|
| **Sensation** | Stepping into a dim, quiet room where books are displayed like artifacts. |
| **Adjacency** | Letterboxd × Are.na × a hardcover monograph from a small art publisher. |
| **Anti-adjacency** | Goodreads, Amazon Kindle Store, any "Top 10 books of 2026" listicle. |
| **Voice** | Lowercase, literary, sober. The kind of voice that uses semicolons. |
| **Restraint** | One accent color. Two typefaces. No badges, no streaks, no rankings. |

---

## What lives in this folder

| File | Owns |
|---|---|
| [`foundations.md`](./foundations.md) | Color tokens, typography stack, type scale, spacing, motion, elevation |
| [`components.md`](./components.md) | Recurring UI patterns (pill, emotion bar, label, divider, quote, cover, card) with concrete specs |
| [`layout.md`](./layout.md) | Page rhythm, hero patterns, carousel patterns, content widths, mobile and desktop breakpoints |
| [`voice.md`](./voice.md) | PT-BR copy conventions, label style, naming, punctuation, what to avoid |
| [`decisions.md`](./decisions.md) | Load-bearing decisions and explicit anti-patterns — the "do not do this" list |

---

## How the frontend team should use this

- Read `foundations.md` first; it sets the tokens that every other file references.
- Treat the tokens as **the contract**: any new component composes existing tokens — it does not invent new colors, type sizes, or spacing values.
- When a screen needs a pattern that is not yet documented, propose the pattern back to the orchestrator with a sketch of the tokens it would compose. The orchestrator decides whether to extend this reference.
- The mockup at `docs/assets/book_overview_mobile.jpg` is the canonical example of the system applied. When in doubt, match its rhythm.

---

## Hierarchy when sources conflict

1. **This brand reference** wins on color, type, spacing, motion, voice.
2. **The product specification** (`docs/product/prd.md`) wins on functional behavior, scope, data, naming of features.
3. **The mockups** illustrate the system; they do not override it. If a future mockup uses a different gold, the gold here wins.

If a real conflict appears (e.g., the PRD specifies a typeface that contradicts this reference), the frontend specialist reports it to the orchestrator. The orchestrator reconciles by updating one of the two source documents.
