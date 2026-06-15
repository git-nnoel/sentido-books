/**
 * Admin login.
 *
 * Single password input that posts to /api/auth via a native HTML form.
 * No react-hook-form, no client-side validation library — one field doesn't
 * earn the weight.
 *
 * The page lives at app/admin/login/ outside the authenticated route group
 * (app/admin/(authenticated)/...) so it bypasses the requireAdminToken
 * guard in the group's layout.
 *
 * Search params:
 *   ?next=...    — preserved across the post so the curator lands back on
 *                  the page they originally requested.
 *   ?error=...   — token-invalid message after the backend 401s on first
 *                  real action. Copy follows voice §3.4 register.
 */
import { Button } from '@/components/brand/Button';
import { PageColumn } from '@/components/layout/PageColumn';

export const metadata = {
  title: 'entrar como curador — sentido',
  robots: { index: false, follow: false },
};

type SearchParams = {
  next?: string | string[];
  error?: string | string[];
};

function firstString(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export default function AdminLoginPage({ searchParams }: { searchParams: SearchParams }) {
  const next = firstString(searchParams.next);
  const error = firstString(searchParams.error);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-canvas py-8">
      <PageColumn width="content">
        <div className="mx-auto w-full max-w-sm">
          <h1 className="font-display italic text-accent text-display-md lowercase">
            entrar como curador
          </h1>

          {error ? (
            <p
              role="alert"
              aria-live="polite"
              className="mt-5 font-body text-body-sm text-text-muted lowercase"
            >
              token inválido — confira e tente de novo.
            </p>
          ) : null}

          <form method="POST" action="/api/auth" className="mt-7 flex flex-col gap-5">
            {next ? <input type="hidden" name="next" value={next} /> : null}

            <div>
              <label
                htmlFor="admin-token"
                className="font-body text-label uppercase tracking-[0.15em] text-text-muted"
              >
                TOKEN
              </label>
              <input
                id="admin-token"
                name="token"
                type="password"
                autoComplete="current-password"
                required
                className="mt-3 w-full rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-md text-text-primary placeholder:font-display placeholder:italic placeholder:text-text-muted focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                placeholder="token"
              />
            </div>

            <Button type="submit" variant="primary">
              entrar
            </Button>
          </form>
        </div>
      </PageColumn>
    </main>
  );
}
