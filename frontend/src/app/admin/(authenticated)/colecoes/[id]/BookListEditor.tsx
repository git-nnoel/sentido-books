'use client';

/**
 * Book-list editor (frontend plan §16.3 F7, section 2 — "the interesting part").
 *
 * Owns local state for the ordered book array. Curators reorder with move
 * up/down buttons (decision F9 — no drag-and-drop), remove books, and add new
 * ones via a substring picker over the admin catalog. The full ordered list is
 * sent on save (decision F10 — replace semantics).
 *
 * The add-book picker fetches the catalog once via a server action
 * (listPickerBooksAction) because listAdminBooks is server-only and the bearer
 * token must stay server-side.
 *
 * Thumbnails: BookCover's smallest size is `sm` (64×96) and the spec asks for
 * an `xs`-scale thumbnail without adding a new BookCover size — so each row
 * uses a plain 40×60 fallback tile in the accent color.
 */
import { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { Button } from '@/components/brand/Button';
import { clsx } from '@/lib/clsx';
import type { AdminCollectionBook } from '@/lib/api/types';
import {
  listPickerBooksAction,
  type ActionResult,
  type PickerBook,
} from './actions';

type ReplaceBooksAction = (formData: FormData) => Promise<ActionResult>;

type BookListEditorProps = {
  initialBooks: AdminCollectionBook[];
  collectionId: string;
  action: ReplaceBooksAction;
};

const MAX_PICKER_RESULTS = 8;

/** Accent-insensitive, case-insensitive normalization for the picker filter. */
function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '');
}

export function BookListEditor({ initialBooks, collectionId, action }: BookListEditorProps) {
  const [books, setBooks] = useState<AdminCollectionBook[]>(initialBooks);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isPending, startTransition] = useTransition();

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= books.length) return;
    setSaved(false);
    setBooks((current) => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function remove(id: string) {
    setSaved(false);
    setBooks((current) => current.filter((book) => book.id !== id));
  }

  function add(book: PickerBook) {
    setSaved(false);
    setBooks((current) => [
      ...current,
      {
        id: book.id,
        slug: book.slug,
        title: book.title,
        author_name: book.author_name,
        published: book.published,
        position: current.length,
      },
    ]);
  }

  function onSave() {
    setError(null);
    setSaved(false);
    const data = new FormData();
    for (const book of books) {
      data.append('book_id', book.id);
    }
    startTransition(async () => {
      const result = await action(data);
      if (result.ok) {
        // The save sent exactly this ordered list (replace semantics, F10), so
        // local state is already authoritative — just renumber positions to
        // mirror what the backend persisted.
        setBooks((current) => current.map((book, index) => ({ ...book, position: index })));
        setSaved(true);
      } else {
        setError(`não foi possível salvar. ${result.error}`);
      }
    });
  }

  const selectedIds = useMemo(() => new Set(books.map((book) => book.id)), [books]);

  return (
    <div className="flex flex-col gap-6">
      {error ? (
        <p
          role="alert"
          aria-live="polite"
          className="rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-sm text-text-muted lowercase"
        >
          {error}
        </p>
      ) : null}

      {books.length === 0 ? (
        <p className="font-body italic text-body-md text-text-muted lowercase">
          nenhum livro nesta coleção ainda
        </p>
      ) : (
        <ul className="flex flex-col">
          {books.map((book, index) => (
            <li
              key={book.id}
              className="flex items-center gap-4 border-b border-divider/60 py-4"
            >
              <Thumbnail title={book.title} />

              <div className="min-w-0 flex-1">
                <p className="truncate font-body text-body-md text-text-primary">
                  {book.title}
                  {!book.published ? (
                    <span className="ml-2 font-body text-body-sm text-text-muted lowercase">
                      (rascunho)
                    </span>
                  ) : null}
                </p>
                <p className="truncate font-body italic text-body-sm text-text-muted">
                  {book.author_name}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => move(index, -1)}
                  disabled={index === 0}
                  className="px-3 py-2"
                >
                  <span aria-hidden="true">↑</span>
                  <span className="sr-only">mover para cima</span>
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => move(index, 1)}
                  disabled={index === books.length - 1}
                  className="px-3 py-2"
                >
                  <span aria-hidden="true">↓</span>
                  <span className="sr-only">mover para baixo</span>
                </Button>
                <button
                  type="button"
                  onClick={() => remove(book.id)}
                  className="rounded-sm font-body text-body-sm text-text-muted underline-offset-4 transition-colors duration-fast ease-standard hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
                >
                  remover
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <AddBookPicker selectedIds={selectedIds} onAdd={add} />

      <div className="flex flex-wrap items-center gap-4 pt-2">
        <Button type="button" variant="primary" onClick={onSave} disabled={isPending}>
          {isPending ? 'salvando…' : 'salvar ordem'}
        </Button>
        {saved ? (
          <span
            role="status"
            aria-live="polite"
            className="font-body text-body-sm text-text-muted lowercase"
          >
            salvo
          </span>
        ) : null}
      </div>
    </div>
  );
}

/** Plain 40×60 accent tile standing in for an xs-scale cover (see file note). */
function Thumbnail({ title }: { title: string }) {
  const letter = title.trim().match(/\p{L}/u)?.[0]?.toUpperCase() ?? '?';
  return (
    <div
      aria-hidden="true"
      className="flex h-[60px] w-[40px] shrink-0 items-center justify-center rounded-sm border border-divider bg-elevated font-display text-title-md text-accent"
    >
      {letter}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Add-book picker — substring filter over the admin catalog. Fetches once on
// mount via the server action; books already selected are excluded.
// ─────────────────────────────────────────────────────────────────────────────

function AddBookPicker({
  selectedIds,
  onAdd,
}: {
  selectedIds: Set<string>;
  onAdd: (book: PickerBook) => void;
}) {
  const [catalog, setCatalog] = useState<PickerBook[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    listPickerBooksAction().then((result) => {
      if (!active) return;
      if (result.ok) {
        setCatalog(result.books);
      } else {
        setLoadError(true);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  // Close the dropdown on outside click.
  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const matches = useMemo(() => {
    const q = normalize(query.trim());
    if (q.length === 0) return [];
    return catalog
      .filter((book) => !selectedIds.has(book.id))
      .filter((book) => normalize(book.title).includes(q))
      .slice(0, MAX_PICKER_RESULTS);
  }, [query, catalog, selectedIds]);

  return (
    <div ref={containerRef} className="relative">
      <label
        htmlFor="add-book-input"
        className="font-body text-label uppercase tracking-[0.15em] text-text-muted"
      >
        adicionar livro
      </label>
      <input
        id="add-book-input"
        type="text"
        value={query}
        autoComplete="off"
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="filtrar por título"
        className="mt-3 w-full rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-md text-text-primary placeholder:font-display placeholder:italic placeholder:text-text-muted focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
      />

      {loadError ? (
        <p className="mt-2 font-body text-body-sm text-text-muted lowercase">
          não foi possível carregar o catálogo. recarregue a página.
        </p>
      ) : null}

      {open && matches.length > 0 ? (
        <ul className="absolute left-0 right-0 z-10 mt-1 max-h-80 overflow-y-auto rounded-md border border-divider bg-elevated shadow-cover">
          {matches.map((book) => (
            <li key={book.id}>
              <button
                type="button"
                onClick={() => {
                  onAdd(book);
                  setQuery('');
                  setOpen(false);
                }}
                className={clsx(
                  'flex w-full items-baseline gap-2 px-4 py-3 text-left font-body text-body-md text-text-primary',
                  'transition-colors duration-fast ease-standard hover:bg-canvas focus-visible:outline-none focus-visible:bg-canvas',
                )}
              >
                <span className="truncate">{book.title}</span>
                <span className="shrink-0 font-body italic text-body-sm text-text-muted">
                  {book.author_name}
                </span>
                {!book.published ? (
                  <span className="shrink-0 font-body text-body-sm text-text-muted lowercase">
                    (rascunho)
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
