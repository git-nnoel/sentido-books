/**
 * Minimal className joiner — local helper to avoid a `clsx` dependency.
 * Filters out falsy values and joins with a space.
 */
export function clsx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}
