"use client";

import React, { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { PersonaSwitcher } from "./PersonaSwitcher";

interface StudentShellProps {
  children: ReactNode;
}

export function StudentShell({ children }: StudentShellProps) {
  const pathname = usePathname();
  const { user } = useAuth();

  const navItems = [
    { label: "My Profile", href: "/student/portal", icon: "badge" },
    { label: "Opportunities", href: "/student/drives", icon: "work" },
    { label: "My Eligibility", href: "/student/eligibility", icon: "verified" },
    { label: "Documents", href: "/student/documents", icon: "description" },
    { label: "Registration", href: "/student/registration", icon: "how_to_reg" },
    { label: "Schedule & Results", href: "/student/schedule-results", icon: "event_available" },
  ];

  return (
    <div className="min-h-screen bg-lavender-mist">
      {/* Top Navbar Header */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-paper-white border-b border-frost-gray z-50 px-6 flex items-center justify-between shadow-sm">
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
          <span className="hidden sm:inline-flex bg-mint-wash text-canopy-green font-body text-xs px-2.5 py-0.5 rounded-full font-semibold">
            {user?.role === "student" ? "VERIFIED CANDIDATE" : "STUDENT PREVIEW"}
          </span>
          <Link
            href="/"
            className="text-xs font-medium text-graphite hover:text-canopy-green flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-lavender-mist/60 hover:bg-lavender-mist transition border border-frost-gray"
          >
            <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
            Coordinator View
          </Link>
          <PersonaSwitcher />
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

