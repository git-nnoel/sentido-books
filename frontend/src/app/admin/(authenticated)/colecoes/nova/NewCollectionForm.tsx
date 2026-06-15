'use client';

/**
 * Client island for creating a collection (frontend plan §16.3 F7).
 *
 * Two fields: título (required) + descrição (optional textarea). On submit the
 * FormData is handed to createCollectionAction, which redirects to the edit
 * screen on success or returns { ok: false, error } to render below the form.
 *
 * While the action is in flight the button reads "criando…".
 */
import { useState, useTransition } from 'react';
import { Button } from '@/components/brand/Button';
import { createCollectionAction } from './actions';

const inputClasses =
  'mt-3 w-full rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-md text-text-primary placeholder:font-display placeholder:italic placeholder:text-text-muted focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring';

const labelClasses =
  'font-body text-label uppercase tracking-[0.15em] text-text-muted';

export function NewCollectionForm() {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const data = new FormData(event.currentTarget);
    startTransition(async () => {
      // On success the action redirects and never returns; on failure it
      // returns { ok: false, error }.
      const result = await createCollectionAction(data);
      if (result && !result.ok) {
        setError(result.error);
      }
    });
  }

  return (
    <form onSubmit={onSubmit} className="mt-7 flex flex-col gap-7">
      {error ? (
        <p
          role="alert"
          aria-live="polite"
          className="rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-sm text-text-muted lowercase"
        >
          {error}
        </p>
      ) : null}

      <div>
        <label htmlFor="collection-title" className={labelClasses}>
          título
        </label>
        <input
          id="collection-title"
          name="title"
          type="text"
          required
          aria-required="true"
          autoComplete="off"
          className={inputClasses}
          placeholder="título da coleção"
        />
      </div>

      <div>
        <label htmlFor="collection-description" className={labelClasses}>
          descrição
        </label>
        <p className="mt-1 font-body text-body-sm text-text-muted lowercase">opcional</p>
        <textarea
          id="collection-description"
          name="description"
          rows={4}
          className={`${inputClasses} resize-y leading-relaxed`}
          placeholder="um eco que atravessa vários livros"
        />
      </div>

      <div className="flex flex-wrap items-center gap-4 pt-2">
        <Button type="submit" variant="primary" disabled={isPending}>
          {isPending ? 'criando…' : 'criar coleção'}
        </Button>
      </div>
    </form>
  );
}
