"use client";

import React, { ReactNode, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { UserNav } from "./UserNav";
import { ArrowLeft, LogIn } from "lucide-react";

interface StudentShellProps {
  children: ReactNode;
}

export function StudentShell({ children }: StudentShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, isAuthenticated, isStudent, isCoordinator } = useAuth();

  const navItems = [
    { label: "My Profile", href: "/student/portal", icon: "badge" },
    { label: "Opportunities", href: "/student/drives", icon: "work" },
    { label: "My Eligibility", href: "/student/eligibility", icon: "verified" },
    { label: "Documents", href: "/student/documents", icon: "description" },
    { label: "Registration", href: "/student/registration", icon: "how_to_reg" },
    { label: "Schedule & Results", href: "/student/schedule-results", icon: "event_available" },
  ];

  // Enforce redirection to login if unauthenticated once loading settles
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [loading, isAuthenticated, router]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-lavender-mist flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-canopy-green text-paper-white flex items-center justify-center font-bold text-lg animate-pulse">
            P
          </div>
          <div className="text-xs font-semibold text-canopy-green font-body">
            Loading Student Portal...
          </div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen bg-lavender-mist flex items-center justify-center p-6">
        <div className="bg-paper-white p-8 rounded-3xl border border-frost-gray shadow-md max-w-md w-full text-center space-y-4">
          <div className="h-12 w-12 rounded-2xl bg-sky-wash text-deep-teal flex items-center justify-center mx-auto">
            <LogIn className="w-6 h-6" />
          </div>
          <h2 className="font-headline text-lg font-bold text-ink-black">
            Student Login Required
          </h2>
          <p className="text-xs text-graphite font-body">
            Please sign in with your student credentials to view verified placement opportunities and personal eligibility.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-canopy-green text-paper-white text-xs font-bold hover:bg-[#153427] transition shadow-xs"
          >
            <span>Sign In to Student Portal</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-lavender-mist">
      {/* Top Navbar Header */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-paper-white border-b border-frost-gray z-50 px-6 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-8">
          <Link href="/student/portal" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-xl bg-canopy-green text-paper-white flex items-center justify-center font-bold text-lg shadow-sm group-hover:scale-105 transition">
              P
            </div>
            <div className="flex flex-col">
              <span className="font-headline text-base font-bold text-canopy-green leading-tight">
                Placement<span className="text-coral-pulse">OS</span>
              </span>
              <span className="font-body text-[11px] text-graphite">Student Self-Service Portal</span>
            </div>
          </Link>

          <nav className="hidden lg:flex items-center gap-1.5" aria-label="Student Navigation">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-body text-xs transition ${
                    active
                      ? "bg-canopy-green text-paper-white font-medium shadow-xs"
                      : "text-graphite hover:text-canopy-green hover:bg-surface-container"
                  }`}
                >
                  <span className="material-symbols-outlined text-[16px]">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Role badge */}
          {isStudent ? (
            <span className="hidden sm:inline-flex bg-mint-wash text-canopy-green font-body text-xs px-2.5 py-0.5 rounded-full font-semibold border border-leaf-bright/30">
              VERIFIED CANDIDATE
            </span>
          ) : (
            <div className="hidden sm:flex items-center gap-2">
              <span className="bg-amber-50 text-amber-800 border border-amber-200 font-body text-[11px] px-2.5 py-0.5 rounded-full font-medium">
                Coordinator Preview Mode
              </span>
              <Link
                href="/coordinator/drives"
                className="text-xs font-semibold text-canopy-green hover:underline flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Return to Workspace
              </Link>
            </div>
          )}

          <UserNav />
        </div>
      </header>

      {/* Main Content Area */}
      <main className="w-full pt-20 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-[1140px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
