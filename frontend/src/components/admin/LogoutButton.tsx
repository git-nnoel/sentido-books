/**
 * Logout affordance — a native HTML form posting to /api/auth/logout, which
 * clears the cookie and redirects to /admin/login.
 *
 * Server component — no interactivity beyond the form post.
 *
 * Rendered as a text link to match the brand's preference for link-styled
 * affordances (components.md §10).
 */
export function LogoutButton() {
  return (
    <form action="/api/auth/logout" method="POST" className="inline">
      <button
        type="submit"
        className="rounded-sm font-body text-body-sm text-text-muted hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring transition-colors duration-fast ease-standard lowercase"
      >
        sair
      </button>
    </form>
  );
}
