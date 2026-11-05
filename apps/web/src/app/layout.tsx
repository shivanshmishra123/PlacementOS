import type { Metadata } from "next";
import "./globals.css";
import { ReactNode } from "react";
import { AuthProvider } from "../context/AuthContext";

export const metadata: Metadata = {
  title: "PlacementOS | Campus Recruitment Operations Platform",
  description:
    "End-to-end recruitment operations platform for college placement coordinators and students.",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Manrope:wght@200..800&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col font-body antialiased bg-lavender-mist text-ink-black">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-xl focus:bg-canopy-green focus:px-4 focus:py-2 focus:text-paper-white focus:shadow-lg font-body text-xs"
        >
          Skip to main content
        </a>
        <AuthProvider>
          <div id="main-content" className="min-h-screen flex flex-col">
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
