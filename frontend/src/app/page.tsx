import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { SectionLabel } from '@/components/brand/SectionLabel';

/**
 * Phase 0 home shell.
 *
 * No search input yet — that lands in F3 with the API client.
 * No catalog grid yet — that lands in Phase 1 with real backend data.
 *
 * The hero uses voice §3.3 copy verbatim.
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
          </section>

          <HairlineDivider />

          <section>
            <SectionLabel>EM BREVE</SectionLabel>
            <p className="mt-5 font-body text-body-md text-text-primary lowercase">
              o catálogo está sendo semeado
            </p>
          </section>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
