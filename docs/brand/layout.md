# Layout

> How components compose into pages. How pages breathe. How the rhythm of the system reads as one thing across mobile and desktop.

The canonical mockup (`docs/assets/book_overview_mobile.jpg`) demonstrates the rhythm at mobile width. This file generalizes the rules so any screen — book page, catalog, search results, author page, admin panel — sits inside the same system.

---

## 1. Page rhythm — the contract

Every page composes from this vertical structure:

```
┌─────────────────────────────────────┐
│  HEADER          (sticky)           │  height ~64px
├─────────────────────────────────────┤
│                                     │
│  PAGE INTRO      (hero or label)    │
│                                     │
│  ─────────────────────              │  divider
│                                     │
│  PRIMARY CONTENT                    │
│                                     │
│  ─────────────────────              │  divider
│                                     │
│  SECONDARY CONTENT                  │
│                                     │
│  ─────────────────────              │  divider
│                                     │
│  ADJACENCY (related, more from…)    │
│                                     │
├─────────────────────────────────────┤
│  FOOTER                             │
└─────────────────────────────────────┘
```

### 1.1 Vertical spacing between sections

| Breakpoint | Section → section |
|---|---|
| Mobile (< 768px) | `space-7` (48px) |
| Tablet / Desktop (≥ 768px) | `space-8` (64px) |

Inside a section, spacing comes from `space-1` … `space-5`. Crossing the `space-6` threshold inside a section signals it has become two sections — split it.

### 1.2 Page top and bottom padding

| Breakpoint | Top | Bottom |
|---|---|---|
| Mobile | `space-7` (48px) | `space-8` (64px) |
| Desktop | `space-9` (96px) | `space-9` (96px) |

The bottom padding is generous on purpose. Pages end with breathing room, not with a hard scroll stop.

---

## 2. Horizontal layout

### 2.1 Content widths

| Token | Width | Use |
|---|---|---|
| `--width-prose` | `38rem` (~608px) | Long-form text: synopsis, biography, collection description. |
| `--width-content` | `42rem` (~672px) | Default page column — book page, author page. |
| `--width-wide` | `64rem` (~1024px) | Catalog grids, search results. |
| `--width-edge` | `90rem` (~1440px) | Maximum page width. Beyond this, padding grows. |

### 2.2 Page padding (horizontal)

| Breakpoint | Padding |
|---|---|
| Mobile (< 640px) | `space-5` (24px) |
| Tablet (640–1024px) | `space-7` (48px) |
| Desktop (≥ 1024px) | `space-8` (64px) |
| Wide (≥ 1440px) | auto-margin to `--width-edge` |

### 2.3 The "centered column" pattern

Most pages use a single centered column at `--width-content`. The book page, author page, collection page, and search-result page all use this. Catalog and grid pages widen to `--width-wide`. The admin panel widens to `--width-edge`.

```
┌────────────────────────────────────────────┐
│                                            │
│    ┌──────────────────────────────┐        │
│    │                              │        │
│    │   --width-content            │        │
│    │                              │        │
│    └──────────────────────────────┘        │
│                                            │
└────────────────────────────────────────────┘
```

---

## 3. Breakpoints

| Token | Min width | Notes |
|---|---|---|
| `--bp-sm` | 640px | Anything below is "mobile". |
| `--bp-md` | 768px | Tablet portrait. Page padding grows. |
| `--bp-lg` | 1024px | Desktop. Grids expand, sidebars appear. |
| `--bp-xl` | 1280px | Wide desktop. Catalog goes to 5–6 columns. |
| `--bp-2xl` | 1440px | Caps at `--width-edge`. |

The system targets mobile first. Desktop is not "the same thing with margins" — desktop unlocks **wider grids** (catalog) and the **two-column hero** (book page).

---

## 4. Header

```
mobile:   [← voltar]      sentido      [          ]
desktop:  [sentido]   [catálogo · coleções · buscar]   [admin]
```

| Property | Value |
|---|---|
| Height | 64px |
| Position | sticky top |
| Background | `--bg-overlay` (canvas at 85% opacity), `backdrop-filter: blur(12px)` |
| Bottom border | 1px `--divider` |
| Mobile layout | grid `[back] [wordmark centered] [actions]` |
| Desktop layout | flex `[wordmark left] [nav center-left] [actions right]` |
| Padding | matches page horizontal padding |

Back link uses a left-chevron + "voltar" in `body-sm` italic, `--text-muted`. Tapping the wordmark always routes to home.

---

## 5. Book page — the canonical hero

The mockup defines this. The structure:

### 5.1 Mobile

```
┌─────────────────────────────────────┐
│  HEADER                             │
├─────────────────────────────────────┤
│                                     │
│  [book-peek carousel]               │  see §6
│                                     │
│      ┌──────────┐                   │
│      │          │                   │
│      │  COVER   │  hero, 220×330    │
│      │          │                   │
│      └──────────┘                   │
│                                     │
│  1942 · PROGRESSIVO       label-sm  │
│  O Estrangeiro            display-lg│
│  Albert Camus             italic    │
│                                     │
│  [pill] [pill] [pill]               │
│                                     │
│  │ "quote"                          │
│                                     │
│  ───────────────────                │
│                                     │
│  PERFIL EMOCIONAL                   │
│  [emotion bars × 6]                 │
│                                     │
│  ───────────────────                │
│                                     │
│  SINOPSE                            │
│  [body-lg prose]                    │
│                                     │
│  ───────────────────                │
│                                     │
│  SE ESSE LIVRO RESSOOU…             │
│  [related carousel]                 │  see §7
│                                     │
└─────────────────────────────────────┘
```

### 5.2 Desktop

The hero becomes two columns:

```
┌─────────────────────────────────────────────────────────┐
│  HEADER                                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    1942 · PROGRESSIVO                     │
│  │          │    O Estrangeiro                          │
│  │  COVER   │    Albert Camus                           │
│  │ 320×480  │                                           │
│  │          │    [pill] [pill] [pill]                   │
│  └──────────┘                                           │
│                  │ "quote"                              │
│                                                         │
│  ────────────────────────────────────────               │
│                                                         │
│  PERFIL EMOCIONAL              SINOPSE                  │
│  [bars]                        [prose, --width-prose]   │
│                                                         │
│  ────────────────────────────────────────               │
│                                                         │
│  SE ESSE LIVRO RESSOOU…                                 │
│  [related carousel, wider]                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Profile and synopsis become a two-column layout on desktop (≥ `--bp-lg`): emotion bars on the left, synopsis on the right, gap `space-8`. Below that, the related carousel runs full width of `--width-content`.

The **book-peek carousel** (top) appears on mobile only. On desktop the peek pattern is replaced with prev/next chevrons floating outside the cover's left and right edges (`§ components → carousel chevron`).

---

## 6. Book-peek carousel pattern

The pattern at the top of the canonical mockup, where adjacent books are visible behind the current one.

```
   ┌─────┐  ┌────────────┐  ┌─────┐
   │ ←   │  │            │  │  → │
   │     │  │   ACTIVE   │  │     │
   │ N…  │  │            │  │ A…  │
   └─────┘  └────────────┘  └─────┘
              [N° / total]
```

| Property | Value |
|---|---|
| Track | horizontally scrolling, snap-x mandatory |
| Active item | centered, full hero size |
| Adjacent items | partially visible, fade to 40% opacity, 80% scale |
| Gap | `space-5` |
| Snap behavior | scroll-snap-align: center on each item |
| Indicator | "N / total" in `label-sm`, `--text-muted`, below the active cover |
| Swipe | native touch scroll on mobile; chevrons on desktop |

When the user lands on a book page through a deep link, they enter at that book's position. Navigating forward/back through the peek carousel updates the URL (`/livro/{slug}`) so each book is bookmarkable.

---

## 7. Related carousel pattern

The "Se esse livro ressoou…" pattern at the bottom of the canonical mockup.

```
   ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐
   │       │  │       │  │       │  │       │
   │ COVER │  │ COVER │  │ COVER │  │ COVER │
   │       │  │       │  │       │  │       │
   └───────┘  └───────┘  └───────┘  └───────┘
   Title       Title       Title       Title
   Author      Author      Author      Author
```

| Property | Value |
|---|---|
| Track | horizontally scrolling, snap-x proximity |
| Item width | 140px (mobile) · 160px (desktop) |
| Gap | `space-4` (16px) |
| Edge fade | linear gradient overlay at left and right edges, 32px wide, masking to indicate more content |
| Item structure | book card per `components.md §8` |
| Quantity | up to 10 items |

The track overflows the page's horizontal padding so the edge fade reaches the viewport edge. Achieve this by negative-margin or by lifting the carousel out of the centered column.

---

## 8. Catalog grid

The home page and search-result page.

| Breakpoint | Columns | Gap |
|---|---|---|
| Mobile (< 640px) | 2 | `space-4` (16px) |
| Tablet (640–1024px) | 3 | `space-5` (24px) |
| Desktop (1024–1280px) | 4 | `space-5` (24px) |
| Wide (≥ 1280px) | 5 | `space-6` (32px) |

Each cell is a book card. Cells are aligned to the top. Title and author may wrap to two lines on cell, then truncate. The grid lives inside `--width-wide`.

No "show more" buttons. Pagination uses infinite scroll for search results; the catalog home is curated and finite per editorial decision.

---

## 9. Editorial sections

For content sections that pair a title + lead-in paragraph with a content block (catalog of a collection, "novidades", featured author):

```
┌─────────────────────────────────────┐
│                                     │
│  COLEÇÃO                            │  label
│  Livros que ficam no corpo          │  display-md
│  Um conjunto de leituras que        │  body-lg, --text-muted
│  permanecem físicas depois          │  max-width --width-prose
│  do último parágrafo.               │
│                                     │
│  [grid or carousel]                 │
│                                     │
└─────────────────────────────────────┘
```

Gap label → title: `space-2`. Gap title → lead: `space-4`. Gap lead → content: `space-6`.

---

## 10. Admin panel layout

The admin panel (`/admin`) is the one place where layout density differs.

| Property | Value |
|---|---|
| Page width | `--width-edge` (`90rem`) |
| Sidebar | 240px fixed left rail with nav items in `body-md`, weight 400, `--text-muted`; active item `--accent` |
| Header | persistent breadcrumb in `label`; right side shows current curator and a logout link |
| Tables | dense — `body-sm`, row height 44px, no zebra striping, hairline `--divider` between rows |
| Forms | label above input, label in `label`, input full width of its column |
| Actions | primary buttons per `components.md §10.1`; destructive actions are ghost buttons that prompt confirm in a dialog |

The admin panel still uses the brand palette and typography. It does not become a generic "dashboard". It is a literary back-office.

---

## 11. Mobile-specific rules

- **No bottom navigation bar.** Navigation is in the top header and inside pages.
- **No floating action button.** The product does not have a "post" action.
- **Tap targets** are minimum 44 × 44 px. Pill chips and emotion bars are not interactive on the book page; they are display only.
- **Safe area insets** are respected at the top (notch) and bottom (home indicator) — add `env(safe-area-inset-*)` to header padding-top and footer padding-bottom.

---

## 12. Density philosophy

The interface is **deliberately under-dense**. Whitespace is not wasted space; it is the thing that signals "this matters." When a page begins to feel cramped, the first move is to **remove** something rather than tighten spacing. The second move is to split into two pages. Tightening spacing is the third option and rare.
