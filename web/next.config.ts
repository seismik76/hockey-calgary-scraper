import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // `standalone` builds a self-contained `.next/standalone` directory with a
  // minimal `server.js` and only the dependencies it actually traces. The Docker
  // image just copies that, the static assets, and `public/` — no node_modules
  // bulk-copy. https://nextjs.org/docs/app/api-reference/config/next-config-js/output
  output: 'standalone',
  // The standalone tracer walks up from the Next project to find a workspace
  // root. With `output: 'standalone'` in a subdirectory it would guess the
  // parent (the Python project), which produces noisy warnings and bloats the
  // trace. Pin it explicitly to this directory.
  outputFileTracingRoot: process.cwd(),
};

export default nextConfig;
