/**
 * Admin shell — server component that gates the authenticated portion of
 * the admin tree. /admin/login lives OUTSIDE this route group so it
 * bypasses this guard.
 *
 * Phase 0 reuses the public Header + Footer. A dedicated admin header lands
 * with the queue tables in Phase 1.
 */
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';
import { LogoutButton } from '@/components/admin/LogoutButton';
import { requireAdminToken } from '@/lib/auth/guard';
import { AdminNav } from './AdminNav';

export const metadata = {
  robots: { index: false, follow: false },
};

export default function AdminAuthenticatedLayout({ children }: { children: React.ReactNode }) {
  // Phase 0 doesn't have middleware exposing the current URL to the layout,
  // so the guard's redirect lands the curator on /admin after login. Server
  // actions that catch a backend 401 build their own `?next=` from the page
  // they're called from.
  requireAdminToken('/admin');

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="wide" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <AdminNav />
            <LogoutButton />
          </div>
          <div className="mt-5">{children}</div>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
