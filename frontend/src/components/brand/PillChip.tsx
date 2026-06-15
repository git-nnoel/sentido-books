import { clsx } from '@/lib/clsx';

/**
 * Per brand/components.md §2.
 *
 * Two variants:
 *   - static: atmosphere tags on the book page. No interactivity, no hover.
 *   - filter: browse-page filter chip. Filled background on active state.
 *
 * F3 only uses `static`. The `filter` variant is included for Phase 1 reuse
 * — server-renderable here since `active` is the only state-bearing prop.
 * Phase-1 browse pages will wrap an interactive chip in a client island
 * that toggles `active` and dispatches the filter change.
 *
 * Server Component by default — no `'use client'`.
 */

type PillChipProps = {
  label: string;
  variant?: 'static' | 'filter';
  active?: boolean;
  className?: string;
};

export function PillChip({ label, variant = 'static', active = false, className }: PillChipProps) {
  const base =
    'inline-flex items-center justify-center rounded-full px-3 py-2 font-body text-body-sm transition-colors duration-fast ease-standard';

  let variantClasses: string;
  if (variant === 'static') {
    variantClasses = 'border border-accent/40 bg-transparent text-accent';
  } else if (active) {
    // Filter chip, active state — filled bg, full accent border.
    variantClasses = 'border border-accent bg-accent/[0.16] text-accent-hover';
  } else {
    // Filter chip, idle — same as static but lifts on hover.
    variantClasses =
      'border border-accent/40 bg-transparent text-accent hover:bg-accent/[0.08] hover:border-accent';
  }

  return <span className={clsx(base, variantClasses, className)}>{label}</span>;
}
