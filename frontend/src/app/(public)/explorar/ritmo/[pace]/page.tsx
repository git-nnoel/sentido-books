/**
 * /explorar/ritmo/[pace] — books browsed by narrative pace (frontend plan
 * §16.4).
 *
 * Server Component. The pace param is validated against the three known paces;
 * an unknown pace renders app/not-found.tsx via notFound(). Results are the
 * first 24; no pagination UI in MVP (plan §16.5).
 */
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { exploreByPace } from '@/lib/api/explore';
import { PACE_LABELS, isNarrativePace } from '@/lib/explore-labels';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';
import { ExploreResults } from '../../_components/ExploreResults';

type PageProps = {
  params: { pace: string };
};

export function generateMetadata({ params }: PageProps): Metadata {
  if (!isNarrativePace(params.pace)) {
    return { title: 'explorar — sentido' };
  }
  return { title: `${PACE_LABELS[params.pace]} — explorar — sentido` };
}

export default async function RitmoPage({ params }: PageProps) {
  const { pace } = params;
  if (!isNarrativePace(pace)) {
    notFound();
  }

  const { results } = await exploreByPace(pace, 24);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <header>
            <SectionLabel>RITMO</SectionLabel>
            <h1 className="mt-3 font-display italic text-display-md text-text-primary lowercase">
              {PACE_LABELS[pace]}
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
