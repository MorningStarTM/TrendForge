import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle (.next/standalone) for a slim Docker
  // runtime image — see frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
