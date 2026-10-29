"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import type {
  DriveResponse,
  InterpretationResponse,
  PolicyResponse,
  ProposalResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";

function parseValue(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

export default function DriveReviewPage() {
  const params = useParams<{ id: string }>();
  const { client, user } = useAuth();
  const driveId = params.id;
  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [interpretations, setInterpretations] = useState<InterpretationResponse[]>([]);
  const [policies, setPolicies] = useState<PolicyResponse[]>([]);
  const [proposal, setProposal] = useState<ProposalResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [manualFacts, setManualFacts] = useState("{}");
  const [manualRationale, setManualRationale] = useState("");
  const [fieldPath, setFieldPath] = useState("");
  const [fieldValue, setFieldValue] = useState("");
  const [fieldRationale, setFieldRationale] = useState("");
  const [clarificationValues, setClarificationValues] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    if (!driveId || !user) return;
    setError(null);
    try {
      const [driveData, interpretationData, policyData] = await Promise.all([
        client.getDrive(driveId),
        client.listInterpretations(driveId),
        client.listPolicies(driveId),
      ]);
      setDrive(driveData);
      setInterpretations(interpretationData);
      setPolicies(policyData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the review workspace");
    }
  }, [client, driveId, user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const current = interpretations[0] ?? null;
  const currentPolicy = policies[0] ?? null;
  const latestSource = useMemo(
    () => drive?.source_artifacts.find((source) => source.status === "extracted") ?? null,
    [drive]
  );
  const openClarifications = current?.clarifications.filter((item) => item.status === "open") ?? [];

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The operation failed");
    } finally {
      setBusy(false);
    }
  }

  async function interpretFixture() {
    if (!latestSource) return;
    await runAction(async () => {
      await client.createInterpretation(driveId, {
        source_artifact_id: latestSource.id,
        mode: "fixture",
      });
      setNotice("A reviewable fixture interpretation was created. No facts were approved automatically.");
    });
  }

  async function submitManual(event: FormEvent) {
    event.preventDefault();
    if (!latestSource) return;
    await runAction(async () => {
      const facts = JSON.parse(manualFacts) as Record<string, unknown>;
      await client.createInterpretation(driveId, {
        source_artifact_id: latestSource.id,
        mode: "manual",
        manual_facts: facts,
        rationale: manualRationale,
      });
      setNotice("Manual facts were saved as an attributed review revision.");
    });
  }

  async function submitCorrection(event: FormEvent) {
    event.preventDefault();
    if (!current) return;
    await runAction(async () => {
      await client.correctInterpretation(current.id, {
        field_path: fieldPath,
        corrected_value: parseValue(fieldValue),
        rationale: fieldRationale,
      });
      setFieldPath("");
      setFieldValue("");
      setFieldRationale("");
      setNotice("The attributed correction was recorded and any pending policy review was invalidated.");
    });
  }

  async function resolveClarification(id: string) {
    const value = clarificationValues[id] ?? "";
    await runAction(async () => {
      await client.resolveClarification(id, parseValue(value), "Coordinator-confirmed clarification");
      setNotice("Clarification resolved with coordinator attribution.");
    });
  }

  async function compilePolicy() {
    if (!current) return;
    await runAction(async () => {
      await client.compilePolicy(driveId, current.id);
      setNotice("A deterministic eligibility-v1 policy draft was compiled. No student was evaluated.");
    });
  }

  async function submitReview() {
    if (!currentPolicy) return;
    await runAction(async () => {
      const created = await client.submitPolicyReview(currentPolicy.id);
      setProposal(created);
      setNotice("The exact immutable policy proposal is awaiting a decision.");
    });
  }

  async function decide(decision: "approved" | "rejected" | "revision_requested") {
    if (!proposal) return;
    await runAction(async () => {
      await client.decideProposal(proposal.id, {
        expected_revision: proposal.revision_number,
        expected_hash: proposal.canonical_hash,
        decision,
        comment: `Coordinator selected ${decision}`,
      });
      setProposal(null);
      setNotice(`Proposal ${decision}. The decision is bound to the displayed hash.`);
    });
  }

  if (!user) return <main className="p-8">Sign in as an assigned coordinator to review this drive.</main>;

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <header>
        <p className="text-sm text-slate-500">Drive source review · Phase P04</p>
        <h1 className="text-3xl font-bold">{drive?.company_name ?? "Drive"}: evidence and rule approval</h1>
        <p className="mt-2 text-slate-600">
          Fixture interpretation creates suggestions only. Corrections, clarifications, policy compilation, and approval remain separate attributable actions.
        </p>
      </header>

      {error && <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{error}</div>}
      {notice && <div role="status" className="rounded border border-emerald-300 bg-emerald-50 p-3 text-emerald-800">{notice}</div>}

      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-semibold">1. Create a review revision</h2>
        <p className="mt-1 text-sm text-slate-600">
          Current accepted source: {latestSource?.original_filename ?? "No successfully extracted source"}
        </p>
        <button className="mt-3 rounded bg-indigo-700 px-4 py-2 text-white disabled:opacity-50" disabled={busy || !latestSource} onClick={interpretFixture}>
          Interpret with visible fixture adapter
        </button>
        <details className="mt-4">
          <summary className="cursor-pointer font-medium">Manual structured fallback</summary>
          <form className="mt-3 grid gap-3" onSubmit={submitManual}>
            <label>Structured facts JSON<textarea className="mt-1 min-h-40 w-full rounded border p-2 font-mono text-sm" value={manualFacts} onChange={(event) => setManualFacts(event.target.value)} /></label>
            <label>Attributed rationale<input className="mt-1 w-full rounded border p-2" required minLength={3} value={manualRationale} onChange={(event) => setManualRationale(event.target.value)} /></label>
            <button className="w-fit rounded border px-4 py-2" disabled={busy || !latestSource}>Save manual review revision</button>
          </form>
        </details>
      </section>

      {current && (
        <>
          <section className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold">2. Reviewed facts</h2>
              <p className="text-sm text-slate-500">Revision {current.revision_number} · {current.adapter_id} · {current.status}</p>
              <pre className="mt-3 max-h-[34rem] overflow-auto rounded bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(current.reviewed_facts, null, 2)}</pre>
            </article>
            <article className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold">Source evidence</h2>
              <ul className="mt-3 space-y-3">
                {current.evidence.map((entry, index) => (
                  <li key={`${String(entry.field_path)}-${index}`} className="rounded border p-3 text-sm">
                    <strong>{String(entry.field_path)}</strong>
                    <p className="mt-1 text-slate-700">{String(entry.excerpt)}</p>
                    <p className="mt-1 text-xs text-slate-500">{String(entry.locator_type)} · page {String(entry.page_number ?? "—")} · paragraph {String(entry.paragraph_index ?? "—")}</p>
                  </li>
                ))}
              </ul>
            </article>
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold">3. Blocking clarifications</h2>
            {openClarifications.length === 0 ? <p className="mt-2 text-emerald-700">No unresolved blocking clarification.</p> : (
              <ul className="mt-3 space-y-3">
                {openClarifications.map((item) => (
                  <li key={item.id} className="rounded border border-amber-300 bg-amber-50 p-3">
                    <p className="font-medium">{item.question}</p>
                    <p className="text-xs text-slate-600">{item.reason_code} · {item.field_path}</p>
                    <div className="mt-2 flex gap-2">
                      <input aria-label={`Resolution for ${item.field_path}`} className="min-w-0 flex-1 rounded border p-2" placeholder='Exact value; JSON is accepted' value={clarificationValues[item.id] ?? ""} onChange={(event) => setClarificationValues((values) => ({ ...values, [item.id]: event.target.value }))} />
                      <button className="rounded bg-amber-800 px-3 py-2 text-white" disabled={busy || !(clarificationValues[item.id] ?? "").trim()} onClick={() => resolveClarification(item.id)}>Resolve</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold">4. Attributed field correction</h2>
            <form className="mt-3 grid gap-3 md:grid-cols-3" onSubmit={submitCorrection}>
              <input aria-label="Field path" className="rounded border p-2" placeholder="eligibility_draft.minimum_cgpa" required value={fieldPath} onChange={(event) => setFieldPath(event.target.value)} />
              <input aria-label="Corrected value" className="rounded border p-2" placeholder='"8.00"' required value={fieldValue} onChange={(event) => setFieldValue(event.target.value)} />
              <input aria-label="Correction rationale" className="rounded border p-2" placeholder="Reason and provenance" required minLength={3} value={fieldRationale} onChange={(event) => setFieldRationale(event.target.value)} />
              <button className="w-fit rounded border px-4 py-2" disabled={busy}>Record correction</button>
            </form>
          </section>

          <section className="rounded-xl border bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold">5. Deterministic policy and exact approval</h2>
            <button className="mt-3 rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50" disabled={busy || openClarifications.length > 0} onClick={compilePolicy}>Compile eligibility-v1 policy</button>
            {currentPolicy && (
              <div className="mt-4 rounded border p-4">
                <p className="font-medium">Version {currentPolicy.version_number} · {currentPolicy.status}</p>
                <p className="mt-1">{currentPolicy.human_summary}</p>
                <p className="mt-2 break-all font-mono text-xs">Policy hash: {currentPolicy.canonical_hash}</p>
                {currentPolicy.status === "draft" && <button className="mt-3 rounded bg-indigo-700 px-4 py-2 text-white" disabled={busy} onClick={submitReview}>Submit exact proposal for review</button>}
              </div>
            )}
            {proposal && (
              <div className="mt-4 rounded border-2 border-indigo-400 p-4">
                <p className="font-semibold">Pending proposal revision {proposal.revision_number}</p>
                <p className="mt-2 break-all font-mono text-xs">Envelope hash: {proposal.canonical_hash}</p>
                <pre className="mt-3 overflow-auto rounded bg-slate-100 p-3 text-xs">{JSON.stringify({ payload: proposal.payload, dependencies: proposal.dependencies }, null, 2)}</pre>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className="rounded bg-emerald-700 px-4 py-2 text-white" disabled={busy} onClick={() => decide("approved")}>Approve exact policy</button>
                  <button className="rounded border px-4 py-2" disabled={busy} onClick={() => decide("revision_requested")}>Request revision</button>
                  <button className="rounded bg-red-700 px-4 py-2 text-white" disabled={busy} onClick={() => decide("rejected")}>Reject</button>
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
