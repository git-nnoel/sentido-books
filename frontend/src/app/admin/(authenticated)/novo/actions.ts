'use server';

/**
 * Server action for the ISBN ingest form (frontend plan F4).
 *
 * Why a server action and not a client mutation? The admin token only lives
 * in the httpOnly cookie. Running the network call inside a server action
 * keeps it that way — the browser JS never touches the token, and the
 * action redirects via Next.js after success.
 *
 * Flow:
 *   1. Validate ISBN locally (non-empty, digits/X only, 10 or 13 chars).
 *   2. Call admin.ingestBook.
 *   3. On 401 → clear cookie, redirect to login with ?next + ?error.
 *   4. On other failure → return { error } for the client island to render.
 *   5. On success → redirect to /admin/novo?ok=<id>&slug=<slug>&title=<title>.
 */
import { redirect } from 'next/navigation';
import { ingestBook } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';

export type IngestFormState = {
  error: string | null;
};

function normalizeIsbn(raw: string): string {
  return raw.replace(/[\s-]/g, '').toUpperCase();
}

function isPlausibleIsbn(value: string): boolean {
  if (value.length !== 10 && value.length !== 13) return false;
  // 10-digit allows trailing X; 13-digit is digits only.
  if (value.length === 10) return /^[0-9]{9}[0-9X]$/.test(value);
  return /^[0-9]{13}$/.test(value);
}

export async function ingestAction(
  _prevState: IngestFormState,
  formData: FormData,
): Promise<IngestFormState> {
  const rawIsbn = formData.get('isbn');
  if (typeof rawIsbn !== 'string' || rawIsbn.trim().length === 0) {
    return { error: 'informe um ISBN.' };
  }

  const isbn = normalizeIsbn(rawIsbn);
  if (!isPlausibleIsbn(isbn)) {
    return { error: 'ISBN deve ter 10 ou 13 dígitos.' };
  }

  let book;
  try {
    book = await ingestBook(isbn);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        clearAdminToken();
        redirect(`/admin/login?next=${encodeURIComponent('/admin/novo')}&error=token%20inv%C3%A1lido`);
      }
      if (err.status === 404) {
        return { error: 'ISBN não encontrado em Open Library nem Google Books.' };
      }
      if (err.status === 409) {
        return { error: 'este livro já está no catálogo.' };
      }
      return { error: err.detail };
    }
    throw err;
  }

  // Success — send the curator straight to the book editor where they
  // can generate the profile, approve, and publish via UI buttons.
  // (The old behavior was to render a curl-chain success state on this
  //  same page; F5 made that workflow UI-driven so the curl block is
  //  no longer the recommended path.)
  redirect(`/admin/livro/${book.id}`);
}
