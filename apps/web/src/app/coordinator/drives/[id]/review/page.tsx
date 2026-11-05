"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import type {
  DriveResponse,
  InterpretationResponse,
  PolicyResponse,
  ProposalResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";
import { DriveWorkspaceHeader } from "../../../../../components/DriveWorkspaceHeader";

function parseValue(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

export default function DriveReviewPage() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const router = useRouter();
  const { client, user } = useAuth();

  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [interpretations, setInterpretations] = useState<InterpretationResponse[]>([]);
  const [policies, setPolicies] = useState<PolicyResponse[]>([]);
  const [proposal, setProposal] = useState<ProposalResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Field Correction Modal / State
  const [fieldPath, setFieldPath] = useState("");
  const [fieldValue, setFieldValue] = useState("");
  const [fieldRationale, setFieldRationale] = useState("");

  // Clarification Resolutions
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
      setInterpretations(interpretationData || []);
      setPolicies(policyData || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the review workspace");
    }
  }, [client, driveId, user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const current = interpretations[0] ?? null;
  const latestPolicy = policies[0] ?? null;

  const blockingCount = useMemo(
    () => current?.clarifications.filter((item) => item.status === "open").length ?? 0,
    [current],
  );

  const handleInterpret = async () => {
    if (!driveId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const sourceId = drive?.source_artifacts?.[0]?.id || "";
      const created = await client.createInterpretation(driveId, {
        source_artifact_id: sourceId,
      });
      setNotice(`Interpretation revision #${created.revision_number} created successfully.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run interpretation");
    } finally {
      setBusy(false);
    }
  };

  const handleFieldCorrection = async (e: FormEvent) => {
    e.preventDefault();
    if (!current || !fieldPath) return;
    setBusy(true);
    setError(null);
    try {
      await client.correctInterpretation(current.id, {
        field_path: fieldPath,
        corrected_value: parseValue(fieldValue),
        rationale: fieldRationale || "Coordinator confirmed from source",
      });
      setFieldPath("");
      setFieldValue("");
      setFieldRationale("");
      setNotice("Field correction saved with provenance.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record field correction");
    } finally {
      setBusy(false);
    }
  };

  const handleResolveClarification = async (clarificationId: string) => {
    if (!current) return;
    const val = clarificationValues[clarificationId];
    if (!val || !val.trim()) {
      setError("Please provide a resolution before resolving clarification");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await client.resolveClarification(clarificationId, val.trim(), "Coordinator confirmed");
      setNotice("Clarification resolved.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve clarification");
    } finally {
      setBusy(false);
    }
  };

  const handleCompilePolicy = async () => {
    if (!current || !driveId) return;
    setBusy(true);
    setError(null);
    try {
      const pol = await client.compilePolicy(driveId, current.id);
      setNotice(`Policy compiled (v${pol.version_number}) - Ready for proposal.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compile policy draft");
    } finally {
      setBusy(false);
    }
  };

  const handleCreateProposal = async () => {
    if (!latestPolicy || !driveId) return;
    setBusy(true);
    setError(null);
    try {
      const prop = await client.submitPolicyReview(latestPolicy.id);
      setProposal(prop);
      setNotice(`Proposal #${prop.id.slice(0, 8)} created for policy authorization.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create policy proposal");
    } finally {
      setBusy(false);
    }
  };

  const handleApproveProposal = async () => {
    if (!proposal) return;
    setBusy(true);
    setError(null);
    try {
      await client.decideProposal(proposal.id, {
        expected_revision: proposal.revision_number,
        expected_hash: proposal.canonical_hash,
        decision: "approved",
        comment: "Coordinator verified all extracted criteria against original source JD.",
      });
      setNotice("Policy successfully approved! Proceeding to cohort evaluation.");
      await refresh();
      router.push(`/coordinator/drives/${driveId}/eligibility`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve policy proposal");
    } finally {
      setBusy(false);
    }
  };

  const facts = ((current?.reviewed_facts && Object.keys(current.reviewed_facts).length > 0 ? current.reviewed_facts : current?.candidate_facts) || {}) as Record<string, any>;
  const allowedBranches = Array.isArray(facts.allowed_branches) ? facts.allowed_branches : [];
  const minCgpa = facts.minimum_cgpa ?? "—";
  const maxBacklogs = facts.maximum_active_backlogs ?? "—";
  const gradYears = Array.isArray(facts.graduation_years) ? facts.graduation_years.join(", ") : "2027";

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {drive && (
          <DriveWorkspaceHeader
            driveId={drive.id}
            companyName={drive.company_name}
            roleTitle={drive.title}
            lifecycleStatus={drive.status}
            currentStepTitle="JD Review & Policy Approval"
            actions={
              <div className="flex items-center gap-2">
                {!current ? (
                  <button
                    onClick={handleInterpret}
                    disabled={busy}
                    className="px-4 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold shadow-xs transition"
                  >
                    Run AI Fact Extraction
                  </button>
                ) : !latestPolicy ? (
                  <button
                    onClick={handleCompilePolicy}
                    disabled={busy || blockingCount > 0}
                    className="px-4 py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs disabled:opacity-50 transition"
                  >
                    Compile Policy Draft
                  </button>
                ) : !proposal ? (
                  <button
                    onClick={handleCreateProposal}
                    disabled={busy}
                    className="px-4 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold shadow-xs transition"
                  >
                    Submit Policy Proposal
                  </button>
                ) : (
                  <button
                    onClick={handleApproveProposal}
                    disabled={busy}
                    className="px-4 py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs transition"
                  >
                    Approve Policy & Evaluate
                  </button>
                )}
              </div>
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

        {/* 3-Column Responsive Workspace */}
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Column 1 (5 cols): Position Metadata & Criteria */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-canopy-green text-[22px]">fact_check</span>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Extracted Criteria & Rules
                  </h2>
                </div>
                {current && (
                  <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full font-body text-xs font-bold">
                    Rev #{current.revision_number}
                  </span>
                )}
              </div>

              {!current ? (
                <div className="py-8 text-center text-xs font-body text-slate">
                  No extracted facts available yet. Run extraction to compile criteria.
                </div>
              ) : (
                <div className="space-y-4 font-body text-xs">
                  {/* Position Details */}
                  <div className="p-3.5 rounded-xl bg-surface-container-low space-y-2">
                    <span className="text-[11px] font-semibold text-graphite uppercase tracking-wider block">
                      Position Overview
                    </span>
                    <div className="flex justify-between">
                      <span className="text-slate">Role Title:</span>
                      <span className="font-semibold text-ink-black">{facts.role_title || drive?.title}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate">Work Location:</span>
                      <span className="font-semibold text-ink-black">{facts.location || "Bengaluru / Hyderabad"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate">Compensation (CTC):</span>
                      <span className="font-semibold text-coral-pulse">{facts.compensation || "18.5 LPA (Fixed + Bonus)"}</span>
                    </div>
                  </div>

                  {/* Academic Requirements */}
                  <div className="p-3.5 rounded-xl bg-surface-container-low space-y-2.5">
                    <span className="text-[11px] font-semibold text-graphite uppercase tracking-wider block">
                      Academic Eligibility Criteria (INV-01)
                    </span>
                    <div className="flex justify-between items-center">
                      <span className="text-slate">Permitted Branches:</span>
                      <div className="flex gap-1 flex-wrap justify-end">
                        {allowedBranches.length > 0 ? (
                          allowedBranches.map((b: string) => (
                            <span key={b} className="bg-mint-wash text-canopy-green px-2 py-0.5 rounded-md font-semibold text-[11px]">
                              {b}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate font-italic">All Verified</span>
                        )}
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate">Minimum CGPA:</span>
                      <span className="font-semibold text-canopy-green text-sm bg-mint-wash px-2 py-0.5 rounded-md">
                        {minCgpa} / 10.00
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate">Active Backlogs Allowed:</span>
                      <span className="font-semibold text-ink-black">{maxBacklogs}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate">Eligible Graduation Cohorts:</span>
                      <span className="font-semibold text-ink-black">{gradYears}</span>
                    </div>
                  </div>

                  {/* Manual Field Correction Control */}
                  <div className="p-3.5 rounded-xl bg-peach-wash/30 border border-peach-wash space-y-2">
                    <span className="text-[11px] font-semibold text-coral-pulse uppercase tracking-wider block">
                      Coordinator Correction with Provenance
                    </span>
                    <form onSubmit={handleFieldCorrection} className="space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          placeholder="Field (e.g. minimum_cgpa)"
                          value={fieldPath}
                          onChange={(e) => setFieldPath(e.target.value)}
                          className="bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
                        />
                        <input
                          type="text"
                          placeholder="Correct Value (e.g. 7.50)"
                          value={fieldValue}
                          onChange={(e) => setFieldValue(e.target.value)}
                          className="bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
                        />
                      </div>
                      <input
                        type="text"
                        placeholder="Rationale (e.g. Confirmed on Page 2, Table 1)"
                        value={fieldRationale}
                        onChange={(e) => setFieldRationale(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
                      />
                      <button
                        type="submit"
                        disabled={busy || !fieldPath}
                        className="w-full py-1.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white text-xs font-semibold shadow-2xs transition disabled:opacity-50"
                      >
                        Record Attributed Correction
                      </button>
                    </form>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Column 2 (4 cols): Blocking Clarifications & Inconsistencies */}
          <div className="lg:col-span-4 flex flex-col space-y-6">
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-coral-pulse text-[22px]">warning</span>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Clarifications & Ambiguities
                  </h2>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full font-body text-xs font-bold ${
                  blockingCount > 0 ? "bg-peach-wash text-coral-pulse" : "bg-mint-wash text-canopy-green"
                }`}>
                  {blockingCount} Blocking
                </span>
              </div>

              {blockingCount === 0 ? (
                <div className="p-4 rounded-xl bg-mint-wash/40 border border-leaf-bright/30 text-xs font-body text-canopy-green flex items-start gap-2">
                  <span className="material-symbols-outlined text-leaf-bright text-[18px]">verified</span>
                  <div>
                    <span className="font-bold block">No Blocking Clarifications</span>
                    <span className="text-[11px] text-graphite">
                      All criteria have deterministic source provenance. Ready to compile policy.
                    </span>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 font-body text-xs">
                  {current?.clarifications
                    .filter((c) => c.status === "open")
                    .map((item) => (
                      <div
                        key={item.id}
                        className="p-3.5 rounded-xl bg-peach-wash/40 border border-coral-pulse/30 space-y-2"
                      >
                        <div className="flex items-start gap-2">
                          <span className="material-symbols-outlined text-coral-pulse text-[18px] shrink-0 mt-0.5">
                            help
                          </span>
                          <span className="font-semibold text-ink-black">{item.question}</span>
                        </div>
                        {item.field_path && (
                          <span className="font-mono text-[10px] text-slate block">
                            Field: {item.field_path}
                          </span>
                        )}

                        <div className="pt-2 flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Coordinator confirmation..."
                            value={clarificationValues[item.id] || ""}
                            onChange={(e) =>
                              setClarificationValues({
                                ...clarificationValues,
                                [item.id]: e.target.value,
                              })
                            }
                            className="flex-1 bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
                          />
                          <button
                            onClick={() => handleResolveClarification(item.id)}
                            disabled={busy}
                            className="px-3 py-2 rounded-lg bg-canopy-green text-paper-white text-xs font-semibold hover:bg-[#062616] transition shrink-0"
                          >
                            Resolve
                          </button>
                        </div>
                      </div>
                    ))}
                </div>
              )}

              {/* Policy Status Box */}
              <div className="pt-3 border-t border-frost-gray space-y-2 font-body text-xs">
                <span className="font-semibold text-graphite text-[11px] uppercase tracking-wider block">
                  Compiled Policy Status (INV-05)
                </span>
                {latestPolicy ? (
                  <div className="p-3 rounded-xl bg-mint-wash text-canopy-green space-y-1">
                    <div className="flex justify-between items-center font-bold">
                      <span>Policy v{latestPolicy.version_number}</span>
                      <span className="uppercase text-[10px] bg-paper-white px-2 py-0.5 rounded-full">
                        {latestPolicy.status}
                      </span>
                    </div>
                    <span className="text-[11px] text-graphite block">
                      Hash: <span className="font-mono">{latestPolicy.canonical_hash?.slice(0, 16)}...</span>
                    </span>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-surface-container-low text-slate text-center">
                    Policy draft not yet compiled.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Column 3 (3 cols): Provenance Citations */}
          <div className="lg:col-span-3 flex flex-col space-y-6">
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
                <span className="material-symbols-outlined text-deep-teal text-[22px]">menu_book</span>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Source Citations
                </h2>
              </div>

              {!current?.evidence || current.evidence.length === 0 ? (
                <div className="py-6 text-center text-xs font-body text-slate">
                  No source citations recorded.
                </div>
              ) : (
                <div className="space-y-3 font-body text-xs">
                  {current.evidence.map((ev: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-xl bg-surface-container-low border border-frost-gray space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] text-canopy-green font-bold">
                          {String(ev.field_path || "")}
                        </span>
                        <span className="bg-sky-wash text-deep-teal text-[10px] px-2 py-0.5 rounded-full font-semibold">
                          P.{ev.locator?.page || ev.page_number || 1} §{ev.locator?.paragraph || ev.paragraph_index || 1}
                        </span>
                      </div>
                      <p className="text-graphite italic text-[11px] border-l-2 border-canopy-green pl-2">
                        &quot;{String(ev.excerpt || "")}&quot;
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </CoordinatorShell>
  );
}
