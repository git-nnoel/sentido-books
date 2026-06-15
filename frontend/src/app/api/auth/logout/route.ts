/**
 * Logout convenience route. Native HTML forms only support GET/POST, so we
 * expose this as a POST endpoint that clears the cookie. The DELETE method
 * on /api/auth is still available for programmatic callers (curl, fetch).
 */
import { NextResponse, type NextRequest } from 'next/server';
import { clearAdminToken } from '@/lib/auth/cookies';

export async function POST(request: NextRequest): Promise<NextResponse> {
  clearAdminToken();
  return NextResponse.redirect(new URL('/admin/login', request.url), 303);
}
