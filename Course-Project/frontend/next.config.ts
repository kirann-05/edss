import type { NextConfig } from "next";

// One origin for the browser: pages and /api/* both come from this server, so the
// session cookie and the SSE run-progress stream need no CORS. The API itself is
// FastAPI, see docs/DECISIONS.md D22.
const apiOrigin = process.env.EDSS_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // The browser tests build into their own folder, so they never touch a dev server that is running
  distDir: process.env.EDSS_DIST_DIR ?? ".next",
  // the container image runs the small server Next.js traces for itself (frontend/Dockerfile)
  output: process.env.EDSS_STANDALONE === "1" ? "standalone" : undefined,
  poweredByHeader: false, // no need to tell anyone what the server runs
  async headers() {
    // For every page and every /api answer. HSTS belongs on the university's HTTPS proxy (RUNBOOK).
    // A full script Content-Security-Policy needs per-request nonces in Next.js, so only framing is
    // limited here.
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" }, // no other site may frame a page, so no clickjacking
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" }, // a report's address never leaves the site
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
