# Components

> Recurring UI patterns visible in the canonical mockup (`docs/assets/book_overview_mobile.jpg`) and their derivatives. Each component composes tokens from `foundations.md`. No component invents its own color, type size, or spacing.

This file does not prescribe a framework or component API. It describes **what each pattern looks like and how it behaves**. The frontend team implements them in whichever component library style fits the Next.js codebase, but the visual contract is binding.

---

## 1. Wordmark

The product name "sentido" in display italic.

| Property | Value |
|---|---|
| Family | `--font-display` italic |
| Size | `title-md` (mobile) · `title-lg` (desktop) |
| Color | `--accent` |
| Case | Lowercase, always |
| Tracking | 0 |
| Weight | 500 |

Used in the app header (centered on mobile, left on desktop) and in the footer (see §12). Do not enlarge it for a splash treatment. Do not pair it with a logo mark — the wordmark **is** the logo.

### 1.1 Footer variant

A smaller, muted variant of the wordmark appears in the footer.

| Property | Value |
|---|---|
| Family | `--font-display` italic |
| Size | `body-sm` |
| Color | `--text-muted` |
| Case | Lowercase |

The footer variant is the only deviation from the header treatment. Do not introduce additional variants.

---

## 2. Pill chip

Visible in the mockup as `apatia`, `absurdo`, `sol como violência` beneath the author name.

```
   ┌─────────────────┐
   │     apatia      │
   └─────────────────┘
```

| Property | Default | Active / hover |
|---|---|---|
| Background | transparent | `rgba(201, 169, 110, 0.08)` |
| Border | 1px solid `rgba(201, 169, 110, 0.40)` | 1px solid `--accent` |
| Text color | `--accent` | `--accent-hover` |
| Text style | `body-sm`, weight 400 | same |
| Padding | `space-2` (8px) vertical, `space-3` (12px) horizontal | same |
| Border radius | `--radius-full` | same |
| Gap between pills | `space-2` (8px) | — |
| Transition | `color, background, border-color` over `--motion-fast` `--ease-standard` | — |

### Variants
- **Static tag** (used on book pages): no interaction, no hover state.
- **Filter chip** (used on browse pages): adds an active state where background fills with `rgba(201, 169, 110, 0.16)` and border goes to full `--accent`.

Do not put icons inside pills. Do not nest pills.

---

## 3. Emotion bar

The horizontal bars that display the emotional profile of a book (`angústia 6.0`, `melancolia 4.0`, etc.).

### 3.1 Anatomy

Three-column grid: `[label] [track] [value]`.

```
   angústia    ━━━━━━━━━━━━━━────────    6.0
```

| Slot | Width | Content |
|---|---|---|
| Label | `7rem` (mobile: `6rem`) | Right-aligned. `body-md` (mobile: `body-sm`). `--text-primary`. Lowercase. |
| Track | `1fr` (flex) | The bar itself. |
| Value | `2.5rem` | Right-aligned. `body-sm`. `--text-muted`. Format `0.0` with one decimal. |

Gap between slots: `space-4` (16px). Vertical gap between bars: `space-3` (12px).

### 3.2 Track and fill

- **Track**: full-width, 2px tall, `--divider` background, `--radius-full`.
- **Fill**: animated width based on value/10. Linear gradient `linear-gradient(90deg, var(--accent-dim) 0%, var(--accent) 100%)`. `--radius-full`.
- **Reveal animation** on first appearance (intersection-observed): width animates from 0 to target over `--motion-glacial` with `--ease-entry`. Animates once; does not re-animate on re-entry.
- **Reduced motion**: skip the reveal — render at final width.

### 3.3 Numeric precision

Values are rendered to one decimal (`6.0`, `8.5`, `1.0`). Never use percentages (no `60%`); never round to integers (no `6`).

---

## 4. Section label

The uppercase letter-spaced text that introduces a section (`PERFIL EMOCIONAL`, `SINOPSE`, `SE ESSE LIVRO RESSOOU, TALVEZ ESTES TAMBÉM`).

| Property | Value |
|---|---|
| Token | `label` (12px) or `label-sm` (11px) for tertiary headers |
| Color | `--text-muted` |
| Case | Uppercase |
| Tracking | +0.15em (`label`) or +0.18em (`label-sm`) |
| Margin below | `space-5` (24px) before content begins |
| Margin above | inherited from the section's outer rhythm — do not add extra |

### Tertiary label variant
`1942 · PROGRESSIVO` (year · pace) above a book title uses `label-sm`. Items separated by ` · ` (with surrounding spaces).

The label is a **single line of text**. It does not get a bottom border, a background pill, or an icon prefix.

---

## 5. Hairline divider

The gold rules that separate sections.

| Property | Value |
|---|---|
| Color | `--divider` (gold at 20% opacity) |
| Height | 1px |
| Width | 100% of content column |
| Margin (mobile) | `space-6` top, `space-6` bottom (32px each side) |
| Margin (desktop) | `space-7` top, `space-7` bottom (48px each side) |

Use sparingly. A divider is for marking a meaningful change in section — not for visual rhythm between every paragraph. If two adjacent sections feel like they need a divider between them but their content is closely related, use spacing instead.

---

## 6. Quote block

The italic gold pull-quote with a left bar.

```
   │
   │  "A indiferença de Meursault é mais
   │   perturbadora do que qualquer grito."
   │
```

| Property | Value |
|---|---|
| Family | `--font-display` italic |
| Size | `body-lg` |
| Color | `--accent` |
| Left border | 1px solid `--accent`, full height |
| Padding left | `space-4` (16px) |
| Padding top/bottom | `space-2` (8px) |
| Quotation marks | Curly quotes (`"…"`) — never straight ASCII quotes |

Use only for **load-bearing quotes** (the editorial line on a book page, a pull-quote on a collection). Do not use for casual quoting in body prose.

---

## 7. Book cover

The single most important visual element in the product. Books are **posters**.

### 7.1 Aspect ratio
**2:3 always.** No exceptions. Source images that don't conform are letterboxed onto the canvas color (`--bg-canvas`) — never cropped, never stretched.

### 7.2 Sizes

| Context | Width | Height (2:3) |
|---|---|---|
| Catalog grid (mobile) | clamp(140px, 42vw, 200px) | derived |
| Catalog grid (desktop) | 200px | 300px |
| Book page hero (mobile) | 220px | 330px |
| Book page hero (desktop) | 320px | 480px |
| Related carousel item | 140px | 210px |
| Inline reference (in prose) | 64px | 96px |

### 7.3 Treatment
- Border radius: `--radius-sm` (2px).
- Shadow: the cover shadow from `foundations.md §5.1`. **The only place a shadow appears in the system.**
- No border, no overlay, no frame.

### 7.4 Fallback for missing covers
When a book has no cover image, render an **embossed letter cover**:

- Background: a deterministic gradient based on the book's first letter or slug hash. Use only colors from a **muted palette** (desaturated, low-luminance). Examples: deep green/black `linear-gradient(135deg, #1a2e1a 0%, #0a1410 100%)`, oxblood `linear-gradient(135deg, #2a1414 0%, #100808 100%)`, slate-blue `linear-gradient(135deg, #14202e 0%, #08101a 100%)`. The fallback palette must never include vivid color.
- The first letter of the title rendered at `display-xl` size, in `--font-display` weight 300, color `rgba(255, 255, 255, 0.06)`, centered, slight blur (`filter: blur(0.5px)`) so it reads as embossed rather than printed.
- The shadow treatment still applies.

The mockup shows this pattern for the related books at the bottom (`N`, `A`, etc.).

---

## 8. Book card

A cover plus its caption, as used in carousels and grids.

```
   ┌──────────┐
   │          │
   │   cover  │
   │          │
   └──────────┘
    Title             ← body-md, 500, --text-primary
    Author            ← body-sm, italic, --text-muted
```

| Property | Value |
|---|---|
| Cover treatment | per §7 |
| Gap cover → title | `space-3` (12px) |
| Gap title → author | `space-1` (4px) |
| Title style | `body-md`, weight 500, `--text-primary`, max 2 lines (`-webkit-line-clamp: 2`) |
| Author style | `body-sm`, italic, `--text-muted`, single line, truncate with ellipsis |
| Card padding | none — the card is content, not a container |
| Interactive area | entire card. Whole surface is the click target. |
| Hover | cover lifts: `transform: translateY(-2px); transition: --motion-base --ease-standard;` |

No "Add to list" button, no star rating, no menu on the card. The card is identity only.

---

## 9. Search field

Not visible in the canonical mockup but central to the product. Specifying it here so it lands inside the system.

| Property | Value |
|---|---|
| Container | full-width, max-width `36rem` on desktop, centered |
| Height | 56px |
| Background | `--bg-elevated` |
| Border | 1px solid `--divider` (`--accent` on focus) |
| Border radius | `--radius-md` (4px) |
| Padding | `space-5` horizontal |
| Placeholder | `"o que você quer sentir?"` — `--font-display` italic, `--text-muted` |
| Input text | `body-lg`, `--text-primary` |
| Icon | leading magnifier from chosen icon set, 20px, `--text-muted`; transitions to `--accent` on focus |
| Submit | implicit (Enter key) — no visible submit button on mobile; desktop shows the icon as the click target |
| Focus ring | `--focus-ring` (2px gold halo, offset 0) |

### Behavior
- On focus, the placeholder fades to 50% opacity before clearing as the user types.
- Empty submit (Enter on blank input) does nothing; no error state.
- Submission triggers a route change to `/buscar?q=...`. The field persists at the top of the results page with the active query as its value.

---

## 10. Button

Buttons are rare in this product. Most affordances are link-styled. When a button is needed:

### 10.1 Primary
| Property | Value |
|---|---|
| Background | `--accent` |
| Text color | `--bg-canvas` |
| Family | `--font-body`, weight 500 |
| Text size | `body-md` |
| Padding | `space-3` vertical, `space-5` horizontal |
| Border radius | `--radius-md` (4px) |
| Hover | background → `--accent-hover` |
| Disabled | background → `--accent-dim`, cursor not-allowed |

### 10.2 Ghost
| Property | Value |
|---|---|
| Background | transparent |
| Border | 1px solid `--divider` |
| Text color | `--accent` |
| Padding | `space-3` vertical, `space-5` horizontal |
| Hover | border → `--accent` |

### 10.3 Text link
- Color: `--accent`
- Underline: none by default; on hover `text-decoration: underline; text-underline-offset: 4px;`
- Family inherits from context

Do not introduce a "Secondary" filled button. Do not use icon-only buttons except in the carousel chevrons and the admin toolbar.

---

## 11. Carousel chevron

Used to navigate the book-peek carousel at the top of a book page and the related carousel at the bottom.

| Property | Value |
|---|---|
| Size | 40px × 40px touch target |
| Visible mark | 16px chevron glyph, `--accent`, 1.5px stroke |
| Background | transparent (no chip) |
| Position | floats over the carousel edge, vertically centered on the cover row |
| Hover | glyph color → `--accent-hover`; nothing else moves |
| Mobile | hidden — touch swipe replaces the chevron |

---

## 12. Footer

Minimal. The product does not have a marketing footer.

| Section | Content |
|---|---|
| Left | Wordmark (small, `body-sm`, italic, `--text-muted`) |
| Center | The single line `um catálogo afetivo de livros` in `body-sm`, `--text-muted` |
| Right | A handful of text links — "sobre", "coleções", "admin" (when authed) — separated by ` · ` |

Padding: `space-8` vertical, `space-5` horizontal. Top border: 1px `--divider`.

No social links. No newsletter signup. No "Made with ❤️".
