"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { EvaluationRunResponse, ParticipantListResponse, PublicationProposalResponse, RequirementResponse } from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";

function localDefault(hours: number) {
  const value = new Date(Date.now() + hours * 60 * 60 * 1000);
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
  return value.toISOString().slice(0, 16);
}

export default function ParticipationWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { client, user } = useAuth();
  const [revision, setRevision] = useState(1);
  const [runs, setRuns] = useState<EvaluationRunResponse[]>([]);
  const [requirements, setRequirements] = useState<RequirementResponse[]>([]);
  const [participants, setParticipants] = useState<ParticipantListResponse | null>(null);
  const [proposal, setProposal] = useState<PublicationProposalResponse | null>(null);
  const [opensAt, setOpensAt] = useState(localDefault(-1));
  const [closesAt, setClosesAt] = useState(localDefault(72));
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!id || user?.role !== "placement_coordinator") return;
    try {
      const [drive, evaluations] = await Promise.all([client.getDrive(id), client.listEvaluationRuns(id)]);
      setRevision(drive.current_revision_number);
      setRuns(evaluations.filter((run) => run.status === "completed" && !run.is_stale));
      try { setRequirements(await client.listDocumentRequirements(id)); } catch { setRequirements([]); }
      try { setParticipants(await client.listParticipants(id)); } catch { setParticipants(null); }
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load participation workspace");
    }
  }, [client, id, user]);

  useEffect(() => { void load(); }, [load]);

  async function configureRequirements() {
    setBusy(true);
    try {
      await client.setDocumentRequirements(id, revision, [
        { document_type: "resume", display_label: "Resume", allowed_extensions: ["pdf", "docx"], required_stage: "registration" },
        { document_type: "marksheet", display_label: "Latest marksheet", allowed_extensions: ["pdf"], required_stage: "scheduling" },
        { document_type: "college_id", display_label: "College identity card", allowed_extensions: ["pdf"], required_stage: "scheduling" },
      ]);
      setMessage("Immutable document requirements created for the current drive revision.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to configure requirements");
    } finally { setBusy(false); }
  }

  async function propose() {
    const evaluation = runs[0];
    if (!evaluation) return;
    setBusy(true);
    try {
      const created = await client.createPublicationProposal(id, {
        expected_drive_revision: revision,
        evaluation_run_id: evaluation.id,
        registration_start_at: new Date(opensAt).toISOString(),
        registration_end_at: new Date(closesAt).toISOString(),
        withdrawal_end_at: new Date(closesAt).toISOString(),
      });
      setProposal(created);
      setMessage("Exact publication proposal created. Review the frozen revision, evaluation, window, and requirements before approval.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create publication proposal");
    } finally { setBusy(false); }
  }

  async function decide(decision: "approved" | "rejected" | "revision_requested") {
    if (!proposal) return;
    setBusy(true);
    try {
      const updated = await client.decidePublicationProposal(proposal.id, {
        expected_revision: proposal.revision_number,
        expected_hash: proposal.canonical_hash,
        decision,
      });
      setProposal(updated);
      setMessage(`Publication proposal ${decision.replace("_", " ")}.`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to decide proposal");
    } finally { setBusy(false); }
  }

  async function registrationAction(
    registrationId: string,
    revisionNumber: number,
    action: "restore" | "withdraw"
  ) {
    const reason = window.prompt(`Reason for coordinator-assisted ${action}:`);
    if (!reason || reason.trim().length < 3) return;
    setBusy(true);
    try {
      await client.coordinatorRegistrationAction(registrationId, revisionNumber, action, reason);
      setMessage(`Registration ${action} recorded with attributable evidence.`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update registration");
    } finally { setBusy(false); }
  }

  if (!user || user.role !== "placement_coordinator") {
    return <main className="rounded-xl border bg-white p-8">Select an assigned coordinator persona to manage participation.</main>;
  }

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-slate-500">Drive {id}</p>
        <h1 className="text-3xl font-bold">Publication and participation</h1>
        <p className="mt-2 text-slate-600">Publication requires an exact approval. It does not send an announcement.</p>
      </header>
      {error && <div role="alert" className="rounded border border-rose-300 bg-rose-50 p-3 text-rose-800">{error}</div>}
      {message && <div role="status" className="rounded border border-emerald-300 bg-emerald-50 p-3 text-emerald-800">{message}</div>}
      <section className="rounded-xl border bg-white p-5">
        <h2 className="text-xl font-semibold">1. Document requirements</h2>
        {requirements.length ? (
          <ul className="mt-3 grid gap-2 md:grid-cols-3">{requirements.map((item) => <li key={item.id} className="rounded border p-3"><strong>{item.display_label}</strong><br/><span className="text-xs text-slate-500">{item.required_stage} · {item.allowed_extensions.join(", ")}</span></li>)}</ul>
        ) : (
          <button disabled={busy} onClick={() => void configureRequirements()} className="mt-3 rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50">Create baseline resume, marksheet and ID requirements</button>
        )}
      </section>
      <section className="rounded-xl border bg-white p-5">
        <h2 className="text-xl font-semibold">2. Exact publication proposal</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <label className="text-sm">Evaluation<select className="mt-1 w-full rounded border p-2" disabled><option>{runs[0] ? `Run ${runs[0].id.slice(0, 8)} · ${runs[0].eligible_count} eligible` : "No current completed run"}</option></select></label>
          <label className="text-sm">Opens at<input className="mt-1 w-full rounded border p-2" type="datetime-local" value={opensAt} onChange={(event) => setOpensAt(event.target.value)} /></label>
          <label className="text-sm">Exclusive deadline<input className="mt-1 w-full rounded border p-2" type="datetime-local" value={closesAt} onChange={(event) => setClosesAt(event.target.value)} /></label>
        </div>
        {!proposal && <button disabled={busy || !requirements.length || !runs.length} onClick={() => void propose()} className="mt-4 rounded bg-indigo-700 px-4 py-2 text-white disabled:opacity-50">Prepare exact proposal</button>}
        {proposal && (
          <div className="mt-4 rounded border border-indigo-200 bg-indigo-50 p-4">
            <p className="font-semibold">Proposal {proposal.state}</p>
            <p className="mt-1 break-all font-mono text-xs">Fingerprint: {proposal.canonical_hash}</p>
            <pre className="mt-3 max-h-56 overflow-auto rounded bg-white p-3 text-xs">{JSON.stringify(proposal.payload, null, 2)}</pre>
            {proposal.state === "pending_approval" && <div className="mt-3 flex gap-2"><button disabled={busy} onClick={() => void decide("approved")} className="rounded bg-emerald-700 px-4 py-2 text-white">Approve exact publication</button><button disabled={busy} onClick={() => void decide("revision_requested")} className="rounded border px-4 py-2">Request revision</button></div>}
          </div>
        )}
      </section>
      <section className="rounded-xl border bg-white p-5">
        <div className="flex items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">3. Candidate participation</h2><p className="text-sm text-slate-500">Combined eligibility, readiness and registration projections.</p></div>{participants && <a href={client.getParticipantExportUrl(id)} className="rounded border px-3 py-2 text-sm">Export safe CSV</a>}</div>
        {participants ? <><div className="mt-3 flex flex-wrap gap-2 text-xs">{Object.entries(participants.counts).map(([key, value]) => <span key={key} className="rounded bg-slate-100 px-2 py-1">{key.replace("_", " ")}: {value}</span>)}</div><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="p-2">Student</th><th>Eligibility</th><th>Readiness</th><th>Registration</th><th>Assisted action</th></tr></thead><tbody>{participants.items.map((item) => <tr key={item.student_profile_id} className="border-b"><td className="p-2"><strong>{item.student_name}</strong><br/><span className="text-xs text-slate-500">{item.student_identifier}</span></td><td>{item.eligibility_status}</td><td>{item.readiness_status}</td><td>{item.registration_state || "not started"}</td><td>{item.registration_id && item.registration_revision && item.registration_state === "eligibility_hold" ? <button disabled={busy || item.eligibility_status !== "eligible"} onClick={() => void registrationAction(item.registration_id!, item.registration_revision!, "restore")} className="rounded border px-2 py-1 disabled:opacity-50">Restore</button> : item.registration_id && item.registration_revision && item.registration_state === "submitted" ? <button disabled={busy} onClick={() => void registrationAction(item.registration_id!, item.registration_revision!, "withdraw")} className="rounded border px-2 py-1 text-rose-700">Withdraw</button> : "—"}</td></tr>)}</tbody></table></div></> : <p className="mt-3 text-sm text-slate-500">Approve publication to populate the participation view.</p>}
      </section>
    </main>
  );
}
