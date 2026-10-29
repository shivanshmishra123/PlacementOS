"use client";

import { useCallback, useEffect, useState } from "react";
import type { StudentEligibilityResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

const badge: Record<string, string> = {
  eligible: "border-emerald-300 bg-emerald-50 text-emerald-800",
  ineligible: "border-red-300 bg-red-50 text-red-800",
  needs_review: "border-amber-300 bg-amber-50 text-amber-800",
};

export default function StudentEligibilityPage() {
  const { client, user } = useAuth();
  const [items, setItems] = useState<StudentEligibilityResponse[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user || user.role !== "student") return;
    try {
      setItems(await client.getMyEligibility());
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load eligibility results");
    }
  }, [client, user]);

  useEffect(() => {
    void load();
  }, [load]);

  async function requestReview(resultId: string) {
    try {
      await client.requestEligibilityReview(resultId, reasons[resultId] ?? "");
      setSubmitted((current) => ({ ...current, [resultId]: true }));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to submit review request");
    }
  }

  if (!user || user.role !== "student") {
    return <main className="p-8">Select a student development persona to view personal eligibility.</main>;
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <p className="text-sm text-slate-500">Personal, scoped explanation</p>
        <h1 className="text-3xl font-bold">My eligibility</h1>
        <p className="mt-2 text-slate-600">Only your own persisted result is shown. Review requests ask the placement office to verify evidence; they do not override eligibility.</p>
      </header>
      {error && <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{error}</div>}
      {items.length === 0 ? (
        <section className="rounded-xl border bg-white p-8 text-center text-slate-600">No completed eligibility evaluation currently includes your profile.</section>
      ) : items.map((item) => (
        <article key={item.result_id} className="rounded-xl border bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">{item.company_name} · {item.drive_title}</h2>
              <p className="text-xs text-slate-500">Policy v{item.policy_version} · evaluated {new Date(item.evaluated_at).toLocaleString()}</p>
            </div>
            <span className={`rounded border px-3 py-1 text-sm font-semibold ${badge[item.outcome]}`}>{item.outcome.replace("_", " ")}</span>
          </div>
          {item.is_stale && <div className="mt-3 rounded border border-red-300 bg-red-50 p-3 text-red-800">Historical result — {item.stale_reason}</div>}
          <p className="mt-4">{item.student_explanation}</p>
          <div className="mt-4 space-y-2">
            {item.predicate_results.map((finding) => (
              <div key={finding.predicate} className="rounded bg-slate-50 p-3 text-sm">
                <p className="font-semibold">{finding.predicate.replace("_", " ")} · {finding.outcome}</p>
                <p>{finding.explanation}</p>
                {finding.outcome !== "true" && <p className="mt-1 font-mono text-xs text-slate-500">{finding.reason_code}</p>}
              </div>
            ))}
          </div>
          {item.outcome !== "eligible" && !submitted[item.result_id] && (
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <input aria-label="Eligibility review reason" value={reasons[item.result_id] ?? ""} onChange={(event) => setReasons((current) => ({ ...current, [item.result_id]: event.target.value }))} placeholder="Describe the academic evidence that should be reviewed" className="min-w-0 flex-1 rounded border p-2" />
              <button disabled={(reasons[item.result_id] ?? "").trim().length < 5} onClick={() => void requestReview(item.result_id)} className="rounded bg-indigo-700 px-4 py-2 text-white disabled:opacity-50">Request evidence review</button>
            </div>
          )}
          {submitted[item.result_id] && <p role="status" className="mt-4 text-emerald-700">Review request submitted. Your result remains unchanged until verified evidence or policy changes.</p>}
        </article>
      ))}
    </main>
  );
}
