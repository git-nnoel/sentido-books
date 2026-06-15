'use client';

/**
 * Global error boundary. Copy per voice §3.4.
 *
 * Next.js requires `'use client'` for `error.tsx` — the boundary needs to
 * catch render-time errors from descendants and offer a `reset()` retry.
 */
import { Button } from '@/components/brand/Button';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ reset }: ErrorPageProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex flex-1 items-center justify-center">
        <PageColumn width="content" className="py-9">
          <div className="mx-auto max-w-prose text-center">
            <h1 className="font-display italic text-accent text-display-lg lowercase">
              o catálogo se recolheu por um momento. volte logo.
            </h1>
            <div className="mt-8 flex justify-center">
              <Button variant="primary" onClick={reset}>
                tentar de novo
              </Button>
            </div>
          </div>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
