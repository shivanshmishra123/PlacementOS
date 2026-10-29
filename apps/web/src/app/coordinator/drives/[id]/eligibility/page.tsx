"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type {
  DriveResponse,
  EvaluationRunResponse,
  PolicyResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";

type OutcomeFilter = "" | "eligible" | "ineligible" | "needs_review";

const badge: Record<string, string> = {
  eligible: "border-emerald-300 bg-emerald-50 text-emerald-800",
  ineligible: "border-red-300 bg-red-50 text-red-800",
  needs_review: "border-amber-300 bg-amber-50 text-amber-800",
};

export default function EligibilityWorkspacePage() {
  const params = useParams<{ id: string }>();
  const driveId = params.id;
  const { client, user } = useAuth();
  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [policies, setPolicies] = useState<PolicyResponse[]>([]);
  const [runs, setRuns] = useState<EvaluationRunResponse[]>([]);
  const [current, setCurrent] = useState<EvaluationRunResponse | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [filter, setFilter] = useState<OutcomeFilter>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const approvedPolicy = useMemo(
    () => policies.find((item) => item.status === "approved") ?? null,
    [policies]
  );

  const load = useCallback(async () => {
    if (!user) return;
    try {
      setError(null);
      const [driveData, policyData, runData] = await Promise.all([
        client.getDrive(driveId),
        client.listPolicies(driveId),
        client.listEvaluationRuns(driveId),
      ]);
      setDrive(driveData);
      setPolicies(policyData);
      setRuns(runData);
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

  useEffect(() => {
    if (!current || !["queued", "processing"].includes(current.status)) return;
    const timer = window.setInterval(() => void load(), 1500);
    return () => window.clearInterval(timer);
  }, [current, load]);

  async function startEvaluation() {
    if (!approvedPolicy) return;
    setBusy(true);
    setError(null);
    try {
      const created = await client.createEvaluationRun(driveId, approvedPolicy.id);
      setSelectedRunId(created.id);
      setCurrent(created);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to queue evaluation");
    } finally {
      setBusy(false);
    }
  }

  async function selectRun(run: EvaluationRunResponse) {
    setSelectedRunId(run.id);
    setCurrent(await client.getEvaluationRun(run.id, filter || undefined));
  }

  if (!user) return <main className="p-8">Select an assigned coordinator persona to continue.</main>;

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">Phase P05 · deterministic eligibility</p>
          <h1 className="text-3xl font-bold">
            {drive?.company_name ?? "Drive"}: cohort evaluation
          </h1>
          <p className="mt-2 text-slate-600">
            Results use frozen verified academic revisions. The UI displays persisted backend decisions and never recomputes eligibility.
          </p>
        </div>
        <Link className="rounded border px-4 py-2 text-sm" href={`/coordinator/drives/${driveId}/review`}>
          Review policy
        </Link>
      </header>

      {error && <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{error}</div>}

      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-semibold">Approved policy and frozen run</h2>
        {approvedPolicy ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">Policy v{approvedPolicy.version_number}: {approvedPolicy.human_summary}</p>
              <p className="mt-1 break-all font-mono text-xs text-slate-500">{approvedPolicy.canonical_hash}</p>
            </div>
            <button disabled={busy} onClick={startEvaluation} className="rounded bg-indigo-700 px-4 py-2 text-white disabled:opacity-50">
              {busy ? "Queuing…" : "Evaluate current cohort"}
            </button>
          </div>
        ) : (
          <p className="mt-2 text-amber-800">Approve a policy in the review workspace before evaluating students.</p>
        )}
      </section>

      {runs.length > 0 && (
        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-semibold">Run history</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {runs.map((run) => (
              <button key={run.id} onClick={() => void selectRun(run)} className={`rounded border px-3 py-2 text-left text-xs ${current?.id === run.id ? "border-indigo-500 bg-indigo-50" : ""}`}>
                <span className="font-semibold">Policy v{run.policy_version} · {run.status}</span>
                <span className="block text-slate-500">{new Date(run.created_at).toLocaleString()}</span>
                {run.is_stale && <span className="block text-red-700">Historical / stale</span>}
              </button>
            ))}
          </div>
        </section>
      )}

      {current && (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Cohort", current.total_count, "border-slate-300 bg-white"],
              ["Eligible", current.eligible_count, badge.eligible],
              ["Ineligible", current.ineligible_count, badge.ineligible],
              ["Needs review", current.needs_review_count, badge.needs_review],
            ].map(([label, value, style]) => (
              <article key={String(label)} className={`rounded-xl border p-4 ${style}`}>
                <p className="text-sm">{label}</p><p className="text-3xl font-bold">{value}</p>
              </article>
            ))}
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Persisted results</h2>
                <p className="text-xs text-slate-500">Engine {current.engine_version} · {current.duration_ms ?? "—"} ms · cohort {current.cohort_fingerprint.slice(0, 16)}…</p>
              </div>
              <select aria-label="Filter eligibility outcome" className="rounded border p-2" value={filter} onChange={(event) => setFilter(event.target.value as OutcomeFilter)}>
                <option value="">All outcomes</option>
                <option value="eligible">Eligible</option>
                <option value="ineligible">Ineligible</option>
                <option value="needs_review">Needs review</option>
              </select>
            </div>
            {current.is_stale && <div className="mt-3 rounded border border-red-300 bg-red-50 p-3 text-red-800">Historical result: {current.stale_reason}</div>}
            {current.status !== "completed" ? (
              <p className="mt-4 text-slate-600">Run status: {current.status}. The durable worker may safely retry this run.</p>
            ) : (
              <div className="mt-4 space-y-3">
                {current.results.map((result) => (
                  <details key={result.id} className="rounded border p-4">
                    <summary className="cursor-pointer list-none">
                      <span className="font-semibold">{result.student_identifier} · {result.student_name}</span>
                      <span className={`ml-3 inline-flex rounded border px-2 py-0.5 text-xs ${badge[result.outcome]}`}>{result.outcome.replace("_", " ")}</span>
                      <span className="ml-3 text-xs text-slate-500">{result.reason_codes.join(", ") || "All predicates satisfied"}</span>
                    </summary>
                    <p className="mt-3 text-sm">{result.student_explanation}</p>
                    <div className="mt-3 grid gap-2 lg:grid-cols-2">
                      {result.predicate_results.map((finding) => (
                        <div key={finding.predicate} className="rounded bg-slate-50 p-3 text-xs">
                          <p className="font-semibold">{finding.predicate} · {finding.outcome} · {finding.reason_code}</p>
                          <p className="mt-1">{finding.explanation}</p>
                          <p className="mt-1 font-mono text-slate-500">expected {JSON.stringify(finding.expected)} · actual {JSON.stringify(finding.actual)}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                ))}
                {current.results.length === 0 && <p className="text-slate-500">No results match this filter.</p>}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
