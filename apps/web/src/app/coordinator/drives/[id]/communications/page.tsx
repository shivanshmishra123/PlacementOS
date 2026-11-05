"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  api,
  AudienceType,
  CommunicationDraftResponse,
  CommunicationProposalResponse,
  CommunicationKind,
  DriveResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";
import { DriveWorkspaceHeader } from "../../../../../components/DriveWorkspaceHeader";

export default function DriveCommunicationsPage() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const { client, user } = useAuth();

  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [kind, setKind] = useState<CommunicationKind>("drive_announcement");
  const [audience, setAudience] = useState<AudienceType>("current_eligible");
  const [replyTo, setReplyTo] = useState("");
  const [drafts, setDrafts] = useState<CommunicationDraftResponse[]>([]);
  const [proposals, setProposals] = useState<CommunicationProposalResponse[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (user?.email) setReplyTo(user.email);
  }, [user]);

  const load = useCallback(async () => {
    if (!driveId) return;
    try {
      const [d, dr, pr] = await Promise.all([
        client.getDrive(driveId),
        client.listCommunicationDrafts(driveId),
        client.listCommunicationProposals(),
      ]);
      setDrive(d);
      setDrafts(dr || []);
      setProposals(pr || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load communications workspace");
    }
  }, [client, driveId]);

  useEffect(() => {
    void load();
  }, [load]);

  const createDraft = async (event: FormEvent) => {
    event.preventDefault();
    if (!driveId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await client.createCommunicationDraft(driveId, {
        communication_kind: kind,
        audience_type: audience,
        reply_to: replyTo || "placements@apex.edu",
      });
      setDrafts((current) => [created, ...current]);
      setNotice("Exact audience frozen into immutable outbox batch. Ready for authorization.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not compile communication draft");
    } finally {
      setBusy(false);
    }
  };

  const submitProposal = async (draft: CommunicationDraftResponse) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
      const proposal = await client.submitCommunicationReview(draft.id, expiresAt);
      setNotice(`Proposal #${proposal.id.slice(0, 8)} drafted for approval.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit communication proposal");
    } finally {
      setBusy(false);
    }
  };

  const approveProposal = async (proposal: CommunicationProposalResponse) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await client.decideCommunicationProposal(proposal.id, {
        expected_revision: proposal.revision_number,
        expected_hash: proposal.canonical_hash,
        decision: "approved",
        comment: "Coordinator verified recipient count and personalized template merge.",
      });
      setNotice("Proposal approved! Transactional outbox relay dispatching via SMTP sink.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not approve proposal");
    } finally {
      setBusy(false);
    }
  };

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {drive && (
          <DriveWorkspaceHeader
            driveId={drive.id}
            companyName={drive.company_name}
            roleTitle={drive.title}
            lifecycleStatus={drive.status}
            currentStepTitle="Communications Workspace"
            actions={
              <Link
                href={`/coordinator/drives/${drive.id}/lifecycle`}
                className="px-4 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold shadow-xs transition flex items-center gap-1"
              >
                <span>Lifecycle & Rounds</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </Link>
            }
          />
        )}

        {notice && (
          <div className="p-3.5 rounded-xl bg-mint-wash text-canopy-green font-body text-xs font-semibold border border-leaf-bright/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-leaf-bright">check_circle</span>
            <span>{notice}</span>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* 2-Column Responsive Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (5 cols): Rule Builder & Dispatch Form */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
              <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
                <span className="material-symbols-outlined text-canopy-green text-[22px]">outgoing_mail</span>
                <div>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Message Rule Builder
                  </h2>
                  <span className="text-slate text-[11px]">
                    Freeze exact audience & template renders (INV-04, INV-05).
                  </span>
                </div>
              </div>

              <form onSubmit={createDraft} className="space-y-4">
                <div>
                  <label className="block text-graphite font-semibold mb-1">Communication Type</label>
                  <select
                    value={kind}
                    onChange={(e) => setKind(e.target.value as CommunicationKind)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs text-ink-black focus:ring-2 focus:ring-canopy-green"
                  >
                    <option value="drive_announcement">Drive Announcement & Registration Invite</option>
                    <option value="missing_documents_reminder">Missing Documents Checklist Reminder</option>
                    <option value="registration_deadline_reminder">Registration Cutoff Deadline Reminder</option>
                    <option value="interview_schedule_notice">Interview Schedule & Session Notice</option>
                    <option value="result_notice">Round Outcome / Selection Memo</option>
                  </select>
                </div>

                <div>
                  <label className="block text-graphite font-semibold mb-1">Target Audience Policy</label>
                  <select
                    value={audience}
                    onChange={(e) => setAudience(e.target.value as AudienceType)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs text-ink-black focus:ring-2 focus:ring-canopy-green"
                  >
                    <option value="current_eligible">Current Verified Eligible Students</option>
                    <option value="submitted_registrants">Officially Submitted Registrants</option>
                    <option value="required_document_findings">Students with Pending/Blocked Documents</option>
                  </select>
                </div>

                <div>
                  <label className="block text-graphite font-semibold mb-1">Reply-To Address</label>
                  <input
                    type="email"
                    required
                    value={replyTo}
                    onChange={(e) => setReplyTo(e.target.value)}
                    placeholder="placements@apex.edu"
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <div className="p-3 bg-lavender-mist/50 rounded-xl border border-frost-gray text-[11px] text-graphite space-y-1">
                  <span className="font-bold text-canopy-green block">Dispatch Guarantees:</span>
                  <p>• Deduplicated operation keys prevent double-sends on queue retry.</p>
                  <p>• Changes to eligibility invalidates unsent stale emails.</p>
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="w-full py-2.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs shadow-xs disabled:opacity-50 transition"
                >
                  {busy ? "Freezing Audience..." : "Freeze Audience & Draft Message"}
                </button>
              </form>
            </div>
          </div>

          {/* Right Column (7 cols): Frozen Drafts & Approval Status */}
          <div className="lg:col-span-7 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
              <div>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Frozen Communication Payloads
                </h2>
                <span className="font-body text-xs text-slate">
                  Attributed action approvals & outbox dispatch telemetry.
                </span>
              </div>
              <span className="bg-mint-wash text-canopy-green font-body text-xs px-2.5 py-0.5 rounded-full font-bold">
                {drafts.length} Batches
              </span>
            </div>

            {drafts.length === 0 ? (
              <div className="py-16 text-center text-slate font-body text-xs">
                No communication drafts compiled yet. Use the rule builder to generate an exact audience snapshot.
              </div>
            ) : (
              <div className="space-y-4">
                {drafts.map((draft) => {
                  const prop = proposals.find((p) => p.draft?.id === draft.id);
                  const status = prop?.state || draft.state || "DRAFT";

                  return (
                    <div
                      key={draft.id}
                      className="p-5 rounded-2xl bg-surface-container-low border border-frost-gray space-y-3 font-body text-xs shadow-2xs"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-headline text-sm font-bold text-canopy-green">
                              {draft.communication_kind.replace(/_/g, " ").toUpperCase()}
                            </span>
                            <span className="bg-sky-wash text-deep-teal px-2 py-0.5 rounded-full text-[10px] font-bold">
                              {draft.audience_type}
                            </span>
                          </div>
                          <span className="font-mono text-[10px] text-slate mt-0.5 block">
                            Draft ID: {draft.id.slice(0, 8)}... • Hash: {draft.content_hash?.slice(0, 10)}...
                          </span>
                        </div>

                        <span className="bg-peach-wash text-coral-pulse px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase">
                          {status}
                        </span>
                      </div>

                      {/* Recipient Count & Subject */}
                      <div className="bg-paper-white p-3 rounded-xl border border-frost-gray space-y-1.5">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate">Frozen Recipient Count:</span>
                          <span className="font-bold text-ink-black text-sm">{draft.included_count} Students</span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate">Subject Line:</span>
                          <span className="font-semibold text-canopy-green truncate">{draft.subject_template}</span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="pt-2 flex items-center justify-between">
                        <span className="text-[11px] text-slate">
                          Reply-To: <span className="font-medium text-graphite">{draft.reply_to}</span>
                        </span>

                        <div className="flex items-center gap-2">
                          {!prop ? (
                            <button
                              onClick={() => submitProposal(draft)}
                              disabled={busy}
                              className="px-4 py-1.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white text-xs font-semibold shadow-2xs transition"
                            >
                              Submit Proposal
                            </button>
                          ) : prop.state === "pending" || prop.state === "draft" ? (
                            <button
                              onClick={() => approveProposal(prop)}
                              disabled={busy}
                              className="px-4 py-1.5 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white text-xs font-semibold shadow-2xs transition"
                            >
                              Approve & Dispatch Outbox
                            </button>
                          ) : (
                            <span className="bg-mint-wash text-canopy-green px-3 py-1 rounded-full text-xs font-bold">
                              Approved & Queued
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </CoordinatorShell>
  );
}
