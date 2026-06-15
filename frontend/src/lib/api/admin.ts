/**
 * Admin mutation + read functions.
 *
 * All functions go through adminApiFetch, which attaches the Bearer token
 * from the server-side cookie. The admin token never reaches the browser JS
 * (frontend plan F4 — server actions only).
 *
 * Surface:
 *   - ingestBook        — POST /v1/admin/books/ingest
 *   - generateArtifacts — POST /v1/admin/books/{id}/generate
 *   - updateBook        — PUT  /v1/admin/books/{id}
 *   - publishBook       — POST /v1/admin/books/{id}/publish
 *   - listAdminBooks    — GET  /v1/admin/books?status=...
 *   - getAdminBookById  — derived from listAdminBooks (see note below)
 */
import 'server-only';

import { adminApiFetch } from './client';
import {
  AdminBookSchema,
  AdminBookListResponseSchema,
  type AdminBook,
  type AdminBookListResponse,
  type AdminBookListStatus,
} from './types';

/**
 * Adds a book to the catalog by ISBN lookup. Lands in
 * embedding_status=pending, profile_status=pending, published=false.
 */
export function ingestBook(isbn: string): Promise<AdminBook> {
  return adminApiFetch(
    '/v1/admin/books/ingest',
    { method: 'POST', body: { isbn } },
    AdminBookSchema,
  );
}

/**
 * Triggers LLM generation: synopsis + emotional_profile + embedding.
 * Synchronous on the backend (no background worker in v1).
 *
 * Pass `regenerate=true` to overwrite existing artifacts.
 */
export function generateArtifacts(bookId: string, regenerate = false): Promise<AdminBook> {
  return adminApiFetch(
    `/v1/admin/books/${encodeURIComponent(bookId)}/generate`,
    { method: 'POST', body: { regenerate } },
    AdminBookSchema,
  );
}

/**
 * Edits arbitrary fields on a book. Used by curators to clean up generated
 * content before publishing.
 *
 * The patch shape is `Partial<AdminBook>`, but the backend whitelists which
 * fields are accepted (backend §5.2 — anything else 422s). This client does
 * not enforce that whitelist; the backend is authoritative.
 */
export function updateBook(bookId: string, patch: Partial<AdminBook>): Promise<AdminBook> {
  return adminApiFetch(
    `/v1/admin/books/${encodeURIComponent(bookId)}`,
    { method: 'PUT', body: patch },
    AdminBookSchema,
  );
}

/**
 * Convenience endpoint equivalent to PUT with
 * `{"profile_status": "approved", "published": true}`. Requires
 * `embedding_status=done`; otherwise the backend returns 422.
 */
export function publishBook(bookId: string): Promise<AdminBook> {
  return adminApiFetch(
    `/v1/admin/books/${encodeURIComponent(bookId)}/publish`,
    { method: 'POST' },
    AdminBookSchema,
  );
}

/**
 * Lists admin books filtered by curation status. Backed by GET
 * /v1/admin/books (backend §5.2).
 *
 *   status:
 *     - 'pending_generation' → embedding_status='pending'
 *     - 'pending_approval'   → embedding_status='done' AND profile_status!='approved'
 *     - 'published'          → published=true
 *     - 'all'                → no filter
 */
export function listAdminBooks(
  status: AdminBookListStatus,
  limit = 50,
  offset = 0,
): Promise<AdminBookListResponse> {
  const params = new URLSearchParams({
    status,
    limit: String(limit),
    offset: String(offset),
  });
  return adminApiFetch(
    `/v1/admin/books?${params.toString()}`,
    { method: 'GET' },
    AdminBookListResponseSchema,
  );
}

/**
 * Fetches a single admin book by id.
 *
 * KNOWN LIMITATION — MVP shim. The backend does not yet expose
 * `GET /v1/admin/books/{id}`. Until it does, this helper lists the first
 * 100 books (status='all') and finds the matching id. Returns `null` when
 * the id is not in that window.
 *
 * Phase 2 follow-up for the backend: add `GET /v1/admin/books/{id}` so this
 * helper can hit it directly. Until then, catalogs over ~100 books may have
 * detail pages that 404 for older entries.
 */
export async function getAdminBookById(id: string): Promise<AdminBook | null> {
  const { books } = await listAdminBooks('all', 100, 0);
  return books.find((book) => book.id === id) ?? null;
}
