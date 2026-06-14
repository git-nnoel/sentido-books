import { clsx } from '@/lib/clsx';

type WordmarkProps = {
  variant?: 'header' | 'footer';
  className?: string;
};

/**
 * The product name "sentido" in display italic.
 * Per brand/components.md §1 and §1.1.
 *
 * Always lowercase. Never paired with a logo mark — the wordmark IS the logo.
 */
export function Wordmark({ variant = 'header', className }: WordmarkProps) {
  const variantClasses =
    variant === 'header'
      ? 'font-display italic text-accent text-title-md md:text-title-lg lowercase'
      : 'font-display italic text-text-muted text-body-sm lowercase';

  return (
    <span className={clsx(variantClasses, className)} style={{ fontWeight: 500 }}>
      sentido
    </span>
  );
}
