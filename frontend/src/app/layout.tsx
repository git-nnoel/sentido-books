import type { Metadata } from 'next';
import { Cormorant_Garamond, Spectral } from 'next/font/google';
import './globals.css';

const display = Cormorant_Garamond({
  subsets: ['latin', 'latin-ext'],
  weight: ['300', '400', '500'],
  style: ['normal', 'italic'],
  variable: '--font-display',
  display: 'swap',
});

const body = Spectral({
  subsets: ['latin', 'latin-ext'],
  weight: ['300', '400', '500', '600'],
  style: ['normal', 'italic'],
  variable: '--font-body',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'sentido — um catálogo afetivo de livros',
  description: 'um catálogo afetivo de livros',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${display.variable} ${body.variable}`}>
      <body className="bg-canvas text-text-primary font-body">{children}</body>
    </html>
  );
}
