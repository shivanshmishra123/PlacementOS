"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type {
  DriveResponse,
  EvaluationRunResponse,
  ParticipantListResponse,
  PublicationProposalResponse,
  RequirementResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";
import { DriveWorkspaceHeader } from "../../../../../components/DriveWorkspaceHeader";

function localDefault(hours: number) {
  const value = new Date(Date.now() + hours * 60 * 60 * 1000);
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
  return value.toISOString().slice(0, 16);
}

export default function ParticipationWorkspace() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const { client, user } = useAuth();

  const [drive, setDrive] = useState<DriveResponse | null>(null);
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
  const [filter, setFilter] = useState<string>("all");

  const load = useCallback(async () => {
    if (!driveId || !user) return;
    try {
      const [driveData, evaluations] = await Promise.all([
        client.getDrive(driveId),
        client.listEvaluationRuns(driveId),
      ]);
      setDrive(driveData);
      setRevision(driveData.current_revision_number || 1);
      setRuns(evaluations.filter((run) => run.status === "completed" && !run.is_stale));
      try {
        setRequirements(await client.listDocumentRequirements(driveId));
      } catch {
        setRequirements([]);
      }
      try {
        setParticipants(await client.listParticipants(driveId));
      } catch {
        setParticipants(null);
      }
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load participation workspace");
    }
  }, [client, driveId, user]);

  useEffect(() => {
    void load();
  }, [load]);

  async function configureRequirements() {
    if (!driveId) return;
    setBusy(true);
    try {
      await client.setDocumentRequirements(driveId, revision, [
        {
          document_type: "resume",
          display_label: "Resume / Curriculum Vitae",
          allowed_extensions: ["pdf", "docx"],
          required_stage: "registration",
        },
        {
          document_type: "marksheet",
          display_label: "Latest Semester Marksheet",
          allowed_extensions: ["pdf"],
          required_stage: "scheduling",
        },
        {
          document_type: "college_id",
          display_label: "College Photo ID Card",
          allowed_extensions: ["pdf"],
          required_stage: "scheduling",
        },
      ]);
      setMessage("Immutable document requirements configured for the current drive revision.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to configure requirements");
    } finally {
      setBusy(false);
    }
  }

  async function handleProposePublication() {
    if (!driveId) return;
    const evaluation = runs[0];
    if (!evaluation) {
      setError("An approved non-stale evaluation run is required to publish registration.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await client.createPublicationProposal(driveId, {
        expected_drive_revision: revision,
        evaluation_run_id: evaluation.id,
        registration_start_at: new Date(opensAt).toISOString(),
        registration_end_at: new Date(closesAt).toISOString(),
      });
      setProposal(result);
      setMessage(`Publication proposal #${result.id.slice(0, 8)} drafted.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to draft publication proposal");
    } finally {
      setBusy(false);
    }
  }

  async function handleApprovePublication() {
    if (!proposal || !driveId) return;
    setBusy(true);
    setError(null);
    try {
      await client.decidePublicationProposal(proposal.id, {
        expected_revision: proposal.revision_number,
        expected_hash: proposal.canonical_hash,
        decision: "approved",
        comment: "Coordinator authorized publication window",
      });
      setProposal(null);
      setMessage("Drive officially published! Student registration window is now active.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to approve publication");
    } finally {
      setBusy(false);
    }
  }

  const items = participants?.items || [];
  const registeredCount = items.filter((p) => p.registration_state === "submitted").length;
  const readyCount = items.filter((p) => p.readiness_status === "ready").length;
  const holdCount = items.filter((p) => p.registration_state === "eligibility_hold").length;

  const filteredItems = items.filter((p) => {
    if (filter === "registered") return p.registration_state === "submitted";
    if (filter === "ready") return p.readiness_status === "ready";
    if (filter === "hold") return p.registration_state === "eligibility_hold";
    return true;
  });

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {drive && (
          <DriveWorkspaceHeader
            driveId={drive.id}
            companyName={drive.company_name}
            roleTitle={drive.title}
            lifecycleStatus={drive.status}
            currentStepTitle="Participation & Document Readiness"
            actions={
              <Link
                href={`/coordinator/drives/${drive.id}/communications`}
                className="px-4 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold shadow-xs transition flex items-center gap-1"
              >
                <span>Draft Announcement</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </Link>
            }
          />
        )}

        {message && (
          <div className="p-3.5 rounded-xl bg-mint-wash text-canopy-green font-body text-xs font-semibold border border-leaf-bright/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-leaf-bright">check_circle</span>
            <span>{message}</span>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* Funnel Telemetry Strip (4 Feature Cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-mint-wash/70 border border-leaf-bright/30">
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-canopy-green uppercase">Eligible Cohort</span>
              <span className="material-symbols-outlined text-canopy-green text-[22px]">verified</span>
            </div>
            <div className="font-headline text-3xl font-bold text-canopy-green">{items.length || "—"}</div>
            <div className="text-[11px] text-graphite font-body mt-1">Verified evaluation snapshot</div>
          </div>

          <div className="p-5 rounded-2xl bg-sky-wash/70 border border-sky-signal/30">
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-deep-teal uppercase">Ready for Reg</span>
              <span className="material-symbols-outlined text-deep-teal text-[22px]">assignment_turned_in</span>
            </div>
            <div className="font-headline text-3xl font-bold text-deep-teal">{readyCount}</div>
            <div className="text-[11px] text-graphite font-body mt-1">Required documents verified</div>
          </div>

          <div className="p-5 rounded-2xl bg-lilac-wash/70 border border-indigo-bloom/30">
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-indigo-bloom uppercase">Registered</span>
              <span className="material-symbols-outlined text-indigo-bloom text-[22px]">how_to_reg</span>
            </div>
            <div className="font-headline text-3xl font-bold text-indigo-bloom">{registeredCount}</div>
            <div className="text-[11px] text-graphite font-body mt-1">Application confirmed</div>
          </div>

          <div className="p-5 rounded-2xl bg-peach-wash/70 border border-coral-pulse/30">
            <div className="flex items-center justify-between mb-2">
              <span className="font-body text-xs font-bold text-coral-pulse uppercase">Eligibility Holds</span>
              <span className="material-symbols-outlined text-coral-pulse text-[22px]">pause_circle</span>
            </div>
            <div className="font-headline text-3xl font-bold text-coral-pulse">{holdCount}</div>
            <div className="text-[11px] text-graphite font-body mt-1">Held on criteria change (INV-08)</div>
          </div>
        </div>

        {/* 2-Column Action Containers */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (5 cols): Requirements & Publication Controls */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            {/* Document Requirements Setup */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-canopy-green text-[20px]">description</span>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Drive Document Requirements
                  </h2>
                </div>
                <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full font-bold">
                  {requirements.length} Active
                </span>
              </div>

              {requirements.length === 0 ? (
                <div className="text-center py-4 space-y-3">
                  <p className="text-slate">No document requirements bound to this revision yet.</p>
                  <button
                    onClick={configureRequirements}
                    disabled={busy}
                    className="px-4 py-2 rounded-full bg-canopy-green text-paper-white font-semibold text-xs shadow-xs hover:bg-[#062616] transition"
                  >
                    Configure Standard Checklist (Resume, Marksheet, ID)
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {requirements.map((req, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-surface-container-low border border-frost-gray flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-ink-black block">{req.display_label}</span>
                        <span className="text-[11px] text-slate font-mono">
                          Format: {req.allowed_extensions.join(", ")} • Stage: {req.required_stage}
                        </span>
                      </div>
                      <span className="bg-sky-wash text-deep-teal px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">
                        {req.required_stage}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Publication Window Control */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
              <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
                <span className="material-symbols-outlined text-coral-pulse text-[20px]">public</span>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Student Registration Window (INV-11)
                </h2>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-graphite font-semibold mb-1">Window Opens At</label>
                  <input
                    type="datetime-local"
                    value={opensAt}
                    onChange={(e) => setOpensAt(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>
                <div>
                  <label className="block text-graphite font-semibold mb-1">Window Closes At (Exclusive Cutoff)</label>
                  <input
                    type="datetime-local"
                    value={closesAt}
                    onChange={(e) => setClosesAt(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                {!proposal ? (
                  <button
                    onClick={handleProposePublication}
                    disabled={busy || runs.length === 0}
                    className="w-full py-2.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs shadow-xs disabled:opacity-50 transition"
                  >
                    Draft Registration Publication Proposal
                  </button>
                ) : (
                  <button
                    onClick={handleApprovePublication}
                    disabled={busy}
                    className="w-full py-2.5 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-semibold text-xs shadow-xs transition"
                  >
                    Approve Publication Proposal #{proposal.id.slice(0, 8)}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Right Column (7 cols): Candidates Roster Table */}
          <div className="lg:col-span-7 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-frost-gray">
              <div>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Student Participation Roster
                </h2>
                <span className="font-body text-xs text-slate">
                  Combined eligibility × document readiness tracking (INV-02)
                </span>
              </div>

              <div className="flex items-center gap-1.5 overflow-x-auto text-xs font-body">
                <button
                  onClick={() => setFilter("all")}
                  className={`px-3 py-1 rounded-full transition ${
                    filter === "all" ? "bg-canopy-green text-paper-white font-semibold" : "bg-cloud-gray text-graphite"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setFilter("ready")}
                  className={`px-3 py-1 rounded-full transition ${
                    filter === "ready" ? "bg-canopy-green text-paper-white font-semibold" : "bg-cloud-gray text-graphite"
                  }`}
                >
                  Ready
                </button>
                <button
                  onClick={() => setFilter("registered")}
                  className={`px-3 py-1 rounded-full transition ${
                    filter === "registered" ? "bg-canopy-green text-paper-white font-semibold" : "bg-cloud-gray text-graphite"
                  }`}
                >
                  Registered
                </button>
              </div>
            </div>

            {filteredItems.length === 0 ? (
              <div className="py-16 text-center font-body text-xs text-slate">
                No participant records available for this filter.
              </div>
            ) : (
              <div className="overflow-x-auto -mx-6 px-6">
                <table className="w-full border-collapse text-left font-body text-xs">
                  <thead>
                    <tr className="bg-surface-container-low text-graphite font-body text-[11px] uppercase tracking-wider">
                      <th className="py-2.5 px-3 rounded-l-lg font-semibold">Student</th>
                      <th className="py-2.5 px-3 font-semibold">Eligibility</th>
                      <th className="py-2.5 px-3 font-semibold">Documents</th>
                      <th className="py-2.5 px-3 rounded-r-lg font-semibold">Registration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-frost-gray">
                    {filteredItems.map((p, idx) => (
                      <tr key={idx} className="hover:bg-lavender-mist/40 transition-colors">
                        <td className="py-3 px-3">
                          <span className="font-semibold text-ink-black block">{p.student_name}</span>
                          <span className="font-mono text-[11px] text-slate">{p.student_identifier}</span>
                        </td>
                        <td className="py-3 px-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-mint-wash text-canopy-green">
                            {p.eligibility_status}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              p.readiness_status === "ready"
                                ? "bg-mint-wash text-canopy-green"
                                : p.readiness_status === "blocked"
                                ? "bg-peach-wash text-coral-pulse"
                                : "bg-sky-wash text-deep-teal"
                            }`}
                          >
                            {p.readiness_status}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              p.registration_state === "submitted"
                                ? "bg-canopy-green text-paper-white"
                                : p.registration_state === "eligibility_hold"
                                ? "bg-peach-wash text-coral-pulse border border-coral-pulse"
                                : "bg-surface-container text-slate"
                            }`}
                          >
                            {(p.registration_state || "not_registered").replace("_", " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </CoordinatorShell>
  );
}
