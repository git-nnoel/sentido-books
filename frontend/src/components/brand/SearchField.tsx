'use client';

/**
 * Per brand/components.md §9.
 *
 * Controlled search input. On Enter (form submit), navigates to
 * /buscar?q={encoded}. Empty submissions do nothing — no error state per §9.
 *
 * Used in two contexts:
 *   - home page: `initialValue` omitted, empty input.
 *   - /buscar page: `initialValue={q}` so the input echoes the active query.
 *
 * Icon: the brand spec calls for a leading magnifier from the chosen icon
 * set (`lucide-react`). That dependency isn't installed in the MVP build,
 * so this component renders **without** a leading icon — the placeholder
 * carries the affordance ("o que você quer sentir?"). When `lucide-react`
 * lands in Phase 2 (or sooner if an icon set is approved), drop a 20px
 * magnifier into the existing left-padding slot — the markup already
 * reserves the space.
 *
 * Mobile has no visible submit button; pressing Enter submits the form.
 * Desktop submission also happens via Enter.
 */
import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { clsx } from '@/lib/clsx';

type SearchFieldProps = {
  initialValue?: string;
  className?: string;
};

export function SearchField({ initialValue = '', className }: SearchFieldProps) {
  const router = useRouter();
  const [value, setValue] = useState(initialValue);
  const [, startTransition] = useTransition();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (trimmed.length === 0) return;
    startTransition(() => {
      router.push(`/buscar?q=${encodeURIComponent(trimmed)}`);
    });
  }

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className={clsx('w-full max-w-prose mx-auto', className)}
    >
      <label htmlFor="sentido-search" className="sr-only">
        buscar livros por sensação, atmosfera ou eco
      </label>
      <input
        id="sentido-search"
        type="search"
        name="q"
        autoComplete="off"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="o que você quer sentir?"
        className={clsx(
          // Layout — 56px tall, padding to align with the brand spec
          'block w-full h-14 rounded-md px-5',
          // Surface
          'bg-elevated border border-divider',
          // Typography — input text in body font; placeholder in display italic muted
          'font-body text-body-lg text-text-primary',
          'placeholder:font-display placeholder:italic placeholder:text-text-muted',
          'lowercase',
          // Focus state — accent border + halo
          'transition-colors duration-fast ease-standard',
          'focus:border-accent focus:outline-none',
          'focus-visible:ring-2 focus-visible:ring-focus-ring',
        )}
      />
    </form>
  );
}
