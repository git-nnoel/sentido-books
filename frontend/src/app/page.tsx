import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';
import { SearchField } from '@/components/brand/SearchField';

/**
 * Home page.
 *
 * The product is a search-first surface — the hero is the wordmark + the
 * voice §3.3 line, then the search field directly beneath. No catalog grid
 * in v1 (the home is curated and finite per layout §8 — Phase 2 will
 * introduce editorial sections).
 */
export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <section>
            <h1 className="font-display italic text-accent text-display-xl md:text-[4rem] lowercase leading-[1.05] tracking-[-0.02em]">
              sentido
            </h1>
            <p className="mt-5 font-body text-body-lg text-text-muted lowercase max-w-prose">
              procure por uma sensação, uma atmosfera, um eco — não por gênero
            </p>

            <div className="mt-7">
              <SearchField />
            </div>
          </section>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
