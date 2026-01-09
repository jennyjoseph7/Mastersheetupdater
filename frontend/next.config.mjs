/** @type {import('next').NextConfig} */
const nextConfig = {

  trailingSlash: true,
  output: "export",

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
  productionBrowserSourceMaps: true,
};

export default nextConfig;
