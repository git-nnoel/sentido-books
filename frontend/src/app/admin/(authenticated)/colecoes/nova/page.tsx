/**
 * Create-collection screen (frontend plan §16.3 F7).
 *
 * Server Component shell + the NewCollectionForm client island. The form posts
 * to createCollectionAction, which redirects to the edit screen on success.
 */
import Link from 'next/link';
import { SectionLabel } from '@/components/brand/SectionLabel';
import { HairlineDivider } from '@/components/brand/HairlineDivider';
import { NewCollectionForm } from './NewCollectionForm';

export const metadata = {
  title: 'nova coleção — sentido admin',
  robots: { index: false, follow: false },
};

export default function NewCollectionPage() {
  return (
    <div className="mx-auto w-full max-w-content">
      <SectionLabel>NOVA COLEÇÃO</SectionLabel>
      <h1 className="mt-3 font-display text-text-primary text-display-md lowercase">
        nova coleção
      </h1>
      <p className="mt-2 max-w-prose font-body text-body-md text-text-muted lowercase">
        dê um título e, se quiser, uma descrição. os livros entram depois, na edição.
      </p>

      <NewCollectionForm />

      <HairlineDivider />

      <Link
        href="/admin/colecoes"
        className="rounded-sm font-body text-body-sm text-text-muted underline-offset-4 hover:text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lowercase"
      >
        ← voltar às coleções
      </Link>
    </div>
  );
}
