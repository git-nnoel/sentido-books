/**
 * /explorar landing — dimension navigation (frontend plan §16.4).
 *
 * Server Component. Three ways into the catalog by experience rather than by
 * genre: por sentimento (the six emotion axes), por atmosfera (the LLM-emitted
 * tag cloud), por ritmo (the three narrative paces).
 *
 * Layout follows the centered-column page rhythm: Header → heading → three
 * sections divided by hairlines → Footer.
 *
 * The atmosphere tag cloud sizes each chip by tertile of its book count
 * (bottom/middle/top third → body-sm/body-md/body-lg) so denser atmospheres
 * read slightly larger. The tag list is fetched with 5-min ISR; the section
 * degrades to a voice-line empty state when nothing has been tagged yet.
 */
import type { Metadata } from 'next';
import Link from 'next/link';
import { listAtmosphereTags } from '@/lib/api/explore';
import type { AtmosphereTagEntry } from '@/lib/api/types';
import {
  EMOTION_AXES,
  EMOTION_LABELS,
  NARRATIVE_PACES,
  PACE_LABELS,
} from '@/lib/explore-labels';
import { PillChip } from '@/components/brand/PillChip';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

export const metadata: Metadata = {
  title: 'explorar — sentido',
};

const DIMENSION_LINK_CLASSES =
  'rounded-sm font-display italic text-title-md text-text-primary lowercase underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring';

export default async function ExplorePage() {
  const { tags } = await listAtmosphereTags();

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="content" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <h1 className="font-display italic text-display-lg text-accent lowercase">
            explorar
          </h1>

          <HairlineDivider />

          <SentimentoSection />

          <HairlineDivider />

          <AtmosferaSection tags={tags} />

          <HairlineDivider />

          <RitmoSection />
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 1 — por sentimento
// ─────────────────────────────────────────────────────────────────────────────

function SentimentoSection() {
  return (
    <section>
      <SectionLabel>POR SENTIMENTO</SectionLabel>
      <div className="mt-4 flex flex-wrap gap-4">
        {EMOTION_AXES.map((axis) => (
          <Link
            key={axis}
            href={`/explorar/sentimento/${axis}`}
            className={DIMENSION_LINK_CLASSES}
          >
            {EMOTION_LABELS[axis]}
          </Link>
        ))}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 2 — por atmosfera (tag cloud)
// ─────────────────────────────────────────────────────────────────────────────

function AtmosferaSection({ tags }: { tags: AtmosphereTagEntry[] }) {
  return (
    <section>
      <SectionLabel>POR ATMOSFERA</SectionLabel>
      <div className="mt-4">
        {tags.length === 0 ? (
          <p className="font-body italic text-body-md text-text-muted lowercase">
            nenhuma atmosfera encontrada ainda
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Link
                key={tag.name}
                href={`/explorar/atmosfera/${encodeURIComponent(tag.name)}`}
                className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
              >
                <PillChip
                  label={tag.name}
                  variant="filter"
                  className={tagSizeClass(tag.count, tags)}
                />
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

/**
 * Size a tag chip by tertile of the count distribution: bottom third → body-sm,
 * middle third → body-md, top third → body-lg. Thresholds are derived from the
 * min/max span so a flat distribution (all counts equal) lands every chip in
 * the middle band rather than collapsing to the smallest.
 */
function tagSizeClass(count: number, tags: AtmosphereTagEntry[]): string {
  const counts = tags.map((t) => t.count);
  const min = Math.min(...counts);
  const max = Math.max(...counts);

  if (max === min) return 'text-body-md';

  const span = max - min;
  const position = (count - min) / span; // 0..1

  if (position < 1 / 3) return 'text-body-sm';
  if (position < 2 / 3) return 'text-body-md';
  return 'text-body-lg';
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 3 — por ritmo
// ─────────────────────────────────────────────────────────────────────────────

function RitmoSection() {
  return (
    <section>
      <SectionLabel>POR RITMO</SectionLabel>
      <div className="mt-4 flex flex-wrap gap-4">
        {NARRATIVE_PACES.map((pace) => (
          <Link
            key={pace}
            href={`/explorar/ritmo/${pace}`}
            className={DIMENSION_LINK_CLASSES}
          >
            {PACE_LABELS[pace]}
          </Link>
        ))}
      </div>
    </section>
  );
}
