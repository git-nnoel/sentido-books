/**
 * Admin book editor — the workflow page.
 *
 * Server Component shell + client islands for the form and the
 * generate buttons. The state branch determines which controls are shown:
 *
 *   embedding_status === 'pending'
 *     → "aguardando geração" — single button to trigger /generate.
 *
 *   embedding_status === 'done' AND profile_status !== 'approved'
 *     → editor with "aprovar e publicar" (primary) + "regerar perfil" (ghost).
 *
 *   published === true
 *     → editor with "salvar alterações" (primary) + "regerar perfil" (ghost).
 *
 * 401 from the backend on initial load → clear cookie + redirect to login
 * (deferred validation, plan §9.2). 404 (id not in the first page of the
 * admin queue) → notFound() — see getAdminBookById docstring for the MVP
 * limitation.
 */
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { getAdminBookById } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';
import type { AdminBook } from '@/lib/api/types';
import { EditForm } from './EditForm';
import { GenerateButton } from './GenerateButton';
import {
  generateAction,
  publishAction,
  regenerateAction,
  updateAction,
} from './actions';

export const metadata = {
  title: 'editar livro — sentido admin',
  robots: { index: false, follow: false },
};

type PageProps = { params: { id: string } };

async function loadBook(id: string): Promise<AdminBook> {
  try {
    const book = await getAdminBookById(id);
    if (!book) notFound();
    return book;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      clearAdminToken();
      redirect(
        `/admin/login?next=${encodeURIComponent(`/admin/livro/${id}`)}&error=token%20inv%C3%A1lido`,
      );
    }
    throw err;
  }
}

function statusLine(book: AdminBook): string {
  const stage = book.published
    ? 'PUBLICADO'
    : book.profile_status === 'approved'
      ? 'APROVADO'
      : 'RASCUNHO';
  return `${book.embedding_status.toUpperCase()} · ${book.profile_status.toUpperCase()} · ${stage}`;
}

export default async function AdminBookEditorPage({ params }: PageProps) {
  const book = await loadBook(params.id);
  const awaitingGeneration = book.embedding_status === 'pending';
  const awaitingApproval =
    book.embedding_status === 'done' && book.profile_status !== 'approved';
  const isPublished = book.published;

  // Server-bound actions — pre-bind the bookId so client islands don't have to.
  const generateBound = async () => generateAction(book.id, false);
  const regenerateBound = async () => regenerateAction(book.id);
  const publishBound = async (id: string, data: FormData) => publishAction(id, data);
  const updateBound = async (id: string, data: FormData) => updateAction(id, data);

  return (
    <div className="mx-auto w-full max-w-content">
      <SectionLabel size="sm">{statusLine(book)}</SectionLabel>
      <h1 className="mt-3 font-display text-text-primary text-display-md lowercase">
        {book.title}
      </h1>
      <p className="mt-2 font-display italic text-body-lg text-text-muted">
        {book.author.name}
      </p>

      <HairlineDivider />

      {awaitingGeneration ? (
        <section>
          <SectionLabel>AGUARDANDO GERAÇÃO</SectionLabel>
          <p className="mt-5 max-w-prose font-body text-body-md text-text-primary lowercase">
            o livro foi ingerido, mas ainda não tem sinopse nem perfil emocional. gere os
            artefatos para revisar e publicar.
          </p>
          <div className="mt-7">
            <GenerateButton
              action={generateBound}
              label="gerar perfil emocional"
              pendingLabel="gerando perfil…"
            />
          </div>
        </section>
      ) : awaitingApproval ? (
        <section>
          <SectionLabel>REVISAR E APROVAR</SectionLabel>
          <p className="mt-5 max-w-prose font-body text-body-md text-text-primary lowercase">
            edite o que precisar e aprove para publicar — ou regere a partir do zero.
          </p>
          <div className="mt-7">
            <EditForm
              book={book}
              action={publishBound}
              submitLabel="aprovar e publicar"
              pendingLabel="publicando…"
            />
          </div>
          <div className="mt-7">
            <GenerateButton
              action={regenerateBound}
              label="regerar perfil"
              pendingLabel="regerando…"
              variant="ghost"
              confirmCopy="regerar substitui a sinopse e o perfil atuais. continuar?"
            />
          </div>
        </section>
      ) : isPublished ? (
        <section>
          <SectionLabel>PUBLICADO</SectionLabel>
          <p className="mt-5 max-w-prose font-body text-body-md text-text-primary lowercase">
            o livro está no catálogo público. ajustes aqui aparecem na próxima revalidação.
          </p>
          <div className="mt-7">
            <EditForm
              book={book}
              action={updateBound}
              submitLabel="salvar alterações"
              pendingLabel="salvando…"
            />
          </div>
          <div className="mt-7">
            <GenerateButton
              action={regenerateBound}
              label="regerar perfil"
              pendingLabel="regerando…"
              variant="ghost"
              confirmCopy="regerar substitui a sinopse e o perfil atuais. continuar?"
            />
          </div>
          <div className="mt-7">
            <Link
              href={`/livro/${book.slug}`}
              className="rounded-sm font-body text-body-md text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
            >
              ver página pública →
            </Link>
          </div>
        </section>
      ) : (
        // Fallback: profile approved but not published (rare, e.g. mid-flow).
        // Treat as "approved, awaiting publish" — same UI as awaitingApproval.
        <section>
          <SectionLabel>PRONTO PARA PUBLICAR</SectionLabel>
          <p className="mt-5 max-w-prose font-body text-body-md text-text-primary lowercase">
            o perfil já está aprovado. revise e publique quando quiser.
          </p>
          <div className="mt-7">
            <EditForm
              book={book}
              action={publishBound}
              submitLabel="aprovar e publicar"
              pendingLabel="publicando…"
            />
          </div>
        </section>
      )}

      <HairlineDivider />

      <Link
        href="/admin"
        className="rounded-sm font-body text-body-sm text-text-muted underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
      >
        ← voltar ao painel
      </Link>
    </div>
  );
}
