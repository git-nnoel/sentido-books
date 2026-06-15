'use client';

/**
 * Admin nav strip (frontend plan §16.3 / §16.6 F11).
 *
 * Co-located with the authenticated admin layout rather than living under
 * components/ — it is admin-chrome, not a reusable brand component (F11 keeps
 * it out of the shared component set). It needs `usePathname()` to compute the
 * active tab, so it must be a Client Component; the layout itself stays a
 * Server Component and renders this island.
 *
 *   livros   → /admin           (active anywhere under /admin EXCEPT /admin/colecoes)
 *   coleções → /admin/colecoes  (active anywhere under /admin/colecoes)
 */
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from '@/lib/clsx';

const LINK_BASE =
  'rounded-sm font-body text-label uppercase tracking-[0.15em] transition-colors duration-fast ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring';

export function AdminNav() {
  const pathname = usePathname() ?? '';
  const onCollections = pathname.startsWith('/admin/colecoes');
  // "livros" owns everything under /admin that isn't the collections subtree.
  const onBooks = pathname.startsWith('/admin') && !onCollections;

  return (
    <nav aria-label="seções do admin" className="flex gap-x-6">
      <Link
        href="/admin"
        aria-current={onBooks ? 'page' : undefined}
        className={clsx(LINK_BASE, onBooks ? 'text-accent' : 'text-text-muted hover:text-text-primary')}
      >
        livros
      </Link>
      <Link
        href="/admin/colecoes"
        aria-current={onCollections ? 'page' : undefined}
        className={clsx(
          LINK_BASE,
          onCollections ? 'text-accent' : 'text-text-muted hover:text-text-primary',
        )}
      >
        coleções
      </Link>
    </nav>
  );
}
