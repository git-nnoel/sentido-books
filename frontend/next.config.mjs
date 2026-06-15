/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    // Phase 0: covers come from external sources (Open Library + placeholder).
    // The `picsum.photos` entry is only used by the /dev/components showcase
    // and can be removed once real cover URLs land in Phase 1.
    remotePatterns: [
      { protocol: 'https', hostname: 'picsum.photos' },
      { protocol: 'https', hostname: 'covers.openlibrary.org' },
      { protocol: 'https', hostname: 'fastly.picsum.photos' },
      // Google Books fallback covers when Open Library doesn't have the ISBN.
      { protocol: 'http', hostname: 'books.google.com' },
      { protocol: 'https', hostname: 'books.google.com' },
      { protocol: 'https', hostname: 'books.googleusercontent.com' },
    ],
  },
};

export default nextConfig;
