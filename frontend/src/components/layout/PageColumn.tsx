import type { ReactNode } from 'react';
import { clsx } from '@/lib/clsx';

type PageColumnWidth = 'prose' | 'content' | 'wide' | 'edge';

type PageColumnProps = {
  width?: PageColumnWidth;
  className?: string;
  children: ReactNode;
};

/**
 * Centered column primitive, per brand/layout.md §2.1–§2.3.
 *
 * Page horizontal padding scales by breakpoint per §2.2:
 *   mobile  → 24px (px-5)
 *   tablet  → 48px (md:px-7)
 *   desktop → 64px (lg:px-8)
 *
 * Default width is `content` — used by book/author/search/collection pages.
 * Catalog grids use `wide`. The admin panel uses `edge`. Long-form prose
 * (synopsis) narrows to `prose`.
 */
export function PageColumn({ width = 'content', className, children }: PageColumnProps) {
  const widthClass = {
    prose: 'max-w-prose',
    content: 'max-w-content',
    wide: 'max-w-wide',
    edge: 'max-w-edge',
  }[width];

  return (
    <div className={clsx('mx-auto w-full px-5 md:px-7 lg:px-8', widthClass, className)}>
      {children}
    </div>
  );
}
