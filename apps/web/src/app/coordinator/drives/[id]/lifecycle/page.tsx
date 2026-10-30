"use client";

import type { OutcomeRevisionResponse, ParticipantResponse, RecruitmentRoundResponse, RecruitmentSessionResponse } from "@placementos/api-client";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "../../../../../context/AuthContext";

export default function DriveLifecyclePage() {
  const { id } = useParams<{ id: string }>();
  const { client } = useAuth();
  const [rounds, setRounds] = useState<RecruitmentRoundResponse[]>([]);
  const [sessions, setSessions] = useState<RecruitmentSessionResponse[]>([]);
  const [participants, setParticipants] = useState<ParticipantResponse[]>([]);
  const [outcomes, setOutcomes] = useState<OutcomeRevisionResponse[]>([]);
  const [roundName, setRoundName] = useState("Technical interview");
  const [selectedRound, setSelectedRound] = useState("");
  const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [venue, setVenue] = useState("Interview Room A");
  const [outcome, setOutcome] = useState<"advanced" | "rejected" | "waitlisted" | "selected" | "withdrawn">("advanced");
  const [sourceReference, setSourceReference] = useState("synthetic://employer/result");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [nextRounds, nextSessions, roster, nextOutcomes] = await Promise.all([
        client.listRounds(id), client.listSessions(id), client.listParticipants(id), client.listOutcomes(id),
      ]);
      setRounds(nextRounds);
      setSessions(nextSessions);
      setParticipants(roster.items);
      setOutcomes(nextOutcomes);
      if (!selectedRound && nextRounds[0]) setSelectedRound(nextRounds[0].id);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load lifecycle workspace");
    }
  }, [client, id, selectedRound]);

  useEffect(() => { void load(); }, [load]);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(null); setNotice(null);
    try { await action(); setNotice(success); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "The action could not be completed"); }
    finally { setBusy(false); }
  };

  const addRound = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      const created = await client.createRound(id, { sequence_number: rounds.length + 1, name: roundName, round_type: "interview", requires_previous_round_outcome: rounds.length > 0 });
      setSelectedRound(created.id);
    }, "Round added as an internal draft stage.");
  };

  const addSession = (event: FormEvent) => {
    event.preventDefault();
    void run(() => client.createSession(selectedRound, {
      start_at: new Date(startAt).toISOString(), end_at: new Date(endAt).toISOString(), timezone: "Asia/Kolkata",
      buffer_minutes: 0, capacity: selectedStudents.length, venue, panel_members: [], student_profile_ids: selectedStudents,
    }), "Session revision saved. It is not visible to students until approved.");
  };

  const publish = (session: RecruitmentSessionResponse) => void run(async () => {
    if (!session.current_revision_id) throw new Error("This session has no revision");
    const proposal = await client.proposeSchedule(session.current_revision_id);
    await client.decideSchedule(proposal, "approved");
  }, "The exact session and participant revision is published.");

  const publishResult = (session: RecruitmentSessionResponse, studentProfileId: string) => void run(async () => {
    const revision = await client.recordOutcome(session.round_id, { student_profile_id: studentProfileId, outcome, source_type: "coordinator_entry", source_reference: sourceReference });
    const proposal = await client.proposeResult(revision.id);
    await client.decideResult(proposal, "approved");
  }, `The exact ${outcome} result revision is now visible to that student.`);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h1 className="text-2xl font-bold">Schedule, results and closure</h1><p className="mt-1 text-sm text-slate-500">Draft internally, approve exact assignments, then complete results and freeze reports.</p></div>
        <Link href={`/coordinator/drives/${id}/participation`} className="rounded-lg border px-3 py-2 text-sm">Open participant readiness</Link>
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={addRound} className="space-y-3 rounded-xl border bg-white p-5 dark:bg-slate-900">
          <h2 className="font-semibold">1. Add an ordered round</h2>
          <input required value={roundName} onChange={(e) => setRoundName(e.target.value)} className="w-full rounded-lg border bg-transparent px-3 py-2" aria-label="Round name" />
          <button disabled={busy} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Add round {rounds.length + 1}</button>
          <ol className="space-y-1 text-sm text-slate-600">{rounds.map((round) => <li key={round.id}>{round.sequence_number}. {round.name} <span className="text-xs">({round.status})</span></li>)}</ol>
        </form>

        <form onSubmit={addSession} className="space-y-3 rounded-xl border bg-white p-5 dark:bg-slate-900">
          <h2 className="font-semibold">2. Draft a session</h2>
          <select required value={selectedRound} onChange={(e) => setSelectedRound(e.target.value)} className="w-full rounded-lg border bg-transparent px-3 py-2"><option value="">Choose round</option>{rounds.map((round) => <option key={round.id} value={round.id}>{round.sequence_number}. {round.name}</option>)}</select>
          <div className="grid grid-cols-2 gap-3"><label className="text-sm">Start<input required type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} className="mt-1 w-full rounded-lg border bg-transparent px-3 py-2" /></label><label className="text-sm">End<input required type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} className="mt-1 w-full rounded-lg border bg-transparent px-3 py-2" /></label></div>
          <input required value={venue} onChange={(e) => setVenue(e.target.value)} className="w-full rounded-lg border bg-transparent px-3 py-2" aria-label="Venue" />
          <fieldset className="max-h-40 overflow-auto rounded-lg border p-3"><legend className="px-1 text-sm font-medium">Submitted, eligible participants</legend>{participants.filter((p) => p.registration_state === "submitted" && p.eligibility_status === "eligible").map((p) => <label key={p.student_profile_id} className="flex gap-2 py-1 text-sm"><input type="checkbox" checked={selectedStudents.includes(p.student_profile_id)} onChange={(e) => setSelectedStudents(e.target.checked ? [...selectedStudents, p.student_profile_id] : selectedStudents.filter((x) => x !== p.student_profile_id))} />{p.student_name} &middot; {p.readiness_status}</label>)}</fieldset>
          <button disabled={busy || selectedStudents.length === 0} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Save private draft</button>
        </form>
      </div>

      <section className="space-y-3"><div className="flex flex-wrap items-end gap-3"><div><h2 className="text-lg font-semibold">Sessions, attendance and employer results</h2><p className="text-sm text-slate-500">Attendance is recorded independently from the employer outcome.</p></div><select value={outcome} onChange={(e) => setOutcome(e.target.value as typeof outcome)} className="rounded-lg border bg-transparent px-3 py-2 text-sm"><option value="advanced">Advanced</option><option value="waitlisted">Waitlisted</option><option value="selected">Selected</option><option value="rejected">Rejected</option><option value="withdrawn">Withdrawn</option></select><input value={sourceReference} onChange={(e) => setSourceReference(e.target.value)} aria-label="Employer result source reference" className="min-w-64 rounded-lg border bg-transparent px-3 py-2 text-sm" /></div>{sessions.length === 0 ? <div className="rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">No sessions yet.</div> : sessions.map((session) => <article key={session.id} className="rounded-xl border bg-white p-4 text-sm dark:bg-slate-900"><div className="flex flex-wrap items-center justify-between gap-3"><div><strong>{session.revision ? new Date(session.revision.start_at).toLocaleString() : "No revision"}</strong><p className="text-slate-500">{session.revision?.venue} &middot; {session.assignments.length} participant(s) &middot; {session.status}</p></div>{session.current_revision_id !== session.published_revision_id && <button disabled={busy} onClick={() => publish(session)} className="rounded-lg border border-brand-600 px-3 py-2 font-semibold text-brand-700">Review & publish exact revision</button>}</div>{session.status !== "draft" && <div className="mt-3 space-y-2 border-t pt-3">{session.assignments.filter((assignment) => assignment.status === "published").map((assignment) => <div key={assignment.student_profile_id} className="flex flex-wrap items-center justify-between gap-2"><span>{participants.find((p) => p.student_profile_id === assignment.student_profile_id)?.student_name || assignment.student_profile_id}</span><div className="flex gap-2"><button disabled={busy} onClick={() => void run(() => client.recordAttendance(session.id, assignment.student_profile_id, "present"), "Attendance revision recorded as present; no result was inferred.")} className="rounded border px-2 py-1">Mark present</button><button disabled={busy || sourceReference.length < 3} onClick={() => publishResult(session, assignment.student_profile_id)} className="rounded border px-2 py-1 capitalize">Record &amp; publish {outcome}</button></div></div>)}<button disabled={busy} onClick={() => void run(() => client.completeSession(session.id), "Session completed after attendance and outcome checks.")} className="rounded-lg bg-emerald-700 px-3 py-2 text-white">Complete session</button></div>}</article>)}</section>

      <section className="rounded-xl border bg-white p-5 dark:bg-slate-900"><h2 className="font-semibold">3. Reporting and closure</h2><p className="mt-1 text-sm text-slate-500">Closure remains blocked until registration, sessions, outcomes, proposals, deliveries and cases are resolved.</p><input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Attributable reason" className="mt-4 w-full rounded-lg border bg-transparent px-3 py-2" /><div className="mt-3 flex flex-wrap gap-2"><button disabled={busy || reason.length < 3} onClick={() => void run(() => client.closeRegistration(id, reason), "Registration closed.")} className="rounded-lg border px-3 py-2 text-sm">Close registration</button><button disabled={busy || reason.length < 3} onClick={() => void run(() => client.freezeReport(id, reason), "Frozen operational report created.")} className="rounded-lg border px-3 py-2 text-sm">Freeze report</button><button disabled={busy || reason.length < 3} onClick={() => void run(() => client.closeDrive(id, reason), "Drive closed with a frozen closure report.")} className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white">Close drive</button><button disabled={busy || reason.length < 3} onClick={() => void run(() => client.reopenDrive(id, reason), "Drive reopened; prior closure snapshot is preserved.")} className="rounded-lg border border-amber-500 px-3 py-2 text-sm text-amber-800">Reopen</button></div></section>
      {outcomes.length > 0 && <section className="rounded-xl border bg-white p-5 dark:bg-slate-900"><h2 className="font-semibold">Employer result revision history</h2><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="py-2">Student</th><th>Revision</th><th>Outcome</th><th>Visibility</th><th>Source</th></tr></thead><tbody>{outcomes.map((item) => <tr key={item.id} className="border-b"><td className="py-2">{participants.find((p) => p.student_profile_id === item.student_profile_id)?.student_name || item.student_profile_id}</td><td>{item.revision_number}</td><td className="capitalize">{item.outcome}</td><td>{item.published_at ? "Published" : "Internal"}</td><td>{item.source_reference}</td></tr>)}</tbody></table></div></section>}
    </div>
  );
}
