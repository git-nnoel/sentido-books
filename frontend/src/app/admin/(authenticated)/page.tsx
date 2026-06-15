import { redirect } from 'next/navigation';

/**
 * Phase 0 admin landing — there is no queue table yet, so we send curators
 * straight to the ingest form. Phase 1 replaces this with the
 * `?status=pending_generation` queue.
 */
export default function AdminIndexPage() {
  redirect('/admin/novo');
}
