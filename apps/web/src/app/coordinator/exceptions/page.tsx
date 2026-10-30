"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { ExceptionCaseResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

export default function ExceptionInboxPage() {
  const { client } = useAuth();
  const [cases, setCases] = useState<ExceptionCaseResponse[]>([]);
  const [filter, setFilter] = useState("open");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setCases(await client.listExceptionCases(filter || undefined));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load exception cases");
    }
  }, [client, filter]);

  useEffect(() => { void load(); }, [load]);

  const act = async (event: FormEvent, item: ExceptionCaseResponse, action: "acknowledged" | "resolved" | "dismissed") => {
    event.preventDefault();
    setBusy(item.id);
    try {
      await client.actOnExceptionCase(item.id, action, notes[item.id] || "Coordinator reviewed this case");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update exception case");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="text-2xl font-bold">Exception inbox</h1><p className="mt-1 text-sm text-slate-500">Review unresolved inputs, stale approvals, failed jobs, and uncertain delivery outcomes.</p></div>
        <label className="text-sm">Status<select value={filter} onChange={(event) => setFilter(event.target.value)} className="ml-2 rounded-lg border bg-transparent p-2"><option value="">All</option><option value="open">Open</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option><option value="dismissed">Dismissed</option></select></label>
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {cases.length === 0 && <div className="rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">No cases match this status.</div>}
      <div className="space-y-4">
        {cases.map((item) => (
          <article key={item.id} className="rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900">
            <div className="flex flex-wrap justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-slate-500">{item.category.replaceAll("_", " ")}</p><h2 className="mt-1 font-semibold">{item.proposed_next_action}</h2></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold capitalize text-amber-800">{item.severity} · {item.status}</span></div>
            <p className="mt-3 text-sm text-slate-600">Evidence: {JSON.stringify(item.evidence)}</p>
            <Link href={`/coordinator/drives/${item.drive_id}/workflow`} className="mt-2 inline-block text-sm font-medium text-brand-700 underline">Open drive workflow</Link>
            {item.status !== "resolved" && item.status !== "dismissed" && (
              <form className="mt-4 flex flex-col gap-2 border-t pt-4 sm:flex-row">
                <input required minLength={3} value={notes[item.id] || ""} onChange={(event) => setNotes((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="Resolution evidence or acknowledgement note" className="flex-1 rounded-lg border bg-transparent px-3 py-2 text-sm" />
                <button disabled={busy === item.id} onClick={(event) => void act(event, item, "acknowledged")} className="rounded-lg border px-3 py-2 text-sm">Acknowledge</button>
                <button disabled={busy === item.id} onClick={(event) => void act(event, item, "resolved")} className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white">Resolve and resume</button>
              </form>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
