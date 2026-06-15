'use client';

/**
 * Client island that wraps a single-button server-action call.
 *
 * Used by the editor page for:
 *   - "gerar perfil emocional" (regenerate=false)
 *   - "regerar perfil" (regenerate=true, with confirm())
 *
 * The action is passed in already-bound to the bookId — the parent (a
 * server component) does the binding so this island stays generic.
 */
import { useState, useTransition } from 'react';
import { Button } from '@/components/brand/Button';

type GenerateButtonProps = {
  action: () => Promise<{ ok: true } | { ok: false; error: string }>;
  label: string;
  pendingLabel: string;
  variant?: 'primary' | 'ghost';
  confirmCopy?: string;
};

export function GenerateButton({
  action,
  label,
  pendingLabel,
  variant = 'primary',
  confirmCopy,
}: GenerateButtonProps) {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const onClick = () => {
    if (confirmCopy && !window.confirm(confirmCopy)) return;
    setError(null);
    startTransition(async () => {
      const result = await action();
      if (!result.ok) {
        setError(`não foi possível concluir. ${result.error}`);
      }
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <Button variant={variant} onClick={onClick} disabled={isPending}>
        {isPending ? pendingLabel : label}
      </Button>
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
