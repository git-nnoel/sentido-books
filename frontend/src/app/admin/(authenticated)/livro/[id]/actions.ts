'use server';

/**
 * Server actions for the admin book editor (frontend plan F4).
 *
 * Every mutation runs server-side so the admin bearer token stays in the
 * httpOnly cookie. On 401 from the backend, we clear the cookie and 302 to
 * /admin/login with the originating path preserved as ?next.
 *
 * Each successful action calls revalidatePath to drop the cached server
 * render of the detail page (and the queue), so the next paint reflects
 * the new state.
 */
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import {
  generateArtifacts,
  publishBook,
  updateBook,
} from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';
import type { AdminBook } from '@/lib/api/types';

export type ActionResult = { ok: true } | { ok: false; error: string };

function handleAdminError(err: unknown, currentPath: string): never {
  if (err instanceof ApiError && err.status === 401) {
    clearAdminToken();
    redirect(
      `/admin/login?next=${encodeURIComponent(currentPath)}&error=token%20inv%C3%A1lido`,
    );
  }
  throw err;
}

// ─────────────────────────────────────────────────────────────────────────────
// Parsing — translate FormData (from EditForm) into the AdminBook patch shape
// the backend accepts (backend §5.2 PUT /v1/admin/books/{id}).
// ─────────────────────────────────────────────────────────────────────────────

const NARRATIVE_PACES = ['slow', 'progressive', 'frenetic'] as const;
type NarrativePace = (typeof NARRATIVE_PACES)[number];

const EMOTION_KEYS = [
  'anguish',
  'melancholy',
  'hope',
  'violence',
  'tenderness',
  'strangeness',
] as const;

function getString(formData: FormData, key: string): string | null {
  const value = formData.get(key);
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length === 0 ? null : trimmed;
}

function getNumber(formData: FormData, key: string): number | null {
  const value = formData.get(key);
  if (typeof value !== 'string' || value.trim().length === 0) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function getPace(formData: FormData): NarrativePace | null {
  const raw = formData.get('narrative_pace');
  if (typeof raw !== 'string') return null;
  return (NARRATIVE_PACES as ReadonlyArray<string>).includes(raw)
    ? (raw as NarrativePace)
    : null;
}

function parseAtmosphereTags(raw: string | null): string[] {
  if (!raw) return [];
  return raw
    .split(',')
    .map((tag) => tag.trim().toLowerCase())
    .filter((tag) => tag.length > 0);
}

function buildPatch(formData: FormData): Partial<AdminBook> {
  const emotional_profile = EMOTION_KEYS.reduce<Record<string, number>>(
    (acc, key) => {
      const value = getNumber(formData, `emotional_profile.${key}`);
      if (value !== null) acc[key] = Math.max(0, Math.min(10, value));
      return acc;
    },
    {},
  );

  const patch: Partial<AdminBook> = {
    title: getString(formData, 'title') ?? undefined,
    original_title: getString(formData, 'original_title'),
    synopsis: getString(formData, 'synopsis'),
    atmosphere_tags: parseAtmosphereTags(getString(formData, 'atmosphere_tags')),
    narrative_pace: getPace(formData),
    cover_url: getString(formData, 'cover_url'),
    year_published: getNumber(formData, 'year_published'),
  };

  if (Object.keys(emotional_profile).length === EMOTION_KEYS.length) {
    patch.emotional_profile = emotional_profile as AdminBook['emotional_profile'];
  }

  // Strip `undefined` so we only send fields the curator actually edited
  // (and explicit nulls for nullable fields).
  return Object.fromEntries(
    Object.entries(patch).filter(([, v]) => v !== undefined),
  ) as Partial<AdminBook>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Actions
// ─────────────────────────────────────────────────────────────────────────────

export async function generateAction(
  id: string,
  regenerate = false,
): Promise<ActionResult> {
  const path = `/admin/livro/${id}`;
  try {
    await generateArtifacts(id, regenerate);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        handleAdminError(err, path);
      }
      return { ok: false, error: err.detail };
    }
    throw err;
  }
  revalidatePath(path);
  revalidatePath('/admin');
  // Regenerating changes the book's embedding, which shifts related-book
  // ranking on every other published book's page. Bust the whole family.
  revalidatePath('/livro/[slug]', 'page');
  return { ok: true };
}

export async function updateAction(
  id: string,
  formData: FormData,
): Promise<ActionResult> {
  const path = `/admin/livro/${id}`;
  const patch = buildPatch(formData);

  try {
    await updateBook(id, patch);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        handleAdminError(err, path);
      }
      return { ok: false, error: err.detail };
    }
    throw err;
  }
  revalidatePath(path);
  revalidatePath('/admin');
  // Editing synopsis/atmosphere/etc. on a published book changes what
  // its public page renders. Bust the family so the next visit reflects.
  revalidatePath('/livro/[slug]', 'page');
  return { ok: true };
}

export async function publishAction(
  id: string,
  formData: FormData,
): Promise<ActionResult> {
  const path = `/admin/livro/${id}`;
  const patch = buildPatch(formData);

  // Save curator edits before flipping to approved+published. If the save
  // fails, surface the error and let the curator retry — we do NOT publish
  // a book whose latest edits we couldn't persist.
  try {
    await updateBook(id, patch);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        handleAdminError(err, path);
      }
      return { ok: false, error: `não foi possível salvar. ${err.detail}` };
    }
    throw err;
  }

  try {
    await publishBook(id);
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        handleAdminError(err, path);
      }
      return { ok: false, error: `não foi possível publicar. ${err.detail}` };
    }
    throw err;
  }

  revalidatePath(path);
  revalidatePath('/admin');
  // Publishing a new book changes the related-books list for EVERY other
  // published book (pgvector cosine similarity), so we have to bust the
  // ISR cache for the entire /livro/[slug] route family — not just the
  // page we just published. Next.js supports invalidating a dynamic
  // route's whole family via the second arg `'page'`.
  revalidatePath('/livro/[slug]', 'page');
  return { ok: true };
}

export async function regenerateAction(id: string): Promise<ActionResult> {
  return generateAction(id, true);
}
