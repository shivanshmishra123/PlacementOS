"use client";

import type { StudentScheduleResult } from "@placementos/api-client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";

export default function StudentScheduleResultsPage() {
  const { client } = useAuth();
  const [items, setItems] = useState<StudentScheduleResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => { try { setItems(await client.listMyScheduleResults()); setError(null); } catch (err) { setError(err instanceof Error ? err.message : "Could not load your schedule"); } }, [client]);
  useEffect(() => { void load(); }, [load]);
  return <div className="space-y-6"><div><h1 className="text-2xl font-bold">My schedule and results</h1><p className="mt-1 text-sm text-slate-500">Only approved sessions and result revisions assigned to you appear here.</p></div>{error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}{items.length === 0 ? <div className="rounded-xl border border-dashed p-10 text-center text-sm text-slate-500">No approved session has been assigned to you.</div> : <div className="grid gap-4 md:grid-cols-2">{items.map((item) => <article key={item.session_id} className="rounded-xl border bg-white p-5 dark:bg-slate-900"><p className="text-xs font-semibold uppercase text-brand-700">{item.round}</p><h2 className="mt-1 text-lg font-semibold">{new Date(item.start_at).toLocaleString()}</h2><p className="text-sm text-slate-500">Until {new Date(item.end_at).toLocaleTimeString()} · {item.timezone}</p><p className="mt-3 text-sm">{item.venue || "Online session"}</p>{item.meeting_url && <a className="mt-2 inline-block text-sm text-brand-700 underline" href={item.meeting_url}>Open meeting link</a>}<div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800">{item.outcome ? <><span className="font-medium capitalize">{item.outcome.outcome}</span><p className="mt-1 text-xs text-slate-500">Published result revision {item.outcome.revision_number}</p></> : <span className="text-slate-500">No result has been published.</span>}</div></article>)}</div>}</div>;
}
