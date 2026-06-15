'use client';

/**
 * Client island for editing an admin book.
 *
 * Form state is owned by react-hook-form; the schema is mirrored in Zod so
 * validation, types, and the patch shape align. On submit, the form's
 * FormData is handed off to a server action (updateAction or publishAction)
 * — the action attaches the admin cookie server-side and revalidates the
 * page on success.
 *
 * The submit button label is parameterized so the parent (server) page can
 * pick the right wording for the curation state:
 *   - pending_approval → "aprovar e publicar"
 *   - published        → "salvar alterações"
 *
 * Voice conventions (docs/brand/voice.md) — lowercase labels, no
 * exclamations, sober error copy.
 */
import { useState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/brand/Button';
import { SectionLabel } from '@/components/brand/SectionLabel';
import type { AdminBook, NarrativePace } from '@/lib/api/types';

const EMOTION_KEYS = [
  'anguish',
  'melancholy',
  'hope',
  'violence',
  'tenderness',
  'strangeness',
] as const;

const EMOTION_LABELS: Record<(typeof EMOTION_KEYS)[number], string> = {
  anguish: 'angústia',
  melancholy: 'melancolia',
  hope: 'esperança',
  violence: 'violência',
  tenderness: 'ternura',
  strangeness: 'estranheza',
};

const PACE_OPTIONS: ReadonlyArray<{ value: NarrativePace; label: string }> = [
  { value: 'slow', label: 'lento' },
  { value: 'progressive', label: 'progressivo' },
  { value: 'frenetic', label: 'frenético' },
];

// ─────────────────────────────────────────────────────────────────────────────
// Schema — single source of truth for shape, validation, and types.
// ─────────────────────────────────────────────────────────────────────────────

const FormSchema = z.object({
  title: z.string().min(1, 'informe um título.'),
  original_title: z.string().nullable(),
  synopsis: z.string().min(1, 'informe uma sinopse.'),
  narrative_pace: z.enum(['slow', 'progressive', 'frenetic']),
  atmosphere_tags: z
    .string()
    .min(1, 'informe ao menos uma atmosfera.')
    .refine(
      (raw) => {
        const tags = raw
          .split(',')
          .map((t) => t.trim())
          .filter((t) => t.length > 0);
        return tags.length >= 1 && tags.length <= 5;
      },
      { message: 'use entre 1 e 5 termos, separados por vírgula.' },
    ),
  emotional_profile: z.object({
    anguish: z.number().min(0).max(10),
    melancholy: z.number().min(0).max(10),
    hope: z.number().min(0).max(10),
    violence: z.number().min(0).max(10),
    tenderness: z.number().min(0).max(10),
    strangeness: z.number().min(0).max(10),
  }),
  cover_url: z.string().url('use uma URL válida.').nullable(),
  year_published: z.number().int().nullable(),
});

type FormValues = z.infer<typeof FormSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Mapping — AdminBook ↔ FormValues
// ─────────────────────────────────────────────────────────────────────────────

function toFormValues(book: AdminBook): FormValues {
  const fallbackProfile = {
    anguish: 0,
    melancholy: 0,
    hope: 0,
    violence: 0,
    tenderness: 0,
    strangeness: 0,
  };
  return {
    title: book.title,
    original_title: book.original_title,
    synopsis: book.synopsis ?? '',
    narrative_pace: book.narrative_pace ?? 'progressive',
    atmosphere_tags: book.atmosphere_tags.join(', '),
    emotional_profile: book.emotional_profile ?? fallbackProfile,
    cover_url: book.cover_url,
    year_published: book.year_published,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The action receives only `formData` — the book id is pre-bound by the
 * parent server component (`publishAction.bind(null, book.id)`). This
 * lets Next.js's RSC layer serialize the action correctly across the
 * server/client boundary.
 */
export type EditFormAction = (formData: FormData) => Promise<{ ok: true } | { ok: false; error: string }>;

type EditFormProps = {
  book: AdminBook;
  action: EditFormAction;
  submitLabel: string;
  pendingLabel: string;
};

export function EditForm({ book, action, submitLabel, pendingLabel }: EditFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: toFormValues(book),
  });

  const [serverError, setServerError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const onSubmit = handleSubmit((values) => {
    setServerError(null);

    // Build FormData explicitly so the server action sees field names that
    // match buildPatch() in actions.ts.
    const data = new FormData();
    data.append('title', values.title);
    if (values.original_title !== null) data.append('original_title', values.original_title);
    data.append('synopsis', values.synopsis);
    data.append('narrative_pace', values.narrative_pace);
    data.append('atmosphere_tags', values.atmosphere_tags);
    for (const key of EMOTION_KEYS) {
      data.append(`emotional_profile.${key}`, String(values.emotional_profile[key]));
    }
    if (values.cover_url !== null) data.append('cover_url', values.cover_url);
    if (values.year_published !== null) {
      data.append('year_published', String(values.year_published));
    }

    startTransition(async () => {
      const result = await action(data);
      if (!result.ok) {
        setServerError(`não foi possível salvar. ${result.error}`);
      }
    });
  });

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-7">
      {serverError ? (
        <p
          role="alert"
          aria-live="polite"
          className="rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-sm text-text-muted lowercase"
        >
          {serverError}
        </p>
      ) : null}

      {/* Title */}
      <Field
        label="título"
        htmlFor="title"
        error={errors.title?.message}
      >
        <input
          id="title"
          type="text"
          className={inputClasses}
          {...register('title')}
        />
      </Field>

      {/* Original title */}
      <Field
        label="título original"
        htmlFor="original_title"
        error={errors.original_title?.message}
        hint="opcional"
      >
        <input
          id="original_title"
          type="text"
          className={inputClasses}
          {...register('original_title', {
            setValueAs: (v) => (typeof v === 'string' && v.trim().length === 0 ? null : v),
          })}
        />
      </Field>

      {/* Synopsis */}
      <Field
        label="sinopse"
        htmlFor="synopsis"
        error={errors.synopsis?.message}
      >
        <textarea
          id="synopsis"
          rows={6}
          className={`${inputClasses} resize-y leading-relaxed`}
          {...register('synopsis')}
        />
      </Field>

      {/* Atmosphere tags */}
      <Field
        label="atmosfera"
        htmlFor="atmosphere_tags"
        error={errors.atmosphere_tags?.message}
        hint="separadas por vírgula — entre 1 e 5 termos"
      >
        <input
          id="atmosphere_tags"
          type="text"
          className={inputClasses}
          {...register('atmosphere_tags')}
        />
      </Field>

      {/* Narrative pace */}
      <div>
        <SectionLabel size="sm">RITMO NARRATIVO</SectionLabel>
        <div
          role="radiogroup"
          aria-label="ritmo narrativo"
          className="mt-3 flex flex-wrap gap-5"
        >
          {PACE_OPTIONS.map((option) => (
            <label
              key={option.value}
              className="flex cursor-pointer items-center gap-2 font-body text-body-md text-text-primary lowercase"
            >
              <input
                type="radio"
                value={option.value}
                className="accent-accent"
                {...register('narrative_pace')}
              />
              {option.label}
            </label>
          ))}
        </div>
        {errors.narrative_pace ? (
          <p className="mt-2 font-body text-body-sm text-text-muted lowercase">
            {errors.narrative_pace.message}
          </p>
        ) : null}
      </div>

      {/* Emotional profile */}
      <div>
        <SectionLabel size="sm">PERFIL EMOCIONAL</SectionLabel>
        <p className="mt-2 font-body text-body-sm text-text-muted lowercase">
          escala de 0 a 10 — uma casa decimal
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {EMOTION_KEYS.map((key) => (
            <Field
              key={key}
              label={EMOTION_LABELS[key]}
              htmlFor={`emotional_profile.${key}`}
              error={errors.emotional_profile?.[key]?.message}
            >
              <input
                id={`emotional_profile.${key}`}
                type="number"
                step="0.1"
                min={0}
                max={10}
                className={inputClasses}
                {...register(`emotional_profile.${key}` as const, {
                  valueAsNumber: true,
                })}
              />
            </Field>
          ))}
        </div>
      </div>

      {/* Cover URL */}
      <Field
        label="capa (URL)"
        htmlFor="cover_url"
        error={errors.cover_url?.message}
        hint="opcional"
      >
        <input
          id="cover_url"
          type="url"
          className={inputClasses}
          {...register('cover_url', {
            setValueAs: (v) => (typeof v === 'string' && v.trim().length === 0 ? null : v),
          })}
        />
      </Field>

      {/* Year */}
      <Field
        label="ano de publicação"
        htmlFor="year_published"
        error={errors.year_published?.message}
        hint="opcional"
      >
        <input
          id="year_published"
          type="number"
          className={inputClasses}
          {...register('year_published', {
            setValueAs: (v) => {
              if (typeof v !== 'string' || v.trim().length === 0) return null;
              const parsed = Number(v);
              return Number.isFinite(parsed) ? parsed : null;
            },
          })}
        />
      </Field>

      <div className="flex flex-wrap items-center gap-4 pt-2">
        <Button type="submit" variant="primary" disabled={isPending}>
          {isPending ? pendingLabel : submitLabel}
        </Button>
      </div>
    </form>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared field shell + input class — consistent label + error rhythm.
// ─────────────────────────────────────────────────────────────────────────────

const inputClasses =
  'mt-3 w-full rounded-md border border-divider bg-elevated px-4 py-3 font-body text-body-md text-text-primary placeholder:font-display placeholder:italic placeholder:text-text-muted focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring';

type FieldProps = {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
};

function Field({ label, htmlFor, error, hint, children }: FieldProps) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="font-body text-label uppercase tracking-[0.15em] text-text-muted"
      >
        {label}
      </label>
      {hint ? (
        <p className="mt-1 font-body text-body-sm text-text-muted lowercase">{hint}</p>
      ) : null}
      {children}
      {error ? (
        <p
          role="alert"
          className="mt-2 font-body text-body-sm text-text-muted lowercase"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
