/**
 * Public book detail page — the canonical mockup
 * (docs/assets/book_overview_mobile.jpg).
 *
 * Server Component fetching via lib/api/books.getBookBySlug with 5-min ISR
 * (frontend plan §8.1). 404s from the backend translate to Next's
 * notFound(), which renders app/not-found.tsx with brand-voice copy.
 *
 * Phase 0 ships these sections (per plan §10 deliverables):
 *   - cover hero
 *   - identity block (year · pace label, title, author, atmosphere pills)
 *   - PERFIL EMOCIONAL (six bars)
 *   - SINOPSE
 *
 * The book-peek and related carousels land in Phase 1.
 */
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getBookBySlug } from '@/lib/api/books';
import { ApiError } from '@/lib/api/client';
import type { BookDetail, NarrativePace } from '@/lib/api/types';
import { BookCover } from '@/components/brand/BookCover';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { PillChip } from '@/components/brand/PillChip';
import { EmotionBar } from '@/components/brand/EmotionBar';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

type PageProps = {
  params: { slug: string };
};

// ─────────────────────────────────────────────────────────────────────────────
// PT-BR labels for enums that ship from the backend in English (voice §5).
// ─────────────────────────────────────────────────────────────────────────────

const NARRATIVE_PACE_LABEL: Record<NarrativePace, string> = {
  slow: 'lento',
  progressive: 'progressivo',
  frenetic: 'frenético',
};

const EMOTION_LABELS: Array<{ key: keyof NonNullable<BookDetail['emotional_profile']>; label: string }> = [
  { key: 'anguish', label: 'angústia' },
  { key: 'melancholy', label: 'melancolia' },
  { key: 'hope', label: 'esperança' },
  { key: 'violence', label: 'violência' },
  { key: 'tenderness', label: 'ternura' },
  { key: 'strangeness', label: 'estranheza' },
];

// ─────────────────────────────────────────────────────────────────────────────
// Data fetch helper — wraps the 404 → notFound() translation.
// ─────────────────────────────────────────────────────────────────────────────

async function fetchBookOrNotFound(slug: string): Promise<BookDetail> {
  try {
    return await getBookBySlug(slug);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Metadata — title and og:image per frontend plan §6.3.
// ─────────────────────────────────────────────────────────────────────────────

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const book = await getBookBySlug(params.slug);
    return {
      title: `${book.title} — ${book.author.name}`,
      openGraph: book.cover_url
        ? {
            title: `${book.title} — ${book.author.name}`,
            images: [{ url: book.cover_url }],
          }
        : { title: `${book.title} — ${book.author.name}` },
    };
  } catch {
    return { title: 'livro — sentido' };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default async function BookDetailPage({ params }: PageProps) {
  const book = await fetchBookOrNotFound(params.slug);

  const metadataLabel = buildMetadataLabel(book);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          {/* Hero — mobile stacks, desktop becomes two columns (layout §5.2) */}
          <section className="md:flex md:items-start md:gap-8">
            {/* Mobile cover — centered */}
            <div className="flex justify-center md:hidden">
              <BookCover
                src={book.cover_url}
                slug={book.slug}
                title={book.title}
                size="hero"
                priority
              />
            </div>

            {/* Desktop cover — left column */}
            <div className="hidden shrink-0 md:block">
              <BookCover
                src={book.cover_url}
                slug={book.slug}
                title={book.title}
                size="hero-md"
                priority
              />
            </div>

            {/* Identity block */}
            <div className="mt-7 md:mt-0 md:flex-1">
              {metadataLabel ? <SectionLabel size="sm">{metadataLabel}</SectionLabel> : null}

              <h1 className="mt-3 font-display text-text-primary text-display-lg md:text-[4rem] md:leading-[1.05] tracking-[-0.015em]">
                {book.title}
              </h1>

              <p className="mt-3 font-display italic text-text-muted text-body-lg">
                {/* Author route is Phase 1 — link to a placeholder hash for now. */}
                <Link
                  href="#"
                  aria-disabled="true"
                  className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                >
                  {book.author.name}
                </Link>
              </p>

              {book.atmosphere_tags.length > 0 ? (
                <ul className="mt-5 flex flex-wrap gap-2" aria-label="atmosfera">
                  {book.atmosphere_tags.map((tag) => (
                    <li key={tag}>
                      <PillChip label={tag} />
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </section>

          {book.emotional_profile ? (
            <>
              <HairlineDivider />
              <section aria-labelledby="perfil-emocional-label">
                <SectionLabel>
                  <span id="perfil-emocional-label">PERFIL EMOCIONAL</span>
                </SectionLabel>
                <div className="mt-5 flex flex-col gap-3">
                  {EMOTION_LABELS.map(({ key, label }) => (
                    <EmotionBar
                      key={key}
                      label={label}
                      value={book.emotional_profile![key]}
                    />
                  ))}
                </div>
              </section>
            </>
          ) : null}

          {book.synopsis ? (
            <>
              <HairlineDivider />
              <section aria-labelledby="sinopse-label">
                <SectionLabel>
                  <span id="sinopse-label">SINOPSE</span>
                </SectionLabel>
                <div className="mt-5 max-w-prose font-body text-body-lg text-text-primary">
                  {splitParagraphs(book.synopsis).map((paragraph, idx) => (
                    <p key={idx} className={idx === 0 ? '' : 'mt-4'}>
                      {paragraph}
                    </p>
                  ))}
                </div>
              </section>
            </>
          ) : null}
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function buildMetadataLabel(book: BookDetail): string | null {
  const parts: string[] = [];
  if (book.year_published !== null) parts.push(String(book.year_published));
  if (book.narrative_pace !== null) {
    parts.push(NARRATIVE_PACE_LABEL[book.narrative_pace].toUpperCase());
  }
  return parts.length > 0 ? parts.join(' · ') : null;
}

function splitParagraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}
