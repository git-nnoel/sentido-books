/**
 * Public collection detail — /colecoes/{slug}.
 *
 * Server Component fetching via lib/api/collections.getCollectionBySlug with
 * 5-min ISR (frontend plan §16.2). 404s from the backend translate to Next's
 * notFound(), which renders app/not-found.tsx with brand-voice copy.
 *
 * A collection reads as an editorial reading list (decision §16.2): books are
 * a vertical stack of BookCards on mobile, a 2-column grid from `md` up — not
 * a horizontal carousel.
 */
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getCollectionBySlug } from '@/lib/api/collections';
import { ApiError } from '@/lib/api/client';
import type { CollectionDetail } from '@/lib/api/types';
import { BookCard } from '@/components/brand/BookCard';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

type PageProps = {
  params: { slug: string };
};

// ─────────────────────────────────────────────────────────────────────────────
// Data fetch helper — wraps the 404 → notFound() translation.
// ─────────────────────────────────────────────────────────────────────────────

async function fetchCollectionOrNotFound(slug: string): Promise<CollectionDetail> {
  try {
    return await getCollectionBySlug(slug);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Metadata — title mirrors the collection (frontend plan §16.2).
// ─────────────────────────────────────────────────────────────────────────────

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const collection = await getCollectionBySlug(params.slug);
    return { title: `${collection.title} — sentido` };
  } catch {
    return { title: 'coleção — sentido' };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default async function CollectionDetailPage({ params }: PageProps) {
  const collection = await fetchCollectionOrNotFound(params.slug);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <header>
            <SectionLabel>COLEÇÃO</SectionLabel>
            <h1 className="mt-3 font-display italic text-display-lg text-text-primary lowercase">
              {collection.title}
            </h1>
            {collection.description ? (
              <p className="mt-3 max-w-prose font-body text-body-lg text-text-muted lowercase">
                {collection.description}
              </p>
            ) : null}
          </header>

          <HairlineDivider />

          {collection.books.length === 0 ? (
            <p className="font-body italic text-body-md text-text-muted lowercase">
              nenhum livro nesta coleção ainda
            </p>
          ) : (
            <ul className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {collection.books.map((book) => (
                <li key={book.slug}>
                  <BookCard
                    slug={book.slug}
                    title={book.title}
                    author_name={book.author_name}
                    cover_url={book.cover_url}
                    year_published={book.year_published}
                  />
                </li>
              ))}
            </ul>
          )}
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
