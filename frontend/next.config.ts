import type { NextConfig } from "next";

const API_ORIGIN = process.env.FINSIGHT_API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // The e2e run on mocks uses its own build folder so it can sit beside a real-API `pnpm dev`.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // msw/browser exports "node": null, which fails the SSR pass of the client bundle even though
  // the worker is only ever started in the browser. Point the browser build at the real file.
  turbopack: {
    resolveAlias: {
      "msw/browser": {
        browser: "./node_modules/msw/lib/browser/index.js",
        default: "./mocks/empty.ts",
      },
    },
  },
  // The rewrite proxy cuts a response after 30 s by default. Job events (minutes) and a first chat
  // answer on a cold reranker (about 40 s) are streams, so the proxy waits an hour.
  experimental: { proxyTimeout: 3_600_000 },
  // Real-API mode: the browser calls same-origin /api/*, Next forwards to FastAPI.
  async rewrites() {
    if (process.env.NEXT_PUBLIC_USE_MOCKS === "1") return [];
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
