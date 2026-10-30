"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { WorkflowRunResponse } from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";

const statusTone: Record<string, string> = {
  monitoring: "bg-emerald-100 text-emerald-800",
  running: "bg-blue-100 text-blue-800",
  queued: "bg-blue-100 text-blue-800",
  held: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
  incompatible: "bg-red-100 text-red-800",
};

export default function DriveWorkflowPage() {
  const { id } = useParams<{ id: string }>();
  const { client } = useAuth();
  const [runs, setRuns] = useState<WorkflowRunResponse[]>([]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRuns(await client.listWorkflowRuns(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load workflow runs");
    }
  }, [client, id]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const active = runs.find((run) => !["failed", "completed", "cancelled", "incompatible"].includes(run.status));

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      await client.startWorkflowRun(id);
      setNotice("Workflow start is durably queued. The page will update after the worker reaches its next checkpoint.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start workflow");
    } finally {
      setBusy(false);
    }
  };

  const changeHold = async (event: FormEvent, run: WorkflowRunResponse) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (run.status === "held") {
        await client.releaseWorkflowHold(run.id, run.concurrency_revision, reason);
        setNotice("Operational hold released. Persisted pending work is eligible for relay again.");
      } else {
        await client.placeWorkflowHold(run.id, run.concurrency_revision, reason);
        setNotice("Operational hold placed. New consequential workflow work is blocked.");
      }
      setReason("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change operational hold");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Durable drive workflow</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Follow persisted intake, policy, publication, communication, and monitoring checkpoints. Human decisions stay in their existing review screens.
          </p>
        </div>
        {!active && (
          <button disabled={busy} onClick={() => void start()} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            Start durable workflow
          </button>
        )}
      </div>

      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}

      {active && (
        <section className="rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Current checkpoint</p>
              <h2 className="mt-1 text-xl font-semibold capitalize">{active.current_step.replaceAll("_", " ")}</h2>
            </div>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone[active.status] || "bg-slate-100 text-slate-700"}`}>
              {active.status.replaceAll("_", " ")}
            </span>
          </div>
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
            <div><dt className="text-slate-500">Graph contract</dt><dd className="font-medium">{active.graph_version} / state {active.state_schema_version}</dd></div>
            <div><dt className="text-slate-500">Run revision</dt><dd className="font-medium">{active.concurrency_revision}</dd></div>
            <div><dt className="text-slate-500">Last update</dt><dd className="font-medium">{new Date(active.updated_at).toLocaleString()}</dd></div>
          </dl>

          {(active.pending_proposal_id || active.pending_clarification_id || active.pending_case_id) && (
            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-semibold">Human action is required</p>
              {active.pending_proposal_id && <p className="mt-1">An exact proposal is waiting. <Link href="/coordinator/approvals" className="underline">Open approvals</Link>.</p>}
              {active.pending_clarification_id && <p className="mt-1">A source clarification is waiting in the drive review workspace.</p>}
              {active.pending_case_id && <p className="mt-1">A baseline exception case is open. <Link href="/coordinator/exceptions" className="underline">Open exception inbox</Link>.</p>}
            </div>
          )}

          {active.error_detail && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{active.error_category}: {active.error_detail}</div>}

          <form onSubmit={(event) => void changeHold(event, active)} className="mt-5 flex flex-col gap-3 border-t pt-5 sm:flex-row">
            <input required minLength={3} value={reason} onChange={(event) => setReason(event.target.value)} placeholder={active.status === "held" ? "Why is it safe to release?" : "Reason for operational hold"} className="flex-1 rounded-lg border bg-transparent px-3 py-2 text-sm" />
            <button disabled={busy} className="rounded-lg border border-amber-500 px-4 py-2 text-sm font-semibold text-amber-800 disabled:opacity-50">
              {active.status === "held" ? "Release hold" : "Place hold"}
            </button>
          </form>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Run history</h2>
        {runs.length === 0 ? (
          <div className="rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">No workflow run has been started for this drive.</div>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <article key={run.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-4 text-sm dark:bg-slate-900">
                <div><strong className="capitalize">{run.current_step.replaceAll("_", " ")}</strong><p className="text-xs text-slate-500">Started {new Date(run.created_at).toLocaleString()}</p></div>
                <span className="capitalize text-slate-600">{run.status.replaceAll("_", " ")}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
