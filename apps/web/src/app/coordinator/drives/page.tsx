"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  CompanyResponse,
  DriveSummaryResponse,
  DriveSummaryListResponse,
} from "@placementos/api-client";
import { CoordinatorShell } from "../../../components/CoordinatorShell";

const CARD_WASHES = [
  "bg-mint-wash border-leaf-bright/30",
  "bg-sky-wash border-sky-signal/30",
  "bg-peach-wash border-coral-pulse/30",
  "bg-lilac-wash border-indigo-bloom/30",
  "bg-cream border-[#e6dcaf]/50",
  "bg-sage-wash border-secondary/30",
];

export default function CoordinatorDrivesPage() {
  const router = useRouter();

  const [drives, setDrives] = useState<DriveSummaryResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
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
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [driveTitle, setDriveTitle] = useState("");
  const [driveDescription, setDriveDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchDrives = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res: DriveSummaryListResponse = await api.listDriveSummaries({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 50,
      });
      setDrives(res.items || []);
      setTotal(res.total || 0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load recruitment drives");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchCompanies = async () => {
    try {
      const res = await api.listCompanies();
      setCompanies(res || []);
      if (res && res.length > 0 && !selectedCompanyId) {
        setSelectedCompanyId(res[0].id);
      }
    } catch (err) {
      console.error("Failed to load companies", err);
    }
  };

  useEffect(() => {
    fetchDrives();
  }, [fetchDrives]);

  const handleOpenCreateModal = () => {
    fetchCompanies();
    setIsModalOpen(true);
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
        const created = await api.createCompany({
          name: newCompanyName.trim(),
          industry: newCompanyIndustry.trim() || undefined,
        });
        companyId = created.id;
      }

      if (!driveTitle.trim()) {
        setModalError("Drive title / role is required");
        setSubmitting(false);
        return;
      }

      const newDrive = await api.createDrive({
        company_id: companyId,
        title: driveTitle.trim(),
        description: driveDescription.trim() || undefined,
        academic_year: academicYear,
      });

      setIsModalOpen(false);
      router.push(`/coordinator/drives/${newDrive.id}/intake`);
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to create drive");
    } finally {
      setSubmitting(false);
    }
  };

  // Filter drives by search
  const filteredDrives = drives.filter((d) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      d.company_name?.toLowerCase().includes(q) ||
      d.title?.toLowerCase().includes(q) ||
      d.status?.toLowerCase().includes(q)
    );
  });

  const filterOptions = [
    { label: `All (${total})`, value: "all" },
    { label: "Draft / Intake", value: "draft" },
    { label: "Published / Active", value: "published" },
    { label: "Registration Closed", value: "registration_closed" },
    { label: "In Progress", value: "in_progress" },
    { label: "Completed", value: "completed" },
  ];

  return (
    <CoordinatorShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Top Control Bar */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
                Campus Recruitment Drives
              </h1>
              <div className="flex items-center gap-2 font-body text-xs text-graphite mt-1">
                <span className="font-semibold text-canopy-green">Institution Allocation:</span>
                <span>{drives.length} active recruitment cycles</span>
                <span className="text-ash">•</span>
                <span className="text-secondary font-medium">Deterministic Rule Tracking</span>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <button
                onClick={handleOpenCreateModal}
                className="bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-sm font-semibold px-5 py-2.5 rounded-full shadow-xs transition flex items-center gap-2 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">add</span>
                <span>Create Drive</span>
              </button>
            </div>
          </div>

          {/* Search Input Bar */}
          <div className="relative w-full">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-ash text-[22px]">
              search
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by company name, role title, status..."
              className="w-full bg-cloud-gray rounded-full pl-12 pr-6 py-3 text-graphite placeholder-ash font-body text-sm focus:outline-none focus:bg-paper-white focus:ring-2 focus:ring-canopy-green transition border border-transparent focus:border-canopy-green"
            />
          </div>
        </div>

        {/* Lifecycle Filter Bar */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {filterOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`shrink-0 px-4 py-1.5 rounded-full font-body text-xs transition ${
                statusFilter === opt.value
                  ? "bg-canopy-green text-paper-white font-semibold shadow-xs"
                  : "bg-paper-white text-graphite hover:bg-surface-container border border-frost-gray"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Drives 2-Column Responsive Grid */}
        {loading ? (
          <div className="py-20 text-center font-body text-sm text-slate animate-pulse">
            Loading recruitment drives...
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-error-container text-on-error-container font-body text-sm">
            {error}
          </div>
        ) : filteredDrives.length === 0 ? (
          <div className="bg-paper-white rounded-2xl p-12 text-center border border-frost-gray font-body text-slate">
            <p className="text-sm">No recruitment drives found matching your criteria.</p>
            <button
              onClick={handleOpenCreateModal}
              className="mt-4 px-5 py-2 rounded-full bg-canopy-green text-paper-white text-xs font-semibold"
            >
              Create New Drive
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredDrives.map((drive, idx) => {
              const washClass = CARD_WASHES[idx % CARD_WASHES.length];
              const monogram = (drive.company_name || "C").charAt(0).toUpperCase();

              return (
                <div
                  key={drive.id}
                  className={`${washClass} rounded-[24px] p-6 border flex flex-col justify-between space-y-4 shadow-xs`}
                >
                  <div className="space-y-4">
                    {/* Top Company & Stage */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-paper-white flex items-center justify-center shrink-0 border border-frost-gray shadow-xs">
                          <span className="font-headline text-xl font-bold text-canopy-green">
                            {monogram}
                          </span>
                        </div>
                        <div>
                          <h2 className="font-headline text-lg font-bold text-canopy-green leading-snug">
                            {drive.company_name}
                          </h2>
                          <p className="font-body text-xs text-graphite font-medium">
                            {drive.title}
                          </p>
                        </div>
                      </div>

                      <span className="px-3 py-1 rounded-full bg-paper-white text-canopy-green font-body text-[11px] font-bold uppercase border border-frost-gray shadow-2xs">
                        {drive.status}
                      </span>
                    </div>

                    {/* Cohort Chips */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="bg-paper-white/90 text-canopy-green font-body text-xs px-3 py-0.5 rounded-full border border-frost-gray/50">
                        Batch of 2027 • Full-time
                      </span>
                      <span className="bg-paper-white/90 text-graphite font-body text-xs px-3 py-0.5 rounded-full border border-frost-gray/50">
                        {drive.academic_year || "2026–27"}
                      </span>
                    </div>

                    {/* Funnel Strip */}
                    <div className="grid grid-cols-3 gap-2 bg-paper-white/90 rounded-xl p-3 text-center border border-frost-gray/50 shadow-2xs">
                      <div>
                        <div className="font-headline text-lg font-bold text-canopy-green">
                          {(drive as any).eligible_count ?? "—"}
                        </div>
                        <div className="font-body text-[10px] text-slate uppercase font-semibold">
                          Eligible
                        </div>
                      </div>
                      <div>
                        <div className="font-headline text-lg font-bold text-canopy-green">
                          {(drive as any).registration_count ?? "—"}
                        </div>
                        <div className="font-body text-[10px] text-slate uppercase font-semibold">
                          Registered
                        </div>
                      </div>
                      <div>
                        <div className="font-headline text-lg font-bold text-coral-pulse">
                          {(drive as any).needs_review_count ?? "0"}
                        </div>
                        <div className="font-body text-[10px] text-slate uppercase font-semibold">
                          Review
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="pt-2 border-t border-black/5 flex items-center justify-between">
                    <span className="font-body text-[11px] text-graphite">
                      ID: <span className="font-mono">{drive.id.slice(0, 8)}...</span>
                    </span>

                    <button
                      onClick={() => router.push(`/coordinator/drives/${drive.id}/intake`)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs transition"
                    >
                      <span>Open Workspace</span>
                      <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Create Drive Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
            <div className="bg-paper-white rounded-3xl p-6 sm:p-8 max-w-lg w-full border border-frost-gray shadow-xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-4 border-b border-frost-gray">
                <div>
                  <h2 className="font-headline text-xl font-bold text-canopy-green">
                    Create Recruitment Drive
                  </h2>
                  <p className="font-body text-xs text-graphite mt-0.5">
                    Establish an audited recruitment cycle (INV-08).
                  </p>
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="p-1 rounded-full text-slate hover:text-ink-black hover:bg-surface-container"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              {modalError && (
                <div className="mt-4 p-3 rounded-xl bg-error-container text-on-error-container font-body text-xs">
                  {modalError}
                </div>
              )}

              <form onSubmit={handleCreateDrive} className="mt-5 space-y-4 font-body text-sm">
                <div>
                  <label className="block text-xs font-semibold text-graphite mb-1">Company</label>
                  {!isCreatingCompany ? (
                    <div className="space-y-2">
                      <select
                        value={selectedCompanyId}
                        onChange={(e) => setSelectedCompanyId(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs text-ink-black focus:outline-none focus:ring-2 focus:ring-canopy-green"
                      >
                        {companies.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} {c.industry ? `(${c.industry})` : ""}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setIsCreatingCompany(true)}
                        className="text-xs text-coral-pulse hover:underline font-semibold"
                      >
                        + Register New Company
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2 bg-lavender-mist/40 p-3 rounded-xl border border-frost-gray">
                      <input
                        type="text"
                        placeholder="Company Name (e.g. Google India)"
                        value={newCompanyName}
                        onChange={(e) => setNewCompanyName(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs"
                      />
                      <input
                        type="text"
                        placeholder="Industry (e.g. Technology)"
                        value={newCompanyIndustry}
                        onChange={(e) => setNewCompanyIndustry(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs"
                      />
                      <button
                        type="button"
                        onClick={() => setIsCreatingCompany(false)}
                        className="text-xs text-slate hover:underline"
                      >
                        ← Select Existing Company
                      </button>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-graphite mb-1">
                    Role Title / Position
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Software Engineer (Campus Graduate)"
                    value={driveTitle}
                    onChange={(e) => setDriveTitle(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-graphite mb-1">
                    Academic Cycle
                  </label>
                  <input
                    type="text"
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-graphite mb-1">
                    Description & Instructions (Optional)
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Brief description or coordinator notes..."
                    value={driveDescription}
                    onChange={(e) => setDriveDescription(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-canopy-green"
                  />
                </div>

                <div className="pt-3 border-t border-frost-gray flex items-center justify-end gap-3">
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
                    {submitting ? "Creating..." : "Create Drive"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </CoordinatorShell>
  );
}
