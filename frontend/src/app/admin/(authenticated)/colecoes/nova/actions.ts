'use server';

/**
 * Server action for creating a collection (frontend plan §16.3 F7).
 *
 * Mirrors the book actions pattern (livro/[id]/actions.ts):
 *   - 401 → clear cookie + redirect to login with ?next preserved.
 *   - other ApiError → return { ok: false, error } for the form to render.
 *   - success → redirect to the new collection's edit screen.
 *
 * The admin bearer token stays in the httpOnly cookie — the create call runs
 * server-side (plan F4).
 */
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { createCollection } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';

export type CreateCollectionResult = { ok: false; error: string };

export async function createCollectionAction(
  formData: FormData,
): Promise<CreateCollectionResult> {
  const path = '/admin/colecoes/nova';

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

  let collection;
  try {
    collection = await createCollection({ title, description });
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        clearAdminToken();
        redirect(
          `/admin/login?next=${encodeURIComponent(path)}&error=token%20inv%C3%A1lido`,
        );
      }
      return { ok: false, error: err.detail };
    }
    throw err;
  }

  // A new collection changes the admin queue.
  revalidatePath('/admin/colecoes');
  redirect(`/admin/colecoes/${collection.id}`);
}
