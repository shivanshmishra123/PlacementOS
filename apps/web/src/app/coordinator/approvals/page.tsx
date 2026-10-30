"use client";

import { useCallback, useEffect, useState } from "react";
import { CommunicationProposalResponse, DispatchBatchResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

export default function ApprovalCenterPage() {
  const { client } = useAuth();
  const [proposals, setProposals] = useState<CommunicationProposalResponse[]>([]);
  const [batches, setBatches] = useState<DispatchBatchResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [evidence, setEvidence] = useState<Record<string, string>>({});
  const [cancelReasons, setCancelReasons] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      const [proposalRows, batchRows] = await Promise.all([
        client.listCommunicationProposals(),
        client.listDispatchBatches(),
      ]);
      setProposals(proposalRows);
      setBatches(batchRows);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load approval center");
    }
  }, [client]);

  useEffect(() => { void load(); }, [load]);

  const decide = async (proposal: CommunicationProposalResponse, decision: "approved" | "rejected" | "revision_requested") => {
    setBusy(true);
    try {
      await client.decideCommunicationProposal(proposal.id, {
        expected_revision: proposal.revision_number,
        expected_hash: proposal.canonical_hash,
        decision,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  };

  const reconcile = async (operationId: string, resolution: "provider_accepted" | "confirmed_not_accepted") => {
    const note = evidence[operationId]?.trim();
    if (!note) {
      setError("Enter provider or coordinator evidence before resolving an unknown outcome.");
      return;
    }
    setBusy(true);
    try {
      await client.reconcileDispatchOperation(operationId, resolution, note);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reconciliation failed");
    } finally {
      setBusy(false);
    }
  };

  const cancel = async (batchId: string) => {
    const reason = cancelReasons[batchId]?.trim();
    if (!reason) {
      setError("Enter a cancellation reason. Already claimed or transmitted messages cannot be recalled.");
      return;
    }
    setBusy(true);
    try {
      await client.cancelDispatchBatch(batchId, reason);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancellation failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Communication approval center</h1>
        <p className="mt-1 text-sm text-slate-500">Inspect exact recipients and rendered content before authorizing external effects.</p>
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Proposals</h2>
        {proposals.length === 0 && <p className="rounded-xl border border-dashed p-6 text-sm text-slate-500">No communication proposals.</p>}
        {proposals.map((proposal) => (
          <article key={proposal.id} className="rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900">
            <div className="flex flex-wrap justify-between gap-3">
              <div>
                <h3 className="font-semibold">{proposal.draft.communication_kind.replaceAll("_", " ")}</h3>
                <p className="text-xs text-slate-500">{proposal.state} · revision {proposal.revision_number} · {proposal.draft.included_count} recipients</p>
              </div>
              {proposal.state === "pending_approval" && (
                <div className="flex gap-2">
                  <button disabled={busy} onClick={() => void decide(proposal, "approved")} className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white">Approve exact batch</button>
                  <button disabled={busy} onClick={() => void decide(proposal, "revision_requested")} className="rounded-lg border px-3 py-2 text-sm">Request revision</button>
                  <button disabled={busy} onClick={() => void decide(proposal, "rejected")} className="rounded-lg border border-red-300 px-3 py-2 text-sm text-red-700">Reject</button>
                </div>
              )}
            </div>
            <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
              <div><dt className="text-slate-500">Sender</dt><dd>{proposal.draft.sender_email}</dd></div>
              <div><dt className="text-slate-500">Audience hash</dt><dd className="font-mono text-xs">{proposal.draft.audience_hash.slice(0, 16)}</dd></div>
              <div><dt className="text-slate-500">Execution expires</dt><dd>{proposal.execution_expires_at ? new Date(proposal.execution_expires_at).toLocaleString() : "—"}</dd></div>
            </dl>
            <div className="mt-4 max-h-72 space-y-3 overflow-auto rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
              {proposal.draft.recipients.map((recipient) => (
                <details key={recipient.id}>
                  <summary className="cursor-pointer text-sm font-medium">{recipient.display_name} · {recipient.email}</summary>
                  <p className="mt-2 text-sm font-semibold">{recipient.rendered_subject}</p>
                  <pre className="mt-1 whitespace-pre-wrap font-sans text-sm">{recipient.rendered_body}</pre>
                </details>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Dispatch progress</h2>
        {batches.length === 0 && <p className="rounded-xl border border-dashed p-6 text-sm text-slate-500">No approved dispatch batches.</p>}
        {batches.map((batch) => (
          <article key={batch.id} className="rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900">
            <div className="flex justify-between gap-3"><strong>{batch.status.replaceAll("_", " ")}</strong><span className="text-xs text-slate-500">{batch.total_count} logical messages</span></div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs sm:grid-cols-6">
              <div className="rounded bg-slate-100 p-2">Pending<br/><b>{batch.pending_count}</b></div>
              <div className="rounded bg-blue-50 p-2">Accepted<br/><b>{batch.accepted_count}</b></div>
              <div className="rounded bg-emerald-50 p-2">Delivered<br/><b>{batch.delivered_count}</b></div>
              <div className="rounded bg-red-50 p-2">Failed<br/><b>{batch.failed_count}</b></div>
              <div className="rounded bg-amber-50 p-2">Unknown<br/><b>{batch.unknown_count}</b></div>
              <div className="rounded bg-slate-100 p-2">Cancelled<br/><b>{batch.cancelled_count}</b></div>
            </div>
            <p className="mt-3 text-xs text-slate-500">Provider acceptance is not proof of inbox delivery. Cancellation stops only unclaimed work.</p>
            {batch.pending_count > 0 && <div className="mt-3 flex gap-2">
              <input aria-label="Cancellation reason" value={cancelReasons[batch.id] || ""} onChange={(event) => setCancelReasons((current) => ({ ...current, [batch.id]: event.target.value }))} placeholder="Reason for stopping unclaimed messages" className="min-w-0 flex-1 rounded-lg border bg-transparent px-3 py-2 text-sm" />
              <button disabled={busy} onClick={() => void cancel(batch.id)} className="rounded-lg border border-red-300 px-3 py-2 text-sm text-red-700">Stop unclaimed</button>
            </div>}
            <div className="mt-3 divide-y text-sm">
              {batch.operations.map((operation) => <div key={operation.id} className="py-2">
                <div className="flex justify-between"><span>{operation.recipient_name} · {operation.recipient}</span><span>{operation.status}</span></div>
                {operation.status === "unknown" && <div className="mt-2 flex flex-wrap gap-2">
                  <input aria-label={`Reconciliation evidence for ${operation.recipient}`} value={evidence[operation.id] || ""} onChange={(event) => setEvidence((current) => ({ ...current, [operation.id]: event.target.value }))} placeholder="Provider lookup or coordinator evidence" className="min-w-64 flex-1 rounded-lg border bg-transparent px-3 py-2 text-sm" />
                  <button disabled={busy} onClick={() => void reconcile(operation.id, "provider_accepted")} className="rounded-lg border px-3 py-2 text-xs">Mark accepted</button>
                  <button disabled={busy} onClick={() => void reconcile(operation.id, "confirmed_not_accepted")} className="rounded-lg border px-3 py-2 text-xs">Confirm not accepted and retry</button>
                </div>}
              </div>)}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
