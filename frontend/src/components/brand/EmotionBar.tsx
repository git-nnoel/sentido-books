'use client';

/**
 * Per brand/components.md §3.
 *
 * Three-column grid: [label] [track] [value]. The track's fill width
 * animates from 0 to (value/10)*100% on first viewport entry, using an
 * IntersectionObserver. Animates once; never re-animates on re-entry.
 *
 * `prefers-reduced-motion: reduce` skips the animation — the fill renders
 * at its final width immediately.
 *
 * Numeric values are always rendered with one decimal: `6.0`, `8.5`, `1.0`.
 * Never percentages; never integers.
 */
import { useEffect, useRef, useState } from 'react';
import { clsx } from '@/lib/clsx';

type EmotionBarProps = {
  label: string;
  value: number;
  className?: string;
};

export function EmotionBar({ label, value, className }: EmotionBarProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    // Respect prefers-reduced-motion: render at final width immediately.
    if (typeof window !== 'undefined') {
      const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      if (reduceMotion) {
        setRevealed(true);
        return;
      }
    }

    const node = containerRef.current;
    if (!node) return;

    // IntersectionObserver might not exist in older test runners — fall back
    // to immediate reveal in that case.
    if (typeof IntersectionObserver === 'undefined') {
      setRevealed(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setRevealed(true);
            observer.disconnect();
            break;
          }
        }
      },
      { threshold: 0.2 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const clamped = Math.max(0, Math.min(10, value));
  const targetWidth = `${(clamped / 10) * 100}%`;

  return (
    <div
      ref={containerRef}
      className={clsx(
        'grid grid-cols-[6rem_1fr_2.5rem] items-center gap-4 md:grid-cols-[7rem_1fr_2.5rem]',
        className,
      )}
    >
      <span className="text-right font-body text-body-sm text-text-primary md:text-body-md lowercase">
        {label}
      </span>

      <div className="relative h-[2px] w-full rounded-full bg-divider">
        <div
          // Inline width because the value is data-driven; the transition is
          // declared via Tailwind so the animation timing comes from tokens.
          style={{ width: revealed ? targetWidth : '0%' }}
          className="h-full rounded-full bg-gradient-to-r from-accent-dim to-accent transition-[width] duration-glacial ease-entry"
        />
      </div>

      <span className="text-right font-body text-body-sm text-text-muted">{clamped.toFixed(1)}</span>
    </div>
  );
}
