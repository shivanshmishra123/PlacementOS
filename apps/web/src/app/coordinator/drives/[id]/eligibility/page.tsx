"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import type {
  DriveResponse,
  EvaluationRunResponse,
  PolicyResponse,
  PredicateFindingResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";
import { DriveWorkspaceHeader } from "../../../../../components/DriveWorkspaceHeader";

type OutcomeFilter = "" | "eligible" | "ineligible" | "needs_review";

function getPredicateActual(results: PredicateFindingResponse[], name: string): string | null {
  const match = results?.find((p) => p.predicate.toLowerCase().includes(name.toLowerCase()));
  return match?.actual !== undefined && match?.actual !== null ? String(match.actual) : null;
}

export default function EligibilityWorkspacePage() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const router = useRouter();
  const { client, user } = useAuth();

  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [policies, setPolicies] = useState<PolicyResponse[]>([]);
  const [runs, setRuns] = useState<EvaluationRunResponse[]>([]);
  const [current, setCurrent] = useState<EvaluationRunResponse | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [filter, setFilter] = useState<OutcomeFilter>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStudentId, setExpandedStudentId] = useState<string | null>(null);

  const approvedPolicy = useMemo(
    () => policies.find((item) => item.status === "approved") ?? null,
    [policies]
  );

  const load = useCallback(async () => {
    if (!driveId || !user) return;
    try {
      setError(null);
      const [driveData, policyData, runData] = await Promise.all([
        client.getDrive(driveId),
        client.listPolicies(driveId),
        client.listEvaluationRuns(driveId),
      ]);
      setDrive(driveData);
      setPolicies(policyData || []);
      setRuns(runData || []);
      const selected = selectedRunId
        ? runData.find((item) => item.id === selectedRunId) ?? runData[0]
        : runData[0];
      if (selected) {
        setCurrent(await client.getEvaluationRun(selected.id, filter || undefined));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load eligibility workspace");
    }
  }, [client, driveId, filter, selectedRunId, user]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRunEvaluation = async () => {
    if (!driveId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await client.createEvaluationRun(driveId);
      setSelectedRunId(created.id);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to evaluate cohort");
    } finally {
      setBusy(false);
    }
  };

  const eligibleCount = current?.eligible_count ?? 0;
  const ineligibleCount = current?.ineligible_count ?? 0;
  const reviewCount = current?.needs_review_count ?? 0;
  const totalCount = eligibleCount + ineligibleCount + reviewCount;

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {drive && (
          <DriveWorkspaceHeader
            driveId={drive.id}
            companyName={drive.company_name}
            roleTitle={drive.title}
            lifecycleStatus={drive.status}
            currentStepTitle="Eligibility Evaluation"
            actions={
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRunEvaluation}
                  disabled={busy}
                  className="px-4 py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs disabled:opacity-50 transition flex items-center gap-1.5 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                  <span>{busy ? "Evaluating..." : "Run Cohort Evaluation"}</span>
                </button>
                <Link
                  href={`/coordinator/drives/${drive.id}/participation`}
                  className="px-4 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold shadow-xs transition flex items-center gap-1"
                >
                  <span>Participation & Docs</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </Link>
              </div>
            }
          />
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* Evaluation Summary Strip (3 Feature Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Eligible */}
          <div
            onClick={() => setFilter(filter === "eligible" ? "" : "eligible")}
            className={`p-5 rounded-2xl border transition cursor-pointer ${
              filter === "eligible"
                ? "bg-mint-wash border-canopy-green ring-2 ring-canopy-green shadow-xs"
                : "bg-mint-wash/60 border-leaf-bright/30 hover:bg-mint-wash"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-canopy-green uppercase tracking-wider">
                Eligible Candidates
              </span>
              <span className="material-symbols-outlined text-canopy-green text-[22px]">check_circle</span>
            </div>
            <div className="font-headline text-3xl font-bold text-canopy-green">
              {eligibleCount}
            </div>
            <div className="text-xs text-graphite font-body mt-1">
              Passed all verified predicates without rounding (INV-01)
            </div>
          </div>

          {/* Ineligible */}
          <div
            onClick={() => setFilter(filter === "ineligible" ? "" : "ineligible")}
            className={`p-5 rounded-2xl border transition cursor-pointer ${
              filter === "ineligible"
                ? "bg-peach-wash border-coral-pulse ring-2 ring-coral-pulse shadow-xs"
                : "bg-peach-wash/60 border-coral-pulse/30 hover:bg-peach-wash"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-coral-pulse uppercase tracking-wider">
                Ineligible Candidates
              </span>
              <span className="material-symbols-outlined text-coral-pulse text-[22px]">cancel</span>
            </div>
            <div className="font-headline text-3xl font-bold text-coral-pulse">
              {ineligibleCount}
            </div>
            <div className="text-xs text-graphite font-body mt-1">
              Deterministic predicate failure (branch, CGPA, or backlog)
            </div>
          </div>

          {/* Needs Review */}
          <div
            onClick={() => setFilter(filter === "needs_review" ? "" : "needs_review")}
            className={`p-5 rounded-2xl border transition cursor-pointer ${
              filter === "needs_review"
                ? "bg-lilac-wash border-indigo-bloom ring-2 ring-indigo-bloom shadow-xs"
                : "bg-lilac-wash/60 border-indigo-bloom/30 hover:bg-lilac-wash"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-indigo-bloom uppercase tracking-wider">
                Needs Academic Review
              </span>
              <span className="material-symbols-outlined text-indigo-bloom text-[22px]">help</span>
            </div>
            <div className="font-headline text-3xl font-bold text-indigo-bloom">
              {reviewCount}
            </div>
            <div className="text-xs text-graphite font-body mt-1">
              Missing evidence or unverified correction (INV-02)
            </div>
          </div>
        </div>

        {/* Main Cohort Results Table Container */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-frost-gray">
            <div>
              <h2 className="font-headline text-base font-bold text-canopy-green">
                Cohort Evaluation Truth Table ({totalCount} Evaluated)
              </h2>
              <span className="font-body text-xs text-slate">
                Frozen snapshot: {current ? `Run #${current.id.slice(0, 8)} • Policy v${approvedPolicy?.version_number || 1}` : "No run selected"}
              </span>
            </div>

            {/* Run Selector */}
            {runs.length > 1 && (
              <div className="flex items-center gap-2 text-xs font-body">
                <span className="text-graphite font-medium">Evaluation Run:</span>
                <select
                  value={selectedRunId || ""}
                  onChange={(e) => setSelectedRunId(e.target.value)}
                  className="bg-paper-white border border-frost-gray rounded-lg px-2.5 py-1 text-xs"
                >
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      Run #{r.id.slice(0, 8)} ({r.created_at?.slice(0, 10)})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {!current || !current.results || current.results.length === 0 ? (
            <div className="py-16 text-center text-slate font-body text-sm">
              <span className="material-symbols-outlined text-[42px] text-ash mb-2 block">
                playlist_add_check
              </span>
              <p>No evaluation results for this run.</p>
              <button
                onClick={handleRunEvaluation}
                disabled={busy}
                className="mt-3 px-4 py-2 rounded-full bg-canopy-green text-paper-white text-xs font-semibold shadow-xs"
              >
                Execute Evaluation Engine
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full border-collapse text-left font-body text-xs">
                <thead>
                  <tr className="bg-surface-container-low text-graphite font-body text-[11px] uppercase tracking-wider">
                    <th className="py-2.5 px-3 rounded-l-lg font-semibold">Candidate</th>
                    <th className="py-2.5 px-3 font-semibold">Branch</th>
                    <th className="py-2.5 px-3 font-semibold">CGPA</th>
                    <th className="py-2.5 px-3 font-semibold">Backlogs</th>
                    <th className="py-2.5 px-3 font-semibold">Cohort</th>
                    <th className="py-2.5 px-3 font-semibold">Outcome</th>
                    <th className="py-2.5 px-3 rounded-r-lg text-right font-semibold">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-frost-gray">
                  {current.results.map((result) => {
                    const isExpanded = expandedStudentId === result.student_profile_id;
                    const outcomeColor =
                      result.outcome === "eligible"
                        ? "bg-mint-wash text-canopy-green border-leaf-bright/40"
                        : result.outcome === "ineligible"
                        ? "bg-peach-wash text-coral-pulse border-coral-pulse/40"
                        : "bg-lilac-wash text-indigo-bloom border-indigo-bloom/40";

                    const branch = (result as any).branch || getPredicateActual(result.predicate_results, "branch") || "—";
                    const cgpa = (result as any).cgpa ?? getPredicateActual(result.predicate_results, "cgpa") ?? "—";
                    const backlogs = (result as any).active_backlogs ?? getPredicateActual(result.predicate_results, "backlog") ?? "0";
                    const graduationYear = (result as any).graduation_year ?? getPredicateActual(result.predicate_results, "grad") ?? "2027";

                    return (
                      <React.Fragment key={result.student_profile_id}>
                        <tr className="hover:bg-lavender-mist/40 transition-colors">
                          <td className="py-3 px-3">
                            <span className="font-semibold text-ink-black text-sm block">
                              {result.student_name}
                            </span>
                            <span className="font-mono text-[11px] text-slate">
                              {result.student_identifier}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span className="font-medium text-graphite">{branch}</span>
                          </td>
                          <td className="py-3 px-3">
                            <span className="font-mono font-bold text-canopy-green">
                              {cgpa}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span className="font-mono text-graphite">
                              {backlogs}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span className="text-slate">{graduationYear}</span>
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${outcomeColor}`}
                            >
                              {result.outcome.replace("_", " ")}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() =>
                                setExpandedStudentId(isExpanded ? null : result.student_profile_id)
                              }
                              className="text-xs text-canopy-green font-semibold hover:underline inline-flex items-center gap-1"
                            >
                              <span>{isExpanded ? "Hide" : "Audit"}</span>
                              <span className="material-symbols-outlined text-[14px]">
                                {isExpanded ? "expand_less" : "expand_more"}
                              </span>
                            </button>
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr className="bg-lavender-mist/30">
                            <td colSpan={7} className="p-4">
                              <div className="bg-paper-white p-4 rounded-xl border border-frost-gray space-y-3 font-body text-xs">
                                <div className="flex items-center justify-between pb-2 border-b border-frost-gray font-semibold text-graphite text-[11px] uppercase">
                                  <span>Predicate Breakdown (Engine v1.0.0)</span>
                                  <span>Snapshot ID: {result.academic_revision_id ? `${result.academic_revision_id.slice(0, 8)}...` : "none"}</span>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                                  {result.predicate_results?.map((pe: PredicateFindingResponse, pIdx: number) => (
                                    <div
                                      key={pIdx}
                                      className="p-2.5 rounded-lg bg-surface-container-low border border-frost-gray"
                                    >
                                      <div className="flex items-center justify-between text-[11px] mb-1">
                                        <span className="font-bold text-ink-black uppercase">
                                          {pe.predicate}
                                        </span>
                                        <span
                                          className={`font-semibold ${
                                            pe.outcome === "true"
                                              ? "text-leaf-bright"
                                              : pe.outcome === "false"
                                              ? "text-error"
                                              : "text-indigo-bloom"
                                          }`}
                                        >
                                          {pe.outcome === "true" ? "PASS" : pe.outcome === "false" ? "FAIL" : "UNKNOWN"}
                                        </span>
                                      </div>
                                      <div className="text-[10px] text-slate">
                                        Expected: {String(pe.expected ?? "—")}
                                      </div>
                                      <div className="text-[10px] text-graphite">
                                        Actual: {String(pe.actual ?? "—")}
                                      </div>
                                      {pe.reason_code && (
                                        <div className="text-[10px] font-mono text-coral-pulse mt-0.5">
                                          {pe.reason_code}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </CoordinatorShell>
  );
}
