import { clsx } from '@/lib/clsx';

type HairlineDividerProps = {
  className?: string;
};

/**
 * Per brand/components.md §5.
 *
 * Gold hairline at 20% opacity. 1px, full width of the content column.
 * Margins: 32px mobile / 48px desktop.
 *
 * Use sparingly — a divider marks a meaningful change in section, not
 * visual rhythm between every paragraph.
 */
export function HairlineDivider({ className }: HairlineDividerProps) {
  return (
    <hr className={clsx('w-full border-0 border-t border-divider my-6 md:my-7', className)} />
  );
}
