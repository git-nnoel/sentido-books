import Link from 'next/link';
import { Wordmark } from '@/components/brand/Wordmark';

/**
 * Per brand/layout.md §4.
 *
 * Sticky top, 64px tall, translucent canvas background with backdrop blur,
 * hairline bottom border. The wordmark always routes to home.
 *
 * Mobile  → 3-col grid: [back slot] [wordmark centered] [actions slot]
 * Desktop → flex:        [wordmark left] [nav center-left] [actions right]
 *
 * The desktop nav links are placeholders for Phase 1 — they render disabled
 * with aria-disabled="true" so the visual rhythm is complete without claiming
 * they're functional.
 *
 * Respects the iOS notch via env(safe-area-inset-top).
 */
export function Header() {
  return (
    <header
      className="sticky top-0 z-40 border-b border-divider bg-overlay backdrop-blur-md"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      {/* Mobile layout — 3-col grid with centered wordmark */}
      <div className="grid h-16 grid-cols-[1fr_auto_1fr] items-center px-5 md:hidden">
        <div aria-hidden="true" />
        <Link
          href="/"
          aria-label="sentido — página inicial"
          className="justify-self-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          <Wordmark variant="header" />
        </Link>
        <div aria-hidden="true" />
      </div>

      {/* Desktop layout — flex with wordmark left, nav center-left, actions right */}
      <div className="hidden h-16 items-center px-7 md:flex lg:px-8">
        <Link
          href="/"
          aria-label="sentido — página inicial"
          className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          <Wordmark variant="header" />
        </Link>

        <nav aria-label="navegação principal" className="ml-8 flex items-center gap-5">
          <PlaceholderNavLink>catálogo</PlaceholderNavLink>
          <PlaceholderNavLink>coleções</PlaceholderNavLink>
          <PlaceholderNavLink>buscar</PlaceholderNavLink>
        </nav>

        <div className="ml-auto" />
      </div>
    </header>
  );
}

/**
 * Phase-0 placeholder link — renders as text-muted, not interactive yet.
 * Wired up to real routes in Phase 1.
 */
function PlaceholderNavLink({ children }: { children: React.ReactNode }) {
  return (
    <span
      aria-disabled="true"
      className="font-body text-body-sm text-text-muted cursor-not-allowed lowercase"
    >
      {children}
    </span>
  );
}
