import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ReactNode } from "react";
import Link from "next/link";
import { AuthProvider } from "../context/AuthContext";
import { PersonaSwitcher } from "../components/PersonaSwitcher";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={`${inter.className} min-h-full flex flex-col antialiased bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100`}>
        <AuthProvider>
          <header className="sticky top-0 z-50 glass-panel border-b border-slate-200 dark:border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
              <div className="flex items-center gap-8">
                <Link href="/" className="flex items-center gap-3 group">
                  <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-sm group-hover:scale-105 transition">
                    P
                  </div>
                  <span className="font-semibold text-xl tracking-tight text-slate-900 dark:text-white">
                    Placement<span className="text-brand-600 dark:text-brand-400">OS</span>
                  </span>
                </Link>

                <nav className="hidden md:flex items-center gap-5 text-sm font-medium">
                  <Link
                    href="/"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition"
                  >
                    Overview
                  </Link>
                  <Link
                    href="/coordinator/drives"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition flex items-center gap-1.5"
                  >
                    Recruitment Drives
                  </Link>
                  <Link
                    href="/coordinator/students"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition flex items-center gap-1.5"
                  >
                    Coordinator Roster
                  </Link>
                  <Link
                    href="/coordinator/approvals"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition flex items-center gap-1.5"
                  >
                    Approvals
                  </Link>
                  <Link
                    href="/student/portal"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition flex items-center gap-1.5"
                  >
                    Student Portal
                  </Link>
                  <Link
                    href="/student/eligibility"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition flex items-center gap-1.5"
                  >
                    My Eligibility
                  </Link>
                  <Link
                    href="/student/drives"
                    className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition flex items-center gap-1.5"
                  >
                    My Drives
                  </Link>
                </nav>
              </div>

              <div className="flex items-center gap-4">
                <span className="hidden sm:inline-flex px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  Phase 7 Safe Dispatch
                </span>
                <PersonaSwitcher />
              </div>
            </div>
          </header>

          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>

          <footer className="border-t border-slate-200 dark:border-slate-800 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
            PlacementOS Operations Baseline &bull; Deterministic Rules &bull; Scoped Multi-Tenant Architecture
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
