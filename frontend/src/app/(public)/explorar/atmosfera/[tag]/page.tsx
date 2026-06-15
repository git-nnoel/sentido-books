/**
 * /explorar/atmosfera/[tag] — books browsed by atmosphere tag (frontend plan
 * §16.4).
 *
 * Server Component. `params.tag` arrives URI-decoded from Next.js, so it is
 * used as-is. Tags are free-form (LLM-emitted) — there is no fixed validation
 * set, so an unknown tag simply returns an empty result set rather than a 404.
 * Results are the first 24; no pagination UI in MVP (plan §16.5).
 */
import type { Metadata } from 'next';
import { exploreByTag } from '@/lib/api/explore';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';
import { ExploreResults } from '../../_components/ExploreResults';

type PageProps = {
  params: { tag: string };
};

export function generateMetadata({ params }: PageProps): Metadata {
  return { title: `${params.tag} — explorar — sentido` };
}

export default async function AtmosferaPage({ params }: PageProps) {
  const { tag } = params;

  const { results } = await exploreByTag(tag, 24);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <header>
            <SectionLabel>ATMOSFERA</SectionLabel>
            <h1 className="mt-3 font-display italic text-display-md text-text-primary lowercase">
              {tag}
            </h1>
          </header>

          <HairlineDivider />

          <ExploreResults results={results} />
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
