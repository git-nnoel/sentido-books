import { Wordmark } from '@/components/brand/Wordmark';

/**
 * Per brand/components.md §12 and layout.md §2.2.
 *
 * Minimal — the product does not have a marketing footer. No social links,
 * no newsletter signup, no "Made with ❤️" (voice §6 anti-patterns).
 *
 *   left   → wordmark (footer variant)
 *   center → "um catálogo afetivo de livros" (voice §3.3 home hero label)
 *   right  → three text links separated by ` · ` — sobre · coleções · admin
 *
 * Links are placeholder anchors for Phase 0 (wired to real routes in Phase 1).
 * They're styled inline rather than via the Button "link" variant because
 * Button is a client component and Footer should stay server.
 *
 * Respects the iOS home indicator via env(safe-area-inset-bottom).
 */
export function Footer() {
  return (
    <footer
      className="border-t border-divider"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="mx-auto flex max-w-edge flex-col items-center gap-4 px-5 py-8 text-center md:flex-row md:justify-between md:gap-5 md:text-left">
        <div className="md:flex-1">
          <Wordmark variant="footer" />
        </div>

        <p className="font-body text-body-sm text-text-muted lowercase md:flex-1 md:text-center">
          um catálogo afetivo de livros
        </p>

        <nav
          aria-label="navegação do rodapé"
          className="font-body text-body-sm text-text-muted md:flex-1 md:text-right"
        >
          <FooterLink href="#">sobre</FooterLink>
          <span aria-hidden="true"> · </span>
          <FooterLink href="#">coleções</FooterLink>
          <span aria-hidden="true"> · </span>
          <FooterLink href="#">admin</FooterLink>
        </nav>
      </div>
    </footer>
  );
}

function FooterLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="rounded-sm text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
    >
      {children}
    </a>
  );
}
