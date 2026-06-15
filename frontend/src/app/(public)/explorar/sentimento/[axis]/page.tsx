/**
 * /explorar/sentimento/[axis] — books browsed by emotion axis (frontend plan
 * §16.4).
 *
 * Server Component. The axis param is validated against the six known emotion
 * axes; an unknown axis renders app/not-found.tsx via notFound(). Results are
 * the first 24 books scoring on that axis (min=0); no pagination UI in MVP
 * (plan §16.5).
 */
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { exploreByEmotion } from '@/lib/api/explore';
import { EMOTION_LABELS, isEmotionAxis } from '@/lib/explore-labels';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';
import { ExploreResults } from '../../_components/ExploreResults';

type PageProps = {
  params: { axis: string };
};

export function generateMetadata({ params }: PageProps): Metadata {
  if (!isEmotionAxis(params.axis)) {
    return { title: 'explorar — sentido' };
  }
  return { title: `${EMOTION_LABELS[params.axis]} — explorar — sentido` };
}

export default async function SentimentoPage({ params }: PageProps) {
  const { axis } = params;
  if (!isEmotionAxis(axis)) {
    notFound();
  }

  const { results } = await exploreByEmotion(axis, 0, 24);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <header>
            <SectionLabel>SENTIMENTO</SectionLabel>
            <h1 className="mt-3 font-display italic text-display-md text-text-primary lowercase">
              {EMOTION_LABELS[axis]}
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
