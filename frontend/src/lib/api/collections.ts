/**
 * Public collection reads.
 *
 * Per backend §14.1 GET /v1/collections and GET /v1/collections/{slug}. Only
 * published collections surface; unpublished slugs yield 404 from the backend,
 * which we re-throw as ApiError(404). The collection detail page catches that
 * and calls notFound().
 *
 * Cache policy: ISR with 5-minute revalidation (frontend plan §16.2) so
 * editorial changes to collections go live without a full redeploy.
 */
import 'server-only';

import { apiFetch } from './client';
import {
  CollectionListResponseSchema,
  CollectionDetailSchema,
  type CollectionListResponse,
  type CollectionDetail,
} from './types';

export function listCollections(
  limit?: number,
  offset?: number,
): Promise<CollectionListResponse> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set('limit', String(limit));
  if (offset !== undefined) params.set('offset', String(offset));
  const query = params.toString();

  return apiFetch(
    `/v1/collections${query ? `?${query}` : ''}`,
    { method: 'GET', next: { revalidate: 300 } },
    CollectionListResponseSchema,
  );
}

export function getCollectionBySlug(slug: string): Promise<CollectionDetail> {
  return apiFetch(
    `/v1/collections/${encodeURIComponent(slug)}`,
    { method: 'GET', next: { revalidate: 300 } },
    CollectionDetailSchema,
  );
}
