import type { ReactNode } from 'react';
import { clsx } from '@/lib/clsx';

type SectionLabelProps = {
  children: ReactNode;
  size?: 'default' | 'sm';
  className?: string;
};

/**
 * Per brand/components.md §4.
 *
 * The uppercase letter-spaced text that introduces a section
 * (`PERFIL EMOCIONAL`, `SINOPSE`).
 *
 * Rendered as a <div>, not a heading — these are UI labels, not semantic
 * headers. Pages still use proper <h*> tags for content titles.
 */
export function SectionLabel({ children, size = 'default', className }: SectionLabelProps) {
  const sizeClasses =
    size === 'sm'
      ? 'text-label-sm uppercase tracking-[0.18em] text-text-muted'
      : 'text-label uppercase tracking-[0.15em] text-text-muted';

  return <div className={clsx('font-body', sizeClasses, className)}>{children}</div>;
}
