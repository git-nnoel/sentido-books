# product.md — Sentido
### Catálogo semântico de livros por sentimento, atmosfera e ressonância

> Versão 1.2 — junho 2026

---

## 1. Visão

A maioria dos sistemas de busca de livros opera por gênero, autor e título — categorias que descrevem *o que* um livro é, não *o que ele faz* com quem lê.

**Sentido** é um catálogo de busca semântica que entende livros como experiências emocionais. Um usuário pode buscar por "solidão que não dói", "fim do mundo sem esperança", "silêncio que sufoca" — e o sistema retorna os livros que mais se aproximam dessa experiência, independente de gênero ou popularidade.

A busca acontece no espaço dos embeddings: cada livro é representado como um vetor multidimensional que captura tom, sentimento, temas, atmosfera e ressonância emocional. Buscas por termos abstratos encontram correlações que nenhum sistema de tags conseguiria prever.

---

## 2. Problema

**O que existe hoje:**
- Skoob e Goodreads organizam por gênero, nota e popularidade
- A recomendação é baseada em "quem leu X também leu Y" — colaborativa, não semântica
- Letterboxd faz isso melhor para cinema, mas nenhum produto equivalente existe para literatura
- Motores de busca como Google retornam resultados editoriais, não experienciais

**O que falta:**
- Busca por *sensação* de leitura, não por metadados
- Descoberta de livros a partir de linguagem natural e imprecisa
- Uma página de livro que trate o livro como objeto cultural completo — não só ficha técnica

---

## 3. Usuário-alvo

Leitores que já sabem que gênero é uma categoria insuficiente. Que buscam um livro porque precisam de algo específico que não conseguem nomear exatamente. Que conhecem Letterboxd e sentem falta de algo assim para livros.

**Perfil primário:** leitores frequentes, 20–40 anos, com repertório eclético, que usam redes como Skoob ou Goodreads mas se frustram com a superficialidade das recomendações.

---

## 4. Funcionalidades principais

### 4.1 Busca semântica por embeddings

A funcionalidade central do produto.

- Campo de busca livre: o usuário digita qualquer coisa — uma frase, uma emoção, uma cena imaginada, um trecho de memória
- A query é convertida em embedding via OpenAI em tempo real
- O sistema retorna os N livros com maior similaridade de cosseno no espaço vetorial
- Resultado exibe: capa, título, autor, e uma frase gerada por IA explicando por que esse livro ressoa com a busca

**Exemplos de queries que o sistema deve responder bem:**
- "angústia que fica no corpo depois que você fecha o livro"
- "fim do mundo sem esperança mas sem drama"
- "solidão voluntária, não patológica"
- "personagem que desmorona devagar, sem que ninguém perceba"
- "silêncio como forma de violência"

### 4.2 Página individual do livro

Cada livro tem uma página dedicada com:

**Bloco de identidade**
- Capa em alta resolução
- Título, autor, ano de publicação original
- Editoras disponíveis (todas as edições mapeadas)
- Idiomas disponíveis
- ISBN

**Bloco semântico** *(diferencial do produto)*
- Escala de sentimentos: angústia, melancolia, esperança, violência, ternura, estranheza (0–10, gerado via IA)
- Atmosfera predominante: termos abstratos que descrevem a experiência de leitura
- Ritmo narrativo: lento / progressivo / frenético
- Densidade emocional
- Comparações: "Se você sentiu X em [Livro A], vai sentir Y aqui"

**Bloco informacional**
- Sinopse própria em PT-BR (não a editorial)
- Sobre a autora/autor: biografia relevante para entender o livro, não currículo
- Prêmios e reconhecimentos
- Como o livro foi recebido no mundo: resenhas notáveis, citações, impacto cultural

**Bloco de descoberta**
- Livros relacionados por similaridade semântica (não por gênero)
- Livros da mesma autora
- Livros que leitores costumam ler em sequência

### 4.3 Exploração por dimensão emocional

Além da busca livre, o usuário pode navegar por eixos pré-definidos:

- Escalas de sentimento (angústia, melancolia, esperança...)
- Atmosferas: silêncio, violência, colapso, reconstrução, estranheza
- Ritmo: livros para ler devagar / livros que não se larga

### 4.4 Coleções editoriais

Listas curadas manualmente agrupando livros por experiência:

- "Livros que ficam no corpo"
- "Leitura para quando você precisa sentir que não está sozinho na sua estranheza"
- "Finais que não resolvem nada — e por isso são perfeitos"

### 4.5 Admin panel de curadoria

Acessível via rota protegida dentro do próprio frontend Next.js (`/admin`). Funcionalidades do MVP:

- Adicionar livro por ISBN (busca automática na Open Library + Google Books)
- Revisar e editar perfil emocional gerado por IA antes de publicar
- Aprovar ou rejeitar sinopse gerada
- Gerenciar status de publicação de cada livro
- Visualizar fila de livros com perfil pendente de geração

---

## 5. Modelo de consumo de LLM e embeddings

### 5.1 Estratégia: geração lazy com cache permanente

O sistema **não pré-processa livros em lote** na instalação, nem gera conteúdo em tempo real sem persistência. O modelo é **lazy com cache permanente**:

```
Livro entra no catálogo via admin panel
  └── Apenas metadados bibliográficos são armazenados
      └── Nenhum embedding ou perfil emocional gerado ainda

Curador aciona geração pelo admin panel (ou usuário acessa pela primeira vez)
  ├── Sistema verifica: embedding existe? perfil emocional existe?
  ├── NÃO → gera agora via OpenAI, armazena no banco, nunca gera de novo
  └── SIM → serve direto do banco, sem custo de LLM

Usuário faz uma busca semântica
  ├── Query → embedding gerado em tempo real (rápido, ~50ms)
  └── Busca por similaridade no pgvector → serve resultados em < 500ms
```

**Livros sem embedding** não aparecem nos resultados de busca semântica até que o perfil seja gerado e aprovado pelo curador.

### 5.2 O que é gerado em cada momento

| Momento | O que é gerado | Modelo | Cache |
|---|---|---|---|
| Usuário faz uma busca | Embedding da query | `text-embedding-3-small` | Não — queries são únicas |
| Curador aciona geração | Sinopse própria em PT-BR | `gpt-4o-mini` | Sim, permanente |
| Curador aciona geração | Perfil emocional (JSON estruturado) | `gpt-4o-mini` | Sim, permanente |
| Curador aciona geração | Embedding do livro | `text-embedding-3-small` | Sim, permanente |
| Página do livro, primeiro acesso | Frase de "motivo de ressonância" para a busca | `gpt-4o-mini` | Sim, por query+livro |

### 5.3 Estimativa de custo

Para um catálogo inicial de 500 livros, com geração acionada pelo curador:

| Item | Volume | Custo estimado |
|---|---|---|
| Embeddings de 500 livros | ~500k tokens | ~$0.01 |
| Perfis emocionais + sinopses (gpt-4o-mini) | ~2M tokens | ~$0.30 input + $1.20 output |
| Embeddings de busca (uso contínuo) | variável | ~$0.001 / 1.000 buscas |

> Custo total de geração do catálogo inicial: **menos de $5**. O custo dominante é operacional (busca em tempo real), que é marginal por volume.

---

## 6. APIs e fontes de dados

Nenhum scraping. Todas as fontes são APIs com documentação pública.

### 6.1 APIs gratuitas

| API | Uso | Limite | Auth |
|---|---|---|---|
| **Open Library API** | Metadados: título, autor, ISBN, editoras, datas | Sem limite documentado; uso razoável | Sem chave |
| **Open Library Covers API** | Capas de livros por ISBN ou OLID | Sem limite documentado | Sem chave |
| **Wikipedia REST API** | Biografia de autores, contexto cultural, prêmios | 200 req/s | Sem chave (User-Agent obrigatório) |
| **Wikidata API** | Dados estruturados: nascimento, nacionalidade, prêmios | Sem limite documentado | Sem chave |
| **Google Books API** (tier gratuito) | Metadados complementares, sinopses editoriais, capas | 1.000 req/dia | Chave gratuita |

### 6.2 APIs pagas

| API | Uso | Preço | Estimativa MVP |
|---|---|---|---|
| **OpenAI `text-embedding-3-small`** | Embeddings de livros e queries | $0.02 / 1M tokens | < $1 para 500 livros |
| **OpenAI `gpt-4o-mini`** | Sinopses PT-BR, perfis emocionais, frases de ressonância | $0.15 input / $0.60 output por 1M tokens | ~$2–5 para 500 livros |

### 6.3 Estratégia de fallback entre APIs

```
Busca de metadados:
  1. Open Library (primária)
  2. Google Books (fallback para dados ausentes ou livros recentes)
  3. Campos ausentes → marcados como pending, preenchidos manualmente via admin

Busca de capa:
  1. Open Library Covers por ISBN
  2. Google Books thumbnail
  3. Placeholder visual do produto

Biografia do autor:
  1. Wikipedia REST API (extrato da página)
  2. Wikidata (dados estruturados complementares)
  3. Campo vazio → gerado por LLM com instrução de ser conservador e factual
```

### 6.4 Idioma

- Sinopses geradas e perfis exibidos sempre em **PT-BR**
- O texto de entrada para geração de embeddings é composto em **inglês** internamente (melhor desempenho no `text-embedding-3-small`)
- Catálogo cobre obras em qualquer idioma; a experiência do usuário é inteiramente em PT-BR

---

## 7. Arquitetura técnica

### 7.1 Stack

| Camada | Tecnologia | Decisão |
|---|---|---|
| Frontend + Admin | Next.js 14 (App Router) | SSR para SEO; admin em rota protegida `/admin` |
| Estilo | Tailwind CSS | Design system consistente |
| Backend | Python + FastAPI | Semântica clara, manutenção simples, ecossistema robusto para IA |
| Banco de dados | PostgreSQL + pgvector | Self-hosted no VPS; relacional + vetorial sem dependência externa |
| LLM e Embeddings | OpenAI API (`gpt-4o-mini` + `text-embedding-3-small`) | SDK única para geração e embeddings |
| Orquestração | Docker + Docker Compose | Todos os serviços no mesmo VPS |
| Reverse proxy | Caddy | HTTPS automático via Let's Encrypt; configuração mínima |
| Frontend deploy | Vercel | Next.js nativo; separado do VPS |
| Dados bibliográficos | Open Library API + Google Books API | Sem scraping; APIs públicas documentadas |

### 7.2 Serviços no VPS (Docker Compose)

```
VPS
└── docker-compose.yml
    ├── db          → PostgreSQL 16 + pgvector
    │   └── porta 5432 (interna)
    ├── api         → FastAPI (Python)
    │   └── porta 8000 (interna)
    └── caddy       → reverse proxy + HTTPS
        ├── api.sentido.app → http://api:8000
        └── porta 443 (externa)

Vercel (separado)
└── Next.js 14
    └── consome api.sentido.app via HTTP
```

### 7.3 Arquitetura de serviços

```
┌─────────────────────────────────────────────┐
│           Frontend (Vercel)                 │
│           Next.js 14                        │
│                                             │
│  /               → catálogo + busca         │
│  /livro/[slug]   → página do livro          │
│  /autor/[slug]   → página do autor          │
│  /admin          → painel de curadoria      │
└──────────────────┬──────────────────────────┘
                   │ HTTPS
┌──────────────────▼──────────────────────────┐
│           Caddy (reverse proxy)             │
│           api.dominio.app                   │
└──────────────────┬──────────────────────────┘
                   │ HTTP interno
┌──────────────────▼──────────────────────────┐
│           FastAPI (Python)                  │
│                                             │
│  POST /search        → busca semântica      │
│  GET  /books/{slug}  → detalhes + lazy gen  │
│  GET  /authors/{slug}                       │
│  POST /admin/books   → ingestão             │
│  POST /admin/books/{id}/generate → gera IA  │
│  PUT  /admin/books/{id}  → edição           │
└──────────┬──────────────────────────────────┘
           │                   │
┌──────────▼──────┐   ┌────────▼───────────────┐
│   PostgreSQL    │   │     OpenAI API          │
│   + pgvector    │   │                         │
│                 │   │  text-embedding-3-small  │
│  metadados      │   │  gpt-4o-mini            │
│  embeddings     │   └─────────────────────────┘
│  perfis         │
└─────────────────┘        ┌──────────────────────┐
                           │   APIs externas       │
                           │  Open Library         │
                           │  Google Books         │
                           │  Wikipedia/Wikidata   │
                           └──────────────────────┘
```

### 7.4 Modelo de dados (PostgreSQL)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Autores
CREATE TABLE authors (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         TEXT NOT NULL,
  slug         TEXT UNIQUE NOT NULL,
  bio          TEXT,               -- gerado por LLM em PT-BR
  nationality  TEXT,
  born         DATE,
  awards       JSONB DEFAULT '[]',
  ol_id        TEXT,               -- Open Library ID
  wiki_url     TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- Livros
CREATE TABLE books (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug               TEXT UNIQUE NOT NULL,
  title              TEXT NOT NULL,
  original_title     TEXT,
  author_id          UUID REFERENCES authors(id),
  year_published     INT,
  synopsis           TEXT,          -- gerado por LLM em PT-BR
  emotional_profile  JSONB,         -- {"anguish": 8.5, "melancholy": 7, ...}
  atmosphere_tags    TEXT[],        -- ["visceral", "dissociativo", "sem catarse"]
  narrative_pace     TEXT,          -- "slow" | "progressive" | "frenetic"
  cover_url          TEXT,
  ol_id              TEXT,          -- Open Library ID
  embedding          vector(1536),  -- gerado por OpenAI (texto em inglês)
  embedding_status   TEXT DEFAULT 'pending',  -- pending | done
  profile_status     TEXT DEFAULT 'pending',  -- pending | approved | rejected
  published          BOOLEAN DEFAULT false,
  created_at         TIMESTAMPTZ DEFAULT now(),
  updated_at         TIMESTAMPTZ DEFAULT now()
);

-- Índice vetorial para busca semântica
CREATE INDEX ON books USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Edições
CREATE TABLE editions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id    UUID REFERENCES books(id),
  publisher  TEXT,
  language   TEXT,
  year       INT,
  isbn       TEXT,
  cover_url  TEXT
);

-- Coleções editoriais
CREATE TABLE collections (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  slug        TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE collection_books (
  collection_id UUID REFERENCES collections(id),
  book_id       UUID REFERENCES books(id),
  position      INT,
  PRIMARY KEY (collection_id, book_id)
);
```

---

## 8. Identidade visual

O produto se posiciona no mesmo espaço estético do **Letterboxd**: escuro, cinematográfico, com tipografia forte e tratamento visual que eleva o livro a objeto de culto — não de consumo.

**Princípios:**
- Fundo escuro como padrão (não como "modo dark", como escolha estética primária)
- Capas de livros como elemento visual dominante, tratadas como pôsteres
- Tipografia com personalidade — não genérica
- Escassez de cor: uma cor de acento, usada com contenção
- Sem gamificação visual (sem badges, streaks, rankings de popularidade)

**Referências visuais:**
- Letterboxd — estrutura de catálogo, tratamento de capa
- Are.na — densidade intelectual, sobriedade
- Typewolf — cuidado tipográfico

---

## 9. Fases de desenvolvimento

### Fase 0 — Fundação *(1–2 semanas)*
- Setup do VPS: Docker Compose com PostgreSQL + pgvector + FastAPI + Caddy
- Schema do banco de dados e migrations
- Integração Open Library API
- Rota `/admin` básica no Next.js com autenticação simples (token fixo no MVP)
- Ingestão manual dos primeiros 50 livros via admin panel

### Fase 1 — MVP público *(3–4 semanas)*
- Busca semântica funcional (embedding de query → pgvector)
- Página de livro com perfil emocional aprovado pelo curador
- Admin panel com fluxo completo: ingerir → gerar → revisar → publicar
- Catálogo inicial: 200–500 livros
- Deploy frontend no Vercel

### Fase 2 — Enriquecimento *(4–6 semanas)*
- Integração Google Books + Wikipedia/Wikidata
- Exploração por dimensão emocional (filtros navegáveis)
- Páginas de autor
- Coleções editoriais

### Fase 3 — Descoberta *(ongoing)*
- Busca por filtros combinados (ex: angústia > 8 + ritmo lento)
- Integração com o projeto *páginas* (importar histórico de leitura)
- API pública para o catálogo

---

## 10. Questões em aberto

| Questão | Opções | Status |
|---|---|---|
| Nome definitivo do produto | — | Em aberto; "Sentido" é provisório |
| Reverse proxy | Caddy (recomendado) vs. Nginx | Decidir antes da Fase 0 |
| Regeneração de perfis | Manual via admin vs. automática com feedback | Manual no MVP |
| Moderação do conteúdo gerado | Revisão obrigatória vs. publicação automática | Revisão obrigatória no MVP |
| Monetização | Freemium / API / parcerias editoriais | Não definir antes da Fase 2 |
| Autenticação de usuários | Sem auth (MVP) → social login na Fase 3 | MVP sem auth confirmado |

---

## 11. Métricas de sucesso

**MVP:**
- Qualidade semântica: queries abstratas retornam resultados coerentes (avaliação qualitativa por leitores)
- Cobertura: 200+ livros publicados com perfil emocional aprovado
- Performance: busca semântica responde em < 500ms

**Produto:**
- Tempo médio na página de livro > 2 minutos
- Taxa de clique em "livros relacionados" > 20%
- Queries sem resultados relevantes < 10%

---

*Versão 1.2 — junho 2026*
