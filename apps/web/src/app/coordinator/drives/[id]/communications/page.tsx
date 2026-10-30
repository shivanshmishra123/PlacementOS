"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  AudienceType,
  CommunicationDraftResponse,
  CommunicationKind,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";

export default function DriveCommunicationsPage() {
  const { id } = useParams<{ id: string }>();
  const { client, user } = useAuth();
  const [kind, setKind] = useState<CommunicationKind>("drive_announcement");
  const [audience, setAudience] = useState<AudienceType>("current_eligible");
  const [replyTo, setReplyTo] = useState("");
  const [drafts, setDrafts] = useState<CommunicationDraftResponse[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (user?.email) setReplyTo(user.email);
  }, [user]);

  const load = async () => {
    try {
      setDrafts(await client.listCommunicationDrafts(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load communication drafts");
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const createDraft = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await client.createCommunicationDraft(id, {
        communication_kind: kind,
        audience_type: audience,
        reply_to: replyTo,
      });
      setDrafts((current) => [created, ...current]);
      setNotice("Exact recipients and personalized message renders are now frozen for review.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create draft");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (draft: CommunicationDraftResponse) => {
    setBusy(true);
    setError(null);
    try {
      const expires = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
      await client.submitCommunicationReview(draft.id, expires);
      setNotice("Proposal submitted. A reviewer must approve this exact content and audience before dispatch.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit review");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Drive communications</h1>
        <p className="mt-1 text-sm text-slate-500">
          Select a deterministic audience, freeze every personalized message, then request exact approval.
        </p>
      </div>

      <form onSubmit={createDraft} className="grid gap-4 rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900 md:grid-cols-2">
        <label className="text-sm font-medium">
          Message type
          <select className="mt-1 w-full rounded-lg border bg-transparent p-2" value={kind} onChange={(e) => setKind(e.target.value as CommunicationKind)}>
            <option value="drive_announcement">Drive announcement</option>
            <option value="registration_deadline_reminder">Registration deadline reminder</option>
            <option value="missing_document_reminder">Missing-document reminder</option>
            <option value="clarification">Clarification</option>
          </select>
        </label>
        <label className="text-sm font-medium">
          Audience query
          <select className="mt-1 w-full rounded-lg border bg-transparent p-2" value={audience} onChange={(e) => setAudience(e.target.value as AudienceType)}>
            <option value="current_eligible">Current eligible students</option>
            <option value="submitted_registrants">Submitted registrants</option>
            <option value="required_document_findings">Students with document findings</option>
          </select>
        </label>
        <label className="text-sm font-medium md:col-span-2">
          Reply/support contact
          <input required type="email" className="mt-1 w-full rounded-lg border bg-transparent p-2" value={replyTo} onChange={(e) => setReplyTo(e.target.value)} />
        </label>
        <div className="md:col-span-2">
          <button disabled={busy} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            Freeze draft and audience
          </button>
        </div>
      </form>

      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}

      <div className="space-y-4">
        {drafts.length === 0 && <div className="rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">No frozen communication drafts yet.</div>}
        {drafts.map((draft) => (
          <article key={draft.id} className="rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{draft.communication_kind.replaceAll("_", " ")}</h2>
                <p className="text-xs text-slate-500">Revision {draft.revision_number} · {draft.state} · content {draft.content_hash.slice(0, 12)}</p>
              </div>
              {draft.state === "draft" && <button disabled={busy} onClick={() => void submit(draft)} className="rounded-lg border border-brand-600 px-3 py-2 text-sm font-semibold text-brand-700">Submit for approval</button>}
            </div>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-4">
              <div><span className="block text-slate-500">Included</span><strong>{draft.included_count}</strong></div>
              <div><span className="block text-slate-500">Excluded</span><strong>{draft.excluded_count}</strong></div>
              <div><span className="block text-slate-500">Duplicates</span><strong>{draft.duplicate_count}</strong></div>
              <div><span className="block text-slate-500">Unresolved</span><strong>{draft.unresolved_count}</strong></div>
            </div>
            {draft.recipients[0] && (
              <div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm dark:bg-slate-800">
                <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Exact sample for {draft.recipients[0].display_name}</p>
                <p className="font-semibold">{draft.recipients[0].rendered_subject}</p>
                <pre className="mt-2 whitespace-pre-wrap font-sans text-slate-600 dark:text-slate-300">{draft.recipients[0].rendered_body}</pre>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
