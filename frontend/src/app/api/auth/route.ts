/**
 * Admin auth route handler.
 *
 * POST   — sets the admin cookie (deferred validation per plan §9.2) and
 *          303-redirects to ?next or /admin.
 * DELETE — clears the cookie and 303-redirects to /admin/login.
 *
 * The form on /admin/login posts here with a native <form method="post">.
 * No client-side fetch, so the redirect is the response.
 */
import { NextResponse, type NextRequest } from 'next/server';
import { setAdminToken, clearAdminToken } from '@/lib/auth/cookies';

function resolveRedirect(request: NextRequest, target: string): URL {
  // Relative paths only — never honor an absolute URL provided as `next`.
  const safe = target.startsWith('/') && !target.startsWith('//') ? target : '/admin';

  // Build the absolute redirect URL from the Host header (what the browser
  // actually connected to) rather than request.url (what Next.js's dev
  // server thinks its hostname is). Without this, accessing the app via a
  // LAN IP — e.g. 192.168.x.x — produces a redirect back to localhost.
  // `x-forwarded-*` are honored when behind a proxy.
  const forwardedHost = request.headers.get('x-forwarded-host');
  const host = forwardedHost ?? request.headers.get('host');
  const protocol = request.headers.get('x-forwarded-proto') ?? 'http';
  const base = host ? `${protocol}://${host}` : request.url;
  return new URL(safe, base);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const contentType = request.headers.get('content-type') ?? '';

  let token: string | undefined;
  let next: string | undefined;

  if (contentType.includes('application/x-www-form-urlencoded') || contentType.includes('multipart/form-data')) {
    const form = await request.formData();
    const rawToken = form.get('token');
    const rawNext = form.get('next');
    token = typeof rawToken === 'string' ? rawToken : undefined;
    next = typeof rawNext === 'string' ? rawNext : undefined;
  } else {
    try {
      const body = (await request.json()) as { token?: unknown; next?: unknown };
      token = typeof body.token === 'string' ? body.token : undefined;
      next = typeof body.next === 'string' ? body.next : undefined;
    } catch {
      // empty body — treated as missing token below
    }
  }

  if (!token || token.trim().length === 0) {
    return NextResponse.json({ error: 'token vazio' }, { status: 400 });
  }

  setAdminToken(token.trim());

  const location = resolveRedirect(request, next ?? '/admin');
  // 303 See Other = "GET the Location"; the standard response to a form POST.
  return NextResponse.redirect(location, 303);
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  clearAdminToken();
  return NextResponse.redirect(resolveRedirect(request, '/admin/login'), 303);
}
