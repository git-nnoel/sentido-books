'use client';

import type { ReactNode } from 'react';
import { clsx } from '@/lib/clsx';

type ButtonVariant = 'primary' | 'ghost' | 'link';

type ButtonProps = {
  variant?: ButtonVariant;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
  onClick?: () => void;
  children: ReactNode;
  className?: string;
};

/**
 * Per brand/components.md §10.
 *
 * Buttons are rare in this product — most affordances are link-styled.
 *
 * Three variants:
 *   - primary: filled gold, the canonical CTA
 *   - ghost:   transparent with divider border, border lifts to accent on hover
 *   - link:    inline gold text, underline on hover
 *
 * Client component: this is the interactive form with `onClick`. Server-only
 * button-shaped affordances (links to other routes) can use a Next <Link>
 * directly rather than this component.
 */
export function Button({
  variant = 'primary',
  type = 'button',
  disabled = false,
  onClick,
  children,
  className,
}: ButtonProps) {
  const base =
    'font-body font-medium text-body-md transition-colors duration-fast ease-standard ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring';

  let variantClasses = '';
  switch (variant) {
    case 'primary':
      variantClasses =
        'bg-accent text-canvas hover:bg-accent-hover px-5 py-3 rounded-md ' +
        'disabled:bg-accent-dim disabled:cursor-not-allowed';
      break;
    case 'ghost':
      variantClasses =
        'bg-transparent border border-divider hover:border-accent text-accent ' +
        'px-5 py-3 rounded-md disabled:opacity-60 disabled:cursor-not-allowed';
      break;
    case 'link':
      variantClasses =
        'text-accent hover:underline underline-offset-4 rounded-sm ' +
        'disabled:text-accent-dim disabled:cursor-not-allowed disabled:no-underline';
      break;
  }

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={clsx(base, variantClasses, className)}
    >
      {children}
    </button>
  );
}
