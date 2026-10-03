import type { NextConfig } from "next";

// One origin for the browser: pages and /api/* both come from this server, so the
// session cookie and the SSE run-progress stream need no CORS. The API itself is
// FastAPI, see docs/DECISIONS.md D22.
const apiOrigin = process.env.EDSS_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
