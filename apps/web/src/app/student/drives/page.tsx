"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { StudentDriveResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";
import { StudentShell } from "../../../components/StudentShell";

const CARD_WASHES = [
  "bg-mint-wash border-leaf-bright/30",
  "bg-sky-wash border-sky-signal/30",
  "bg-peach-wash border-coral-pulse/30",
  "bg-lilac-wash border-indigo-bloom/30",
  "bg-cream border-[#e6dcaf]/50",
  "bg-sage-wash border-secondary/30",
];

export default function StudentDrivesPage() {
  const router = useRouter();
  const { client, user } = useAuth();

  const [drives, setDrives] = useState<StudentDriveResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "eligible" | "registered">("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const publishedDrives = await client.listStudentDrives();
      setDrives(publishedDrives || []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load published opportunities");
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredDrives = drives.filter((d) => {
    if (filter === "eligible" && d.eligibility_status !== "eligible") return false;
    if (filter === "registered" && d.registration?.state !== "submitted") return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        d.company_name?.toLowerCase().includes(q) ||
        d.role_title?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <StudentShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Header Strip */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
                Campus Recruitment Opportunities
              </h1>
              <p className="font-body text-xs text-graphite mt-1">
                Approved employer drives for your academic cohort (Academic Cycle 2026–27).
              </p>
            </div>

            <span className="bg-mint-wash text-canopy-green font-body text-xs px-3 py-1 rounded-full font-bold border border-leaf-bright/30">
              {drives.length} Opportunities Published
            </span>
          </div>

          {/* Search & Filter Strip */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
            <div className="relative flex-1 max-w-md">
              <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-ash text-[20px]">
                search
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by company or job role..."
                className="w-full bg-cloud-gray rounded-full pl-10 pr-4 py-2.5 text-xs focus:bg-paper-white focus:ring-2 focus:ring-canopy-green font-body border border-transparent focus:border-canopy-green"
              />
            </div>

            <div className="flex items-center gap-2 overflow-x-auto text-xs font-body">
              <button
                onClick={() => setFilter("all")}
                className={`px-4 py-1.5 rounded-full transition ${
                  filter === "all" ? "bg-canopy-green text-paper-white font-semibold shadow-2xs" : "bg-paper-white text-graphite border border-frost-gray"
                }`}
              >
                All Drives ({drives.length})
              </button>
              <button
                onClick={() => setFilter("eligible")}
                className={`px-4 py-1.5 rounded-full transition ${
                  filter === "eligible" ? "bg-canopy-green text-paper-white font-semibold shadow-2xs" : "bg-paper-white text-graphite border border-frost-gray"
                }`}
              >
                Eligible For Me
              </button>
              <button
                onClick={() => setFilter("registered")}
                className={`px-4 py-1.5 rounded-full transition ${
                  filter === "registered" ? "bg-canopy-green text-paper-white font-semibold shadow-2xs" : "bg-paper-white text-graphite border border-frost-gray"
                }`}
              >
                My Registrations
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30">
            {error}
          </div>
        )}

        {/* Drives Grid */}
        {loading ? (
          <div className="py-20 text-center font-body text-sm text-slate animate-pulse">
            Loading recruitment opportunities...
          </div>
        ) : filteredDrives.length === 0 ? (
          <div className="bg-paper-white rounded-2xl p-12 text-center border border-frost-gray font-body text-slate">
            <span className="material-symbols-outlined text-[42px] text-ash mb-2 block">
              work_off
            </span>
            <p className="text-sm">No published drives matching your filter.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredDrives.map((d, idx) => {
              const washClass = CARD_WASHES[idx % CARD_WASHES.length];
              const monogram = (d.company_name || "C").charAt(0).toUpperCase();

              const eligibilityPill =
                d.eligibility_status === "eligible"
                  ? "bg-mint-wash text-canopy-green border-leaf-bright/30"
                  : d.eligibility_status === "ineligible"
                  ? "bg-peach-wash text-coral-pulse border-coral-pulse/30"
                  : "bg-lilac-wash text-indigo-bloom border-indigo-bloom/30";

              return (
                <div
                  key={d.drive_id}
                  className={`${washClass} rounded-[24px] p-6 border flex flex-col justify-between space-y-4 shadow-xs`}
                >
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-paper-white flex items-center justify-center shrink-0 border border-frost-gray shadow-xs">
                          <span className="font-headline text-xl font-bold text-canopy-green">
                            {monogram}
                          </span>
                        </div>
                        <div>
                          <h2 className="font-headline text-lg font-bold text-canopy-green leading-snug">
                            {d.company_name}
                          </h2>
                          <p className="font-body text-xs text-graphite font-medium">
                            {d.role_title}
                          </p>
                        </div>
                      </div>

                      <span className={`px-3 py-1 rounded-full font-body text-[11px] font-bold uppercase border ${eligibilityPill}`}>
                        {d.eligibility_status.replace("_", " ")}
                      </span>
                    </div>

                    {/* Metadata Chips */}
                    <div className="flex items-center gap-2 flex-wrap text-xs font-body">
                      <span className="bg-paper-white/90 text-canopy-green px-3 py-0.5 rounded-full border border-frost-gray/50">
                        {d.location || "Bengaluru / Pan-India"}
                      </span>
                      <span className="bg-paper-white/90 text-coral-pulse font-semibold px-3 py-0.5 rounded-full border border-frost-gray/50">
                        {d.compensation_details?.ctc ? String(d.compensation_details.ctc) : d.work_mode || "Full Time"}
                      </span>
                    </div>

                    {/* Deadline Box */}
                    <div className="bg-paper-white/90 rounded-xl p-3 text-xs font-body border border-frost-gray/50 space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-slate">Registration Cutoff:</span>
                        <span className="font-semibold text-ink-black">
                          {d.registration_end_at ? new Date(d.registration_end_at).toLocaleDateString() : "Open"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate">Document Readiness:</span>
                        <span className="font-semibold text-canopy-green uppercase text-[11px]">
                          {d.document_readiness?.status || "pending"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="pt-2 border-t border-black/5 flex items-center justify-between">
                    <span className="text-[11px] font-body text-graphite">
                      Status: <span className="font-semibold text-canopy-green">{d.registration?.state || "not registered"}</span>
                    </span>

                    <div className="flex items-center gap-2">
                      <Link
                        href="/student/eligibility"
                        className="px-3 py-1.5 rounded-full border border-frost-gray bg-paper-white hover:bg-surface-container font-body text-xs font-medium transition"
                      >
                        Breakdown
                      </Link>
                      <Link
                        href="/student/registration"
                        className="inline-flex items-center gap-1 px-4 py-1.5 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs transition"
                      >
                        <span>{d.registration?.state === "submitted" ? "View Registration" : "Register Now"}</span>
                        <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </StudentShell>
  );
}
