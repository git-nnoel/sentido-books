import Image from 'next/image';
import { clsx } from '@/lib/clsx';

type BookCoverSize = 'sm' | 'md' | 'lg' | 'xl' | 'hero' | 'hero-md';

type BookCoverProps = {
  src?: string | null;
  slug: string;
  title: string;
  size?: BookCoverSize;
  priority?: boolean;
  className?: string;
};

/**
 * Per brand/components.md §7.
 *
 * Books are posters. 2:3 always. Cover art is the only chromatic element
 * the system allows (foundations §1.2) — never overlay it.
 *
 * Source images that don't conform to 2:3 are letterboxed onto the canvas
 * color, never cropped or stretched.
 *
 * Default size is `md` (140×210, carousel).
 */

// Fixed-pixel size map (per components.md §7.2).
// `xl` (catalog mobile) uses a clamp width via inline style instead.
const FIXED_SIZES: Record<
  Exclude<BookCoverSize, 'xl'>,
  { width: number; height: number; sizes: string }
> = {
  sm: { width: 64, height: 96, sizes: '64px' },
  md: { width: 140, height: 210, sizes: '140px' },
  lg: { width: 200, height: 300, sizes: '200px' },
  hero: { width: 220, height: 330, sizes: '220px' },
  'hero-md': { width: 320, height: 480, sizes: '320px' },
};

// Deterministic muted palette for the embossed-letter fallback.
// Per components.md §7.4 — desaturated, low-luminance. Never vivid.
// Slug hashes (djb2-lite) to one of four gradients.
const FALLBACK_GRADIENTS = [
  'linear-gradient(135deg, #1a2e1a 0%, #0a1410 100%)', // deep-green
  'linear-gradient(135deg, #2a1414 0%, #100808 100%)', // oxblood
  'linear-gradient(135deg, #14202e 0%, #08101a 100%)', // slate-blue
  'linear-gradient(135deg, #1c1a18 0%, #0c0a08 100%)', // char-gray
] as const;

function pickGradient(slug: string): string {
  let hash = 5381;
  for (let i = 0; i < slug.length; i += 1) {
    hash = (hash * 33) ^ slug.charCodeAt(i);
  }
  const index = Math.abs(hash) % FALLBACK_GRADIENTS.length;
  return FALLBACK_GRADIENTS[index];
}

function firstLetter(title: string): string {
  const trimmed = title.trim();
  if (!trimmed) return '?';
  // grab the first letter, uppercase, ignoring punctuation
  const match = trimmed.match(/\p{L}/u);
  return (match ? match[0] : trimmed[0]).toUpperCase();
}

export function BookCover({
  src,
  slug,
  title,
  size = 'md',
  priority = false,
  className,
}: BookCoverProps) {
  // Container styling — 2:3 ratio, slight radius, the system's only shadow.
  // The `xl` size uses a fluid clamp for catalog mobile.
  const isFluid = size === 'xl';
  const containerStyle: React.CSSProperties = isFluid
    ? { width: 'clamp(140px, 42vw, 200px)' }
    : { width: `${FIXED_SIZES[size].width}px` };

  const hasImage = Boolean(src);

  return (
    <div
      className={clsx(
        'relative aspect-[2/3] overflow-hidden rounded-sm bg-canvas shadow-cover',
        className,
      )}
      // `containerType: size` lets the fallback letter scale with the cover via cqh units.
      style={{ ...containerStyle, containerType: 'size' }}
    >
      {hasImage ? (
        <Image
          src={src as string}
          alt={title}
          fill
          // `contain` letterboxes onto the canvas background; never crops or stretches.
          // The wrapping <div> has bg-canvas so the letterbox bars use the system color.
          className="object-contain"
          sizes={isFluid ? '(max-width: 640px) 42vw, 200px' : FIXED_SIZES[size].sizes}
          priority={priority}
        />
      ) : (
        <FallbackEmbossed slug={slug} title={title} />
      )}
    </div>
  );
}

/**
 * Fallback embossed-letter cover, per components.md §7.4.
 * The shadow treatment still applies (handled by the parent container).
 */
function FallbackEmbossed({ slug, title }: { slug: string; title: string }) {
  const gradient = pickGradient(slug);
  const letter = firstLetter(title);

  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 flex items-center justify-center"
      style={{ background: gradient }}
    >
      <span
        className="font-display select-none"
        style={{
          color: 'rgba(255, 255, 255, 0.06)',
          fontWeight: 300,
          // Scales with the cover height (parent has containerType: size).
          // 60% of container height keeps the embossed letter at the same
          // visual weight across sm (96px tall) through hero-md (480px tall).
          fontSize: '60cqh',
          lineHeight: 1,
          filter: 'blur(0.5px)',
        }}
      >
        {letter}
      </span>
    </div>
  );
}
