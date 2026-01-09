/** @type {import('next').NextConfig} */
const nextConfig = {
  // Removed "output: export" to enable API routes
  // API routes fix CORS by proxying requests server-to-server
  trailingSlash: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  transpilePackages: ["lucide-react"],
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
};

export default nextConfig;
