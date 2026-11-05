"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface DriveWorkspaceHeaderProps {
  driveId: string;
  companyName: string;
  roleTitle: string;
  lifecycleStatus?: string;
  currentStepTitle: string;
  actions?: React.ReactNode;
}

export function DriveWorkspaceHeader({
  driveId,
  companyName,
  roleTitle,
  lifecycleStatus = "ACTIVE",
  currentStepTitle,
  actions,
}: DriveWorkspaceHeaderProps) {
  const pathname = usePathname();

  const tabs = [
    { label: "Intake", href: `/coordinator/drives/${driveId}/intake`, icon: "upload_file" },
    { label: "JD Review & Policy", href: `/coordinator/drives/${driveId}/review`, icon: "fact_check" },
    { label: "Eligibility", href: `/coordinator/drives/${driveId}/eligibility`, icon: "rule" },
    { label: "Participation", href: `/coordinator/drives/${driveId}/participation`, icon: "group" },
    { label: "Communications", href: `/coordinator/drives/${driveId}/communications`, icon: "mail" },
    { label: "Lifecycle", href: `/coordinator/drives/${driveId}/lifecycle`, icon: "task_alt" },
  ];

  return (
    <div className="flex flex-col space-y-4 mb-6">
      {/* Breadcrumb & Revision Meta */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-graphite font-body">
          <Link href="/coordinator/drives" className="hover:text-canopy-green transition">
            Drives
          </Link>
          <span className="material-symbols-outlined text-[14px] text-slate">chevron_right</span>
          <span className="text-graphite font-medium">
            {companyName} • {roleTitle}
          </span>
          <span className="material-symbols-outlined text-[14px] text-slate">chevron_right</span>
          <span className="text-canopy-green font-semibold">{currentStepTitle}</span>
        </nav>

        <div className="flex items-center gap-2">
          <span className="bg-peach-wash text-coral-pulse px-3 py-0.5 rounded-full font-body text-xs font-semibold border border-coral-pulse/30">
            {lifecycleStatus.toUpperCase()}
          </span>
          <span className="bg-mint-wash text-canopy-green px-3 py-0.5 rounded-full font-body text-xs font-bold border border-leaf-bright/30">
            INV-03 SYNCHRONIZED
          </span>
        </div>
      </div>

      {/* Drive Identification Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-paper-white p-5 rounded-2xl border border-frost-gray shadow-xs">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-headline text-2xl font-bold text-canopy-green">
              {companyName} <span className="font-normal text-slate">•</span> {roleTitle}
            </h1>
          </div>
          <p className="font-body text-xs text-graphite mt-1">
            Campus Graduate Hiring Cycle 2026–27 • Deterministic Rule Compilation & Audited Action State
          </p>
        </div>

        {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
      </div>

      {/* Drive Workspace Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-frost-gray">
        {tabs.map((tab) => {
          const active = pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-body text-xs whitespace-nowrap transition ${
                active
                  ? "bg-canopy-green text-paper-white font-medium shadow-xs"
                  : "bg-paper-white text-graphite hover:bg-surface-container hover:text-canopy-green border border-frost-gray"
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

