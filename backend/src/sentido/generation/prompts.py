"""Voice-locked LLM prompt strings.

These constants mirror ``docs/brand/voice.md §4`` **verbatim** — the
voice file is the brand source of truth for every word the model
emits on Sentido's behalf. Any change here is a brand change and must
be made in ``docs/brand/voice.md`` first, then copied across.

The three constants below are **system messages**. Per-call variables
(``{title}``, ``{author}``, ``{year}``, ``{query}``) are substituted by
the helper functions further down, which return the **user message**
string for each artifact. We deliberately do not use ``f``-strings on
the constants themselves: keeping ``{title}`` etc. as literal template
placeholders means the prompts are inspectable as written in the voice
file, not as an opaque concatenation built at import time.

Source line references in ``docs/brand/voice.md``:

* :data:`SYNOPSIS_SYSTEM_PROMPT` — §4.1, lines 131–146.
* :data:`EMOTIONAL_PROFILE_SYSTEM_PROMPT` — §4.2, lines 150–171.
* :data:`RESONANCE_LINE_SYSTEM_PROMPT` — §4.3, lines 175–186.

B4 uses only the first two. The resonance prompt is defined here so
``search/`` (B5+) can import it without writing a second voice file —
keeping a single seam between brand and code.
"""

from __future__ import annotations

# --- §4.1 ---------------------------------------------------------------
# Copied verbatim from docs/brand/voice.md §4.1 (lines 131–146).
SYNOPSIS_SYSTEM_PROMPT = """\
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
"""

# --- §4.2 ---------------------------------------------------------------
# Copied verbatim from docs/brand/voice.md §4.2 (lines 150–171).
EMOTIONAL_PROFILE_SYSTEM_PROMPT = """\
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
"""

# --- §4.3 ---------------------------------------------------------------
# Copied verbatim from docs/brand/voice.md §4.3 (lines 175–186).
# Defined here so search/ (B5) can import without re-declaring voice.
RESONANCE_LINE_SYSTEM_PROMPT = """\
A pessoa buscou: "{query}".
O livro recomendado é "{title}" de {author}.

Escreva UMA frase em português brasileiro explicando por que esse
livro ressoa com essa busca. Máximo 20 palavras. Use a sensibilidade
de quem entende a busca como uma sensação, não como uma palavra-chave.
Sem exclamações. Não use "porque" — comece direto na imagem.

Exemplo do tom: "Meursault não chora; a recusa de sentir é a sua
forma de existir."
"""


# --- Variable substitution helpers --------------------------------------
#
# The prompts above are templates; the functions below produce the
# final user-facing message string for one call. We use ``str.replace``
# (not ``str.format``) so a stray ``{`` or ``}`` inside the prompt body
# never raises a KeyError — the constants are voice copy, not Python
# format strings.


def synopsis_user_prompt(*, title: str, author: str, year: int | str | None) -> str:
    """Render the §4.1 synopsis prompt with concrete book metadata."""
    year_str = str(year) if year is not None else "ano desconhecido"
    return (
        SYNOPSIS_SYSTEM_PROMPT.replace("{title}", title)
        .replace("{author}", author)
        .replace("{year}", year_str)
    )


def emotional_profile_user_prompt(*, title: str, author: str) -> str:
    """Render the §4.2 emotional-profile prompt with concrete metadata."""
    return EMOTIONAL_PROFILE_SYSTEM_PROMPT.replace("{title}", title).replace(
        "{author}", author
    )


def resonance_line_user_prompt(*, query: str, title: str, author: str) -> str:
    """Render the §4.3 resonance-line prompt with concrete query + book.

    Provided for B5 search; B4 does not call it.
    """
    return (
        RESONANCE_LINE_SYSTEM_PROMPT.replace("{query}", query)
        .replace("{title}", title)
        .replace("{author}", author)
    )
