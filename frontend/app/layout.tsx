import type React from "react";
import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import "./globals.css";
import TopNavigation from "@/components/top-navigation";
import { ThemeProvider } from "@/components/theme-provider";
import { ScrollGradientBackground } from "@/components/scroll-gradient-background";
import { AuthProvider } from "@/lib/auth-context";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600"],
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  weight: ["600", "700", "800"],
});

export const metadata: Metadata = {
  title: "autoNgage Analytics",
  description: "Dashboard for monitoring autoNgage performance",
  generator: "v0.app",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${manrope.variable} ${inter.className}`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="min-h-screen w-full relative bg-background">
            <div
              className="absolute inset-0 z-0"
              style={{
                background: "hsl(var(--background))",
                backgroundImage: `
        radial-gradient(
          circle at bottom center,
          rgba(173, 109, 244, 0.5),
          transparent 40%
        )
      `,
                filter: "blur(280px)",
                backgroundRepeat: "no-repeat",
              }}
            />
            {/* Your Content/Components */}
            <AuthProvider>
              <ScrollGradientBackground />
              <div className="min-h-screen relative z-10">
                <TopNavigation />
                <main className="container mx-auto px-4 py-5">{children}</main>
              </div>
            </AuthProvider>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
