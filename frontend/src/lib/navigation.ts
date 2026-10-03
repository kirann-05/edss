/**
 * Where to go after signing in. Only a same-site path is accepted, so a crafted
 * /login?next=https://evil.example link cannot bounce a person to another site.
 */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/")) return "/";
  if (next.startsWith("//") || next.startsWith("/\\")) return "/";
  if (next === "/login" || next.startsWith("/login?") || next.startsWith("/login/")) return "/";
  return next;
}
