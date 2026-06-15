import Link from 'next/link';
import { BookCover } from './BookCover';
import { clsx } from '@/lib/clsx';

/**
 * Per brand/components.md §8.
 *
 * A cover plus its caption — the identity of a book inside a carousel or grid.
 * The whole card is the click target; on hover the cover lifts -2px per the
 * brand spec.
 *
 * Server Component — the only interactivity is the wrapping <Link>.
 *
 * The card itself has no container padding (per §8 — "the card is content,
 * not a container"). The caption clamps title to 2 lines and truncates the
 * author to a single line.
 *
 * Sizes:
 *   - md (default) → cover 140×210, used in carousels.
 *   - sm           → cover 64×96, used for inline references in prose.
 */

type BookCardSize = 'md' | 'sm';

type BookCardProps = {
  slug: string;
  title: string;
  author_name: string;
  cover_url: string | null;
  year_published: number | null;
  size?: BookCardSize;
  className?: string;
};

export function BookCard({
  slug,
  title,
  author_name,
  cover_url,
  size = 'md',
  className,
}: BookCardProps) {
  const coverSize = size === 'sm' ? 'sm' : 'md';

  return (
    <Link
      href={`/livro/${slug}`}
      className={clsx(
        'group block rounded-sm transition-transform duration-base ease-standard',
        'hover:-translate-y-0.5',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring',
        className,
      )}
    >
      <BookCover src={cover_url} slug={slug} title={title} size={coverSize} />

      <div className="mt-3">
        <p
          className="font-body text-body-md text-text-primary"
          style={{
            fontWeight: 500,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {title}
        </p>
        <p className="mt-1 truncate font-body italic text-body-sm text-text-muted">
          {author_name}
        </p>
      </div>
    </Link>
  );
}
