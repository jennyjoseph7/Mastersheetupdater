import type { NextConfig } from 'next';

const isDev = process.env.NODE_ENV === 'development';

const nextConfig: NextConfig = {
  output: isDev ? undefined : 'export',
  basePath: isDev ? '' : '/Mastersheetupdater',
  assetPrefix: isDev ? '' : '/Mastersheetupdater/',
  trailingSlash: true,
  images: { unoptimized: true },
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
