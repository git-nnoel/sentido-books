/**
 * Loading UI for the /buscar route — rendered while the Server Component
 * resolves the semantic-search request. Copy per voice §3.1.
 */
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

export default function SearchLoading() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex-1">
        <PageColumn width="wide" className="pt-7 md:pt-9 pb-8 md:pb-9">
          <div className="mx-auto max-w-prose text-center">
            <p className="font-body italic text-body-md text-text-muted lowercase">
              procurando uma ressonância…
            </p>
          </div>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
