# Foundations

> The atoms of the visual system. Every component composes these tokens; nothing in the product introduces a value outside this file without a deliberate change here.

---

## 1. Color

Sentido uses **one canvas, one accent, one text family**. There is no second hue. The constraint is the brand.

### 1.1 Tokens

| Token | Hex | Use |
|---|---|---|
| `--bg-canvas` | `#0B0A08` | Primary background. Warm near-black; not pure `#000`. |
| `--bg-elevated` | `#14110D` | Cards, modals, sheets. Slightly lifted from canvas. |
| `--bg-overlay` | `rgba(11, 10, 8, 0.85)` | Modal scrims, sticky headers when content scrolls behind. |
| `--accent` | `#C9A96E` | The gold. Brand mark, active state, emotion bars, pill outlines, dividers, quote bars. |
| `--accent-hover` | `#D7BA82` | Interactive lift on hover/focus. |
| `--accent-dim` | `#8A7A5E` | Dimmed gold for secondary metadata and the "muted" tier of labels. |
| `--text-primary` | `#E8DFD2` | Body, titles, default UI text. Warm off-white — never pure `#FFF`. |
| `--text-muted` | `#8A7A5E` | Section labels, captions, metadata. Same value as `--accent-dim` (deliberate). |
| `--text-subtle` | `#4A4338` | Tertiary text, disabled states. Just visible against canvas. |
| `--divider` | `rgba(201, 169, 110, 0.20)` | Hairline rules. Gold at 20% — never a flat gray. |
| `--focus-ring` | `rgba(215, 186, 130, 0.45)` | Focus outline. Soft gold halo, 2px. |

### 1.2 Rules

- **The canvas is warm**, not cool. Never `#0a0a0a`, never `#111`. The `#0B0A08` value has the slight amber bias that lets the gold sit naturally on it.
- **Gold is structural, not decorative.** It carries hierarchy (active, focus, accent rules). It is not used to "spice up" copy or sections.
- **Never introduce a second hue** for status (no red errors, no green confirms). State color comes from the gold's brightness curve (`--accent-dim` → `--accent` → `--accent-hover`).
- The book cover is the **only** place uncontrolled color appears. Cover art lives on its own; the system around it stays disciplined.

### 1.3 Contrast

| Pair | Ratio | WCAG |
|---|---|---|
| `--text-primary` on `--bg-canvas` | 13.4 : 1 | AAA |
| `--accent` on `--bg-canvas` | 7.8 : 1 | AAA |
| `--text-muted` on `--bg-canvas` | 4.6 : 1 | AA |
| `--text-subtle` on `--bg-canvas` | 1.9 : 1 | Decorative only — never load-bearing copy. |

`--text-subtle` is for ornament (e.g., the embossed letter inside a fallback cover). Functional copy uses `--text-muted` or above.

---

## 2. Typography

Two typefaces. Both serifs. Both via Google Fonts (Next.js `next/font` recommended for self-hosting and CLS prevention).

### 2.1 Families

| Token | Family | Weight axis | Use |
|---|---|---|---|
| `--font-display` | **Cormorant Garamond** | 300 / 400 / 500 / 500 italic | Wordmark, page titles, book titles, hero headlines. |
| `--font-body` | **Spectral** | 300 / 400 / 500 / 600 | Body, captions, labels, UI text. |

Both families ship italic variants — italics are used **structurally** in this system (wordmark, author name, pull-quotes), not for emphasis inside prose. For mid-sentence emphasis, use italics of the surrounding family but reserve heavy use for the structural slots.

### 2.2 Type scale

Mobile-first. Sizes use `rem` (assume 16px root) to respect user preferences. Desktop values listed where they differ.

| Token | Mobile | Desktop | Line | Weight | Tracking | Family |
|---|---|---|---|---|---|---|
| `display-xl` | 2.75rem (44px) | 4rem (64px) | 1.05 | 500 | -0.02em | display |
| `display-lg` | 2.25rem (36px) | 3rem (48px) | 1.1 | 500 | -0.015em | display |
| `display-md` | 1.75rem (28px) | 2.25rem (36px) | 1.15 | 500 | -0.01em | display |
| `title-lg` | 1.375rem (22px) | 1.5rem (24px) | 1.3 | 500 | 0 | display |
| `title-md` | 1.125rem (18px) | 1.25rem (20px) | 1.35 | 500 | 0 | display |
| `body-lg` | 1.0625rem (17px) | 1.125rem (18px) | 1.6 | 400 | 0 | body |
| `body-md` | 1rem (16px) | 1rem (16px) | 1.6 | 400 | 0 | body |
| `body-sm` | 0.875rem (14px) | 0.875rem (14px) | 1.55 | 400 | 0 | body |
| `label` | 0.75rem (12px) | 0.75rem (12px) | 1.4 | 500 | +0.15em | body, uppercase |
| `label-sm` | 0.6875rem (11px) | 0.6875rem (11px) | 1.4 | 500 | +0.18em | body, uppercase |

### 2.3 Italics & small caps

- **The wordmark** "sentido" is always Cormorant Garamond Italic, lowercase, `--accent` color. It is never set in roman, never uppercased.
- **Author names** appear in body italic.
- **Pull-quotes** use display italic at `body-lg` size, in `--accent` color, with a left bar (see `components.md`).
- **Section labels** (`PERFIL EMOCIONAL`, `SINOPSE`) use the `label` token: body family, uppercase, +0.15em tracking, `--text-muted`. We do not use real small caps — uppercase with tracking gives a more uniform look at the sizes we use.

### 2.4 Prose defaults

For long-form text (synopsis, biography, collection descriptions):

- Size: `body-lg`
- Color: `--text-primary`
- Measure: 60–70 characters per line (enforced via `max-width: 38rem`).
- Paragraph spacing: `space-4` between paragraphs.
- No first-line indent. No drop caps in MVP.

---

## 3. Spacing

Base unit: **4px**. Scale uses a near-geometric progression to keep relations harmonic.

| Token | Value | Common use |
|---|---|---|
| `space-1` | 4px | Title ↔ author gap inside a card |
| `space-2` | 8px | Pill padding-y; bar gaps |
| `space-3` | 12px | Cover ↔ caption; pill padding-x |
| `space-4` | 16px | Paragraph break; mobile gutter inset |
| `space-5` | 24px | Mobile horizontal padding; label ↔ content |
| `space-6` | 32px | Divider vertical margin; card ↔ card |
| `space-7` | 48px | Section ↔ section (mobile) |
| `space-8` | 64px | Section ↔ section (desktop); hero ↔ identity |
| `space-9` | 96px | Page top padding (desktop); end-of-page padding |
| `space-10` | 128px | Generous editorial breaks |

Spacing inside a component composes from `space-1` … `space-5`. Spacing **between** components uses `space-6` and above. Mixing the two scales is what makes screens feel busy.

---

## 4. Motion

Motion is restrained. Nothing bounces. Nothing pops.

### 4.1 Durations

| Token | Value | Use |
|---|---|---|
| `--motion-fast` | 120ms | Hover/focus state changes, color transitions |
| `--motion-base` | 200ms | Element entry, opacity fades |
| `--motion-slow` | 360ms | Modal/sheet entry, page transitions, carousel snap |
| `--motion-glacial` | 600ms | Hero image reveals, deliberate emphasis |

### 4.2 Easing

| Token | Curve | Use |
|---|---|---|
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Default. Quick start, soft settle. |
| `--ease-entry` | `cubic-bezier(0.16, 1, 0.3, 1)` | Things appearing. |
| `--ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | Things leaving. |

### 4.3 Rules

- **No bounce, no overshoot.** This is not a playful interface.
- **No spring physics** for UI transitions. Reserve any "physical" motion for carousel scroll inertia handled by the platform.
- **Hover** state transitions in `--motion-fast` only. Color changes; nothing moves.
- **Respect `prefers-reduced-motion`** — disable non-essential transitions, fade instead of slide.

---

## 5. Elevation

There is essentially no elevation system. The interface is flat. **The one exception is the book cover.**

### 5.1 Cover shadow

```css
box-shadow:
  0 24px 48px -12px rgba(0, 0, 0, 0.6),
  0 8px 24px -8px rgba(201, 169, 110, 0.08);
```

The dark layer gives the poster its weight. The faint gold layer is the room's ambient bounce light on the cover. Together they create the "object on a shelf" feeling.

### 5.2 Everything else

- Cards, panels, modals: **no shadow**. They live on `--bg-elevated` and are distinguished by background, not depth.
- Buttons, inputs: **no shadow**. They are distinguished by border color and state.
- Sticky headers: **no shadow**. Use `--bg-overlay` and a `--divider` rule at the bottom.

---

## 6. Border radius

Almost everything is sharp.

| Token | Value | Use |
|---|---|---|
| `--radius-none` | 0 | Most surfaces. Cards, sections, inputs. |
| `--radius-sm` | 2px | Book covers (the slightest softening). |
| `--radius-md` | 4px | Buttons (rectangular but not razor-cut). |
| `--radius-full` | 9999px | Pills only (tag chips, filter chips). |

We do not have a `--radius-lg`. If a design needs one, the design needs to be reconsidered first.

---

## 7. Iconography

- **Icon style:** thin-line, 1.5px stroke, no fill, rounded line joins.
- **Recommended set:** Phosphor (light weight) or Lucide. Pick one and use only that one.
- **Default size:** 20px. Available at 16px (inline) and 24px (standalone).
- **Color:** `currentColor` always. Icons inherit from the text they sit beside.
- **No emoji** in product UI. Ever.

---

## 8. Image treatment

- **Book covers** — the only image content the product owns. See `components.md → Book cover`.
- **Author portraits** (Phase 2) — circular crop at 64px or 128px, subtle 1px inner ring at `--accent` 20%, no shadow.
- **All other imagery** is avoided. No stock illustration. No decorative photography. No hero banners.

The product's visual surface is books + type + space. Adding imagery beyond that breaks the system.
