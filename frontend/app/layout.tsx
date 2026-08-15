import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

// Used only for the Architecture section's schematic diagram labels — never
// for headlines or body copy. Real typography stays Inter-only end to end.
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Argus",
  description: "The agentic seeing-eye copilot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="data-theme"
          themes={["light", "dark", "high-contrast"]}
          defaultTheme="system"
          enableSystem
        >
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
