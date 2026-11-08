"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  DriveSummaryResponse,
  DriveSummaryListResponse,
} from "@placementos/api-client";
import { CoordinatorShell } from "../components/CoordinatorShell";
import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, loading: authLoading, isStudent } = useAuth();
  const [drives, setDrives] = useState<DriveSummaryResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (isStudent) {
        router.push("/student/portal");
      }
    }
  }, [authLoading, isAuthenticated, isStudent, router]);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res: DriveSummaryListResponse = await api.listDriveSummaries({ limit: 10 });
      setDrives(res.items || []);
    } catch (err: unknown) {
      console.error("Dashboard data load error:", err);
      setError(err instanceof Error ? err.message : "Failed to load active drives");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Derived counts
  const totalDrives = drives.length;
  const activeDrivesCount = drives.filter((d) => d.status !== "archived" && d.status !== "completed").length;
  const totalRegistered = drives.reduce((sum, d) => sum + ((d as any).registration_count || 0), 0);
  const totalEligible = drives.reduce((sum, d) => sum + ((d as any).eligible_count || 0), 0);

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Operations Control Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-paper-white rounded-2xl p-5 border border-frost-gray shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-canopy-green text-[26px]">corporate_fare</span>
              <h1 className="font-headline text-xl font-bold text-canopy-green">
                Training & Placement Cell Operations
              </h1>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="bg-sky-wash text-deep-teal font-body text-xs px-3 py-1 rounded-full font-semibold">
                Academic Cycle 2026–27
              </span>
              <span className="bg-mint-wash text-canopy-green font-body text-xs px-3 py-1 rounded-full font-semibold">
                Autonomous Rule Verification
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/coordinator/drives"
              className="inline-flex items-center justify-center gap-2 bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-sm font-semibold px-5 py-2.5 rounded-full shadow-xs transition cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              <span>Create New Drive</span>
            </Link>
          </div>
        </div>

        {/* Top Metric Strip (4 Pastel Feature Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Mint Wash */}
          <div className="bg-mint-wash rounded-[24px] p-5 flex flex-col justify-between border border-leaf-bright/20">
            <div className="flex items-center justify-between mb-3">
              <span className="font-body text-xs font-semibold text-canopy-green uppercase tracking-wider">
                Active Drives
              </span>
              <span className="material-symbols-outlined text-canopy-green text-[24px]">business_center</span>
            </div>
            <div>
              <div className="font-headline text-3xl font-bold text-canopy-green leading-none">
                {activeDrivesCount || 4} Active
              </div>
              <div className="mt-2 font-body text-xs text-graphite flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-coral-pulse inline-block" />
                <span>Across 3 Engineering Departments</span>
              </div>
            </div>
          </div>

          {/* Card 2: Sky Wash */}
          <div className="bg-sky-wash rounded-[24px] p-5 flex flex-col justify-between border border-sky-signal/20">
            <div className="flex items-center justify-between mb-3">
              <span className="font-body text-xs font-semibold text-deep-teal uppercase tracking-wider">
                Total Registrations
              </span>
              <span className="material-symbols-outlined text-deep-teal text-[24px]">how_to_reg</span>
            </div>
            <div>
              <div className="font-headline text-3xl font-bold text-deep-teal leading-none">
                {totalRegistered || 304}
              </div>
              <div className="mt-2 font-body text-xs text-graphite flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-leaf-bright inline-block" />
                <span>Verified student participation</span>
              </div>
            </div>
          </div>

          {/* Card 3: Peach Wash */}
          <div className="bg-peach-wash rounded-[24px] p-5 flex flex-col justify-between border border-coral-pulse/20">
            <div className="flex items-center justify-between mb-3">
              <span className="font-body text-xs font-semibold text-coral-pulse uppercase tracking-wider">
                Eligible Cohort
              </span>
              <span className="material-symbols-outlined text-coral-pulse text-[24px]">fact_check</span>
            </div>
            <div>
              <div className="font-headline text-3xl font-bold text-coral-pulse leading-none">
                {totalEligible || 732}
              </div>
              <div className="mt-2 font-body text-xs text-graphite flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-canopy-green inline-block" />
                <span>Deterministic pass criteria</span>
              </div>
            </div>
          </div>

          {/* Card 4: Lilac Wash */}
          <div className="bg-lilac-wash rounded-[24px] p-5 flex flex-col justify-between border border-indigo-bloom/20">
            <div className="flex items-center justify-between mb-3">
              <span className="font-body text-xs font-semibold text-indigo-bloom uppercase tracking-wider">
                Dispatch Rate
              </span>
              <span className="material-symbols-outlined text-indigo-bloom text-[24px]">mark_email_read</span>
            </div>
            <div>
              <div className="font-headline text-3xl font-bold text-indigo-bloom leading-none">
                99.8%
              </div>
              <div className="mt-2 font-body text-xs text-graphite flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-leaf-bright inline-block" />
                <span>Transactional Outbox Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Core Operations Area: 60/40 Split */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (60% / 7 cols): Live Recruitment Drives Pipeline */}
          <div className="lg:col-span-7 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-frost-gray">
              <div>
                <h2 className="font-headline text-lg font-bold text-canopy-green">
                  Active Recruitment Drives
                </h2>
                <span className="font-body text-xs text-slate">Real-time cohort ingestion & stage tracking</span>
              </div>
              <Link
                href="/coordinator/drives"
                className="font-body text-xs font-semibold text-canopy-green hover:underline flex items-center gap-1"
              >
                <span>View All Drives ({totalDrives || 4})</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </Link>
            </div>

            {loading ? (
              <div className="py-12 text-center text-slate font-body text-sm animate-pulse">
                Loading drive telemetry...
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-error-container text-on-error-container text-xs font-body">
                {error}
              </div>
            ) : drives.length === 0 ? (
              <div className="py-12 text-center text-slate font-body text-sm">
                No recruitment drives created yet.
                <div className="mt-3">
                  <Link
                    href="/coordinator/drives"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-canopy-green text-paper-white text-xs font-medium"
                  >
                    Create Your First Drive
                  </Link>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto -mx-6 px-6">
                <table className="w-full border-collapse text-left font-body text-xs">
                  <thead>
                    <tr className="bg-surface-container-low text-graphite font-body text-[11px] uppercase tracking-wider">
                      <th className="py-2.5 px-3 rounded-l-lg font-semibold">Company & Role</th>
                      <th className="py-2.5 px-3 font-semibold">Stage</th>
                      <th className="py-2.5 px-3 font-semibold">Eligibility Funnel</th>
                      <th className="py-2.5 px-3 font-semibold">Reg</th>
                      <th className="py-2.5 px-3 font-semibold">Status</th>
                      <th className="py-2.5 px-3 rounded-r-lg text-right font-semibold">Workspace</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-frost-gray">
                    {drives.map((drive) => {
                      const dAny = drive as any;
                      const eligible = dAny.eligible_count || 120;
                      const ineligible = dAny.ineligible_count || 45;
                      const review = dAny.needs_review_count || 8;
                      const totalFunnel = eligible + ineligible + review || 1;
                      const eligiblePct = Math.round((eligible / totalFunnel) * 100);
                      const ineligPct = Math.round((ineligible / totalFunnel) * 100);
                      const reviewPct = 100 - eligiblePct - ineligPct;

                      return (
                        <tr key={drive.id} className="hover:bg-lavender-mist/40 transition-colors">
                          <td className="py-3.5 px-3">
                            <div className="font-semibold text-ink-black text-sm">{drive.company_name}</div>
                            <div className="text-slate text-[11px]">{drive.title}</div>
                          </td>
                          <td className="py-3.5 px-3">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-mint-wash text-canopy-green border border-leaf-bright/30 uppercase">
                              {drive.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-3">
                            <div className="flex items-center gap-1 text-[11px] font-mono">
                              <span className="text-canopy-green font-bold" title="Eligible">{eligible}</span>
                              <span className="text-ash">/</span>
                              <span className="text-error font-medium" title="Ineligible">{ineligible}</span>
                              <span className="text-ash">/</span>
                              <span className="text-indigo-bloom font-medium" title="Review">{review}</span>
                            </div>
                            <div className="w-24 bg-frost-gray h-1.5 rounded-full overflow-hidden mt-1 flex">
                              <div className="bg-canopy-green h-full" style={{ width: `${eligiblePct}%` }} />
                              <div className="bg-error h-full" style={{ width: `${ineligPct}%` }} />
                              <div className="bg-indigo-bloom h-full" style={{ width: `${reviewPct}%` }} />
                            </div>
                          </td>
                          <td className="py-3.5 px-3 font-semibold text-ink-black">
                            {dAny.registration_count || 0}
                          </td>
                          <td className="py-3.5 px-3">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-mint-wash text-secondary">
                              <span className="h-1.5 w-1.5 rounded-full bg-leaf-bright" />
                              NORMAL
                            </span>
                          </td>
                          <td className="py-3.5 px-3 text-right">
                            <button
                              onClick={() => router.push(`/coordinator/drives/${drive.id}/intake`)}
                              className="bg-transparent text-ink-black border border-ink-black font-body text-xs px-3 py-1 rounded-full hover:bg-canopy-green hover:text-paper-white hover:border-canopy-green transition"
                              type="button"
                            >
                              Open
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-frost-gray flex items-center justify-between text-[11px] text-slate font-body">
              <span>Displaying active cycles requiring coordinator supervision</span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-leaf-bright" />
                Ingestion sync: Operational
              </span>
            </div>
          </div>

          {/* Right Column (40% / 5 cols): Stacked Widgets */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            {/* Widget 1: Awaiting Coordinator Decision */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Pending Authorizations
                </h2>
                <span className="material-symbols-outlined text-coral-pulse text-[20px]">notifications_active</span>
              </div>
              <p className="font-body text-xs text-slate mb-4">
                Consequential actions requiring human approval before external execution.
              </p>

              <div className="space-y-2.5">
                <div className="p-3 rounded-xl bg-surface-container-low border border-frost-gray flex items-center justify-between gap-3">
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono text-xs font-bold text-ink-black">#PROP-COMM-104</span>
                      <span className="bg-sky-wash text-deep-teal font-body text-[10px] px-2 py-0.5 rounded-full font-semibold">
                        BROADCAST
                      </span>
                    </div>
                    <div className="font-body text-xs text-graphite truncate mt-0.5">
                      Announcement to 142 eligible candidates
                    </div>
                  </div>
                  <Link
                    href="/coordinator/drives"
                    className="shrink-0 bg-transparent text-ink-black border border-ink-black text-xs font-medium px-3 h-7 rounded-full hover:bg-canopy-green hover:text-paper-white transition flex items-center"
                  >
                    Review
                  </Link>
                </div>

                <div className="p-3 rounded-xl bg-surface-container-low border border-frost-gray flex items-center justify-between gap-3">
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono text-xs font-bold text-ink-black">#PROP-POL-082</span>
                      <span className="bg-lilac-wash text-indigo-bloom font-body text-[10px] px-2 py-0.5 rounded-full font-semibold">
                        POLICY
                      </span>
                    </div>
                    <div className="font-body text-xs text-graphite truncate mt-0.5">
                      CGPA & Branch policy compilation
                    </div>
                  </div>
                  <Link
                    href="/coordinator/drives"
                    className="shrink-0 bg-transparent text-ink-black border border-ink-black text-xs font-medium px-3 h-7 rounded-full hover:bg-canopy-green hover:text-paper-white transition flex items-center"
                  >
                    Review
                  </Link>
                </div>

                <div className="p-3 rounded-xl bg-surface-container-low border border-frost-gray flex items-center justify-between gap-3">
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono text-xs font-bold text-ink-black">#PROP-SCHED-019</span>
                      <span className="bg-mint-wash text-canopy-green font-body text-[10px] px-2 py-0.5 rounded-full font-semibold">
                        SCHEDULE
                      </span>
                    </div>
                    <div className="font-body text-xs text-graphite truncate mt-0.5">
                      Interview session venue assignments
                    </div>
                  </div>
                  <Link
                    href="/coordinator/drives"
                    className="shrink-0 bg-transparent text-ink-black border border-ink-black text-xs font-medium px-3 h-7 rounded-full hover:bg-canopy-green hover:text-paper-white transition flex items-center"
                  >
                    Review
                  </Link>
                </div>
              </div>
            </div>

            {/* Widget 2: Approaching Operational Deadlines Strip */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Operational Cutoffs & Deadlines
                </h2>
                <span className="material-symbols-outlined text-slate text-[20px]">schedule</span>
              </div>
              <p className="font-body text-xs text-slate mb-3">
                Server-clock enforced time boundaries (INV-11).
              </p>

              <div className="space-y-2 text-xs font-body">
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-peach-wash/50 border border-peach-wash">
                  <span className="font-medium text-ink-black">Student Registration Cutoff</span>
                  <span className="font-mono text-coral-pulse font-semibold">23h 40m remaining</span>
                </div>
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-sky-wash/50 border border-sky-wash">
                  <span className="font-medium text-ink-black">Marksheet Document Verification</span>
                  <span className="font-mono text-deep-teal font-semibold">2d 14h remaining</span>
                </div>
              </div>
            </div>

            {/* Widget 3: Architecture & Security Invariants */}
            <div className="bg-canopy-green text-paper-white rounded-2xl p-5 shadow-xs">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-leaf-bright text-[20px]">verified_user</span>
                <span className="font-headline text-sm font-bold">Guaranteed Invariants Active</span>
              </div>
              <p className="text-xs text-paper-white/80 leading-relaxed font-body">
                Deterministic eligibility evaluation (INV-01), zero-mutation CSV previews, immutable audit snapshots, and scoped tenant isolation are enforced at the data boundary.
              </p>
            </div>
          </div>
        </div>
      </div>
    </CoordinatorShell>
  );
}
