/**
 * PT-BR labels and validation sets for the /explorar dimension navigation
 * (frontend plan §16.4). Shared between the landing page and the per-dimension
 * result pages so the axis/pace vocabulary stays in lockstep — no drift.
 *
 * The six emotion axes mirror EmotionalProfileSchema (lib/api/types.ts); the
 * three paces mirror NarrativePaceSchema.
 */
import type { NarrativePace } from './api/types';

export const EMOTION_AXES = [
  'anguish',
  'melancholy',
  'hope',
  'violence',
  'tenderness',
  'strangeness',
] as const;

export type EmotionAxis = (typeof EMOTION_AXES)[number];

export const EMOTION_LABELS: Record<EmotionAxis, string> = {
  anguish: 'angústia',
  melancholy: 'melancolia',
  hope: 'esperança',
  violence: 'violência',
  tenderness: 'ternura',
  strangeness: 'estranheza',
};

export function isEmotionAxis(value: string): value is EmotionAxis {
  return (EMOTION_AXES as readonly string[]).includes(value);
}

export const NARRATIVE_PACES = ['slow', 'progressive', 'frenetic'] as const;

export const PACE_LABELS: Record<NarrativePace, string> = {
  slow: 'lento',
  progressive: 'progressivo',
  frenetic: 'frenético',
};

export function isNarrativePace(value: string): value is NarrativePace {
  return (NARRATIVE_PACES as readonly string[]).includes(value);
}
