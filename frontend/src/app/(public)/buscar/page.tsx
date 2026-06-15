/**
 * Public search results page.
 *
 * Server Component — reads `searchParams.q`, calls semanticSearch via the
 * lib/api/search module, and renders the results as a list of book rows
 * with the per-result resonance_line beside each cover.
 *
 * Behavior contract:
 *   - Empty q: render the search field + a short hint, no query fired.
 *   - Non-empty q: fetch, then either render the result rows or the empty
 *     state copy (voice §3.1).
 *   - ApiError 503: render the inline 503 copy (voice §3.4) in the results
 *     area. The page itself stays up — search is dynamic and the user may
 *     want to try a different phrase.
 *   - Other ApiErrors: rethrown to error.tsx.
 *
 * Loading state is implicit (Server Component suspends while fetching);
 * `loading.tsx` next door renders the brand-voice "procurando uma
 * ressonância…" line.
 */
import type { Metadata } from 'next';
import { ApiError } from '@/lib/api/client';
import { semanticSearch } from '@/lib/api/search';
import type { SearchResult } from '@/lib/api/types';
import { BookCard } from '@/components/brand/BookCard';
import { SearchField } from '@/components/brand/SearchField';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

type PageProps = {
  searchParams: { q?: string | string[] };
};

export const metadata: Metadata = {
  title: 'buscar — sentido',
};

function readQuery(searchParams: PageProps['searchParams']): string {
  const raw = searchParams.q;
  if (Array.isArray(raw)) return raw[0]?.trim() ?? '';
  return raw?.trim() ?? '';
}

export default async function SearchPage({ searchParams }: PageProps) {
  const query = readQuery(searchParams);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="wide" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <SearchField initialValue={query} />

          <div className="mt-7 md:mt-8">
            {query.length === 0 ? <IdleHint /> : <Results query={query} />}
          </div>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sections
// ─────────────────────────────────────────────────────────────────────────────

function IdleHint() {
  return (
    <p className="mx-auto max-w-prose text-center font-body italic text-body-md text-text-muted lowercase">
      procure por uma sensação, uma atmosfera, um eco — não por gênero.
    </p>
  );
}

async function Results({ query }: { query: string }) {
  let results: SearchResult[];
  try {
    const response = await semanticSearch(query, 12);
    results = response.results;
  } catch (err) {
    if (err instanceof ApiError && err.status === 503) {
      return <ServiceUnavailable />;
    }
    throw err;
  }

  if (results.length === 0) {
    return <EmptyState />;
  }

  return (
    <div>
      <p className="font-body text-body-sm text-text-muted lowercase">
        {results.length === 1
          ? '1 livro encontrado'
          : `${results.length} livros encontrados`}
      </p>

      <ul className="mt-6 flex flex-col gap-7 md:gap-8">
        {results.map((result) => (
          <li key={result.slug}>
            <ResultRow result={result} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function ResultRow({ result }: { result: SearchResult }) {
  return (
    <article className="grid grid-cols-1 gap-5 md:grid-cols-[200px_1fr] md:gap-6">
      <div className="mx-auto md:mx-0">
        <BookCard
          slug={result.slug}
          title={result.title}
          author_name={result.author_name}
          cover_url={result.cover_url}
          year_published={result.year_published}
          size="md"
        />
      </div>

      <blockquote className="border-l border-accent pl-4 py-2 font-display italic text-body-lg text-accent">
        {`“${result.resonance_line}”`}
      </blockquote>
    </article>
  );
}

function EmptyState() {
  return (
    <div className="mx-auto max-w-prose text-center">
      <p className="font-display italic text-display-md text-accent lowercase">
        nenhum livro ressoa com isso ainda
      </p>
      <p className="mt-5 font-body text-body-md text-text-muted lowercase">
        tente uma frase mais aberta — uma cena, um silêncio, uma sensação no corpo.
      </p>
    </div>
  );
}

function ServiceUnavailable() {
  return (
    <p className="mx-auto max-w-prose text-center font-body text-body-md text-text-muted lowercase">
      algo ficou em silêncio. tente de novo em um instante.
    </p>
  );
}
