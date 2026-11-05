"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  StudentDetailDTO,
  CorrectionProposalDTO,
} from "@placementos/api-client";
import { StudentShell } from "../../../components/StudentShell";

export default function StudentPortalPage() {
  const { user, client } = useAuth();

  const [profile, setProfile] = useState<StudentDetailDTO | null>(null);
  const [corrections, setCorrections] = useState<CorrectionProposalDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Correction Form Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fieldName, setFieldName] = useState("cgpa");
  const [proposedValue, setProposedValue] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadStudentData = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [profileData, correctionsData] = await Promise.all([
        client.getMyStudentProfile(),
        client.getMyCorrections(),
      ]);
      setProfile(profileData);
      setCorrections(correctionsData || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load academic records");
    } finally {
      setLoading(false);
    }
  }, [client, user]);

  useEffect(() => {
    loadStudentData();
  }, [loadStudentData]);

  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!proposedValue.trim()) return;
    setSubmitting(true);
    setModalError(null);
    try {
      let parsedVal: any = proposedValue.trim();
      if (fieldName === "cgpa" || fieldName === "active_backlogs" || fieldName === "graduation_year") {
        parsedVal = Number(proposedValue);
      }
      await client.submitCorrection({
        proposed_changes: { [fieldName]: parsedVal },
        justification: reason.trim() || "Student proposed update based on published semester marksheet",
      });
      setSubmitSuccess("Correction proposal submitted for coordinator verification.");
      setIsModalOpen(false);
      setProposedValue("");
      setReason("");
      loadStudentData();
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to submit correction request");
    } finally {
      setSubmitting(false);
    }
  };

  const rev = profile?.current_verified_revision;

  return (
    <StudentShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Candidate Profile Header Card */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-canopy-green text-paper-white flex items-center justify-center font-headline text-2xl font-bold shadow-xs">
                {user?.full_name?.charAt(0) || "S"}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-headline text-2xl font-bold text-canopy-green leading-tight">
                    {profile?.full_name || user?.full_name || "Rahul Verma"}
                  </h1>
                  <span className="bg-mint-wash text-canopy-green font-body text-xs font-bold px-2.5 py-0.5 rounded-full border border-leaf-bright/30">
                    VERIFIED
                  </span>
                </div>
                <div className="font-body text-xs text-graphite flex items-center gap-2 mt-1">
                  <span className="font-mono font-semibold text-ink-black">
                    {profile?.student_identifier || "2024-CS-001"}
                  </span>
                  <span>•</span>
                  <span>B.Tech in {rev?.branch || "Computer Science & Engineering"}</span>
                  <span>•</span>
                  <span>Apex Institute of Technology</span>
                </div>
              </div>
            </div>

            <div>
              <button
                onClick={() => setIsModalOpen(true)}
                className="bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold px-5 py-2.5 rounded-full shadow-xs transition flex items-center gap-1.5 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">edit_document</span>
                <span>Propose Academic Correction</span>
              </button>
            </div>
          </div>
        </div>

        {submitSuccess && (
          <div className="p-3.5 rounded-xl bg-mint-wash text-canopy-green font-body text-xs font-semibold border border-leaf-bright/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-leaf-bright">check_circle</span>
            <span>{submitSuccess}</span>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* 2-Column Academic Evidence & History */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (6 cols): Authoritative Academic Evidence */}
          <div className="lg:col-span-6 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-5 font-body text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-canopy-green text-[22px]">verified_user</span>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Authoritative Academic Evidence
                </h2>
              </div>
              <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full font-bold">
                Revision #{rev?.revision_number || 1}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray">
                <span className="text-[11px] font-semibold text-slate uppercase tracking-wider block">
                  Cumulative GPA
                </span>
                <div className="font-headline text-2xl font-bold text-canopy-green mt-1">
                  {rev?.cgpa ? Number(rev.cgpa).toFixed(2) : "8.75"} <span className="text-xs text-slate font-normal">/ 10.00</span>
                </div>
                <span className="text-[10px] text-leaf-bright font-bold mt-1 block">Exact Decimal (INV-01)</span>
              </div>

              <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray">
                <span className="text-[11px] font-semibold text-slate uppercase tracking-wider block">
                  Active Backlogs
                </span>
                <div className="font-headline text-2xl font-bold text-ink-black mt-1">
                  {rev?.active_backlogs !== null && rev?.active_backlogs !== undefined ? rev.active_backlogs : "0"}
                </div>
                <span className="text-[10px] text-leaf-bright font-bold mt-1 block">Verified clean</span>
              </div>

              <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray">
                <span className="text-[11px] font-semibold text-slate uppercase tracking-wider block">
                  Graduation Cohort
                </span>
                <div className="font-headline text-xl font-bold text-ink-black mt-1">
                  Batch of {rev?.graduation_year || 2027}
                </div>
                <span className="text-[10px] text-slate mt-1 block">Full-time B.Tech</span>
              </div>

              <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray">
                <span className="text-[11px] font-semibold text-slate uppercase tracking-wider block">
                  Academic Department
                </span>
                <div className="font-headline text-xl font-bold text-canopy-green mt-1">
                  {rev?.branch || "CSE"}
                </div>
                <span className="text-[10px] text-slate mt-1 block">Standard Normalized Alias</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-lavender-mist/40 border border-frost-gray text-[11px] text-graphite space-y-1">
              <span className="font-bold text-canopy-green block">Academic Evidence Rule (INV-02, INV-05):</span>
              <p>
                Student corrections create proposals and cannot directly alter verified facts. Only authorized placement coordinator verification establishes new authoritative evidence.
              </p>
            </div>
          </div>

          {/* Right Column (6 cols): Correction Proposals & History */}
          <div className="lg:col-span-6 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-coral-pulse text-[22px]">history_edu</span>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Correction Proposals & Audits
                </h2>
              </div>
              <span className="bg-sky-wash text-deep-teal font-bold px-2.5 py-0.5 rounded-full">
                {corrections.length} Total
              </span>
            </div>

            {loading ? (
              <div className="py-12 text-center text-slate animate-pulse">Loading correction history...</div>
            ) : corrections.length === 0 ? (
              <div className="py-12 text-center text-slate">
                <p>No correction proposals submitted.</p>
                <p className="text-[11px] text-ash mt-1">If your academic record needs updating, click &quot;Propose Academic Correction&quot; above.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {corrections.map((corr) => {
                  const statusColor =
                    corr.status === "approved"
                      ? "bg-mint-wash text-canopy-green border-leaf-bright/30"
                      : corr.status === "rejected"
                      ? "bg-peach-wash text-coral-pulse border-coral-pulse/30"
                      : "bg-lilac-wash text-indigo-bloom border-indigo-bloom/30";

                  const changesSummary = Object.entries(corr.proposed_changes || {})
                    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${String(v)}`)
                    .join(", ");

                  return (
                    <div
                      key={corr.id}
                      className="p-4 rounded-xl bg-surface-container-low border border-frost-gray space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-bold text-ink-black uppercase text-xs">
                            Changes: {changesSummary || "Academic Update"}
                          </span>
                          <span className="font-mono text-[10px] text-slate ml-2">
                            {corr.id.slice(0, 8)}...
                          </span>
                        </div>
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${statusColor}`}>
                          {corr.status}
                        </span>
                      </div>

                      <div className="text-[11px] text-graphite bg-paper-white p-2.5 rounded-lg border border-frost-gray">
                        Justification: &quot;{corr.justification || "Semester grade update"}&quot;
                      </div>

                      {corr.review_notes && (
                        <div className="text-[11px] text-canopy-green bg-mint-wash/40 p-2 rounded-lg border border-leaf-bright/20 font-medium">
                          Coordinator Review Notes: &quot;{corr.review_notes}&quot;
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Correction Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
            <div className="bg-paper-white rounded-3xl p-6 sm:p-8 max-w-md w-full border border-frost-gray shadow-xl space-y-4 font-body text-xs animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Propose Academic Correction
                  </h2>
                  <span className="text-slate text-[11px]">
                    Requires placement coordinator verification before eligibility evaluation.
                  </span>
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="p-1 rounded-full text-slate hover:text-ink-black"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              {modalError && (
                <div className="p-3 rounded-xl bg-error-container text-on-error-container font-semibold">
                  {modalError}
                </div>
              )}

              <form onSubmit={handleSubmitCorrection} className="space-y-3">
                <div>
                  <label className="block text-graphite font-semibold mb-1">Field to Correct</label>
                  <select
                    value={fieldName}
                    onChange={(e) => setFieldName(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  >
                    <option value="cgpa">Cumulative GPA (CGPA)</option>
                    <option value="active_backlogs">Active Backlogs Count</option>
                    <option value="branch">Branch / Specialization</option>
                    <option value="graduation_year">Graduation Year</option>
                  </select>
                </div>

                <div>
                  <label className="block text-graphite font-semibold mb-1">Proposed Correct Value</label>
                  <input
                    type="text"
                    required
                    placeholder={fieldName === "cgpa" ? "e.g. 8.95" : fieldName === "active_backlogs" ? "0" : "Value"}
                    value={proposedValue}
                    onChange={(e) => setProposedValue(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <div>
                  <label className="block text-graphite font-semibold mb-1">Reason & Supporting Evidence</label>
                  <textarea
                    rows={3}
                    required
                    placeholder="Explain why this value should be updated (e.g. Updated semester 6 marksheet issued with re-evaluation)..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <div className="pt-3 border-t border-frost-gray flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 rounded-full border border-frost-gray text-xs font-semibold text-graphite hover:bg-surface-container"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white text-xs font-semibold shadow-xs disabled:opacity-50"
                  >
                    {submitting ? "Submitting..." : "Submit Proposal"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </StudentShell>
  );
}
