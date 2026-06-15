/**
 * Collection editor (frontend plan §16.3 F7).
 *
 * Server Component shell. Fetches the collection via getAdminCollectionById;
 * 404 → notFound(), 401 → clear cookie + redirect to login (deferred
 * validation, plan §9.2). Renders three sections divided by HairlineDivider:
 *
 *   1. metadata form    (CollectionMetaForm — client)
 *   2. book-list editor (BookListEditor — client; the interesting part)
 *   3. danger zone      (DeleteCollectionButton — client)
 *
 * Server actions are pre-bound with the collection id before crossing the
 * server/client boundary — `Function.prototype.bind` on a server action
 * returns another server action that Next.js can serialize (same pattern as
 * the book editor; an inline arrow would break serialization).
 */
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { getAdminCollectionById } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';
import type { AdminCollection } from '@/lib/api/types';
import { CollectionMetaForm } from './CollectionMetaForm';
import { BookListEditor } from './BookListEditor';
import { DeleteCollectionButton } from './DeleteCollectionButton';
import {
  deleteCollectionAction,
  replaceBooksAction,
  updateCollectionAction,
} from './actions';

export const metadata = {
  title: 'editar coleção — sentido admin',
  robots: { index: false, follow: false },
};

type PageProps = { params: { id: string } };

async function loadCollection(id: string): Promise<AdminCollection> {
  try {
    return await getAdminCollectionById(id);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        clearAdminToken();
        redirect(
          `/admin/login?next=${encodeURIComponent(`/admin/colecoes/${id}`)}&error=token%20inv%C3%A1lido`,
        );
      }
      if (err.status === 404) {
        notFound();
      }
    }
    throw err;
  }
}

export default async function AdminCollectionEditorPage({ params }: PageProps) {
  const collection = await loadCollection(params.id);

  const updateBound = updateCollectionAction.bind(null, collection.id);
  const replaceBooksBound = replaceBooksAction.bind(null, collection.id);
  const deleteBound = deleteCollectionAction.bind(null, collection.id);

  return (
    <div className="mx-auto w-full max-w-content">
      <SectionLabel>{collection.published ? 'COLEÇÃO · PUBLICADA' : 'COLEÇÃO · RASCUNHO'}</SectionLabel>
      <h1 className="mt-3 font-display text-text-primary text-display-md lowercase">
        {collection.title}
      </h1>

      <HairlineDivider />

      {/* Section 1 — metadata */}
      <section>
        <SectionLabel>METADADOS</SectionLabel>
        <div className="mt-5">
          <CollectionMetaForm collection={collection} action={updateBound} />
        </div>
      </section>

      <HairlineDivider />

      {/* Section 2 — book list */}
      <section>
        <SectionLabel>LIVROS</SectionLabel>
        <p className="mt-2 max-w-prose font-body text-body-sm text-text-muted lowercase">
          a ordem aqui é a ordem na página pública. mova, remova ou adicione e salve.
        </p>
        <div className="mt-5">
          <BookListEditor
            initialBooks={collection.books}
            collectionId={collection.id}
            action={replaceBooksBound}
          />
        </div>
      </section>

      <HairlineDivider />

      {/* Section 3 — danger zone */}
      <section>
        <SectionLabel>ZONA DE RISCO</SectionLabel>
        <p className="mt-2 max-w-prose font-body text-body-sm text-text-muted lowercase">
          excluir uma coleção é permanente. os livros continuam no catálogo.
        </p>
        <div className="mt-5">
          <DeleteCollectionButton action={deleteBound} />
        </div>
      </section>

      <HairlineDivider />

      <Link
        href="/admin/colecoes"
        className="rounded-sm font-body text-body-sm text-text-muted underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
      >
        ← voltar às coleções
      </Link>
    </div>
  );
}
