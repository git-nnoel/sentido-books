'use server';

/**
 * Server actions for the collection editor (frontend plan §16.3 F7).
 *
 * All mutations run server-side so the admin bearer token stays in the
 * httpOnly cookie (plan F4). Pattern matches livro/[id]/actions.ts:
 *   - 401 → clear cookie + redirect to login with ?next preserved.
 *   - other ApiError → return { ok: false, error }.
 *   - success → revalidate affected paths, then return { ok: true } (or
 *     redirect, for delete).
 *
 * Revalidated paths on metadata/book changes:
 *   - /admin/colecoes/[id]  (this editor)
 *   - /admin/colecoes       (the queue: title / status / count may change)
 *   - /colecoes/[slug]      (the public collection page changed too)
 */
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import {
  deleteCollection,
  listAdminBooks,
  replaceCollectionBooks,
  updateCollection,
} from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';

export type ActionResult = { ok: true } | { ok: false; error: string };

/**
 * A book candidate for the add-book picker — the minimal shape the
 * BookListEditor needs to render a row and add it to the collection.
 */
export type PickerBook = {
  id: string;
  slug: string;
  title: string;
  author_name: string;
  published: boolean;
  cover_url: string | null;
};

/**
 * Returns the admin book catalog for the add-book picker. The picker is a
 * Client Component and can't call the server-only `listAdminBooks` directly,
 * so this server action wraps it — the bearer token stays server-side (F4).
 *
 * On 401 we return `{ ok: false }` rather than redirecting: the picker is a
 * non-critical enhancement, and a hard redirect from a background fetch would
 * be jarring. The metadata-form save will surface the real auth failure.
 */
export async function listPickerBooksAction(): Promise<
  { ok: true; books: PickerBook[] } | { ok: false }
> {
  try {
    const { books } = await listAdminBooks('all', 100, 0);
    return {
      ok: true,
      books: books.map((book) => ({
        id: book.id,
        slug: book.slug,
        title: book.title,
        author_name: book.author.name,
        published: book.published,
        cover_url: book.cover_url,
      })),
    };
  } catch {
    return { ok: false };
  }
}

function loginRedirect(id: string): never {
  clearAdminToken();
  redirect(
    `/admin/login?next=${encodeURIComponent(`/admin/colecoes/${id}`)}&error=token%20inv%C3%A1lido`,
  );
}

function revalidateCollectionPaths(): void {
  revalidatePath('/admin/colecoes/[id]', 'page');
  revalidatePath('/admin/colecoes');
  revalidatePath('/colecoes/[slug]', 'page');
}

export async function updateCollectionAction(
  id: string,
  formData: FormData,
): Promise<ActionResult> {
  const rawTitle = formData.get('title');
  const title = typeof rawTitle === 'string' ? rawTitle.trim() : '';
  if (title.length === 0) {
    return { ok: false, error: 'informe um título.' };
  }

  const rawDescription = formData.get('description');
  const description =
    typeof rawDescription === 'string' && rawDescription.trim().length > 0
      ? rawDescription.trim()
      : null;

  // An unchecked checkbox sends no value; checked sends 'on' (or its value attr).
  const published = formData.get('published') !== null;

  try {
    await updateCollection(id, { title, description, published });
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) loginRedirect(id);
      return { ok: false, error: err.detail };
    }
    throw err;
  }

  revalidateCollectionPaths();
  return { ok: true };
}

export async function replaceBooksAction(
  id: string,
  formData: FormData,
): Promise<ActionResult> {
  const bookIds = formData
    .getAll('book_id')
    .filter((value): value is string => typeof value === 'string');

  try {
    await replaceCollectionBooks(id, bookIds);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) loginRedirect(id);
      return { ok: false, error: err.detail };
    }
    throw err;
  }

  revalidateCollectionPaths();
  return { ok: true };
}

export async function deleteCollectionAction(id: string): Promise<ActionResult> {
  try {
    await deleteCollection(id);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) loginRedirect(id);
      return { ok: false, error: err.detail };
    }
    throw err;
  }

  revalidatePath('/admin/colecoes');
  revalidatePath('/colecoes/[slug]', 'page');
  redirect('/admin/colecoes');
}
