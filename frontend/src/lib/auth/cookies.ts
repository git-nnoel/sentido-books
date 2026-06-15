/**
 * Server-only cookie helpers for the admin bearer token.
 *
 * The admin token never reaches browser JS — it lives in an httpOnly cookie
 * read by server components and server actions (frontend plan F4 + §9.2).
 *
 * Cookie name and lifetime are constants here so the route handler, the
 * api client, and the guard agree on a single source of truth.
 */
import 'server-only';

import { cookies } from 'next/headers';

export const ADMIN_COOKIE_NAME = 'sentido_admin';

/** 7 days, per frontend plan §9.2. */
export const ADMIN_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

export function getAdminToken(): string | null {
  return cookies().get(ADMIN_COOKIE_NAME)?.value ?? null;
}

export function setAdminToken(token: string): void {
  cookies().set({
    name: ADMIN_COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: ADMIN_COOKIE_MAX_AGE,
    path: '/',
  });
}

export function clearAdminToken(): void {
  cookies().set({
    name: ADMIN_COOKIE_NAME,
    value: '',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 0,
    path: '/',
  });
}
