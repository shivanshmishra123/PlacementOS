"use client";

import { useCallback, useEffect, useState } from "react";
import type { StudentDriveResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";
import { StudentShell } from "../../../components/StudentShell";

export default function StudentRegistrationPage() {
  const { client, user } = useAuth();
  const [drives, setDrives] = useState<StudentDriveResponse[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.listStudentDrives();
      setDrives(res || []);
      if (!selectedDriveId && res && res.length > 0) {
        setSelectedDriveId(res[0].drive_id);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load registration opportunities");
    } finally {
      setLoading(false);
    }
  }, [client, selectedDriveId]);

  useEffect(() => {
    void load();
  }, [load]);

  const currentDrive = drives.find((d) => d.drive_id === selectedDriveId) || drives[0];

  const handleRegister = async () => {
    if (!currentDrive) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await client.submitRegistration(currentDrive.drive_id);
      setNotice(`Registration officially confirmed for ${currentDrive.company_name}!`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  const handleWithdraw = async () => {
    if (!currentDrive || !currentDrive.registration) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await client.withdrawRegistration(
        currentDrive.registration.id,
        currentDrive.registration.concurrency_revision,
        withdrawReason.trim() || "Student withdrew candidacy"
      );
      setNotice(`Registration successfully withdrawn for ${currentDrive.company_name}.`);
      setWithdrawReason("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Withdrawal failed");
    } finally {
      setBusy(false);
    }
  };

  const isEligible = currentDrive?.eligibility_status === "eligible";
  const isRegistered = currentDrive?.registration?.state === "submitted";
  const isHold = currentDrive?.registration?.state === "eligibility_hold";
  const isDocsReady = currentDrive?.document_readiness?.status === "ready";

  return (
    <StudentShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Header & Drive Selector */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
                Recruitment Drive Registration & Candidacy Status
              </h1>
              <p className="font-body text-xs text-graphite mt-1">
                Server-clock enforced cutoff bounds and deterministic eligibility verification (INV-08, INV-11).
              </p>
            </div>

            {drives.length > 1 && (
              <div className="flex items-center gap-2 text-xs font-body">
                <span className="font-semibold text-graphite">Select Drive:</span>
                <select
                  value={selectedDriveId}
                  onChange={(e) => setSelectedDriveId(e.target.value)}
                  className="bg-paper-white border border-frost-gray rounded-xl px-3 py-1.5 text-xs text-ink-black focus:ring-2 focus:ring-canopy-green font-medium"
                >
                  {drives.map((d) => (
                    <option key={d.drive_id} value={d.drive_id}>
                      {d.company_name} — {d.role_title}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

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

        {loading ? (
          <div className="py-20 text-center font-body text-sm text-slate animate-pulse">
            Loading drive status...
          </div>
        ) : !currentDrive ? (
          <div className="bg-paper-white rounded-2xl p-12 text-center border border-frost-gray font-body text-slate">
            No published drives available for registration.
          </div>
        ) : (
          <div className="space-y-6 font-body text-xs">
            {/* Status Hero Card */}
            <div
              className={`p-6 sm:p-8 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                isRegistered
                  ? "bg-mint-wash border-leaf-bright/40 text-canopy-green"
                  : isHold
                  ? "bg-peach-wash border-coral-pulse/40 text-coral-pulse"
                  : isEligible
                  ? "bg-sky-wash border-sky-signal/40 text-deep-teal"
                  : "bg-surface-container border-frost-gray text-slate"
              }`}
            >
              <div className="flex items-center gap-4">
                <span className="material-symbols-outlined text-[36px] shrink-0">
                  {isRegistered ? "task_alt" : isHold ? "pause_circle" : "how_to_reg"}
                </span>
                <div>
                  <h2 className="font-headline text-lg font-bold uppercase tracking-tight">
                    {isRegistered
                      ? "YOU ARE OFFICIALLY REGISTERED"
                      : isHold
                      ? "APPLICATION ON ELIGIBILITY HOLD"
                      : isEligible
                      ? "REGISTRATION WINDOW OPEN — ACTION REQUIRED"
                      : "ELIGIBILITY REQUIREMENTS NOT YET SATISFIED"}
                  </h2>
                  <p className="text-xs text-graphite font-body mt-0.5">
                    {currentDrive.company_name} • {currentDrive.role_title}
                  </p>
                </div>
              </div>

              {!isRegistered && isEligible && (
                <button
                  onClick={handleRegister}
                  disabled={busy}
                  className="px-6 py-2.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs shadow-xs transition shrink-0 cursor-pointer"
                >
                  {busy ? "Registering..." : "Confirm Drive Registration"}
                </button>
              )}
            </div>

            {/* Mandatory Registration Prerequisites Checklist */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-canopy-green text-[22px]">checklist</span>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Mandatory Registration Prerequisites
                  </h2>
                </div>
                <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full font-bold">
                  {isEligible && isDocsReady ? "All Cleared" : "Action Required"}
                </span>
              </div>

              <div className="space-y-3">
                {/* Item 1: Academic Eligibility */}
                <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span
                      className={`material-symbols-outlined text-[20px] mt-0.5 ${
                        isEligible ? "text-leaf-bright" : "text-coral-pulse"
                      }`}
                    >
                      {isEligible ? "check_circle" : "cancel"}
                    </span>
                    <div>
                      <span className="font-bold text-ink-black text-xs block">
                        Deterministic Academic Eligibility (INV-01)
                      </span>
                      <span className="text-[11px] text-slate block mt-0.5">
                        Evaluated strictly against verified institutional CGPA, active backlogs, and permitted branches.
                      </span>
                    </div>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase shrink-0 ${
                      isEligible ? "bg-mint-wash text-canopy-green" : "bg-peach-wash text-coral-pulse"
                    }`}
                  >
                    {currentDrive.eligibility_status}
                  </span>
                </div>

                {/* Item 2: Document Readiness */}
                <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span
                      className={`material-symbols-outlined text-[20px] mt-0.5 ${
                        isDocsReady ? "text-leaf-bright" : "text-sky-signal"
                      }`}
                    >
                      {isDocsReady ? "check_circle" : "pending"}
                    </span>
                    <div>
                      <span className="font-bold text-ink-black text-xs block">
                        Required Registration Documents (INV-06)
                      </span>
                      <span className="text-[11px] text-slate block mt-0.5">
                        Standard verified resume uploaded to secure quarantine and integrity validated.
                      </span>
                    </div>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase shrink-0 ${
                      isDocsReady ? "bg-mint-wash text-canopy-green" : "bg-sky-wash text-deep-teal"
                    }`}
                  >
                    {currentDrive.document_readiness?.status || "pending"}
                  </span>
                </div>

                {/* Item 3: Operational Cutoff */}
                <div className="p-4 rounded-xl bg-surface-container-low border border-frost-gray flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-leaf-bright text-[20px] mt-0.5">
                      check_circle
                    </span>
                    <div>
                      <span className="font-bold text-ink-black text-xs block">
                        Registration Window Enforced by Server Clock (INV-11)
                      </span>
                      <span className="text-[11px] text-slate block mt-0.5">
                        Closes: {currentDrive.registration_end_at ? new Date(currentDrive.registration_end_at).toLocaleString() : "Active"} (Exclusive cutoff boundary)
                      </span>
                    </div>
                  </div>
                  <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase shrink-0">
                    WINDOW ACTIVE
                  </span>
                </div>
              </div>
            </div>

            {/* Self-Service Withdrawal Panel (if registered) */}
            {isRegistered && (
              <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-3">
                <div className="flex items-center gap-2 pb-2 border-b border-frost-gray">
                  <span className="material-symbols-outlined text-slate text-[20px]">cancel</span>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Self-Service Registration Withdrawal
                  </h2>
                </div>
                <p className="text-slate text-[11px]">
                  You may self-withdraw prior to the drive deadline. Once withdrawn, re-registration requires coordinator assistance.
                </p>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Reason for withdrawal (optional)..."
                    value={withdrawReason}
                    onChange={(e) => setWithdrawReason(e.target.value)}
                    className="flex-1 bg-paper-white border border-frost-gray rounded-xl p-2 text-xs"
                  />
                  <button
                    onClick={handleWithdraw}
                    disabled={busy}
                    className="px-5 py-2 rounded-full border border-coral-pulse text-coral-pulse hover:bg-peach-wash font-semibold text-xs transition shrink-0"
                  >
                    Withdraw Registration
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </StudentShell>
  );
}

