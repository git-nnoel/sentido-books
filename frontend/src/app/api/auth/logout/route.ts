/**
 * Logout convenience route. Native HTML forms only support GET/POST, so we
 * expose this as a POST endpoint that clears the cookie. The DELETE method
 * on /api/auth is still available for programmatic callers (curl, fetch).
 */
import { NextResponse, type NextRequest } from 'next/server';
import { clearAdminToken } from '@/lib/auth/cookies';

export async function POST(request: NextRequest): Promise<NextResponse> {
  clearAdminToken();
  // Build the redirect from the Host header so accessing the app from a
  // LAN IP doesn't bounce back to localhost (see /api/auth/route.ts for
  // the same pattern + rationale).
  const forwardedHost = request.headers.get('x-forwarded-host');
  const host = forwardedHost ?? request.headers.get('host');
  const protocol = request.headers.get('x-forwarded-proto') ?? 'http';
  const base = host ? `${protocol}://${host}` : request.url;
  return NextResponse.redirect(new URL('/admin/login', base), 303);
}
