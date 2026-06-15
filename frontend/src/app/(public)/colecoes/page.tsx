/**
 * Public collections index — /colecoes.
 *
 * Server Component listing published editorial collections (frontend plan
 * §16.2). Fetches via lib/api/collections.listCollections with 5-min ISR.
 *
 * Layout follows the centered-column page rhythm (layout §1, §2.3):
 *   Header → heading block → divider → collection rows → Footer.
 *
 * Each row is a title link to /colecoes/{slug} plus an optional clamped
 * description, separated by hairline dividers. Empty state uses brand voice.
 */
import type { Metadata } from 'next';
import Link from 'next/link';
import { listCollections } from '@/lib/api/collections';
import type { CollectionSummary } from '@/lib/api/types';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

export const metadata: Metadata = {
  title: 'coleções — sentido',
};

export default async function CollectionsIndexPage() {
  const { collections } = await listCollections();

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <header>
            <h1 className="font-display italic text-display-lg text-accent lowercase">
              coleções
            </h1>
            <p className="mt-3 font-display italic text-body-lg text-text-muted lowercase">
              agrupamentos editoriais. um eco que atravessa vários livros.
            </p>
          </header>

          <HairlineDivider />

          {collections.length === 0 ? (
            <EmptyState />
          ) : (
            <ul className="flex flex-col">
              {collections.map((collection, index) => (
                <li key={collection.slug}>
                  <CollectionRow collection={collection} />
                  {index < collections.length - 1 ? <HairlineDivider /> : null}
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

// ─────────────────────────────────────────────────────────────────────────────
// Rows
// ─────────────────────────────────────────────────────────────────────────────

function CollectionRow({ collection }: { collection: CollectionSummary }) {
  return (
    <article>
      <h2>
        <Link
          href={`/colecoes/${collection.slug}`}
          className="rounded-sm font-display italic text-title-lg text-accent lowercase underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          {collection.title}
        </Link>
      </h2>

      {collection.description ? (
        <p
          className="mt-3 font-body text-body-md text-text-muted lowercase"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {collection.description}
        </p>
      ) : null}
    </article>
  );
}

function EmptyState() {
  return (
    <p className="font-body italic text-body-md text-text-muted lowercase">
      nenhuma coleção publicada ainda
    </p>
  );
}
