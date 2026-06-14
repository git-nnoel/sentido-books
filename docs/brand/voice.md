# Voice

> How Sentido writes. The product is in Portuguese (Brazilian). The tone is literary, sober, comfortable with quiet. The product never sells, never celebrates itself, never asks you to do anything urgently.

This file governs every string that appears in the product — UI labels, empty states, errors, microcopy, generated synopses, generated emotional descriptions, admin panel text. It does not govern user-generated content (there is none in MVP) or external/editorial content from third parties.

---

## 1. Voice essence

| Sentido sounds like | Sentido does not sound like |
|---|---|
| A small bookstore at the end of a quiet street | A landing page for a productivity app |
| The back cover of a Cosac Naify reissue | The front page of Amazon |
| A friend who reads a lot and texts you in lowercase | A marketing department |
| An editorial note in a small literary magazine | A push notification |
| Someone who says "talvez você goste" instead of "recomendado para você" | Someone who says "personalized just for you ✨" |

### Three rules under everything

1. **Lowercase is the default register**, except where typography rules require uppercase (section labels). Even page titles start with a lowercase article when grammatically natural. "o estrangeiro" is fine — but for book titles we respect the editorial casing the book itself uses ("O Estrangeiro").
2. **Punctuation is literary**, not informal. Em-dashes, semicolons, ellipses. Avoid exclamation marks entirely except in quoted text. Question marks are allowed sparingly.
3. **The product is never the subject of its own copy.** Don't write "Sentido encontra livros para você" — write "encontre o livro que ressoa". The user is the actor; the product is the room.

---

## 2. Portuguese specifics

The product is **Brazilian Portuguese (PT-BR)**. Every string is in PT-BR; no language switcher in MVP. The PRD §6.4 confirms this: synopses are generated in PT-BR, the embedding source text lives in English internally but never surfaces.

### 2.1 Treatment of the reader

- **Você**, never **tu**, never **vós**. Even in regions that use *tu*, the written register settles on *você*.
- **Verb-only forms** in CTAs (no pronouns): "buscar" not "buscar agora". "ler mais" not "leia mais".
- **No vocative openings**. Don't write "Olá! O que você quer ler hoje?" Write "o que você quer sentir?".

### 2.2 Foreign words

- Avoid English mid-sentence. **No** "feed", "trending", "match", "highlights", "library". Equivalents: "página inicial", "em alta" *(avoid this concept altogether)*, "afinidade", "destaques", "biblioteca".
- Loan words are acceptable only when there is no PT-BR equivalent that doesn't feel forced (`embedding` in admin docs, `slug` in dev contexts). They stay in roman, not italic.

### 2.3 Punctuation conventions

| Use | Example |
|---|---|
| Em-dash with spaces | `melancolia — não tristeza, melancolia` |
| Semicolon for related clauses | `o livro não termina; cessa` |
| Curly quotes always | `"o que você quer sentir?"` not `"o que você quer sentir?"` |
| Ellipsis as single glyph | `…` not `...` |
| Number ranges with en-dash | `1942–1960` |
| Series separator in metadata | ` · ` (space, middle dot, space): `1942 · progressivo` |

### 2.4 Capitalization

- **Book titles**: respect the published casing of the book. *O Estrangeiro*, *A vegetariana* (lowercase article in the Brazilian edition).
- **Author names**: full name, properly cased.
- **Collection titles**: sentence case. *Livros que ficam no corpo*.
- **Section labels**: uppercase (typography rule, not editorial).
- **The product name**: always *sentido*, lowercase, italic when the typography allows it.
- **Categories of feeling** (angústia, melancolia, esperança, violência, ternura, estranheza): lowercase always.

---

## 3. Microcopy library

These strings are canonical. Reuse them; do not invent variations.

### 3.1 Search

| Slot | Copy |
|---|---|
| Placeholder | `o que você quer sentir?` |
| Empty results | `nenhum livro ressoa com isso ainda` |
| Empty results — subtext | `tente uma frase mais aberta — uma cena, um silêncio, uma sensação no corpo` |
| Loading | `procurando uma ressonância…` |
| Result count (one) | `1 livro encontrado` |
| Result count (many) | `{n} livros encontrados` |

### 3.2 Book page

| Slot | Copy |
|---|---|
| Related section title | `se esse livro ressoou, talvez estes também` |
| Author section title (Phase 2) | `sobre {nome do autor}` |
| Awards section title | `reconhecimentos` |
| Missing synopsis state (visible only in admin) | `sinopse pendente de geração` |

### 3.3 Catalog

| Slot | Copy |
|---|---|
| Home hero label | `um catálogo afetivo de livros` |
| Home hero subtitle | `procure por uma sensação, uma atmosfera, um eco — não por gênero` |
| Browse by emotion entry | `explorar por sentimento` |
| Browse by atmosphere entry | `explorar por atmosfera` |
| Collections entry | `coleções` |

### 3.4 Errors

The product avoids "erro". Frame the rare failure as an absence of result, not a system fault.

| Situation | Copy |
|---|---|
| Network failure on search | `algo ficou em silêncio. tente de novo em um instante.` |
| 404 (book not found) | `esse livro ainda não vive aqui` |
| 500 (server fault) | `o catálogo se recolheu por um momento. volte logo.` |

Never use "Oops", "Algo deu errado", or "Tente novamente" verbatim.

### 3.5 Admin

The admin panel writes more directly because the curator is a working user, not a reader. But it stays in the same register — no exclamation marks, no "Success!" toasts.

| Slot | Copy |
|---|---|
| New book CTA | `adicionar livro por ISBN` |
| Generate profile CTA | `gerar perfil emocional` |
| Approve CTA | `aprovar e publicar` |
| Reject CTA | `descartar geração` |
| Confirmation on publish | `publicado no catálogo` |
| Confirmation on reject | `geração descartada` |

---

## 4. Generated content — instructions for the LLM

The product uses `gpt-4o-mini` to generate two long-form artifacts and one short artifact per book (PRD §5). Each generation must be constrained by a voice prompt that aligns with this file.

### 4.1 Synopsis prompt (canonical)

```
Escreva uma sinopse em português brasileiro do livro "{title}" de
{author}, publicado em {year}.

Diretrizes:
- 4 a 6 frases. Sem títulos, sem listas.
- Voz: sóbria, literária, sem entusiasmo. Não use exclamações.
- Não revele o final. Não diga "este livro é importante".
- Não use clichês como "uma jornada emocionante", "uma obra-prima",
  "um clássico atemporal".
- Foque no que o livro provoca em quem lê — não na trama exata.
- Evite metáforas batidas (espelho da alma, retrato de uma época).
- Comece com uma frase concreta sobre o que acontece no livro,
  depois deslize para a experiência de lê-lo.
- Use pontuação literária (vírgulas, ponto-e-vírgula, travessões).
```

### 4.2 Emotional profile prompt (canonical)

```
Avalie o livro "{title}" de {author} em uma escala de 0 a 10 para
cada uma destas dimensões emocionais. Retorne JSON estrito.

Dimensões:
- anguish (angústia)
- melancholy (melancolia)
- hope (esperança)
- violence (violência)
- tenderness (ternura)
- strangeness (estranheza)

Adicione também:
- atmosphere_tags: 3 a 5 termos curtos em português, lowercase,
  que descrevem a atmosfera de leitura. Exemplos de tom:
  "sol como violência", "silêncio que sufoca", "luz fria",
  "absurdo cotidiano". Não use termos genéricos como "dramático"
  ou "envolvente".
- narrative_pace: um de "slow" | "progressive" | "frenetic".

Sem comentários, sem explicações. Apenas o JSON.
```

### 4.3 Resonance line (per query × book)

```
A pessoa buscou: "{query}".
O livro recomendado é "{title}" de {author}.

Escreva UMA frase em português brasileiro explicando por que esse
livro ressoa com essa busca. Máximo 20 palavras. Use a sensibilidade
de quem entende a busca como uma sensação, não como uma palavra-chave.
Sem exclamações. Não use "porque" — comece direto na imagem.

Exemplo do tom: "Meursault não chora; a recusa de sentir é a sua
forma de existir."
```

These prompts are the **canonical voice gate** for generated content. Any change to them is a brand decision and lands here, not only in the backend plan.

---

## 5. Naming inside the system

The product has a few proper nouns. Use these exact forms in UI copy and in code (when names appear in user-facing strings):

| Concept | UI form (PT-BR) | Code form (English) |
|---|---|---|
| The product | sentido | `sentido` |
| The emotional profile | perfil emocional | `emotional_profile` |
| The atmosphere tags | atmosfera | `atmosphere_tags` |
| The narrative pace | ritmo narrativo | `narrative_pace` |
| The editorial collections | coleções | `collections` |
| The resonance line | linha de ressonância | `resonance_line` |
| A search | busca | `search` |
| The catalog | catálogo | `catalog` |
| The curator role | curador / curadora | `curator` (role string) |

The English forms exist in the codebase per backend conventions; the PT-BR forms are the only ones users see.

---

## 6. Voice anti-patterns

| Do not write | Write instead |
|---|---|
| "Encontre os melhores livros!" | "encontre o livro que ressoa" |
| "Olá! Bem-vindo ao sentido." | (silent — no welcome strings) |
| "Top livros desta semana" | (no popularity surfaces) |
| "Personalizado para você" | (no personalization framing) |
| "Tente novamente mais tarde" | "algo ficou em silêncio. tente de novo em um instante." |
| "Carregando..." | "procurando uma ressonância…" |
| "Sucesso! Livro publicado." | "publicado no catálogo" |
| "Adicionar à minha lista" | (no lists in MVP) |
| "Você pode amar este livro" | "talvez você queira sentir isso" |
| Emoji 📚 ✨ ❤️ anywhere | (none, ever) |

---

## 7. Inclusivity and care

- Default to PT-BR neutral where natural. Use "leitor ou leitora" / "curador ou curadora" only where it actually appears in copy; do not pepper every sentence with both forms.
- Avoid graphic content warnings in metadata (no spoilers, no "trigger warnings" labels). The emotional profile + atmosphere tags do this implicitly — a book with violência 9.0 + atmosphere "violência ritual" tells the reader what they need to know without imposing a content-warning genre.
- Be careful with mental health framing in atmosphere tags and resonance lines. "Solidão" is a feeling; "depressão" is a clinical term and stays out of generated copy unless the book itself names it.

---

## 8. Documentation voice (internal docs)

This file, the PRD, and the implementation plans are **internal documents**. They can be more direct than product copy. But:

- Still no marketing language. No "delight users". No "magic".
- Still no emoji.
- Tables and lists are preferred over long paragraphs for spec content.
- Code samples use the same naming conventions as the codebase they describe.

The brand reference applies to user-facing strings; internal docs follow the **same restraint** but with looser register where clarity demands it.
