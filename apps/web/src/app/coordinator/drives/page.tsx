"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  CompanyResponse,
  DriveResponse,
  DriveListResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

export default function CoordinatorDrivesPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [drives, setDrives] = useState<DriveResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [companies, setCompanies] = useState<CompanyResponse[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [isCreatingCompany, setIsCreatingCompany] = useState(false);

  // Form Fields
  const [newCompanyName, setNewCompanyName] = useState("");
  const [newCompanyIndustry, setNewCompanyIndustry] = useState("");
  const [newCompanyWebsite, setNewCompanyWebsite] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [driveTitle, setDriveTitle] = useState("");
  const [driveDescription, setDriveDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchDrives = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res: DriveListResponse = await api.listDrives({
        status: statusFilter || undefined,
        limit: 50,
      });
      setDrives(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.message || "Failed to load recruitment drives");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchCompanies = async () => {
    try {
      const res = await api.listCompanies();
      setCompanies(res);
      if (res.length > 0 && !selectedCompanyId) {
        setSelectedCompanyId(res[0].id);
      }
    } catch (err) {
      console.error("Failed to load companies", err);
    }
  };

  useEffect(() => {
    fetchDrives();
  }, [fetchDrives]);

  const handleOpenModal = () => {
    fetchCompanies();
    setIsModalOpen(true);
    setModalError(null);
  };

  const handleCreateDrive = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setModalError(null);

    try {
      let companyId = selectedCompanyId;

      if (isCreatingCompany) {
        if (!newCompanyName.trim()) {
          setModalError("Company name is required");
          setSubmitting(false);
          return;
        }
        const createdComp = await api.createCompany({
          name: newCompanyName.trim(),
          industry: newCompanyIndustry.trim() || undefined,
          website: newCompanyWebsite.trim() || undefined,
        });
        companyId = createdComp.id;
      }

      if (!companyId) {
        setModalError("Please select or create a company");
        setSubmitting(false);
        return;
      }

      if (!driveTitle.trim()) {
        setModalError("Drive title is required");
        setSubmitting(false);
        return;
      }

      const createdDrive = await api.createDrive({
        company_id: companyId,
        academic_year: academicYear.trim(),
        title: driveTitle.trim(),
        description: driveDescription.trim() || undefined,
      });

      setIsModalOpen(false);
      router.push(`/coordinator/drives/${createdDrive.id}/intake`);
    } catch (err: any) {
      setModalError(err?.message || "Failed to create recruitment drive");
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "draft":
        return "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800";
      case "published":
        return "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800";
      case "active":
        return "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800";
      case "closed":
        return "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
      default:
        return "bg-slate-100 text-slate-800 border-slate-300";
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Campus Recruitment Drives
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage intake, eligibility policies, schedules, and workflows across hiring partners.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleOpenModal}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg shadow-sm transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            New Recruitment Drive
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Filter Status:
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="active">Active</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400">
          Total Drives: <span className="font-semibold text-slate-900 dark:text-slate-200">{total}</span>
        </div>
      </div>

      {/* Drives Table */}
      <div className="mt-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">
            <div className="animate-spin inline-block w-6 h-6 border-[3px] border-current border-t-transparent text-brand-600 rounded-full" />
            <p className="mt-2 text-sm">Loading recruitment drives...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600 dark:text-red-400 bg-red-50/50 dark:bg-red-950/20">
            <p className="font-medium">{error}</p>
          </div>
        ) : drives.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <svg className="w-12 h-12 mx-auto text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p className="text-base font-semibold text-slate-700 dark:text-slate-300">No recruitment drives found</p>
            <p className="text-sm text-slate-500 mt-1">Get started by creating your first drive or uploading a JD.</p>
            <button
              onClick={handleOpenModal}
              className="mt-4 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg shadow-sm transition"
            >
              Create Drive
            </button>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-left">
            <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
              <tr>
                <th className="px-6 py-3">Company & Title</th>
                <th className="px-6 py-3">Academic Cohort</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Revision</th>
                <th className="px-6 py-3">Source Documents</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-sm">
              {drives.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                  <td className="px-6 py-4">
                    <div className="font-semibold text-slate-900 dark:text-white">{d.company_name}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{d.title}</div>
                  </td>
                  <td className="px-6 py-4 text-slate-600 dark:text-slate-300 font-mono text-xs">
                    {d.academic_year}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize ${getStatusBadge(
                        d.status
                      )}`}
                    >
                      {d.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs font-mono text-slate-600 dark:text-slate-400">
                    Rev #{d.current_revision_number}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500">
                    {d.source_artifacts.length === 0 ? (
                      <span className="text-amber-600 dark:text-amber-400 font-medium">Pending JD</span>
                    ) : (
                      <span>{d.source_artifacts.length} file(s) attached</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Link href={`/coordinator/drives/${d.id}/eligibility`} className="inline-flex items-center px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium rounded-lg transition">Eligibility</Link>
                      <Link href={`/coordinator/drives/${d.id}/workflow`} className="inline-flex items-center px-3 py-1.5 bg-violet-50 hover:bg-violet-100 text-violet-700 text-xs font-medium rounded-lg transition">Workflow</Link>
                      {d.status === "published" && <Link href={`/coordinator/drives/${d.id}/communications`} className="inline-flex items-center px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-medium rounded-lg transition">Communications</Link>}
                      <Link
                        href={`/coordinator/drives/${d.id}/intake`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition"
                      >
                        Intake & Workspace
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                        </svg>
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Drive Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Create New Recruitment Drive</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-xs rounded-lg border border-red-200 dark:border-red-900">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateDrive} className="mt-4 space-y-4">
              {/* Company Selection */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    Hiring Company
                  </label>
                  <button
                    type="button"
                    onClick={() => setIsCreatingCompany(!isCreatingCompany)}
                    className="text-xs text-brand-600 hover:text-brand-700 dark:text-brand-400 font-medium"
                  >
                    {isCreatingCompany ? "← Select existing company" : "+ Register new company"}
                  </button>
                </div>

                {isCreatingCompany ? (
                  <div className="space-y-3 bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                    <div>
                      <input
                        type="text"
                        placeholder="Company Name (e.g. Acme Cloud Corp)"
                        value={newCompanyName}
                        onChange={(e) => setNewCompanyName(e.target.value)}
                        className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                        required
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="Industry (e.g. FinTech)"
                        value={newCompanyIndustry}
                        onChange={(e) => setNewCompanyIndustry(e.target.value)}
                        className="px-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                      />
                      <input
                        type="text"
                        placeholder="Website (e.g. acme.com)"
                        value={newCompanyWebsite}
                        onChange={(e) => setNewCompanyWebsite(e.target.value)}
                        className="px-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                ) : (
                  <select
                    value={selectedCompanyId}
                    onChange={(e) => setSelectedCompanyId(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  >
                    {companies.length === 0 ? (
                      <option value="">No companies registered. Register a new one.</option>
                    ) : (
                      companies.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} {c.industry ? `(${c.industry})` : ""}
                        </option>
                      ))
                    )}
                  </select>
                )}
              </div>

              {/* Academic Year */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  Academic Cohort / Year
                </label>
                <input
                  type="text"
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  placeholder="2026-2027"
                  className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  required
                />
              </div>

              {/* Drive Title */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  Drive Title
                </label>
                <input
                  type="text"
                  value={driveTitle}
                  onChange={(e) => setDriveTitle(e.target.value)}
                  placeholder="e.g. Software Development Engineer - Campus 2026"
                  className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  required
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  Notes / Description (Optional)
                </label>
                <textarea
                  value={driveDescription}
                  onChange={(e) => setDriveDescription(e.target.value)}
                  rows={2}
                  placeholder="Additional context or coordinator notes..."
                  className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg shadow-sm transition disabled:opacity-50"
                >
                  {submitting ? "Creating..." : "Create & Start Intake"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
