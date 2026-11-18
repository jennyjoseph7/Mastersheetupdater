import type { NextConfig } from 'next';

const isDev = process.env.NODE_ENV === 'development';

const nextConfig: NextConfig = {
  allowedDevOrigins: isDev ? ['192.168.1.2'] : undefined,
  output: isDev ? undefined : 'export',
  basePath: isDev ? '' : '/Mastersheetupdater',
  assetPrefix: isDev ? '' : '/Mastersheetupdater/',
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  images: { unoptimized: true },
  // ponytail: dev proxy to bypass browser cross-origin CORS on non-3000 ports
  ...(isDev ? {
    async rewrites() {
      return [
        {
          source: '/auth/:path*',
          destination: 'https://autongagetools.jennyjoseph-k.workers.dev/auth/:path*',
        },
        {
          source: '/gryd/:path*',
          destination: 'https://autongagetools.jennyjoseph-k.workers.dev/gryd/:path*',
        },
        // ponytail: proxy billing API through server-side so Origin header is not localhost:3000
        {
          source: '/api-proxy/billing',
          destination: 'https://api.autongage.com/gryd/db/objects/billing',
        },
        {
          source: '/api-proxy/billing-dev',
          destination: 'https://autobot-webapp-dev.gryd.in/gryd/db/objects/billing',
        },
      ];
    },
  } : {}),
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Permissions-Policy', value: 'geolocation=(), microphone=(), camera=()' },
        ],
      },
    ];
  },
};

export default nextConfig;
