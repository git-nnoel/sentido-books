/**
 * Admin queue — the landing page of the authenticated admin area.
 *
 * Server Component. Lists books filtered by curation status (tabs):
 *
 *   pending_generation → just-ingested books waiting for LLM artifacts
 *   pending_approval   → generated but not yet approved/published
 *   published          → live on the public catalog
 *   all                → no filter
 *
 * Each row links to /admin/livro/{id} — the editor that drives the rest of
 * the workflow (generate → approve → publish).
 *
 * 401 from the backend → clear cookie + redirect to login (deferred
 * validation, plan §9.2). Other backend errors propagate to error.tsx.
 *
 * No client-side state — switching tabs is a `<Link>` to the same path with
 * a different `?status=` query, which the server re-fetches.
 */
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { listAdminBooks } from '@/lib/api/admin';
import { ApiError } from '@/lib/api/client';
import { clearAdminToken } from '@/lib/auth/cookies';
import type { AdminBook, AdminBookListStatus } from '@/lib/api/types';
import { clsx } from '@/lib/clsx';

export const metadata = {
  title: 'painel — sentido admin',
  robots: { index: false, follow: false },
};

type SearchParams = {
  status?: string | string[];
};

const VALID_STATUSES: ReadonlyArray<AdminBookListStatus> = [
  'pending_generation',
  'pending_approval',
  'published',
  'all',
];

const STATUS_LABELS: Record<AdminBookListStatus, string> = {
  pending_generation: 'aguardando geração',
  pending_approval: 'aguardando aprovação',
  published: 'publicados',
  all: 'todos',
};

const STATUS_EMPTY_COPY: Record<AdminBookListStatus, string> = {
  pending_generation: 'nenhum livro aguardando geração.',
  pending_approval: 'nenhum livro aguardando aprovação.',
  published: 'nenhum livro publicado ainda.',
  all: 'o catálogo está vazio.',
};

function firstString(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function coerceStatus(raw: string | undefined): AdminBookListStatus {
  if (raw && (VALID_STATUSES as ReadonlyArray<string>).includes(raw)) {
    return raw as AdminBookListStatus;
  }
  return 'pending_generation';
}

export default async function AdminQueuePage({ searchParams }: { searchParams: SearchParams }) {
  const status = coerceStatus(firstString(searchParams.status));

  let books: AdminBook[];
  let total: number;
  try {
    const response = await listAdminBooks(status, 50, 0);
    books = response.books;
    total = response.total;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      clearAdminToken();
      redirect(
        `/admin/login?next=${encodeURIComponent('/admin')}&error=token%20inv%C3%A1lido`,
      );
    }
    throw err;
  }

  return (
    <div className="w-full">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <SectionLabel>ADMIN · PAINEL</SectionLabel>
          <h1 className="mt-3 font-display italic text-accent text-display-lg lowercase">
            curadoria
          </h1>
        </div>
        <Link
          href="/admin/novo"
          className="rounded-md border border-divider px-5 py-3 font-body font-medium text-body-md text-accent hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring transition-colors duration-fast ease-standard lowercase"
        >
          + adicionar livro
        </Link>
      </div>

      <nav aria-label="filtrar por estágio" className="mt-7">
        <ul className="flex flex-wrap gap-x-6 gap-y-2">
          {VALID_STATUSES.map((value) => {
            const active = value === status;
            return (
              <li key={value}>
                <Link
                  href={`/admin?status=${value}`}
                  aria-current={active ? 'page' : undefined}
                  className={clsx(
                    'rounded-sm font-body text-label uppercase tracking-[0.15em] transition-colors duration-fast ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring',
                    active
                      ? 'text-accent'
                      : 'text-text-muted hover:text-accent',
                  )}
                >
                  {STATUS_LABELS[value]}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <HairlineDivider />

      {books.length === 0 ? (
        <EmptyState status={status} />
      ) : (
        <>
          <p className="font-body text-body-sm text-text-muted lowercase">
            {`mostrando ${books.length} de ${total} ${total === 1 ? 'livro' : 'livros'}`}
          </p>
          <QueueTable books={books} />
        </>
      )}
    </div>
  );
}

function EmptyState({ status }: { status: AdminBookListStatus }) {
  return (
    <div className="py-7">
      <SectionLabel size="sm">VAZIO</SectionLabel>
      <p className="mt-3 font-body text-body-md text-text-muted lowercase">
        {STATUS_EMPTY_COPY[status]}
      </p>
    </div>
  );
}

function QueueTable({ books }: { books: AdminBook[] }) {
  return (
    <div className="mt-5 overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-divider">
            <th
              scope="col"
              className="py-3 pr-4 text-left font-body text-label uppercase tracking-[0.15em] text-text-muted"
            >
              título
            </th>
            <th
              scope="col"
              className="py-3 pr-4 text-left font-body text-label uppercase tracking-[0.15em] text-text-muted"
            >
              autor
            </th>
            <th
              scope="col"
              className="py-3 pr-4 text-left font-body text-label uppercase tracking-[0.15em] text-text-muted"
            >
              atualizado
            </th>
            <th
              scope="col"
              className="py-3 text-right font-body text-label uppercase tracking-[0.15em] text-text-muted"
            >
              <span className="sr-only">ações</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => (
            <tr
              key={book.id}
              className="border-b border-divider/60 transition-colors duration-fast ease-standard hover:bg-elevated"
            >
              <td className="py-4 pr-4 align-top">
                <Link
                  href={`/admin/livro/${book.id}`}
                  className="rounded-sm font-body text-body-md text-text-primary underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                >
                  {book.title}
                </Link>
              </td>
              <td className="py-4 pr-4 align-top font-body italic text-body-sm text-text-muted">
                {book.author.name}
              </td>
              <td className="py-4 pr-4 align-top font-body text-body-sm text-text-muted lowercase">
                {formatUpdatedAt(book.updated_at)}
              </td>
              <td className="py-4 align-top text-right">
                <Link
                  href={`/admin/livro/${book.id}`}
                  className="rounded-sm font-body text-body-sm text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
                >
                  abrir →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Formatting helpers — relative for ≤ 7 days, absolute date otherwise.
// PT-BR via Intl.
// ─────────────────────────────────────────────────────────────────────────────

const RELATIVE_FORMATTER = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' });
const ABSOLUTE_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

function formatUpdatedAt(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return iso;

  const diffMs = then.getTime() - Date.now();
  const absMs = Math.abs(diffMs);

  if (absMs > SEVEN_DAYS_MS) {
    return ABSOLUTE_FORMATTER.format(then);
  }

  // Pick the coarsest unit that gives a non-zero count.
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (absMs >= day) {
    return RELATIVE_FORMATTER.format(Math.round(diffMs / day), 'day');
  }
  if (absMs >= hour) {
    return RELATIVE_FORMATTER.format(Math.round(diffMs / hour), 'hour');
  }
  if (absMs >= minute) {
    return RELATIVE_FORMATTER.format(Math.round(diffMs / minute), 'minute');
  }
  return RELATIVE_FORMATTER.format(Math.round(diffMs / 1000), 'second');
}
