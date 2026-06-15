/**
 * Per brand/layout.md §7 — the "se esse livro ressoou…" pattern at the
 * bottom of the canonical book page.
 *
 * Native CSS scroll-snap track. No carousel library. No chevrons in MVP —
 * touch swipe is enough on mobile and horizontal scroll suffices on desktop;
 * the chevrons described in brand/components.md §11 land in Phase 2 alongside
 * the book-peek carousel.
 *
 * Item widths come from §7 itself: 140px mobile, 160px desktop. The track
 * uses snap-x proximity (not mandatory) so the user can scrub freely.
 *
 * Edge fade is rendered with mask-image (linear-gradient) so the leading
 * and trailing covers fade into the canvas — the affordance that "there is
 * more" without a hard cropping edge.
 *
 * Server Component — accepts pre-fetched items.
 */
import type { ReactNode } from 'react';
import { BookCard } from '@/components/brand/BookCard';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { clsx } from '@/lib/clsx';

type RelatedCarouselItem = {
  slug: string;
  title: string;
  author_name: string;
  cover_url: string | null;
  year_published: number | null;
};

type RelatedCarouselProps = {
  items: RelatedCarouselItem[];
  label?: string;
  className?: string;
};

const EDGE_FADE_MASK =
  'linear-gradient(to right, transparent 0, #000 32px, #000 calc(100% - 32px), transparent 100%)';

export function RelatedCarousel({ items, label, className }: RelatedCarouselProps) {
  if (items.length === 0) return null;

  const carousel = (
    <div className={clsx('w-full', label ? 'mt-5' : '', className)}>
      <ul
        // snap-x proximity + horizontal overflow + edge fade.
        // The mask-image creates the soft fade on left and right edges.
        className={clsx(
          'flex snap-x snap-proximity gap-4 overflow-x-auto pb-2',
          // Hide native scrollbar (subtle is the brand's whole register).
          '[scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden',
        )}
        style={{
          WebkitMaskImage: EDGE_FADE_MASK,
          maskImage: EDGE_FADE_MASK,
        }}
      >
        {items.map((item) => (
          <li
            key={item.slug}
            className="w-[140px] shrink-0 snap-start md:w-[160px]"
          >
            <BookCard
              slug={item.slug}
              title={item.title}
              author_name={item.author_name}
              cover_url={item.cover_url}
              year_published={item.year_published}
              size="md"
            />
          </li>
        ))}
      </ul>
    </div>
  );

  if (!label) return carousel;

  return (
    <SectionedWrapper label={label}>{carousel}</SectionedWrapper>
  );
}

function SectionedWrapper({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section aria-label={label}>
      <SectionLabel>{label}</SectionLabel>
      {children}
    </section>
  );
}
