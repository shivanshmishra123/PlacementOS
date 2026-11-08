"use client";

import React, { ReactNode, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { UserNav } from "./UserNav";
import { ShieldAlert, ArrowRight, LogIn, School } from "lucide-react";

interface CoordinatorShellProps {
  children: ReactNode;
}

export function CoordinatorShell({ children }: CoordinatorShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, isAuthenticated, isCoordinator, isStudent } = useAuth();

  const navItems = [
    { label: "Dashboard", href: "/", icon: "dashboard", exact: true },
    { label: "Recruitment Drives", href: "/coordinator/drives", icon: "business_center" },
    { label: "Student Roster", href: "/coordinator/students", icon: "school" },
    { label: "Integrations Hub", href: "/coordinator/integrations", icon: "hub" },
  ];

  const isNavActive = (itemHref: string, exact?: boolean) => {
    if (exact) return pathname === itemHref;
    return pathname.startsWith(itemHref);
  };

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
            Verifying Institutional Authorization...
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
            Authentication Required
          </h2>
          <p className="text-xs text-graphite font-body">
            You must be signed in with an authorized Placement Coordinator account to access this operational workspace.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-canopy-green text-paper-white text-xs font-bold hover:bg-[#153427] transition shadow-xs"
          >
            <span>Go to Institutional Login</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  // RBAC Access Control: Students cannot access coordinator operational controls!
  if (isStudent) {
    return (
      <div className="min-h-screen bg-lavender-mist flex items-center justify-center p-6">
        <div className="bg-paper-white p-8 rounded-3xl border border-red-200 shadow-md max-w-lg w-full text-center space-y-4">
          <div className="h-12 w-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-red-100 text-red-700">
              Access Restricted (RBAC)
            </span>
            <h2 className="font-headline text-xl font-bold text-ink-black mt-2">
              Coordinator Controls Unavailable
            </h2>
          </div>
          <p className="text-xs text-graphite font-body leading-relaxed">
            Your current account (<span className="font-semibold text-ink-black">{user.email}</span>) is registered as a <span className="font-semibold text-canopy-green">Student Candidate</span>. Institutional recruitment controls, JD extractions, policy approvals, and dispatching are restricted to Placement Coordinators.
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/student/portal"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto py-2.5 px-5 rounded-xl bg-canopy-green text-paper-white text-xs font-bold hover:bg-[#153427] transition shadow-xs"
            >
              <School className="w-4 h-4" />
              <span>Open Student Portal</span>
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto py-2.5 px-5 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold hover:bg-slate-200 transition"
            >
              <span>Sign In as Coordinator</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-lavender-mist">
      {/* Fixed Left Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-[240px] bg-paper-white border-r border-frost-gray z-50 flex flex-col">
        {/* Monogram Brand Header */}
        <div className="h-16 px-4 flex items-center gap-3 border-b border-frost-gray">
          <div className="h-9 w-9 rounded-xl bg-canopy-green text-paper-white flex items-center justify-center font-bold text-lg shadow-sm">
            P
          </div>
          <div className="flex flex-col">
            <span className="font-headline text-base font-bold text-canopy-green leading-tight">
              Placement<span className="text-coral-pulse">OS</span>
            </span>
            <span className="font-body text-[11px] text-graphite">Coordinator Operations</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const active = isNavActive(item.href, item.exact);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 h-11 px-3.5 rounded-xl font-body text-sm transition-all ${
                  active
                    ? "bg-canopy-green text-paper-white shadow-sm border-l-4 border-leaf-bright font-medium"
                    : "text-ink-black hover:bg-surface-container hover:text-on-surface"
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Institutional Tenant Badge */}
        <div className="p-3 border-t border-frost-gray">
          <div className="bg-mint-wash rounded-xl p-2.5 flex items-center justify-between border border-leaf-bright/30">
            <div className="flex flex-col">
              <span className="font-body text-[10px] text-graphite uppercase font-semibold">
                Tenant Scope
              </span>
              <span className="font-headline text-xs font-bold text-canopy-green truncate">
                {user.institution_slug === "beacon-state"
                  ? "Beacon College"
                  : "Apex Institute"}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-leaf-bright animate-pulse" />
              <span className="text-[10px] text-canopy-green font-medium">RBAC Active</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="pl-[240px]">
        {/* Top Header */}
        <header className="fixed top-0 left-[240px] right-0 h-16 bg-paper-white border-b border-frost-gray z-40 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-headline text-base text-canopy-green font-semibold tracking-tight">
              {user.institution_slug.toUpperCase()} Placement Operations
            </span>
            <span className="bg-sky-wash text-deep-teal font-body text-xs px-2.5 py-0.5 rounded-full font-medium">
              Cycle 2026–27
            </span>
            <span className="bg-mint-wash text-canopy-green font-body text-xs px-2.5 py-0.5 rounded-full font-bold">
              COORDINATOR
            </span>
          </div>

          <div className="flex items-center gap-4">
            <UserNav />
          </div>
        </header>

        {/* Page Content */}
        <main className="w-full pt-16 min-h-[calc(100vh-4rem)] p-6">
          <div className="max-w-[1240px] mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
