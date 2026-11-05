"use client";

import type { StudentScheduleResult } from "@placementos/api-client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import { StudentShell } from "../../../components/StudentShell";

export default function StudentScheduleResultsPage() {
  const { client } = useAuth();
  const [items, setItems] = useState<StudentScheduleResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.listMyScheduleResults();
      setItems(res || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load personal schedule and results");
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <StudentShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Header Strip */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-2">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-canopy-green text-[26px]">event_available</span>
            <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
              My Interview Schedule & Verified Recruitment Results
            </h1>
          </div>
          <p className="font-body text-xs text-graphite">
            Only approved interview sessions and student-published outcome revisions appear here (INV-04, INV-10).
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-20 text-center font-body text-sm text-slate animate-pulse">
            Loading assigned sessions and results...
          </div>
        ) : items.length === 0 ? (
          <div className="bg-paper-white rounded-2xl p-12 text-center border border-frost-gray font-body text-slate">
            <span className="material-symbols-outlined text-[42px] text-ash mb-2 block">
              calendar_today
            </span>
            <p className="text-sm">No scheduled sessions or published outcomes assigned to you yet.</p>
            <p className="text-xs text-ash mt-1">Once coordinators publish interview slots for registered drives, they will display here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-body text-xs">
            {items.map((item) => {
              const hasOutcome = !!item.outcome;
              const isSelected = item.outcome?.outcome === "selected";
              const isAdvanced = item.outcome?.outcome === "advanced";

              return (
                <div
                  key={item.session_id}
                  className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    {/* Round Header */}
                    <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                      <span className="font-headline text-sm font-bold text-canopy-green uppercase tracking-wide">
                        {item.round}
                      </span>
                      <span className="bg-sky-wash text-deep-teal px-2.5 py-0.5 rounded-full text-[10px] font-bold">
                        {item.timezone || "Asia/Kolkata"}
                      </span>
                    </div>

                    {/* Time & Venue */}
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2 text-ink-black font-semibold text-sm">
                        <span className="material-symbols-outlined text-coral-pulse text-[18px]">schedule</span>
                        <span>
                          {new Date(item.start_at).toLocaleDateString(undefined, {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          })} • {new Date(item.start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - {new Date(item.end_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-graphite text-xs">
                        <span className="material-symbols-outlined text-canopy-green text-[18px]">location_on</span>
                        <span>Venue / Link: {item.venue || "Placement Operations Centre - Room 204"}</span>
                      </div>

                      {item.meeting_url && (
                        <a
                          href={item.meeting_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-coral-pulse hover:underline font-semibold text-xs mt-1"
                        >
                          <span>Open Online Interview Room</span>
                          <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Outcome Box */}
                  <div className="pt-3 border-t border-frost-gray">
                    {hasOutcome ? (
                      <div
                        className={`p-3.5 rounded-xl border flex items-center justify-between ${
                          isSelected
                            ? "bg-mint-wash border-leaf-bright/40 text-canopy-green"
                            : isAdvanced
                            ? "bg-sky-wash border-sky-signal/40 text-deep-teal"
                            : "bg-surface-container border-frost-gray text-graphite"
                        }`}
                      >
                        <div>
                          <span className="font-headline text-xs font-bold uppercase block">
                            Outcome: {item.outcome?.outcome}
                          </span>
                          <span className="text-[10px] text-slate mt-0.5 block">
                            Revision #{item.outcome?.revision_number} • Published by Placement Coordinator
                          </span>
                        </div>

                        <span className="material-symbols-outlined text-[24px]">
                          {isSelected ? "stars" : isAdvanced ? "trending_up" : "task_alt"}
                        </span>
                      </div>
                    ) : (
                      <div className="p-3 rounded-xl bg-surface-container-low text-slate text-center text-[11px]">
                        Session attendance recorded. Awaiting employer result publication.
                      </div>
                    )}
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
