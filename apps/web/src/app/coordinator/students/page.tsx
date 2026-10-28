"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  StudentListItemDTO,
  StudentDetailDTO,
  CorrectionProposalDTO,
} from "@placementos/api-client";
import {
  Users,
  UploadCloud,
  FileCheck2,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  History,
  Eye,
  ArrowRight,
  ShieldAlert,
  Building,
  GraduationCap,
  Sparkles,
} from "lucide-react";

const SAMPLE_APEX_CSV = `roll_number,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
APEX-2024-001,Aarav Sharma,aarav.sharma@apex.edu,CSE,8.75,10.0,2025,0
APEX-2024-002,Ishita Patel,ishita.patel@apex.edu,ECE,7.90,10.0,2025,
APEX-2024-003,Rohan Verma,rohan.verma@apex.edu,CSE,9.15,10.0,2025,0
APEX-2024-004,Pooja Nair,pooja.nair@apex.edu,MECH,6.80,10.0,2025,1
APEX-2024-005,Vikram Singh,vikram.singh@apex.edu,CSE,8.20,10.0,2025,0`;

const SAMPLE_BEACON_CSV = `roll_number,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
BEAC-2024-101,Kavita Rao,kavita.rao@beacon.edu,CSE,8.95,10.0,2025,0
BEAC-2024-102,Sameer Gupta,sameer.gupta@beacon.edu,IT,7.40,10.0,2025,0
BEAC-2024-103,Divya Menon,divya.menon@beacon.edu,ECE,8.10,10.0,2025,
BEAC-2024-104,Aditya Joshi,aditya.joshi@beacon.edu,CSE,6.50,10.0,2025,2`;

export default function CoordinatorStudentsPage() {
  const { user, client, loginAsPersona } = useAuth();

  const [activeTab, setActiveTab] = useState<"roster" | "import" | "corrections">("roster");
  const [students, setStudents] = useState<StudentListItemDTO[]>([]);
  const [loadingStudents, setLoadingStudents] = useState<boolean>(false);
  const [studentError, setStudentError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [branchFilter, setBranchFilter] = useState("");
  const [minCgpaFilter, setMinCgpaFilter] = useState<string>("");

  // Student Detail Modal
  const [selectedStudent, setSelectedStudent] = useState<StudentDetailDTO | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // CSV Import State
  const [csvText, setCsvText] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [commitLoading, setCommitLoading] = useState(false);
  const [importReport, setImportReport] = useState<{
    preview_token: string;
    total_rows: number;
    valid_rows_count: number;
    invalid_rows_count: number;
    new_students_count: number;
    updating_students_count: number;
    sample_rows: Record<string, unknown>[];
    invalid_rows: Record<string, unknown>[];
  } | null>(null);
  const [importFeedback, setImportFeedback] = useState<string | null>(null);

  // Pending Corrections State
  const [pendingCorrections, setPendingCorrections] = useState<CorrectionProposalDTO[]>([]);
  const [loadingCorrections, setLoadingCorrections] = useState<boolean>(false);
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});
  const [decisionProcessing, setDecisionProcessing] = useState<Record<string, boolean>>({});

  const isCoordinator = user?.role === "coordinator" || user?.capabilities.includes("student:read");

  // Load Students
  const loadStudents = useCallback(async () => {
    if (!isCoordinator) return;
    setLoadingStudents(true);
    setStudentError(null);
    try {
      const params: { branch?: string; min_cgpa?: number } = {};
      if (branchFilter) params.branch = branchFilter;
      if (minCgpaFilter && !isNaN(Number(minCgpaFilter))) {
        params.min_cgpa = Number(minCgpaFilter);
      }
      const data = await client.listStudents(params);
      setStudents(data);
    } catch (err: unknown) {
      setStudentError(err instanceof Error ? err.message : "Failed to load student roster");
    } finally {
      setLoadingStudents(false);
    }
  }, [client, isCoordinator, branchFilter, minCgpaFilter]);

  // Load Pending Corrections
  const loadCorrections = useCallback(async () => {
    if (!isCoordinator) return;
    setLoadingCorrections(true);
    try {
      const data = await client.listPendingCorrections();
      setPendingCorrections(data);
    } catch (err: unknown) {
      console.warn("Error loading pending corrections:", err);
    } finally {
      setLoadingCorrections(false);
    }
  }, [client, isCoordinator]);

  useEffect(() => {
    if (isCoordinator) {
      loadStudents();
      loadCorrections();
    }
  }, [isCoordinator, loadStudents, loadCorrections]);

  // Fetch Student Detail Modal
  const viewStudentDetail = async (studentId: string) => {
    setLoadingDetail(true);
    try {
      const detail = await client.getStudentDetail(studentId);
      setSelectedStudent(detail);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to retrieve student details");
    } finally {
      setLoadingDetail(false);
    }
  };

  // Preview CSV
  const handlePreviewCsv = async () => {
    if (!csvText.trim()) return;
    setPreviewLoading(true);
    setImportFeedback(null);
    try {
      const rep = await client.previewCsv(csvText);
      setImportReport(rep);
    } catch (err: unknown) {
      setImportFeedback(err instanceof Error ? err.message : "Failed to preview CSV");
    } finally {
      setPreviewLoading(false);
    }
  };

  // Commit CSV
  const handleCommitCsv = async () => {
    if (!importReport?.preview_token) return;
    setCommitLoading(true);
    setImportFeedback(null);
    try {
      const res = await client.commitCsv(importReport.preview_token);
      setImportFeedback(`Successfully committed ${res.total_committed} student records! (${res.created_students} created, ${res.updated_students} updated)`);
      setImportReport(null);
      setCsvText("");
      await loadStudents();
      setActiveTab("roster");
    } catch (err: unknown) {
      setImportFeedback(err instanceof Error ? err.message : "Commit failed");
    } finally {
      setCommitLoading(false);
    }
  };

  // Decide Correction
  const handleDecideCorrection = async (proposalId: string, decision: "approved" | "rejected") => {
    setDecisionProcessing((prev) => ({ ...prev, [proposalId]: true }));
    try {
      const notes = decisionNotes[proposalId] || (decision === "approved" ? "Verified by coordinator" : "Rejected");
      await client.decideCorrection(proposalId, decision, notes);
      await loadCorrections();
      await loadStudents();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setDecisionProcessing((prev) => ({ ...prev, [proposalId]: false }));
    }
  };

  // Filter students locally by search query
  const filteredStudents = students.filter((s) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.student_identifier.toLowerCase().includes(q) ||
      s.full_name.toLowerCase().includes(q) ||
      s.email.toLowerCase().includes(q)
    );
  });

  if (!user || !isCoordinator) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
        <div className="h-16 w-16 mx-auto rounded-3xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
            Placement Coordinator Access Required
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            This module manages institutional student intake, immutable academic revisions, and correction verification. Please select an authorized coordinator persona below:
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto pt-4">
          <button
            onClick={() => loginAsPersona("coord_apex")}
            className="p-4 rounded-2xl glass-panel border border-slate-200 dark:border-slate-800 hover:border-indigo-500 text-left transition space-y-1 group"
          >
            <div className="text-xs font-mono uppercase text-indigo-600 dark:text-indigo-400 font-semibold">
              Institution: Apex
            </div>
            <div className="font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 transition">
              Priya Sharma
            </div>
            <div className="text-xs text-slate-500">Lead Placement Coordinator</div>
          </button>

          <button
            onClick={() => loginAsPersona("coord_beacon")}
            className="p-4 rounded-2xl glass-panel border border-slate-200 dark:border-slate-800 hover:border-indigo-500 text-left transition space-y-1 group"
          >
            <div className="text-xs font-mono uppercase text-indigo-600 dark:text-indigo-400 font-semibold">
              Institution: Beacon
            </div>
            <div className="font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 transition">
              Ananya Das
            </div>
            <div className="text-xs text-slate-500">Placement Coordinator</div>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Institution Banner & Metrics Header */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              <Building className="w-3.5 h-3.5" />
              Institutional Tenant: {user.institution_slug.toUpperCase()}
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Student Records & Intake
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Verified institutional academic records with immutable revisions, CSV zero-mutation preview, and auditable correction approvals.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab("import")}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-xs shadow-sm transition"
            >
              <UploadCloud className="w-4 h-4" />
              Import CSV Roster
            </button>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-200/80 dark:border-slate-800/80">
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Total Records</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {students.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Verified Profiles</div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {students.filter((s) => s.is_verified).length}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Pending Corrections</div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
              {pendingCorrections.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Active Scope</div>
            <div className="text-base font-semibold text-slate-800 dark:text-slate-200 mt-1 capitalize">
              {user.institution_slug} &bull; {user.role}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-8">
        <button
          onClick={() => setActiveTab("roster")}
          className={`pb-4 text-sm font-semibold transition flex items-center gap-2 relative ${
            activeTab === "roster"
              ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400"
              : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Users className="w-4 h-4" />
          Student Roster ({students.length})
        </button>

        <button
          onClick={() => setActiveTab("import")}
          className={`pb-4 text-sm font-semibold transition flex items-center gap-2 relative ${
            activeTab === "import"
              ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400"
              : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          CSV Intake & Preview
        </button>

        <button
          onClick={() => setActiveTab("corrections")}
          className={`pb-4 text-sm font-semibold transition flex items-center gap-2 relative ${
            activeTab === "corrections"
              ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400"
              : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          Correction Review
          {pendingCorrections.length > 0 && (
            <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 font-bold">
              {pendingCorrections.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: Student Roster */}
      {activeTab === "roster" && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="glass-panel p-4 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row items-center gap-4 justify-between">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Search roll number, name, or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Filter className="w-3.5 h-3.5" />
                <span>Filters:</span>
              </div>

              <select
                value={branchFilter}
                onChange={(e) => setBranchFilter(e.target.value)}
                className="text-xs px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-none"
              >
                <option value="">All Branches</option>
                <option value="CSE">CSE</option>
                <option value="ECE">ECE</option>
                <option value="MECH">MECH</option>
                <option value="CIVIL">CIVIL</option>
                <option value="IT">IT</option>
              </select>

              <input
                type="number"
                step="0.1"
                placeholder="Min CGPA"
                value={minCgpaFilter}
                onChange={(e) => setMinCgpaFilter(e.target.value)}
                className="w-24 px-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-none"
              />

              {(branchFilter || minCgpaFilter || searchQuery) && (
                <button
                  onClick={() => {
                    setBranchFilter("");
                    setMinCgpaFilter("");
                    setSearchQuery("");
                  }}
                  className="text-xs text-rose-500 hover:text-rose-600 font-medium px-2 py-1"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Student Table */}
          {loadingStudents ? (
            <div className="py-16 text-center text-sm text-slate-500">
              Loading student roster...
            </div>
          ) : studentError ? (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900 text-sm">
              {studentError}
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="glass-panel rounded-3xl p-12 text-center border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="h-12 w-12 mx-auto rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                <Users className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold text-base text-slate-900 dark:text-white">
                  No Student Records Found
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                  No students match the current query in this institution. Import a student roster using the CSV Intake tab.
                </p>
              </div>
              <button
                onClick={() => setActiveTab("import")}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 text-white text-xs font-medium hover:bg-brand-700 transition"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                Open CSV Intake
              </button>
            </div>
          ) : (
            <div className="glass-panel rounded-3xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 uppercase tracking-wider text-[11px] text-slate-500 dark:text-slate-400">
                    <tr>
                      <th className="px-6 py-3.5 font-semibold">Roll Number</th>
                      <th className="px-6 py-3.5 font-semibold">Student Name & Email</th>
                      <th className="px-6 py-3.5 font-semibold">Branch</th>
                      <th className="px-6 py-3.5 font-semibold">CGPA</th>
                      <th className="px-6 py-3.5 font-semibold">Active Backlogs</th>
                      <th className="px-6 py-3.5 font-semibold">Status</th>
                      <th className="px-6 py-3.5 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {filteredStudents.map((stu) => (
                      <tr key={stu.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition">
                        <td className="px-6 py-4 font-mono font-medium text-slate-900 dark:text-white">
                          {stu.student_identifier}
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-semibold text-slate-900 dark:text-white">
                            {stu.full_name}
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-slate-400">
                            {stu.email}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {stu.branch || "Unspecified"}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-mono font-semibold text-slate-900 dark:text-white">
                          {stu.cgpa !== null && stu.cgpa !== undefined ? (
                            <span>
                              {stu.cgpa.toFixed(2)}{" "}
                              <span className="text-[10px] text-slate-400">
                                / {stu.cgpa_scale?.toFixed(1) || "10.0"}
                              </span>
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">None</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          {stu.active_backlogs === 0 ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                              <CheckCircle2 className="w-3 h-3" />
                              0 Clean
                            </span>
                          ) : stu.active_backlogs === null || stu.active_backlogs === undefined ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800" title="Backlog count was not provided; distinct from 0">
                              <AlertTriangle className="w-3 h-3" />
                              Unknown
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                              <XCircle className="w-3 h-3" />
                              {stu.active_backlogs} Active
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          {stu.is_verified ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Verified
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400">
                              <Clock className="w-3.5 h-3.5" />
                              Pending
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => viewStudentDetail(stu.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition font-medium text-[11px]"
                          >
                            <History className="w-3 h-3" />
                            History
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: CSV Intake & Preview */}
      {activeTab === "import" && (
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-3xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                  <UploadCloud className="w-4 h-4 text-brand-600" />
                  Roster CSV Upload & Zero-Mutation Preview
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Import student records idempotently. Previews validate schema and constraints without touching the database.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCsvText(SAMPLE_APEX_CSV)}
                  className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium transition"
                >
                  Load Apex Sample
                </button>
                <button
                  type="button"
                  onClick={() => setCsvText(SAMPLE_BEACON_CSV)}
                  className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium transition"
                >
                  Load Beacon Sample
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Paste CSV Content
              </label>
              <textarea
                rows={7}
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder="roll_number,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs..."
                className="w-full p-4 font-mono text-xs rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                Supports column aliases: <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">roll_no</code>, <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">gpa</code>, <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">cohort</code>
              </div>

              <button
                onClick={handlePreviewCsv}
                disabled={previewLoading || !csvText.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-xs shadow-sm transition disabled:opacity-50"
              >
                <Eye className="w-3.5 h-3.5" />
                {previewLoading ? "Validating..." : "Preview Import"}
              </button>
            </div>

            {importFeedback && (
              <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-800 dark:text-indigo-200 border border-indigo-200 dark:border-indigo-800 text-xs">
                {importFeedback}
              </div>
            )}
          </div>

          {/* Preview Results Panel */}
          {importReport && (
            <div className="glass-panel p-6 rounded-3xl border border-indigo-200 dark:border-indigo-900 space-y-6 animate-in fade-in">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h4 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-brand-600" />
                    Zero-Mutation Preview Report
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Token: <code className="font-mono text-brand-600">{importReport.preview_token.slice(0, 16)}...</code> (Valid for 15 mins)
                  </p>
                </div>

                <button
                  onClick={handleCommitCsv}
                  disabled={commitLoading || importReport.valid_rows_count === 0}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shadow-sm transition disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  {commitLoading ? "Committing Revisions..." : `Commit ${importReport.valid_rows_count} Valid Students`}
                </button>
              </div>

              {/* Statistics Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">Total Rows</div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                    {importReport.total_rows}
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900">
                  <div className="text-[11px] text-emerald-600 dark:text-emerald-400">Valid Rows</div>
                  <div className="text-xl font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">
                    {importReport.valid_rows_count}
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900">
                  <div className="text-[11px] text-indigo-600 dark:text-indigo-400">New Students</div>
                  <div className="text-xl font-bold text-indigo-700 dark:text-indigo-300 mt-0.5">
                    {importReport.new_students_count}
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900">
                  <div className="text-[11px] text-amber-600 dark:text-amber-400">Updating Revisions</div>
                  <div className="text-xl font-bold text-amber-700 dark:text-amber-300 mt-0.5">
                    {importReport.updating_students_count}
                  </div>
                </div>
              </div>

              {/* Sample Rows Table */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Parsed Student Preview
                </div>
                <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="px-4 py-2.5">Roll No</th>
                        <th className="px-4 py-2.5">Name</th>
                        <th className="px-4 py-2.5">Email</th>
                        <th className="px-4 py-2.5">Branch</th>
                        <th className="px-4 py-2.5">CGPA</th>
                        <th className="px-4 py-2.5">Backlogs</th>
                        <th className="px-4 py-2.5">Cohort</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800 font-mono">
                      {importReport.sample_rows.map((r, i) => (
                        <tr key={i} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                          <td className="px-4 py-2 font-semibold text-slate-900 dark:text-white">
                            {String(r.roll_number || "")}
                          </td>
                          <td className="px-4 py-2 font-sans">{String(r.full_name || "")}</td>
                          <td className="px-4 py-2 font-sans">{String(r.email || "")}</td>
                          <td className="px-4 py-2">{String(r.branch || "")}</td>
                          <td className="px-4 py-2">{String(r.cgpa || "")}</td>
                          <td className="px-4 py-2">
                            {r.active_backlogs !== null && r.active_backlogs !== undefined
                              ? String(r.active_backlogs)
                              : "None (Unknown)"}
                          </td>
                          <td className="px-4 py-2">{String(r.graduation_year || "")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Invalid Rows if Any */}
              {importReport.invalid_rows && importReport.invalid_rows.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Invalid Rows ({importReport.invalid_rows.length})
                  </div>
                  <div className="rounded-xl border border-rose-200 dark:border-rose-900 overflow-x-auto bg-rose-50/50 dark:bg-rose-950/20">
                    <table className="w-full text-left text-xs text-rose-700 dark:text-rose-300">
                      <thead className="text-[10px] uppercase border-b border-rose-200 dark:border-rose-900">
                        <tr>
                          <th className="px-4 py-2">Row #</th>
                          <th className="px-4 py-2">Raw Data</th>
                          <th className="px-4 py-2">Error</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-rose-200 dark:divide-rose-900 font-mono">
                        {importReport.invalid_rows.map((inv, idx) => (
                          <tr key={idx}>
                            <td className="px-4 py-2">{String(inv.row_index || idx + 1)}</td>
                            <td className="px-4 py-2">{JSON.stringify(inv.row_data || {})}</td>
                            <td className="px-4 py-2 font-sans font-medium text-rose-600">
                              {String(inv.error || "Validation error")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Correction Review */}
      {activeTab === "corrections" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-brand-600" />
                Pending Student Correction Proposals
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Review self-service student correction requests. Approved changes create a new verified revision; rejected changes leave facts unchanged.
              </p>
            </div>

            <button
              onClick={loadCorrections}
              disabled={loadingCorrections}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition font-medium"
            >
              {loadingCorrections ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {loadingCorrections ? (
            <div className="py-12 text-center text-sm text-slate-500">
              Loading pending correction proposals...
            </div>
          ) : pendingCorrections.length === 0 ? (
            <div className="glass-panel rounded-3xl p-12 text-center border border-slate-200 dark:border-slate-800 space-y-3">
              <div className="h-12 w-12 mx-auto rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h4 className="font-semibold text-slate-900 dark:text-white">
                All Caught Up!
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                No pending correction proposals awaiting review for this institution.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {pendingCorrections.map((proposal) => {
                const isBusy = decisionProcessing[proposal.id];
                return (
                  <div
                    key={proposal.id}
                    className="glass-panel p-6 rounded-3xl border border-slate-200 dark:border-slate-800 space-y-4"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-amber-600 flex items-center justify-center font-bold">
                          {proposal.student_name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900 dark:text-white text-sm">
                            {proposal.student_name} &bull;{" "}
                            <span className="font-mono text-brand-600">
                              {proposal.student_identifier}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-slate-400">
                            Submitted on {new Date(proposal.created_at).toLocaleString()}
                          </div>
                        </div>
                      </div>

                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                        Pending Decision
                      </span>
                    </div>

                    {/* Proposed Changes Diff */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1">
                        <div className="text-[10px] font-semibold uppercase text-slate-400 tracking-wider">
                          Proposed Academic Updates
                        </div>
                        <div className="font-mono font-medium text-slate-900 dark:text-white space-y-1 pt-1">
                          {Object.entries(proposal.proposed_changes).map(([k, v]) => (
                            <div key={k} className="flex items-center justify-between">
                              <span className="text-slate-500 capitalize">{k}:</span>
                              <span className="text-brand-600 dark:text-brand-400 font-bold">
                                {String(v)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1">
                        <div className="text-[10px] font-semibold uppercase text-slate-400 tracking-wider">
                          Student Justification
                        </div>
                        <p className="text-slate-700 dark:text-slate-300 italic pt-1 text-xs">
                          &ldquo;{proposal.justification}&rdquo;
                        </p>
                        {proposal.supporting_document_url && (
                          <div className="text-[11px] text-brand-600 pt-1 truncate">
                            Doc: {proposal.supporting_document_url}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Review Notes & Actions */}
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
                      <input
                        type="text"
                        placeholder="Add review notes or justification (e.g., verified via registrar)..."
                        value={decisionNotes[proposal.id] || ""}
                        onChange={(e) =>
                          setDecisionNotes({
                            ...decisionNotes,
                            [proposal.id]: e.target.value,
                          })
                        }
                        className="flex-1 px-4 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                      />

                      <div className="flex items-center gap-2 justify-end">
                        <button
                          onClick={() => handleDecideCorrection(proposal.id, "rejected")}
                          disabled={isBusy}
                          className="px-4 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:hover:bg-rose-900 dark:text-rose-300 text-xs font-semibold transition border border-rose-200 dark:border-rose-900 disabled:opacity-50"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => handleDecideCorrection(proposal.id, "approved")}
                          disabled={isBusy}
                          className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
                        >
                          Approve & Commit
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Student Detail & Revision History Modal */}
      {selectedStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in">
          <div className="glass-panel w-full max-w-2xl rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-700 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="text-xs font-mono uppercase text-brand-600 font-semibold">
                  Student Record Detail
                </div>
                <h3 className="text-2xl font-bold text-slate-900 dark:text-white">
                  {selectedStudent.full_name}
                </h3>
                <div className="text-xs text-slate-500 font-mono">
                  {selectedStudent.student_identifier} &bull; {selectedStudent.email}
                </div>
              </div>

              <button
                onClick={() => setSelectedStudent(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            {/* Current Verified Revision Card */}
            {selectedStudent.current_verified_revision ? (
              <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Active Verified Revision #{selectedStudent.current_verified_revision.revision_number}
                  </div>
                  <span className="text-[10px] text-slate-500">
                    Source: {selectedStudent.current_verified_revision.source}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500">Branch:</span>
                    <div className="font-semibold text-slate-900 dark:text-white mt-0.5">
                      {selectedStudent.current_verified_revision.branch}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500">CGPA:</span>
                    <div className="font-mono font-bold text-slate-900 dark:text-white mt-0.5">
                      {selectedStudent.current_verified_revision.cgpa.toFixed(2)} / {selectedStudent.current_verified_revision.cgpa_scale.toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500">Graduation Year:</span>
                    <div className="font-semibold text-slate-900 dark:text-white mt-0.5">
                      {selectedStudent.current_verified_revision.graduation_year}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500">Active Backlogs:</span>
                    <div className="font-semibold mt-0.5">
                      {selectedStudent.current_verified_revision.active_backlogs === 0
                        ? "0 Clean"
                        : selectedStudent.current_verified_revision.active_backlogs === null
                        ? "None (Unknown)"
                        : `${selectedStudent.current_verified_revision.active_backlogs} Active`}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300">
                No active verified revision bound to this student profile yet.
              </div>
            )}

            {/* Full Immutable Revision History Table */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase text-slate-400 tracking-wider flex items-center gap-2">
                <History className="w-3.5 h-3.5" />
                Immutable Academic Revision History
              </h4>

              <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 text-[10px] uppercase">
                    <tr>
                      <th className="px-3.5 py-2">Rev #</th>
                      <th className="px-3.5 py-2">Branch</th>
                      <th className="px-3.5 py-2">CGPA</th>
                      <th className="px-3.5 py-2">Backlogs</th>
                      <th className="px-3.5 py-2">Source</th>
                      <th className="px-3.5 py-2">Verified</th>
                      <th className="px-3.5 py-2">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {selectedStudent.revision_history.map((rev) => (
                      <tr key={rev.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                        <td className="px-3.5 py-2 font-bold text-brand-600">
                          #{rev.revision_number}
                        </td>
                        <td className="px-3.5 py-2">{rev.branch}</td>
                        <td className="px-3.5 py-2">{rev.cgpa.toFixed(2)}</td>
                        <td className="px-3.5 py-2">
                          {rev.active_backlogs === null ? "None" : rev.active_backlogs}
                        </td>
                        <td className="px-3.5 py-2 capitalize font-sans">{rev.source}</td>
                        <td className="px-3.5 py-2 font-sans">
                          {rev.is_verified ? "Yes" : "No"}
                        </td>
                        <td className="px-3.5 py-2 text-[10px] text-slate-400">
                          {new Date(rev.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setSelectedStudent(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
