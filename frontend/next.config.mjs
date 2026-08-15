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
};

export default nextConfig;
