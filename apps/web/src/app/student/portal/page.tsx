"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  StudentDetailDTO,
  CorrectionProposalDTO,
} from "@placementos/api-client";
import {
  GraduationCap,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  History,
  FileEdit,
  Send,
  Building,
  Clock,
  XCircle,
  FileText,
  User,
  Sparkles,
} from "lucide-react";

export default function StudentPortalPage() {
  const { user, client, loginAsPersona } = useAuth();

  const [profile, setProfile] = useState<StudentDetailDTO | null>(null);
  const [corrections, setCorrections] = useState<CorrectionProposalDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Correction Form State
  const [proposedBranch, setProposedBranch] = useState("");
  const [proposedCgpa, setProposedCgpa] = useState("");
  const [proposedBacklogs, setProposedBacklogs] = useState("");
  const [justification, setJustification] = useState("");
  const [documentUrl, setDocumentUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitFeedback, setSubmitFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const isStudent = user?.role === "student" || user?.capabilities.includes("student:self_read");

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
      setCorrections(correctionsData);
      if (profileData.current_verified_revision) {
        setProposedBranch(profileData.current_verified_revision.branch);
        setProposedCgpa(String(profileData.current_verified_revision.cgpa));
        setProposedBacklogs(
          profileData.current_verified_revision.active_backlogs !== null &&
            profileData.current_verified_revision.active_backlogs !== undefined
            ? String(profileData.current_verified_revision.active_backlogs)
            : ""
        );
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load student profile. Your account may not have an imported student record yet."
      );
    } finally {
      setLoading(false);
    }
  }, [client, user]);

  useEffect(() => {
    if (user && isStudent) {
      loadStudentData();
    } else {
      setLoading(false);
    }
  }, [user, isStudent, loadStudentData]);

  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!justification.trim()) {
      setSubmitFeedback({
        type: "error",
        message: "Please provide a detailed justification for your correction request.",
      });
      return;
    }

    setSubmitting(true);
    setSubmitFeedback(null);
    try {
      const changes: Record<string, unknown> = {};
      if (proposedBranch) changes.branch = proposedBranch.toUpperCase();
      if (proposedCgpa) changes.cgpa = parseFloat(proposedCgpa);
      if (proposedBacklogs !== "") {
        changes.active_backlogs = parseInt(proposedBacklogs, 10);
      }

      await client.submitCorrection({
        proposed_changes: changes,
        justification: justification.trim(),
        supporting_document_url: documentUrl.trim() || undefined,
      });

      setSubmitFeedback({
        type: "success",
        message: "Correction proposal submitted! Your coordinator has been notified for verification.",
      });
      setJustification("");
      setDocumentUrl("");
      await loadStudentData();
    } catch (err: unknown) {
      setSubmitFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to submit correction proposal.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (!user || !isStudent) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
        <div className="h-16 w-16 mx-auto rounded-3xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shadow-sm">
          <GraduationCap className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
            Student Self-Service Portal
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            View your verified academic records, audit revision history, and propose corrections with supporting evidence. Select a student persona to continue:
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto pt-4">
          <button
            onClick={() => loginAsPersona("student_apex")}
            className="p-4 rounded-2xl glass-panel border border-slate-200 dark:border-slate-800 hover:border-emerald-500 text-left transition space-y-1 group"
          >
            <div className="text-xs font-mono uppercase text-emerald-600 dark:text-emerald-400 font-semibold">
              Institution: Apex
            </div>
            <div className="font-semibold text-slate-900 dark:text-white group-hover:text-emerald-600 transition">
              Rahul Verma
            </div>
            <div className="text-xs text-slate-500">Roll: 2024-CS-001 (CSE)</div>
          </button>

          <button
            onClick={() => loginAsPersona("student_beacon")}
            className="p-4 rounded-2xl glass-panel border border-slate-200 dark:border-slate-800 hover:border-emerald-500 text-left transition space-y-1 group"
          >
            <div className="text-xs font-mono uppercase text-emerald-600 dark:text-emerald-400 font-semibold">
              Institution: Beacon
            </div>
            <div className="font-semibold text-slate-900 dark:text-white group-hover:text-emerald-600 transition">
              Sneha Roy
            </div>
            <div className="text-xs text-slate-500">Roll: 2024-CS-001 (CSE)</div>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Student Banner */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
              <Building className="w-3.5 h-3.5" />
              {user.institution_slug.toUpperCase()} Student Portal
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Verified Academic Profile
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Your official academic facts used for recruitment eligibility. Propose verified corrections if registrar records change.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-slate-500">Signed in as</div>
              <div className="font-semibold text-sm text-slate-900 dark:text-white">
                {user.full_name}
              </div>
            </div>
            <div className="h-10 w-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-bold">
              {user.full_name.charAt(0)}
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center text-sm text-slate-500">
          Loading your verified academic record...
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-3xl border border-amber-200 dark:border-amber-900 bg-amber-50/40 dark:bg-amber-950/20 text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-amber-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            No Student Record Found
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
            {error}
          </p>
        </div>
      ) : profile ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Verified Facts Card & Revisions */}
          <div className="lg:col-span-2 space-y-6">
            {/* Current Verified Facts */}
            <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 space-y-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-2xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                      Current Verified Facts
                    </h2>
                    <div className="text-xs text-slate-500 font-mono">
                      Roll Number: {profile.student_identifier}
                    </div>
                  </div>
                </div>

                {profile.current_verified_revision ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    Revision #{profile.current_verified_revision.revision_number} Verified
                  </span>
                ) : (
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    Unverified
                  </span>
                )}
              </div>

              {profile.current_verified_revision ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <div className="text-xs text-slate-500">Degree Branch</div>
                    <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                      {profile.current_verified_revision.branch}
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <div className="text-xs text-slate-500">Cumulative GPA</div>
                    <div className="text-lg font-mono font-bold text-slate-900 dark:text-white mt-1">
                      {profile.current_verified_revision.cgpa.toFixed(2)}{" "}
                      <span className="text-xs font-normal text-slate-400">
                        / {profile.current_verified_revision.cgpa_scale.toFixed(1)}
                      </span>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <div className="text-xs text-slate-500">Active Backlogs</div>
                    <div className="text-lg font-bold mt-1">
                      {profile.current_verified_revision.active_backlogs === 0 ? (
                        <span className="text-emerald-600 dark:text-emerald-400">0 Clean</span>
                      ) : profile.current_verified_revision.active_backlogs === null ? (
                        <span className="text-amber-600 dark:text-amber-400 text-sm">Unknown</span>
                      ) : (
                        <span className="text-rose-600 dark:text-rose-400">
                          {profile.current_verified_revision.active_backlogs} Active
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <div className="text-xs text-slate-500">Graduation Year</div>
                    <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                      {profile.current_verified_revision.graduation_year}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500">
                  No verified academic facts on record yet.
                </div>
              )}

              {profile.current_verified_revision && (
                <div className="text-xs text-slate-400 border-t border-slate-200/60 dark:border-slate-800/60 pt-4 flex flex-wrap items-center justify-between gap-2">
                  <span>
                    Verified via{" "}
                    <strong className="text-slate-600 dark:text-slate-300 uppercase">
                      {profile.current_verified_revision.source}
                    </strong>
                  </span>
                  <span>
                    Last Updated:{" "}
                    {profile.current_verified_revision.verified_at
                      ? new Date(profile.current_verified_revision.verified_at).toLocaleString()
                      : "Pending"}
                  </span>
                </div>
              )}
            </div>

            {/* Revision History */}
            <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <History className="w-4 h-4 text-brand-600" />
                Immutable Revision History ({profile.revision_history.length})
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                PlacementOS retains an immutable audit log of all academic revisions. Unverified edits cannot alter your eligibility facts.
              </p>

              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 text-[10px] uppercase">
                    <tr>
                      <th className="px-4 py-2.5">Rev #</th>
                      <th className="px-4 py-2.5">Branch</th>
                      <th className="px-4 py-2.5">CGPA</th>
                      <th className="px-4 py-2.5">Backlogs</th>
                      <th className="px-4 py-2.5">Source</th>
                      <th className="px-4 py-2.5">Status</th>
                      <th className="px-4 py-2.5">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {profile.revision_history.map((rev) => (
                      <tr key={rev.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                        <td className="px-4 py-2.5 font-bold text-brand-600">
                          #{rev.revision_number}
                        </td>
                        <td className="px-4 py-2.5">{rev.branch}</td>
                        <td className="px-4 py-2.5">{rev.cgpa.toFixed(2)}</td>
                        <td className="px-4 py-2.5">
                          {rev.active_backlogs === null ? "None" : rev.active_backlogs}
                        </td>
                        <td className="px-4 py-2.5 font-sans capitalize">{rev.source}</td>
                        <td className="px-4 py-2.5 font-sans">
                          {rev.is_verified ? (
                            <span className="text-emerald-600 font-semibold">Verified</span>
                          ) : (
                            <span className="text-slate-400">Draft</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-[10px] text-slate-400">
                          {new Date(rev.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* My Correction Requests & Status Tracker */}
            <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-600" />
                Correction Requests Tracker ({corrections.length})
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Track the status and review notes of any correction proposals submitted to your placement office.
              </p>

              {corrections.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
                  You haven&apos;t submitted any correction proposals.
                </div>
              ) : (
                <div className="space-y-3">
                  {corrections.map((corr) => (
                    <div
                      key={corr.id}
                      className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-400">
                          Submitted {new Date(corr.created_at).toLocaleDateString()}
                        </span>
                        {corr.status === "pending" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border border-amber-200">
                            <Clock className="w-3 h-3" />
                            Pending Review
                          </span>
                        ) : corr.status === "approved" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" />
                            Approved
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300 border border-rose-200">
                            <XCircle className="w-3 h-3" />
                            Rejected
                          </span>
                        )}
                      </div>

                      <div className="font-mono text-[11px] text-slate-700 dark:text-slate-300">
                        Proposed changes: {JSON.stringify(corr.proposed_changes)}
                      </div>
                      <div className="text-slate-600 dark:text-slate-400 italic">
                        &ldquo;{corr.justification}&rdquo;
                      </div>

                      {corr.review_notes && (
                        <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px]">
                          <strong className="text-slate-700 dark:text-slate-300">Coordinator Notes:</strong>{" "}
                          <span className="text-slate-600 dark:text-slate-400">{corr.review_notes}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Propose Correction Form */}
          <div className="space-y-6">
            <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 space-y-6 shadow-sm sticky top-24">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileEdit className="w-4 h-4 text-brand-600" />
                  Propose Record Correction
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Submit revised academic information with official rationale. Unreviewed requests never alter verified facts.
                </p>
              </div>

              <form onSubmit={handleSubmitCorrection} className="space-y-4 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    Branch / Major
                  </label>
                  <input
                    type="text"
                    value={proposedBranch}
                    onChange={(e) => setProposedBranch(e.target.value)}
                    placeholder="e.g., CSE, ECE"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    Cumulative CGPA (Scale 10.0)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="10"
                    value={proposedCgpa}
                    onChange={(e) => setProposedCgpa(e.target.value)}
                    placeholder="e.g., 8.90"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    Active Backlogs Count
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={proposedBacklogs}
                    onChange={(e) => setProposedBacklogs(e.target.value)}
                    placeholder="0 for clean record"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    Supporting Document URL (Optional)
                  </label>
                  <input
                    type="url"
                    value={documentUrl}
                    onChange={(e) => setDocumentUrl(e.target.value)}
                    placeholder="Link to verified semester grade card..."
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    Justification Statement <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    placeholder="Explain why this correction is required (e.g. re-evaluation cleared backlogs in Sem 5)..."
                    className="w-full p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                {submitFeedback && (
                  <div
                    className={`p-3 rounded-xl text-xs border ${
                      submitFeedback.type === "success"
                        ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800"
                        : "bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-200 border-rose-200 dark:border-rose-800"
                    }`}
                  >
                    {submitFeedback.message}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submitting ? "Submitting..." : "Submit Correction Proposal"}
                </button>
              </form>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
