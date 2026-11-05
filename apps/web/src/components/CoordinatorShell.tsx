"use client";

import React, { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { PersonaSwitcher } from "./PersonaSwitcher";

interface CoordinatorShellProps {
  children: ReactNode;
}

export function CoordinatorShell({ children }: CoordinatorShellProps) {
  const pathname = usePathname();
  const { user } = useAuth();

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
            <span className="font-body text-[11px] text-graphite">Recruitment Operations</span>
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

        {/* System Status Pill */}
        <div className="p-3 border-t border-frost-gray">
          <div className="bg-mint-wash rounded-xl p-2.5 flex items-center justify-between border border-leaf-bright/30">
            <span className="font-body text-[11px] text-canopy-green font-semibold uppercase tracking-wider">
              System Status
            </span>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-leaf-bright animate-pulse" />
              <span className="text-[10px] text-canopy-green font-medium">Normal</span>
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
              {user?.institution_slug ? user.institution_slug.toUpperCase() + " Recruitment" : "Apex Institute of Technology"}
            </span>
            <span className="bg-sky-wash text-deep-teal font-body text-xs px-2.5 py-0.5 rounded-full font-medium">
              Academic Cycle 2026–27
            </span>
            <span className="bg-mint-wash text-canopy-green font-body text-xs px-2.5 py-0.5 rounded-full font-bold">
              SYNTHETIC DEMO
            </span>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/student/portal"
              className="text-xs font-medium text-graphite hover:text-canopy-green flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-lavender-mist/60 hover:bg-lavender-mist transition border border-frost-gray"
            >
              <span className="material-symbols-outlined text-[16px]">school</span>
              Student Portal View
            </Link>
            <PersonaSwitcher />
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

