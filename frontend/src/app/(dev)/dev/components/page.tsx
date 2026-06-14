import { notFound } from 'next/navigation';
import { Wordmark } from '@/components/brand/Wordmark';
import { BookCover } from '@/components/brand/BookCover';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { Button } from '@/components/brand/Button';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

export const metadata = {
  title: 'componentes — dev',
  robots: { index: false, follow: false },
};

/**
 * Dev-only showcase of every Phase-0 brand and layout component.
 *
 * Gated to non-production: in `NODE_ENV === 'production'` this returns 404
 * so it never appears in a deployed build.
 */
export default function DevComponentsPage() {
  if (process.env.NODE_ENV === 'production') {
    notFound();
  }

  // Stand-in cover URL — picsum returns a 2:3 image, exercising the letterbox path
  // is the responsibility of the BookCover's `object-contain`. For "no cover" we
  // pass src={null} to render the embossed-letter fallback.
  const sampleCoverUrl = 'https://picsum.photos/seed/sentido-md/400/600';

  return (
    <PageColumn width="wide" className="py-9">
      <h1 className="font-display italic text-accent text-display-lg lowercase">
        componentes — sentido
      </h1>
      <p className="mt-3 font-body text-body-md text-text-muted lowercase max-w-prose">
        catálogo visual dos componentes da fase 0. esta rota não existe em produção.
      </p>

      <HairlineDivider />

      {/* Wordmark */}
      <section className="mt-7">
        <SectionLabel>WORDMARK</SectionLabel>
        <div className="mt-5 space-y-6">
          <ShowcaseRow label="variant=header (default)">
            <Wordmark variant="header" />
          </ShowcaseRow>
          <ShowcaseRow label="variant=footer">
            <Wordmark variant="footer" />
          </ShowcaseRow>
        </div>
      </section>

      <HairlineDivider />

      {/* BookCover */}
      <section className="mt-7">
        <SectionLabel>BOOKCOVER — COM IMAGEM</SectionLabel>
        <div className="mt-5 flex flex-wrap items-end gap-6">
          <CoverSample size="sm" src={sampleCoverUrl} />
          <CoverSample size="md" src={sampleCoverUrl} />
          <CoverSample size="lg" src={sampleCoverUrl} />
          <CoverSample size="xl" src={sampleCoverUrl} />
          <CoverSample size="hero" src={sampleCoverUrl} />
          <CoverSample size="hero-md" src={sampleCoverUrl} />
        </div>

        <div className="mt-7">
          <SectionLabel size="sm">FALLBACK — LETRA EMBOSSADA</SectionLabel>
          <div className="mt-5 flex flex-wrap items-end gap-6">
            <CoverSample size="md" slug="agua-viva" title="Água viva" />
            <CoverSample size="md" slug="o-estrangeiro" title="O Estrangeiro" />
            <CoverSample size="md" slug="nada" title="Nada" />
            <CoverSample size="md" slug="a-vegetariana" title="A vegetariana" />
            <CoverSample size="lg" slug="malina" title="Malina" />
          </div>
        </div>
      </section>

      <HairlineDivider />

      {/* SectionLabel */}
      <section className="mt-7">
        <SectionLabel>SECTIONLABEL</SectionLabel>
        <div className="mt-5 space-y-6">
          <ShowcaseRow label="size=default">
            <SectionLabel>PERFIL EMOCIONAL</SectionLabel>
          </ShowcaseRow>
          <ShowcaseRow label="size=sm">
            <SectionLabel size="sm">1942 · PROGRESSIVO</SectionLabel>
          </ShowcaseRow>
        </div>
      </section>

      <HairlineDivider />

      {/* HairlineDivider */}
      <section className="mt-7">
        <SectionLabel>HAIRLINEDIVIDER</SectionLabel>
        <div className="mt-5">
          <p className="font-body text-body-md text-text-primary">
            seção anterior — texto acima do divisor.
          </p>
          <HairlineDivider />
          <p className="font-body text-body-md text-text-primary">
            seção seguinte — texto abaixo do divisor.
          </p>
        </div>
      </section>

      <HairlineDivider />

      {/* Button */}
      <section className="mt-7">
        <SectionLabel>BUTTON</SectionLabel>
        <div className="mt-5 grid grid-cols-1 gap-6 md:grid-cols-2">
          <ShowcaseRow label="variant=primary">
            <div className="flex flex-wrap items-center gap-4">
              <Button variant="primary">aprovar e publicar</Button>
              <Button variant="primary" disabled>
                aprovar e publicar
              </Button>
            </div>
          </ShowcaseRow>
          <ShowcaseRow label="variant=ghost">
            <div className="flex flex-wrap items-center gap-4">
              <Button variant="ghost">descartar geração</Button>
              <Button variant="ghost" disabled>
                descartar geração
              </Button>
            </div>
          </ShowcaseRow>
          <ShowcaseRow label="variant=link">
            <div className="flex flex-wrap items-center gap-4">
              <Button variant="link">ler mais</Button>
              <Button variant="link" disabled>
                ler mais
              </Button>
            </div>
          </ShowcaseRow>
        </div>
      </section>

      <HairlineDivider />

      {/* Header */}
      <section className="mt-7">
        <SectionLabel>HEADER</SectionLabel>
        <div className="mt-5 space-y-7">
          <div>
            <SectionLabel size="sm">MOBILE (360PX)</SectionLabel>
            <div className="mt-3 w-[360px] overflow-hidden rounded-sm border border-divider bg-canvas">
              <Header />
              <div className="px-5 py-7">
                <p className="font-body text-body-sm text-text-muted">
                  conteúdo da página vai aqui.
                </p>
              </div>
            </div>
          </div>
          <div>
            <SectionLabel size="sm">FULL WIDTH</SectionLabel>
            <div className="mt-3 overflow-hidden rounded-sm border border-divider bg-canvas">
              <Header />
              <div className="px-7 py-7">
                <p className="font-body text-body-sm text-text-muted">
                  conteúdo da página vai aqui.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <HairlineDivider />

      {/* Footer */}
      <section className="mt-7">
        <SectionLabel>FOOTER</SectionLabel>
        <div className="mt-5 overflow-hidden rounded-sm border border-divider bg-canvas">
          <Footer />
        </div>
      </section>

      <HairlineDivider />

      {/* PageColumn */}
      <section className="mt-7">
        <SectionLabel>PAGECOLUMN</SectionLabel>
        <p className="mt-3 font-body text-body-sm text-text-muted max-w-prose">
          cada coluna está demarcada com borda fina para visualização. a borda não faz parte do
          componente.
        </p>
        <div className="mt-5 space-y-5">
          <PageColumnPreview width="prose" />
          <PageColumnPreview width="content" />
          <PageColumnPreview width="wide" />
          <PageColumnPreview width="edge" />
        </div>
      </section>
    </PageColumn>
  );
}

function ShowcaseRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="font-body text-body-sm text-text-muted lowercase">{label}</p>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function CoverSample({
  size,
  src,
  slug = 'sample-slug',
  title = 'Livro de Exemplo',
}: {
  size: 'sm' | 'md' | 'lg' | 'xl' | 'hero' | 'hero-md';
  src?: string;
  slug?: string;
  title?: string;
}) {
  return (
    <div>
      <BookCover size={size} src={src ?? null} slug={slug} title={title} />
      <p className="mt-3 font-body text-body-sm text-text-muted lowercase">size={size}</p>
    </div>
  );
}

function PageColumnPreview({ width }: { width: 'prose' | 'content' | 'wide' | 'edge' }) {
  return (
    <div>
      <p className="font-body text-body-sm text-text-muted lowercase">width={width}</p>
      <div className="mt-2 border border-divider">
        <PageColumn width={width}>
          <div className="py-4">
            <p className="font-body text-body-sm text-text-primary lowercase">
              coluna centralizada — largura {width}
            </p>
          </div>
        </PageColumn>
      </div>
    </div>
  );
}
