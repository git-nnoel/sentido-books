/**
 * Site-wide 404. Copy per voice §3.4.
 */
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PageColumn } from '@/components/layout/PageColumn';

export const metadata = {
  title: 'não encontrado — sentido',
};

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="flex flex-1 items-center justify-center">
        <PageColumn width="content" className="py-9">
          <div className="mx-auto max-w-prose text-center">
            <h1 className="font-display italic text-accent text-display-lg lowercase">
              esse livro ainda não vive aqui
            </h1>
            <p className="mt-5 font-body text-body-lg text-text-muted lowercase">
              talvez tenha sido recolhido. talvez ainda esteja sendo lido.
            </p>
            <p className="mt-8">
              <Link
                href="/"
                className="rounded-sm font-body text-body-md text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
              >
                voltar ao início
              </Link>
            </p>
          </div>
        </PageColumn>
      </main>

      <Footer />
    </div>
  );
}
