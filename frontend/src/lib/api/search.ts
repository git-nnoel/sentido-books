/**
 * Public semantic search.
 *
 * Per backend §5 — POST /v1/search with `{query, limit}` returns
 * `{query, results: SearchResult[]}`. Each result includes a
 * resonance_line generated against the user's query and the book.
 *
 * Cache policy: `no-store` — every query is dynamic. The /buscar page
 * Server Component re-issues the request on every render.
 */
import 'server-only';

import { apiFetch } from './client';
import { SearchResponseSchema, type SearchResponse } from './types';

export function semanticSearch(query: string, limit = 12): Promise<SearchResponse> {
  return apiFetch(
    '/v1/search',
    {
      method: 'POST',
      body: { query, limit },
      cache: 'no-store',
    },
    SearchResponseSchema,
  );
}
