'use client';

/**
 * Collection metadata editor (frontend plan §16.3 F7, section 1).
 *
 * Fields: título (text), descrição (textarea, nullable), publicada (styled
 * checkbox). On submit the FormData is handed to updateCollectionAction, which
 * is pre-bound with the collection id by the parent server page
 * (`updateCollectionAction.bind(null, id)`).
 */
import { useState, useTransition } from 'react';
import { Button } from '@/components/brand/Button';
import type { AdminCollection } from '@/lib/api/types';

const inputClasses =
  'mt-3 w-full rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-md text-text-primary placeholder:font-display placeholder:italic placeholder:text-text-muted focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring';

const labelClasses =
  'font-body text-label uppercase tracking-[0.15em] text-text-muted';

type MetaFormAction = (formData: FormData) => Promise<{ ok: true } | { ok: false; error: string }>;

type CollectionMetaFormProps = {
  collection: AdminCollection;
  action: MetaFormAction;
};

export function CollectionMetaForm({ collection, action }: CollectionMetaFormProps) {
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isPending, startTransition] = useTransition();

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    const data = new FormData(event.currentTarget);
    startTransition(async () => {
      const result = await action(data);
      if (result.ok) {
        setSaved(true);
      } else {
        setError(`não foi possível salvar. ${result.error}`);
      }
    });
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-7">
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
          defaultValue={collection.title}
          className={inputClasses}
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
          defaultValue={collection.description ?? ''}
          className={`${inputClasses} resize-y leading-relaxed`}
        />
      </div>

      <label className="flex cursor-pointer items-center gap-3 font-body text-body-md text-text-primary lowercase">
        <input
          type="checkbox"
          name="published"
          defaultChecked={collection.published}
          className="h-4 w-4 rounded-sm accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        />
        publicada
      </label>

      <div className="flex flex-wrap items-center gap-4 pt-2">
        <Button type="submit" variant="primary" disabled={isPending}>
          {isPending ? 'salvando…' : 'salvar'}
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
    </form>
  );
}
