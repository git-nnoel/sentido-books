/**
 * Admin mutation functions.
 *
 * All functions go through adminApiFetch, which attaches the Bearer token
 * from the server-side cookie. The admin token never reaches the browser JS
 * (frontend plan F4 — server actions only).
 *
 * Phase 0 surface:
 *   - ingestBook        — POST /v1/admin/books/ingest
 *   - generateArtifacts — POST /v1/admin/books/{id}/generate
 *   - updateBook        — PUT  /v1/admin/books/{id}
 *   - publishBook       — POST /v1/admin/books/{id}/publish
 *
 * GAP: `listAdminBooks` (GET /v1/admin/books?status=...) is a Phase 1
 * backend deliverable. It will live here when the admin queue tables ship.
 * The login flow uses deferred validation in Phase 0 — see plan §9.2.
 */
import 'server-only';

import { adminApiFetch } from './client';
import { AdminBookSchema, type AdminBook } from './types';

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
