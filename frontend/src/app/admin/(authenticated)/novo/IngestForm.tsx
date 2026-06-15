'use client';

/**
 * Client island for the ISBN ingest form.
 *
 * Uses React's `useFormState` (returned as a hook in 18.3 via the
 * `react-dom` form actions API) to surface server-action errors back to the
 * UI without a page-level fetch dance. On success, the action redirects
 * server-side — this component never sees the success state directly; the
 * page reads ?ok=... and renders the success block.
 */
import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/brand/Button';
import { ingestAction, type IngestFormState } from './actions';

const initialState: IngestFormState = { error: null };

export function IngestForm() {
  const [state, formAction] = useFormState(ingestAction, initialState);

  return (
    <form action={formAction} className="mt-7 flex flex-col gap-5">
      <div>
        <label
          htmlFor="isbn-input"
          className="font-body text-label uppercase tracking-[0.15em] text-text-muted"
        >
          ISBN
        </label>
        <input
          id="isbn-input"
          name="isbn"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          required
          className="mt-3 w-full rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-md text-text-primary placeholder:font-display placeholder:italic placeholder:text-text-muted focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          placeholder="isbn"
        />
      </div>

      {state.error ? (
        <p
          role="alert"
          aria-live="polite"
          className="font-body text-body-sm text-text-muted lowercase"
        >
          {state.error}
        </p>
      ) : null}

      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" variant="primary" disabled={pending}>
      {pending ? 'adicionando livro…' : 'adicionar livro'}
    </Button>
  );
}
