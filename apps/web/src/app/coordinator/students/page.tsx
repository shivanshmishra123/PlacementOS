"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  StudentListItemDTO,
  StudentDetailDTO,
  CorrectionProposalDTO,
} from "@placementos/api-client";
import { CoordinatorShell } from "../../../components/CoordinatorShell";

interface CsvPreviewType {
  preview_token: string;
  total_rows: number;
  valid_rows_count: number;
  invalid_rows_count: number;
  new_students_count: number;
  updating_students_count: number;
  sample_rows?: Record<string, unknown>[];
  invalid_rows?: Record<string, unknown>[];
}

const SAMPLE_CSV = `roll_number,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
APEX-2024-001,Aarav Sharma,aarav.sharma@apex.edu,CSE,8.75,10.0,2027,0
APEX-2024-002,Ishita Patel,ishita.patel@apex.edu,ECE,7.90,10.0,2027,
APEX-2024-003,Rohan Verma,rohan.verma@apex.edu,CSE,9.15,10.0,2027,0
APEX-2024-004,Pooja Nair,pooja.nair@apex.edu,IT,7.80,10.0,2027,0
APEX-2024-005,Vikram Singh,vikram.singh@apex.edu,CSE,8.20,10.0,2027,0`;

export default function CoordinatorStudentsPage() {
  const { client, user } = useAuth();

  const [activeTab, setActiveTab] = useState<"roster" | "import" | "corrections">("roster");
  const [students, setStudents] = useState<StudentListItemDTO[]>([]);
  const [loadingStudents, setLoadingStudents] = useState<boolean>(false);
  const [studentError, setStudentError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [branchFilter, setBranchFilter] = useState("ALL");

  // Detail Drawer
  const [selectedStudent, setSelectedStudent] = useState<StudentDetailDTO | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // CSV Import State
  const [csvText, setCsvText] = useState(SAMPLE_CSV);
  const [previewResult, setPreviewResult] = useState<CsvPreviewType | null>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  // Correction Proposals State
  const [proposals, setProposals] = useState<CorrectionProposalDTO[]>([]);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [proposalNotes, setProposalNotes] = useState<Record<string, string>>({});

  const fetchStudents = useCallback(async () => {
    try {
      setLoadingStudents(true);
      setStudentError(null);
      const res = await client.listStudents({
        branch: branchFilter === "ALL" ? undefined : branchFilter,
      });
      let list = res || [];
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        list = list.filter(
          (s) =>
            s.full_name?.toLowerCase().includes(q) ||
            s.student_identifier?.toLowerCase().includes(q) ||
            s.email?.toLowerCase().includes(q)
        );
      }
      setStudents(list);
    } catch (err: unknown) {
      setStudentError(err instanceof Error ? err.message : "Failed to load student roster");
    } finally {
      setLoadingStudents(false);
    }
  }, [client, branchFilter, searchQuery]);

  const fetchProposals = useCallback(async () => {
    try {
      setLoadingProposals(true);
      const res = await client.listPendingCorrections();
      setProposals(res || []);
    } catch (err) {
      console.error("Proposals fetch error:", err);
    } finally {
      setLoadingProposals(false);
    }
  }, [client]);

  useEffect(() => {
    if (activeTab === "roster") fetchStudents();
    if (activeTab === "corrections") fetchProposals();
  }, [activeTab, fetchStudents, fetchProposals]);

  const handlePreviewImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvText.trim()) return;
    setImporting(true);
    setImportError(null);
    setImportSuccess(null);
    try {
      const res = await client.previewCsv(csvText.trim());
      setPreviewResult(res as CsvPreviewType);
    } catch (err: unknown) {
      setImportError(err instanceof Error ? err.message : "CSV preview failed");
    } finally {
      setImporting(false);
    }
  };

  const handleCommitImport = async () => {
    if (!previewResult) return;
    setImporting(true);
    setImportError(null);
    try {
      const res = await client.commitCsv(previewResult.preview_token);
      setImportSuccess(
        `Successfully committed ${res.created_students || res.total_committed} new candidates & updated ${res.updated_students || 0} verified revisions!`
      );
      setPreviewResult(null);
      fetchStudents();
    } catch (err: unknown) {
      setImportError(err instanceof Error ? err.message : "Import commit failed");
    } finally {
      setImporting(false);
    }
  };

  const handleReviewProposal = async (proposalId: string, decision: "approved" | "rejected") => {
    try {
      await client.decideCorrection(
        proposalId,
        decision,
        proposalNotes[proposalId] || `Coordinator ${decision} with verified evidence`
      );
      fetchProposals();
      fetchStudents();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to review proposal");
    }
  };

  const handleViewDetail = async (studentId: string) => {
    try {
      setLoadingDetail(true);
      const res = await client.getStudent(studentId);
      setSelectedStudent(res);
    } catch (err) {
      console.error("Failed to load student details:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Header Strip */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
                Institutional Student Directory & Academic Records
              </h1>
              <p className="font-body text-xs text-graphite mt-1">
                Zero-mutation CSV ingestion, verified academic revisions, and student correction workflows (INV-02, INV-05).
              </p>
            </div>

            {/* Tab Toggles */}
            <div className="flex items-center gap-2 bg-cloud-gray p-1 rounded-full text-xs font-body font-semibold">
              <button
                onClick={() => setActiveTab("roster")}
                className={`px-4 py-1.5 rounded-full transition ${
                  activeTab === "roster"
                    ? "bg-canopy-green text-paper-white shadow-2xs"
                    : "text-graphite hover:text-ink-black"
                }`}
              >
                Roster ({students.length})
              </button>
              <button
                onClick={() => setActiveTab("import")}
                className={`px-4 py-1.5 rounded-full transition ${
                  activeTab === "import"
                    ? "bg-canopy-green text-paper-white shadow-2xs"
                    : "text-graphite hover:text-ink-black"
                }`}
              >
                CSV Ingestion
              </button>
              <button
                onClick={() => setActiveTab("corrections")}
                className={`px-4 py-1.5 rounded-full transition ${
                  activeTab === "corrections"
                    ? "bg-canopy-green text-paper-white shadow-2xs"
                    : "text-graphite hover:text-ink-black"
                }`}
              >
                Corrections ({proposals.length})
              </button>
            </div>
          </div>
        </div>

        {/* TAB 1: Roster */}
        {activeTab === "roster" && (
          <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
            {/* Search & Filters */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-frost-gray">
              <div className="relative flex-1 max-w-md">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-ash text-[20px]">
                  search
                </span>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by candidate name, roll number, email..."
                  className="w-full bg-cloud-gray rounded-full pl-10 pr-4 py-2 text-xs focus:bg-paper-white focus:ring-2 focus:ring-canopy-green border border-transparent focus:border-canopy-green"
                />
              </div>

              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {["ALL", "CSE", "ECE", "IT", "MECH"].map((b) => (
                  <button
                    key={b}
                    onClick={() => setBranchFilter(b)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                      branchFilter === b
                        ? "bg-canopy-green text-paper-white"
                        : "bg-surface-container text-graphite hover:bg-lavender-mist"
                    }`}
                  >
                    {b}
                  </button>
                ))}
              </div>
            </div>

            {loadingStudents ? (
              <div className="py-16 text-center text-slate font-body text-sm animate-pulse">
                Loading student records...
              </div>
            ) : studentError ? (
              <div className="p-4 rounded-xl bg-error-container text-on-error-container font-body text-xs">
                {studentError}
              </div>
            ) : students.length === 0 ? (
              <div className="py-16 text-center text-slate">
                No students found. Use the CSV Ingestion tab to import candidate records.
              </div>
            ) : (
              <div className="overflow-x-auto -mx-6 px-6">
                <table className="w-full border-collapse text-left font-body text-xs">
                  <thead>
                    <tr className="bg-surface-container-low text-graphite font-body text-[11px] uppercase tracking-wider">
                      <th className="py-2.5 px-3 rounded-l-lg font-semibold">Student Name & Roll No</th>
                      <th className="py-2.5 px-3 font-semibold">Email</th>
                      <th className="py-2.5 px-3 font-semibold">Branch</th>
                      <th className="py-2.5 px-3 font-semibold">CGPA</th>
                      <th className="py-2.5 px-3 font-semibold">Backlogs</th>
                      <th className="py-2.5 px-3 font-semibold">Cohort</th>
                      <th className="py-2.5 px-3 rounded-r-lg text-right font-semibold">Audit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-frost-gray">
                    {students.map((stu) => (
                      <tr key={stu.id} className="hover:bg-lavender-mist/40 transition-colors">
                        <td className="py-3 px-3">
                          <span className="font-semibold text-ink-black text-sm block">
                            {stu.full_name}
                          </span>
                          <span className="font-mono text-[11px] text-slate">
                            {stu.student_identifier}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate">{stu.email}</td>
                        <td className="py-3 px-3">
                          <span className="bg-mint-wash text-canopy-green font-semibold px-2 py-0.5 rounded-md text-[11px]">
                            {stu.branch}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono font-bold text-canopy-green">
                          {stu.cgpa ? Number(stu.cgpa).toFixed(2) : "—"}
                        </td>
                        <td className="py-3 px-3 font-mono text-graphite">
                          {stu.active_backlogs !== null ? stu.active_backlogs : "Unknown"}
                        </td>
                        <td className="py-3 px-3 text-slate">{stu.graduation_year}</td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => handleViewDetail(stu.id)}
                            className="text-xs font-semibold text-canopy-green hover:underline"
                          >
                            Revisions
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: CSV Ingestion Pipeline */}
        {activeTab === "import" && (
          <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-6 font-body text-xs">
            <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
              <span className="material-symbols-outlined text-canopy-green text-[22px]">upload_file</span>
              <div>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Registrar CSV Batch Ingestion Pipeline
                </h2>
                <span className="text-slate text-[11px]">
                  Zero-mutation preview cached in Redis. Atomic commit creates immutable revisions (INV-05).
                </span>
              </div>
            </div>

            {importSuccess && (
              <div className="p-3.5 rounded-xl bg-mint-wash text-canopy-green font-semibold border border-leaf-bright/30">
                {importSuccess}
              </div>
            )}

            {importError && (
              <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-semibold border border-error/30">
                {importError}
              </div>
            )}

            {!previewResult ? (
              <form onSubmit={handlePreviewImport} className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="font-semibold text-graphite">Raw CSV Data</label>
                    <button
                      type="button"
                      onClick={() => setCsvText(SAMPLE_CSV)}
                      className="text-xs text-coral-pulse hover:underline font-semibold"
                    >
                      Load Sample Cohort CSV
                    </button>
                  </div>
                  <textarea
                    rows={8}
                    required
                    value={csvText}
                    onChange={(e) => setCsvText(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-3 font-mono text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <button
                  type="submit"
                  disabled={importing || !csvText.trim()}
                  className="px-6 py-2.5 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-semibold text-xs shadow-xs disabled:opacity-50 transition"
                >
                  {importing ? "Validating Columns..." : "Generate Zero-Mutation Preview"}
                </button>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-mint-wash rounded-xl border border-leaf-bright/30">
                  <div>
                    <span className="font-headline text-sm font-bold text-canopy-green block">
                      Preview Verified: {previewResult.total_rows} Records
                    </span>
                    <span className="text-slate text-[11px]">
                      Token: <span className="font-mono">{previewResult.preview_token.slice(0, 16)}...</span> • TTL: 15m
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPreviewResult(null)}
                      className="px-4 py-1.5 rounded-full border border-frost-gray text-xs font-semibold text-graphite hover:bg-surface-container"
                    >
                      Discard
                    </button>
                    <button
                      onClick={handleCommitImport}
                      disabled={importing}
                      className="px-5 py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white text-xs font-semibold shadow-xs"
                    >
                      {importing ? "Committing..." : "Commit Verified Records"}
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto max-h-60 overflow-y-auto">
                  <table className="w-full border-collapse text-left font-body text-xs">
                    <thead>
                      <tr className="bg-surface-container-low text-graphite font-body text-[11px] uppercase">
                        <th className="p-2">Roll No</th>
                        <th className="p-2">Name</th>
                        <th className="p-2">Branch</th>
                        <th className="p-2">CGPA</th>
                        <th className="p-2">Cohort</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-frost-gray">
                      {previewResult.sample_rows?.map((row: Record<string, unknown>, idx: number) => (
                        <tr key={idx}>
                          <td className="p-2 font-mono">{String(row.roll_number || row.student_identifier || "")}</td>
                          <td className="p-2">{String(row.full_name || row.name || "")}</td>
                          <td className="p-2">{String(row.branch || "")}</td>
                          <td className="p-2 font-mono">{String(row.cgpa ?? "")}</td>
                          <td className="p-2">{String(row.graduation_year ?? "")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Correction Proposals */}
        {activeTab === "corrections" && (
          <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
              <div>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Pending Academic Correction Requests
                </h2>
                <span className="text-slate text-[11px]">
                  Student submitted proposals requiring coordinator audit before becoming verified facts (INV-02).
                </span>
              </div>
              <span className="bg-peach-wash text-coral-pulse px-2.5 py-0.5 rounded-full font-bold">
                {proposals.length} Pending
              </span>
            </div>

            {loadingProposals ? (
              <div className="py-16 text-center text-slate font-body text-sm animate-pulse">
                Loading proposals...
              </div>
            ) : proposals.length === 0 ? (
              <div className="py-16 text-center text-slate">
                No pending correction proposals.
              </div>
            ) : (
              <div className="space-y-4">
                {proposals.map((prop) => (
                  <div
                    key={prop.id}
                    className="p-4 rounded-xl bg-surface-container-low border border-frost-gray space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="font-headline text-sm font-bold text-canopy-green block">
                          {prop.student_name} ({prop.student_identifier})
                        </span>
                        <span className="text-slate text-[11px]">
                          Proposed Changes:{" "}
                          <span className="font-mono font-bold text-coral-pulse">
                            {JSON.stringify(prop.proposed_changes)}
                          </span>
                        </span>
                      </div>
                      <span className="bg-peach-wash text-coral-pulse px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">
                        {prop.status}
                      </span>
                    </div>

                    <div className="p-3 bg-paper-white rounded-lg border border-frost-gray text-slate text-[11px]">
                      Student Reason: &quot;{prop.justification || "Updated after semester grade sheet publication"}&quot;
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="text"
                        placeholder="Coordinator audit notes..."
                        value={proposalNotes[prop.id] || ""}
                        onChange={(e) =>
                          setProposalNotes({
                            ...proposalNotes,
                            [prop.id]: e.target.value,
                          })
                        }
                        className="flex-1 bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
                      />
                      <button
                        onClick={() => handleReviewProposal(prop.id, "approved")}
                        className="px-4 py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white text-xs font-semibold shadow-xs transition"
                      >
                        Approve & Verify
                      </button>
                      <button
                        onClick={() => handleReviewProposal(prop.id, "rejected")}
                        className="px-4 py-2 rounded-full border border-coral-pulse text-coral-pulse hover:bg-peach-wash text-xs font-semibold transition"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Student Detail Modal */}
        {selectedStudent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
            <div className="bg-paper-white rounded-3xl p-6 sm:p-8 max-w-lg w-full border border-frost-gray shadow-xl space-y-4 font-body text-xs animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div>
                  <h2 className="font-headline text-lg font-bold text-canopy-green">
                    {selectedStudent.full_name}
                  </h2>
                  <span className="font-mono text-slate text-xs">{selectedStudent.student_identifier}</span>
                </div>
                <button
                  onClick={() => setSelectedStudent(null)}
                  className="p-1 rounded-full text-slate hover:text-ink-black"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate">Email:</span>
                  <span className="font-semibold text-ink-black">{selectedStudent.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate">Branch:</span>
                  <span className="font-semibold text-canopy-green">
                    {selectedStudent.current_verified_revision?.branch || "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate">CGPA:</span>
                  <span className="font-mono font-bold text-canopy-green">
                    {selectedStudent.current_verified_revision?.cgpa ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate">Graduation Year:</span>
                  <span className="font-semibold text-ink-black">
                    {selectedStudent.current_verified_revision?.graduation_year ?? "—"}
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-frost-gray">
                <span className="font-semibold text-graphite text-[11px] uppercase tracking-wider block mb-2">
                  Academic Revision History ({selectedStudent.revision_history?.length || 0})
                </span>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedStudent.revision_history?.map((rev, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-surface-container-low border border-frost-gray text-[11px]">
                      <div className="flex justify-between font-bold text-canopy-green">
                        <span>Rev #{rev.revision_number}</span>
                        <span className="uppercase text-[10px] bg-mint-wash px-2 py-0.5 rounded-full">
                          {rev.is_verified ? "VERIFIED" : "UNVERIFIED"}
                        </span>
                      </div>
                      <div className="text-slate mt-0.5">
                        CGPA: {rev.cgpa} • Backlogs: {rev.active_backlogs ?? "None"} • Source: {rev.source}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </CoordinatorShell>
  );
}
