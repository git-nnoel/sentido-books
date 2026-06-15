/**
 * Zod schemas mirroring backend-implementation-plan.md §5 (contract surface).
 *
 * This file is the single TS truth for the backend shapes. Any change to the
 * backend §5 contract propagates here in the same orchestrator pass
 * (frontend-implementation-plan.md F5).
 *
 * Naming convention (frontend plan §3.2): schemas are `XxxSchema`; the inferred
 * TS type is `Xxx = z.infer<typeof XxxSchema>`.
 *
 * Phase 0 only consumes: BookDetailSchema, AdminBookSchema, ErrorBodySchema.
 * The Author / Collection / Search schemas are shipped now so Phase 1 plugs in
 * cleanly without contract drift.
 */
import { z } from 'zod';

// ─────────────────────────────────────────────────────────────────────────────
// Emotional profile — 6 axes, 0–10 each, per backend §5.1 GET /v1/books/{slug}.
// ─────────────────────────────────────────────────────────────────────────────

export const EmotionalProfileSchema = z.object({
  anguish: z.number().min(0).max(10),
  melancholy: z.number().min(0).max(10),
  hope: z.number().min(0).max(10),
  violence: z.number().min(0).max(10),
  tenderness: z.number().min(0).max(10),
  strangeness: z.number().min(0).max(10),
});

export type EmotionalProfile = z.infer<typeof EmotionalProfileSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Search results — POST /v1/search response.
// ─────────────────────────────────────────────────────────────────────────────

export const SearchResultSchema = z.object({
  slug: z.string(),
  title: z.string(),
  author_name: z.string(),
  year_published: z.number().nullable(),
  cover_url: z.string().nullable(),
  resonance_line: z.string(),
  similarity: z.number(),
});

export type SearchResult = z.infer<typeof SearchResultSchema>;

export const SearchResponseSchema = z.object({
  query: z.string(),
  results: z.array(SearchResultSchema),
});

export type SearchResponse = z.infer<typeof SearchResponseSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Book detail — GET /v1/books/{slug}.
// ─────────────────────────────────────────────────────────────────────────────

export const RelatedBookSchema = z.object({
  slug: z.string(),
  title: z.string(),
  author_name: z.string(),
  year_published: z.number().nullable(),
  cover_url: z.string().nullable(),
});

export type RelatedBook = z.infer<typeof RelatedBookSchema>;

export const EditionSchema = z.object({
  publisher: z.string().nullable(),
  language: z.string().nullable(),
  year: z.number().nullable(),
  isbn: z.string().nullable(),
});

export type Edition = z.infer<typeof EditionSchema>;

export const NarrativePaceSchema = z.enum(['slow', 'progressive', 'frenetic']);

export type NarrativePace = z.infer<typeof NarrativePaceSchema>;

export const BookAuthorSummarySchema = z.object({
  slug: z.string(),
  name: z.string(),
});

export type BookAuthorSummary = z.infer<typeof BookAuthorSummarySchema>;

export const BookDetailSchema = z.object({
  slug: z.string(),
  title: z.string(),
  original_title: z.string().nullable(),
  year_published: z.number().nullable(),
  author: BookAuthorSummarySchema,
  synopsis: z.string().nullable(),
  emotional_profile: EmotionalProfileSchema.nullable(),
  atmosphere_tags: z.array(z.string()),
  narrative_pace: NarrativePaceSchema.nullable(),
  cover_url: z.string().nullable(),
  editions: z.array(EditionSchema),
  related_books: z.array(RelatedBookSchema),
});

export type BookDetail = z.infer<typeof BookDetailSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Author detail — GET /v1/authors/{slug}. Phase 1 surface; shipped now so the
// frontend contract is complete.
// ─────────────────────────────────────────────────────────────────────────────

export const AuthorBookSummarySchema = z.object({
  slug: z.string(),
  title: z.string(),
  cover_url: z.string().nullable(),
  year_published: z.number().nullable(),
});

export type AuthorBookSummary = z.infer<typeof AuthorBookSummarySchema>;

export const AuthorDetailSchema = z.object({
  slug: z.string(),
  name: z.string(),
  bio: z.string().nullable(),
  books: z.array(AuthorBookSummarySchema),
});

export type AuthorDetail = z.infer<typeof AuthorDetailSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Collections — GET /v1/collections and /v1/collections/{slug}. Phase 1
// surface; shipped now for contract completeness.
// ─────────────────────────────────────────────────────────────────────────────

export const CollectionSummarySchema = z.object({
  slug: z.string(),
  title: z.string(),
  description: z.string().nullable(),
});

export type CollectionSummary = z.infer<typeof CollectionSummarySchema>;

export const CollectionListResponseSchema = z.object({
  collections: z.array(CollectionSummarySchema),
});

export type CollectionListResponse = z.infer<typeof CollectionListResponseSchema>;

export const CollectionDetailSchema = CollectionSummarySchema.extend({
  books: z.array(RelatedBookSchema),
});

export type CollectionDetail = z.infer<typeof CollectionDetailSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Admin book — admin endpoints return BookDetail plus six extra fields.
// Per backend §5.2 "the admin book shape".
// ─────────────────────────────────────────────────────────────────────────────

export const EmbeddingStatusSchema = z.enum(['pending', 'done']);
export const ProfileStatusSchema = z.enum(['pending', 'approved', 'rejected']);

export type EmbeddingStatus = z.infer<typeof EmbeddingStatusSchema>;
export type ProfileStatus = z.infer<typeof ProfileStatusSchema>;

export const AdminBookSchema = BookDetailSchema.extend({
  id: z.string().uuid(),
  embedding_status: EmbeddingStatusSchema,
  profile_status: ProfileStatusSchema,
  published: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type AdminBook = z.infer<typeof AdminBookSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Health — GET /v1/health.
// ─────────────────────────────────────────────────────────────────────────────

export const HealthResponseSchema = z.object({
  status: z.string(),
  version: z.string(),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Error body — backend errors are always `{"detail": "..."}` per §5.
// ─────────────────────────────────────────────────────────────────────────────

export const ErrorBodySchema = z.object({
  detail: z.string(),
});

export type ErrorBody = z.infer<typeof ErrorBodySchema>;
