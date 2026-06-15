/**
 * Single typed fetch wrapper. The only place `fetch` is called.
 *
 * Per frontend-implementation-plan.md §5.3 and the frontend-system-pattern
 * skill's R1–R3 (single HTTP client; typed responses via Zod; backend DTOs
 * mirror 1:1).
 *
 * Two helpers:
 *   - apiFetch        — public reads (no auth attached).
 *   - adminApiFetch   — server-only; attaches Bearer token from the admin
 *                       cookie. Throws if called from the browser.
 *
 * Both validate every 2xx response against the supplied Zod schema before
 * returning. Validation failures throw ApiContractError — contract drift
 * fails loudly in dev/preview rather than silently in production.
 */
import 'server-only';

import type { ZodSchema, ZodIssue } from 'zod';
import { ErrorBodySchema } from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Error classes
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Backend returned a non-2xx status, or the network call itself failed
 * (status 0). The `detail` carries the message from the backend's
 * `{"detail": "..."}` body when present.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`api error ${status}: ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Response body did not match the expected Zod schema. This indicates
 * contract drift between frontend and backend — the backend changed a
 * shape without the frontend's types being updated in lockstep.
 *
 * Per plan F5, this fails loudly in dev/preview.
 */
export class ApiContractError extends Error {
  readonly issues: ZodIssue[];
  readonly path: string;

  constructor(path: string, issues: ZodIssue[]) {
    super(
      `api contract drift at ${path}: ${issues
        .map((i) => `${i.path.join('.')}: ${i.message}`)
        .join('; ')}`,
    );
    this.name = 'ApiContractError';
    this.issues = issues;
    this.path = path;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

function baseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!url) {
    throw new Error(
      'NEXT_PUBLIC_API_BASE_URL is not configured. Set it in .env.local (see frontend plan §14).',
    );
  }
  return url.replace(/\/+$/, '');
}

function buildUrl(path: string): string {
  const trimmedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl()}${trimmedPath}`;
}

/**
 * Attempt to extract `{detail: string}` from an error response. Falls back
 * to the HTTP status text when the body isn't the expected shape.
 */
async function extractErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const parsed = ErrorBodySchema.safeParse(body);
    if (parsed.success) return parsed.data.detail;
    if (typeof body === 'string') return body;
  } catch {
    // Body wasn't JSON; fall through to status text.
  }
  return response.statusText || `http ${response.status}`;
}

type FetchOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
  next?: NextFetchRequestConfig;
  cache?: RequestCache;
};

async function performFetch<T>(
  path: string,
  options: FetchOptions,
  schema: ZodSchema<T>,
): Promise<T> {
  // Default to no-store; callers opt into caching explicitly.
  const cache = options.cache;
  const next = options.next;
  const init: RequestInit & { next?: NextFetchRequestConfig } = {
    method: options.method ?? 'GET',
    headers: {
      Accept: 'application/json',
      ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers ?? {}),
    },
    ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
    ...(cache !== undefined ? { cache } : {}),
    ...(next !== undefined ? { next } : {}),
  };

  // If neither cache nor next is set, default to no-store (R1: callers opt in).
  if (cache === undefined && next === undefined) {
    init.cache = 'no-store';
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path), init);
  } catch {
    throw new ApiError(0, 'network failure');
  }

  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new ApiError(response.status, detail);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiContractError(path, [
      {
        code: 'custom',
        path: [],
        message: 'response was not valid JSON',
      } as ZodIssue,
    ]);
  }

  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw new ApiContractError(path, parsed.error.issues);
  }
  return parsed.data;
}

// ─────────────────────────────────────────────────────────────────────────────
// Public read helper — no auth attached. Used by Server Components fetching
// public catalog data.
// ─────────────────────────────────────────────────────────────────────────────

export function apiFetch<T>(
  path: string,
  options: FetchOptions,
  schema: ZodSchema<T>,
): Promise<T> {
  return performFetch(path, options, schema);
}

// ─────────────────────────────────────────────────────────────────────────────
// Admin helper — server-only. Reads the admin cookie via next/headers and
// attaches Authorization: Bearer <token>. Cache is forced to 'no-store' so the
// admin surface always sees fresh data (per §5.3).
// ─────────────────────────────────────────────────────────────────────────────

export async function adminApiFetch<T>(
  path: string,
  options: FetchOptions,
  schema: ZodSchema<T>,
): Promise<T> {
  const { headers } = await adminAuthHeaders(options);

  return performFetch(
    path,
    {
      ...options,
      headers,
      // Admin surface is never cached.
      cache: 'no-store',
    },
    schema,
  );
}

/**
 * Admin helper for endpoints that return `204 No Content` (no response body
 * to validate) — e.g. DELETE /v1/admin/collections/{id}. Attaches the bearer
 * token server-side, maps non-2xx to ApiError, and resolves to void without
 * attempting to parse JSON. Calling adminApiFetch here would throw
 * ApiContractError on the empty body.
 */
export async function adminApiFetchNoContent(
  path: string,
  options: FetchOptions,
): Promise<void> {
  const { headers } = await adminAuthHeaders(options);

  const init: RequestInit & { next?: NextFetchRequestConfig } = {
    method: options.method ?? 'GET',
    headers: {
      Accept: 'application/json',
      ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
    cache: 'no-store',
  };

  let response: Response;
  try {
    response = await fetch(buildUrl(path), init);
  } catch {
    throw new ApiError(0, 'network failure');
  }

  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new ApiError(response.status, detail);
  }
  // 204 (or any 2xx) — nothing to parse. Discard the body.
}

/**
 * Shared admin auth: reads the httpOnly cookie via next/headers and returns
 * headers with the Bearer token attached. Throws ApiError(401) when the
 * cookie is missing (a bypassed guard) so server actions can clear + redirect.
 */
async function adminAuthHeaders(
  options: FetchOptions,
): Promise<{ headers: Record<string, string> }> {
  // Lazy-import next/headers so module load works in any context; the actual
  // call still hard-fails in client code because of `import 'server-only'` above.
  const { cookies } = await import('next/headers');
  const { ADMIN_COOKIE_NAME } = await import('@/lib/auth/cookies');

  const token = cookies().get(ADMIN_COOKIE_NAME)?.value;
  if (!token) {
    throw new ApiError(401, 'unauthorized');
  }

  return {
    headers: {
      ...(options.headers as Record<string, string> | undefined),
      Authorization: `Bearer ${token}`,
    },
  };
}
