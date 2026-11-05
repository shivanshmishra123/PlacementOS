"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { StudentEligibilityResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";
import { StudentShell } from "../../../components/StudentShell";

export default function StudentEligibilityPage() {
  const { client, user } = useAuth();
  const [items, setItems] = useState<StudentEligibilityResponse[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getMyEligibility();
      setItems(res || []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load personal eligibility results");
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void load();
  }, [load]);

  async function requestReview(resultId: string) {
    try {
      await client.requestEligibilityReview(resultId, reasons[resultId] || "Student requested evidence review");
      setSubmitted((current) => ({ ...current, [resultId]: true }));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to submit review request");
    }
  }

  return (
    <StudentShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Header Strip */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-2">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-canopy-green text-[24px]">verified</span>
            <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
              Personal Deterministic Eligibility Breakdown
            </h1>
          </div>
          <p className="font-body text-xs text-graphite">
            Every outcome is evaluated strictly by deterministic rules against your verified academic record (INV-01). No AI model makes eligibility decisions.
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-20 text-center font-body text-sm text-slate animate-pulse">
            Loading your verified evaluation breakdown...
          </div>
        ) : items.length === 0 ? (
          <div className="bg-paper-white rounded-2xl p-12 text-center border border-frost-gray font-body text-slate">
            <span className="material-symbols-outlined text-[42px] text-ash mb-2 block">
              rule
            </span>
            <p className="text-sm">No completed eligibility evaluations for your profile yet.</p>
            <p className="text-xs text-ash mt-1">Drives currently in intake or policy review will appear once evaluated.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {items.map((item) => {
              const isEligible = item.outcome === "eligible";
              const isNeedsReview = item.outcome === "needs_review";

              return (
                <div
                  key={item.result_id}
                  className="bg-paper-white rounded-2xl p-6 sm:p-8 border border-frost-gray shadow-xs space-y-6 font-body text-xs"
                >
                  {/* Drive Overview */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-frost-gray">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-headline text-xl font-bold text-canopy-green">
                          {item.company_name}
                        </span>
                        <span className="text-slate">•</span>
                        <span className="font-headline text-base text-graphite font-semibold">
                          {item.drive_title}
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-slate mt-0.5 block">
                        Evaluation Snapshot: {item.evaluation_run_id?.slice(0, 8)}... • Engine v1.0.0
                      </span>
                    </div>

                    <Link
                      href="/student/registration"
                      className="px-5 py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-semibold text-xs shadow-xs transition flex items-center gap-1.5 self-start sm:self-auto"
                    >
                      <span>Proceed to Registration</span>
                      <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                    </Link>
                  </div>

                  {/* Overall Outcome Banner */}
                  <div
                    className={`p-5 rounded-2xl border flex items-center gap-4 ${
                      isEligible
                        ? "bg-mint-wash border-leaf-bright/40 text-canopy-green"
                        : isNeedsReview
                        ? "bg-lilac-wash border-indigo-bloom/40 text-indigo-bloom"
                        : "bg-peach-wash border-coral-pulse/40 text-coral-pulse"
                    }`}
                  >
                    <span className="material-symbols-outlined text-[32px] shrink-0">
                      {isEligible ? "check_circle" : isNeedsReview ? "help" : "cancel"}
                    </span>
                    <div>
                      <span className="font-headline text-base font-bold uppercase tracking-tight block">
                        {isEligible
                          ? "YOU MEET ALL ELIGIBILITY CRITERIA FOR THIS DRIVE"
                          : isNeedsReview
                          ? "ACADEMIC EVIDENCE REVIEW REQUIRED"
                          : "CURRENT ACADEMIC EVIDENCE DOES NOT MEET THRESHOLD"}
                      </span>
                      <span className="text-xs text-graphite font-body mt-0.5 block">
                        {isEligible
                          ? "All required criteria verified against your academic record. You are eligible to register."
                          : isNeedsReview
                          ? "Missing required backlog or scale evidence requires placement office review (INV-02)."
                          : "One or more academic thresholds (CGPA, Branch, or Backlogs) were not met."}
                      </span>
                    </div>
                  </div>

                  {/* Predicate Breakdown Grid */}
                  <div className="space-y-3">
                    <span className="font-headline text-sm font-bold text-canopy-green block">
                      Predicate-by-Predicate Audit Breakdown
                    </span>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                      {item.predicate_results?.map((pred, pIdx) => {
                        const pass = pred.outcome === "true";
                        const fail = pred.outcome === "false";

                        return (
                          <div
                            key={pIdx}
                            className={`p-4 rounded-xl border space-y-1.5 ${
                              pass
                                ? "bg-mint-wash/30 border-leaf-bright/30"
                                : fail
                                ? "bg-peach-wash/30 border-coral-pulse/30"
                                : "bg-lilac-wash/30 border-indigo-bloom/30"
                            }`}
                          >
                            <div className="flex items-center justify-between text-xs font-semibold">
                              <span className="text-ink-black uppercase">{pred.predicate}</span>
                              <span
                                className={`font-bold px-2 py-0.5 rounded-full text-[10px] ${
                                  pass
                                    ? "bg-mint-wash text-canopy-green"
                                    : fail
                                    ? "bg-peach-wash text-coral-pulse"
                                    : "bg-lilac-wash text-indigo-bloom"
                                }`}
                              >
                                {pass ? "PASS" : fail ? "FAIL" : "UNKNOWN"}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate">
                              Required: <span className="font-semibold text-graphite">{String(pred.expected ?? "")}</span>
                            </div>
                            <div className="text-[11px] text-slate">
                              Your Record: <span className="font-semibold text-ink-black">{String(pred.actual ?? "")}</span>
                            </div>
                            {(pred.reason_code || pred.explanation) && (
                              <div className="text-[10px] text-coral-pulse font-medium pt-1 border-t border-frost-gray/50">
                                {pred.explanation || pred.reason_code}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Review Request Section for Non-Eligible / Needs Review */}
                  {!isEligible && (
                    <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray space-y-3">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-coral-pulse text-[20px]">
                          contact_support
                        </span>
                        <span className="font-headline text-sm font-bold text-canopy-green">
                          Request Academic Evidence Verification
                        </span>
                      </div>
                      <p className="text-slate text-[11px]">
                        If your institutional record contains an error (e.g. recent semester re-evaluation or cleared backlog), submit a request to the placement coordinator.
                      </p>

                      {submitted[item.result_id] ? (
                        <div className="p-2.5 rounded-lg bg-mint-wash text-canopy-green font-semibold text-xs flex items-center gap-2">
                          <span className="material-symbols-outlined text-[16px]">check</span>
                          <span>Evidence review request submitted to coordinator.</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Briefly state reason for review (e.g. Backlog cleared in Sem 5 makeup exam)..."
                            value={reasons[item.result_id] || ""}
                            onChange={(e) =>
                              setReasons({
                                ...reasons,
                                [item.result_id]: e.target.value,
                              })
                            }
                            className="flex-1 bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
                          />
                          <button
                            onClick={() => requestReview(item.result_id)}
                            className="px-4 py-2 rounded-full bg-canopy-green text-paper-white font-semibold text-xs hover:bg-[#062616] transition shrink-0"
                          >
                            Submit Review Request
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </StudentShell>
  );
}
