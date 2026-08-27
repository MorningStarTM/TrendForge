import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle (.next/standalone) for a slim Docker runtime.
  output: "standalone",
};

export default nextConfig;
