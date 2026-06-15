/**
 * Public dimension navigation — the /explorar family (frontend plan §16.4).
 *
 * Per backend §14.3:
 *   - GET /v1/explore?mode=tag&value={tag}&limit&offset
 *   - GET /v1/explore?mode=emotion&axis={axis}&min&limit&offset
 *   - GET /v1/explore?mode=pace&value={pace}&limit&offset
 *   - GET /v1/explore/tags
 *
 * Cache policy: the /explore reads are `no-store` — the result set shifts as
 * new books are published, and these pages are browse surfaces where freshness
 * matters more than a cached first paint. The tag cloud (/explore/tags) is the
 * exception: it tolerates a 5-minute ISR window (frontend plan §16.4).
 *
 * Server-side only (no 'use client'): these are called from Server Components.
 */
import 'server-only';

import { apiFetch } from './client';
import {
  ExploreResponseSchema,
  AtmosphereTagsResponseSchema,
  type ExploreResponse,
  type AtmosphereTagsResponse,
  type NarrativePace,
} from './types';

export function exploreByTag(
  tag: string,
  limit?: number,
  offset?: number,
): Promise<ExploreResponse> {
  const params = new URLSearchParams({ mode: 'tag', value: tag });
  if (limit !== undefined) params.set('limit', String(limit));
  if (offset !== undefined) params.set('offset', String(offset));

  return apiFetch(
    `/v1/explore?${params.toString()}`,
    { method: 'GET', cache: 'no-store' },
    ExploreResponseSchema,
  );
}

export function exploreByEmotion(
  axis: string,
  min?: number,
  limit?: number,
  offset?: number,
): Promise<ExploreResponse> {
  const params = new URLSearchParams({ mode: 'emotion', axis });
  if (min !== undefined) params.set('min', String(min));
  if (limit !== undefined) params.set('limit', String(limit));
  if (offset !== undefined) params.set('offset', String(offset));

  return apiFetch(
    `/v1/explore?${params.toString()}`,
    { method: 'GET', cache: 'no-store' },
    ExploreResponseSchema,
  );
}

export function exploreByPace(
  pace: NarrativePace,
  limit?: number,
  offset?: number,
): Promise<ExploreResponse> {
  const params = new URLSearchParams({ mode: 'pace', value: pace });
  if (limit !== undefined) params.set('limit', String(limit));
  if (offset !== undefined) params.set('offset', String(offset));

  return apiFetch(
    `/v1/explore?${params.toString()}`,
    { method: 'GET', cache: 'no-store' },
    ExploreResponseSchema,
  );
}

export function listAtmosphereTags(): Promise<AtmosphereTagsResponse> {
  return apiFetch(
    '/v1/explore/tags',
    { method: 'GET', next: { revalidate: 300 } },
    AtmosphereTagsResponseSchema,
  );
}
