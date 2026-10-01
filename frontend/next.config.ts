import type { NextConfig } from "next";

const API_ORIGIN = process.env.FINSIGHT_API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
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
  // Real-API mode: the browser calls same-origin /api/*, Next forwards to FastAPI.
  async rewrites() {
    if (process.env.NEXT_PUBLIC_USE_MOCKS === "1") return [];
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
