import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Argus — the agentic seeing-eye copilot",
    short_name: "Argus",
    description: "Real-time agentic guidance for blind and low-vision navigation.",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#F7F9FA",
    theme_color: "#1B5E77",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
