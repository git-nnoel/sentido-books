/**
 * Public book reads.
 *
 * Per backend §5.1 GET /v1/books/{slug}. Only published books are returned;
 * unpublished slugs yield 404 from the backend, which we re-throw as
 * ApiError(404). The book detail page catches that and calls notFound().
 *
 * Cache policy: ISR with 5-minute revalidation (frontend plan §8.1) so
 * editorial edits go live without a full redeploy.
 */
import 'server-only';

import { apiFetch } from './client';
import { BookDetailSchema, type BookDetail } from './types';

export function getBookBySlug(slug: string): Promise<BookDetail> {
  return apiFetch(
    `/v1/books/${encodeURIComponent(slug)}`,
    { method: 'GET', next: { revalidate: 300 } },
    BookDetailSchema,
  );
}
