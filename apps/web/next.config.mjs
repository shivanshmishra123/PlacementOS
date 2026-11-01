/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@placementos/api-client"],
  output: process.env.PLACEMENTOS_STANDALONE === "true" ? "standalone" : undefined,
};

export default nextConfig;
