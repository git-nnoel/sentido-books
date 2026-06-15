'use client';

/**
 * Danger-zone delete control (frontend plan §16.3 F7, section 3).
 *
 * Uses window.confirm for the destructive confirmation — admin-only and the
 * simplest accessible pattern for a one-off destructive confirm (no Radix
 * Dialog needed). On confirm, calls deleteCollectionAction (pre-bound with the
 * id by the parent), which deletes + revalidates + redirects to the queue.
 */
import { useState, useTransition } from 'react';
import { Button } from '@/components/brand/Button';
import type { ActionResult } from './actions';

type DeleteAction = () => Promise<ActionResult>;

export function DeleteCollectionButton({ action }: { action: DeleteAction }) {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function onClick() {
    if (!window.confirm('excluir esta coleção?')) return;
    setError(null);
    startTransition(async () => {
      // On success the action redirects and never returns; a returned result
      // means it failed.
      const result = await action();
      if (result && !result.ok) {
        setError(`não foi possível excluir. ${result.error}`);
      }
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <Button
          variant="ghost"
          onClick={onClick}
          disabled={isPending}
          className="text-text-muted hover:border-accent hover:text-accent"
        >
          {isPending ? 'excluindo…' : 'excluir coleção'}
        </Button>
      </div>
      {error ? (
        <p
          role="alert"
          aria-live="polite"
          className="font-body text-body-sm text-text-muted lowercase"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
