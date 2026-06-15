/**
 * ISBN ingest page (admin).
 *
 * Two states:
 *   - default      → renders <IngestForm>.
 *   - ?ok=<id>     → renders the success block with the three follow-up
 *                    curls (generate, approve via PUT, publish) and a link
 *                    to preview the public page once those finish.
 *
 * Phase 0 — full generate→approve→publish UI lands in Phase 1 with the
 * BookEditForm + GenerationPanel. For now the curator runs the curls from
 * their terminal; the page hands them the exact commands.
 */
import Link from 'next/link';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { IngestForm } from './IngestForm';

export const metadata = {
  title: 'adicionar livro — sentido admin',
};

type SearchParams = {
  ok?: string | string[];
  slug?: string | string[];
  title?: string | string[];
};

function firstString(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export default function AdminNewBookPage({ searchParams }: { searchParams: SearchParams }) {
  const bookId = firstString(searchParams.ok);
  const slug = firstString(searchParams.slug);
  const title = firstString(searchParams.title);

  if (bookId && slug && title) {
    return <IngestSuccess bookId={bookId} slug={slug} title={title} />;
  }

  return (
    <div className="mx-auto w-full max-w-content">
      <SectionLabel>ADMIN · NOVO LIVRO</SectionLabel>
      <h1 className="mt-3 font-display italic text-accent text-display-lg lowercase">
        adicionar livro por ISBN
      </h1>
      <p className="mt-5 font-body text-body-md text-text-muted lowercase max-w-prose">
        informe o ISBN. o catálogo busca o livro em Open Library e Google Books, cria o registro, e
        aguarda a geração dos artefatos.
      </p>

      <IngestForm />
    </div>
  );
}

function IngestSuccess({ bookId, slug, title }: { bookId: string; slug: string; title: string }) {
  // The token is read from the `$ADMIN_TOKEN` shell variable in the curl
  // chain. Curators set this once per terminal session.
  const generateCmd = `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \\\n  http://localhost:8000/v1/admin/books/${bookId}/generate`;
  const approveCmd = `curl -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" \\\n     -H "Content-Type: application/json" \\\n     -d '{"profile_status":"approved"}' \\\n     http://localhost:8000/v1/admin/books/${bookId}`;
  const publishCmd = `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \\\n  http://localhost:8000/v1/admin/books/${bookId}/publish`;

  return (
    <div className="mx-auto w-full max-w-content">
      <SectionLabel>LIVRO ADICIONADO</SectionLabel>
      <h1 className="mt-3 font-display italic text-accent text-display-lg lowercase">
        {`"${title}"`}
      </h1>
      <p className="mt-5 font-body text-body-md text-text-primary max-w-prose lowercase">
        o catálogo recebeu o livro. próximos passos: gerar perfil, aprovar, publicar.
      </p>

      <HairlineDivider />

      <SectionLabel size="sm">1 · GERAR PERFIL</SectionLabel>
      <CurlBlock>{generateCmd}</CurlBlock>

      <div className="mt-6">
        <SectionLabel size="sm">2 · APROVAR PERFIL</SectionLabel>
        <CurlBlock>{approveCmd}</CurlBlock>
      </div>

      <div className="mt-6">
        <SectionLabel size="sm">3 · PUBLICAR</SectionLabel>
        <CurlBlock>{publishCmd}</CurlBlock>
      </div>

      <HairlineDivider />

      <div className="flex flex-wrap items-center gap-4">
        <Link
          href={`/livro/${slug}`}
          className="rounded-sm font-body text-body-md text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          ver página pública →
        </Link>
        <Link
          href="/admin/novo"
          className="rounded-sm font-body text-body-sm text-text-muted underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
        >
          adicionar outro livro
        </Link>
      </div>
    </div>
  );
}

function CurlBlock({ children }: { children: string }) {
  return (
    <pre className="mt-3 overflow-x-auto rounded-md border border-divider bg-elevated p-4 font-mono text-body-sm text-text-primary">
      <code>{children}</code>
    </pre>
  );
}
