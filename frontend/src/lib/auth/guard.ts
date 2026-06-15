/**
 * Server-side admin route guard.
 *
 * Called at the top of `app/admin/(authenticated)/layout.tsx`. If the cookie
 * is missing, redirects to /admin/login with the original path preserved as
 * `?next=...` (frontend plan §9.2).
 *
 * Phase 0 uses deferred validation: a present cookie passes this guard, even
 * if the token is bogus. The backend will reject bogus tokens with 401 on
 * the next real admin action, and the server action handles the cleanup.
 */
import 'server-only';

import { redirect } from 'next/navigation';
import { getAdminToken } from './cookies';

export function requireAdminToken(currentPath: string): string {
  const token = getAdminToken();
  if (!token) {
    redirect(`/admin/login?next=${encodeURIComponent(currentPath)}`);
  }
  return token;
}
