import path from "node:path";
import { fileURLToPath } from "node:url";
import { config as loadEnv } from "dotenv";

// argus/.env is the single source of truth for env vars shared by frontend/
// and backend/. Next.js only auto-loads .env files from its own directory,
// so load the repo-root .env explicitly before the config is evaluated.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
loadEnv({ path: path.resolve(__dirname, "..", ".env") });

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained server bundle for the container image the Cloud Run
  // frontend service runs — `.next/standalone` ships its own minimal
  // node_modules, so the runtime stage never needs pnpm or a full install.
  output: "standalone",
};

export default nextConfig;
