/**
 * Shared results grid for the three /explorar dimension pages (sentimento,
 * atmosfera, ritmo). Renders ExploreResults as a responsive BookCard grid —
 * a card grid rather than the search page's resonance-line rows, because
 * explore results carry no per-result line.
 *
 * Server Component — no interactivity beyond each BookCard's own <Link>.
 */
import type { ExploreResult } from '@/lib/api/types';
import { BookCard } from '@/components/brand/BookCard';

export function ExploreResults({ results }: { results: ExploreResult[] }) {
  if (results.length === 0) {
    return (
      <p className="font-body italic text-body-md text-text-muted lowercase">
        nenhum livro encontrado para esta dimensão
      </p>
    );
  }

  return (
    <ul className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4">
      {results.map((result) => (
        <li key={result.slug}>
          <BookCard
            slug={result.slug}
            title={result.title}
            author_name={result.author_name}
            cover_url={result.cover_url}
            year_published={result.year_published}
          />
        </li>
      ))}
    </ul>
  );
}
