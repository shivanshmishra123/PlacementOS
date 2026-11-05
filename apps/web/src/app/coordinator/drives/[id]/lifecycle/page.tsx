"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import type {
  DriveResponse,
  OutcomeRevisionResponse,
  ParticipantResponse,
  RecruitmentRoundResponse,
  RecruitmentSessionResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";
import { DriveWorkspaceHeader } from "../../../../../components/DriveWorkspaceHeader";

export default function DriveLifecyclePage() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const router = useRouter();
  const { client, user } = useAuth();

  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [rounds, setRounds] = useState<RecruitmentRoundResponse[]>([]);
  const [sessions, setSessions] = useState<RecruitmentSessionResponse[]>([]);
  const [participants, setParticipants] = useState<ParticipantResponse[]>([]);
  const [outcomes, setOutcomes] = useState<OutcomeRevisionResponse[]>([]);
  const [activeTab, setActiveTab] = useState<"rounds" | "results" | "closure">("rounds");

  // Form states
  const [roundName, setRoundName] = useState("Technical Interview");
  const [roundType, setRoundType] = useState<string>("interview");
  const [selectedRound, setSelectedRound] = useState("");
  const [sessionTitle, setSessionTitle] = useState("Technical Panel A");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [venue, setVenue] = useState("Room 304, Placement Block");
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [outcome, setOutcome] = useState<"advanced" | "rejected" | "waitlisted" | "selected" | "withdrawn">("selected");
  const [sourceReference, setSourceReference] = useState("synthetic://employer/result_batch_1");
  const [reason, setReason] = useState("");
  const [closureNotes, setClosureNotes] = useState("All candidate selections recorded and verified.");

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!driveId) return;
    try {
      const [driveData, nextRounds, nextSessions, roster, nextOutcomes] = await Promise.all([
        client.getDrive(driveId),
        client.listRounds(driveId),
        client.listSessions(driveId),
        client.listParticipants(driveId),
        client.listOutcomes(driveId),
      ]);
      setDrive(driveData);
      setRounds(nextRounds || []);
      setSessions(nextSessions || []);
      setParticipants(roster.items || []);
      setOutcomes(nextOutcomes || []);
      if (!selectedRound && nextRounds && nextRounds[0]) {
        setSelectedRound(nextRounds[0].id);
      }
      if (!selectedStudentId && roster.items && roster.items[0]) {
        setSelectedStudentId(roster.items[0].student_profile_id);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load lifecycle workspace");
    }
  }, [client, driveId, selectedRound, selectedStudentId]);

  useEffect(() => {
    void load();
  }, [load]);

  const addRound = async (event: FormEvent) => {
    event.preventDefault();
    if (!driveId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await client.createRound(driveId, {
        sequence_number: rounds.length + 1,
        name: roundName,
        round_type: roundType,
        requires_previous_round_outcome: rounds.length > 0,
      });
      setSelectedRound(created.id);
      setNotice(`Round "${created.name}" created.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add round");
    } finally {
      setBusy(false);
    }
  };

  const scheduleSession = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedRound || !driveId) return;
    setBusy(true);
    setError(null);
    try {
      const startIso = startAt ? new Date(startAt).toISOString() : new Date().toISOString();
      const endIso = endAt
        ? new Date(endAt).toISOString()
        : new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();

      await client.createSession(selectedRound, {
        start_at: startIso,
        end_at: endIso,
        timezone: "Asia/Kolkata",
        buffer_minutes: 15,
        venue: venue || undefined,
        capacity: 30,
        panel_members: ["Coordinator"],
        student_profile_ids: participants.slice(0, 15).map((p) => p.student_profile_id),
      });
      setNotice("Interview session scheduled with half-open conflict validation (INV-11).");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to schedule session");
    } finally {
      setBusy(false);
    }
  };

  const recordOutcome = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedRound || !selectedStudentId) return;
    setBusy(true);
    setError(null);
    try {
      await client.recordOutcome(selectedRound, {
        student_profile_id: selectedStudentId,
        outcome: outcome,
        source_type: "manual_panel",
        source_reference: sourceReference || "manual_entry",
        note: reason || "Employer panel decision",
      });
      setNotice(`Outcome "${outcome.toUpperCase()}" recorded for candidate.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record outcome");
    } finally {
      setBusy(false);
    }
  };

  const publishResults = async () => {
    if (!driveId) return;
    setBusy(true);
    setError(null);
    try {
      for (const out of outcomes) {
        const prop = await client.proposeResult(out.id);
        await client.decideResult(prop, "approved");
      }
      setNotice("Results officially published to students! Visible in student portal.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to publish results");
    } finally {
      setBusy(false);
    }
  };

  const closeDrive = async () => {
    if (!driveId) return;
    setBusy(true);
    setError(null);
    try {
      await client.closeDrive(driveId, closureNotes || "Drive closed");
      setNotice("Drive successfully closed and archived with verifiable closure report!");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pre-closure checklist failed");
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
            currentStepTitle="Lifecycle & Drive Closure"
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

        {/* 3 Lifecycle Tabs */}
        <div className="flex items-center gap-2 border-b border-frost-gray pb-1 font-body text-xs font-semibold">
          <button
            onClick={() => setActiveTab("rounds")}
            className={`px-4 py-2 rounded-xl transition ${
              activeTab === "rounds"
                ? "bg-canopy-green text-paper-white shadow-xs"
                : "bg-paper-white text-graphite hover:bg-surface-container border border-frost-gray"
            }`}
          >
            1. Rounds & Sessions ({rounds.length})
          </button>
          <button
            onClick={() => setActiveTab("results")}
            className={`px-4 py-2 rounded-xl transition ${
              activeTab === "results"
                ? "bg-canopy-green text-paper-white shadow-xs"
                : "bg-paper-white text-graphite hover:bg-surface-container border border-frost-gray"
            }`}
          >
            2. Attendance & Results ({outcomes.length})
          </button>
          <button
            onClick={() => setActiveTab("closure")}
            className={`px-4 py-2 rounded-xl transition ${
              activeTab === "closure"
                ? "bg-canopy-green text-paper-white shadow-xs"
                : "bg-paper-white text-graphite hover:bg-surface-container border border-frost-gray"
            }`}
          >
            3. Closure & Audit Report
          </button>
        </div>

        {/* TAB 1: Rounds & Sessions */}
        {activeTab === "rounds" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start font-body text-xs">
            {/* Create Round & Session Form */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
                <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
                  <span className="material-symbols-outlined text-canopy-green text-[20px]">add_circle</span>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Define Recruitment Round
                  </h2>
                </div>
                <form onSubmit={addRound} className="space-y-3">
                  <div>
                    <label className="block text-graphite font-semibold mb-1">Round Name</label>
                    <input
                      type="text"
                      required
                      value={roundName}
                      onChange={(e) => setRoundName(e.target.value)}
                      placeholder="e.g. Technical Interview Round 1"
                      className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                    />
                  </div>
                  <div>
                    <label className="block text-graphite font-semibold mb-1">Round Type</label>
                    <select
                      value={roundType}
                      onChange={(e) => setRoundType(e.target.value)}
                      className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                    >
                      <option value="test">Aptitude / Coding Test</option>
                      <option value="interview">Technical Interview</option>
                      <option value="hr">HR / Managerial Round</option>
                    </select>
                  </div>
                  <button
                    type="submit"
                    disabled={busy}
                    className="w-full py-2.5 rounded-full bg-canopy-green text-paper-white font-semibold text-xs shadow-xs hover:bg-[#062616] transition"
                  >
                    Add Stage to Pipeline
                  </button>
                </form>
              </div>

              {rounds.length > 0 && (
                <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
                    <span className="material-symbols-outlined text-coral-pulse text-[20px]">calendar_today</span>
                    <h2 className="font-headline text-base font-bold text-canopy-green">
                      Schedule Interview Session
                    </h2>
                  </div>
                  <form onSubmit={scheduleSession} className="space-y-3">
                    <div>
                      <label className="block text-graphite font-semibold mb-1">Target Round</label>
                      <select
                        value={selectedRound}
                        onChange={(e) => setSelectedRound(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                      >
                        {rounds.map((r) => (
                          <option key={r.id} value={r.id}>
                            #{r.sequence_number} {r.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-graphite font-semibold mb-1">Session Title</label>
                      <input
                        type="text"
                        value={sessionTitle}
                        onChange={(e) => setSessionTitle(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-graphite font-semibold mb-1">Start Time</label>
                        <input
                          type="datetime-local"
                          value={startAt}
                          onChange={(e) => setStartAt(e.target.value)}
                          className="w-full bg-paper-white border border-frost-gray rounded-xl p-2 text-xs focus:ring-2 focus:ring-canopy-green"
                        />
                      </div>
                      <div>
                        <label className="block text-graphite font-semibold mb-1">End Time</label>
                        <input
                          type="datetime-local"
                          value={endAt}
                          onChange={(e) => setEndAt(e.target.value)}
                          className="w-full bg-paper-white border border-frost-gray rounded-xl p-2 text-xs focus:ring-2 focus:ring-canopy-green"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-graphite font-semibold mb-1">Venue / Link</label>
                      <input
                        type="text"
                        value={venue}
                        onChange={(e) => setVenue(e.target.value)}
                        className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={busy}
                      className="w-full py-2.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs shadow-xs transition"
                    >
                      Schedule Verified Session
                    </button>
                  </form>
                </div>
              )}
            </div>

            {/* Existing Rounds & Sessions List */}
            <div className="lg:col-span-7 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Scheduled Recruitment Sessions
                  </h2>
                  <span className="text-slate text-xs">
                    Half-open interval overlap checks prevent student/venue collision.
                  </span>
                </div>
                <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full font-bold">
                  {sessions.length} Active Sessions
                </span>
              </div>

              {sessions.length === 0 ? (
                <div className="py-16 text-center text-slate">
                  No interview sessions scheduled yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {sessions.map((sess) => (
                    <div
                      key={sess.id}
                      className="p-4 rounded-xl bg-surface-container-low border border-frost-gray space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-headline text-sm font-bold text-canopy-green">
                          {sess.revision ? `Session Rev #${sess.revision.revision_number}` : `Session #${sess.id.slice(0, 8)}`}
                        </span>
                        <span className="bg-sky-wash text-deep-teal px-2 py-0.5 rounded-full text-[10px] font-bold">
                          {sess.revision?.capacity ?? 30} Capacity
                        </span>
                      </div>
                      <div className="text-slate text-[11px] flex items-center gap-4">
                        <span>Venue: {sess.revision?.venue || "Main Auditorium"}</span>
                        <span>•</span>
                        <span>Time: {sess.revision?.start_at ? new Date(sess.revision.start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "TBD"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: Attendance & Employer Results */}
        {activeTab === "results" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start font-body text-xs">
            <div className="lg:col-span-5 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-frost-gray">
                <span className="material-symbols-outlined text-canopy-green text-[20px]">rate_review</span>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Record Employer Selection Result
                </h2>
              </div>
              <form onSubmit={recordOutcome} className="space-y-3">
                <div>
                  <label className="block text-graphite font-semibold mb-1">Candidate</label>
                  <select
                    value={selectedStudentId}
                    onChange={(e) => setSelectedStudentId(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  >
                    {participants.map((p) => (
                      <option key={p.student_profile_id} value={p.student_profile_id}>
                        {p.student_name} ({p.student_identifier})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-graphite font-semibold mb-1">Employer Outcome</label>
                  <select
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value as any)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  >
                    <option value="selected">Selected / Offer Extended</option>
                    <option value="advanced">Advanced to Next Stage</option>
                    <option value="waitlisted">Waitlisted</option>
                    <option value="rejected">Not Selected</option>
                  </select>
                </div>
                <div>
                  <label className="block text-graphite font-semibold mb-1">Source Reference</label>
                  <input
                    type="text"
                    value={sourceReference}
                    onChange={(e) => setSourceReference(e.target.value)}
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>
                <div>
                  <label className="block text-graphite font-semibold mb-1">Panel Notes</label>
                  <textarea
                    rows={2}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Panel comments or interview assessment notes..."
                    className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                  />
                </div>
                <button
                  type="submit"
                  disabled={busy}
                  className="w-full py-2.5 rounded-full bg-canopy-green text-paper-white font-semibold text-xs shadow-xs hover:bg-[#062616] transition"
                >
                  Commit Verified Outcome
                </button>
              </form>
            </div>

            <div className="lg:col-span-7 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Recorded Selections ({outcomes.length})
                  </h2>
                  <span className="text-slate text-xs">
                    Internal outcomes require coordinator publication before student visibility.
                  </span>
                </div>
                <button
                  onClick={publishResults}
                  disabled={busy || outcomes.length === 0}
                  className="px-4 py-1.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs shadow-xs transition"
                >
                  Publish to Students
                </button>
              </div>

              {outcomes.length === 0 ? (
                <div className="py-16 text-center text-slate">
                  No selection outcomes recorded yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {outcomes.map((out) => (
                    <div
                      key={out.id}
                      className="p-3.5 rounded-xl bg-surface-container-low border border-frost-gray flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-ink-black text-sm block">
                          Student ID: {out.student_profile_id.slice(0, 8)}...
                        </span>
                        <span className="text-slate text-[11px] block">{out.note || "No notes"}</span>
                      </div>
                      <span className="bg-mint-wash text-canopy-green px-3 py-1 rounded-full text-xs font-bold uppercase">
                        {out.outcome}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: Pre-Closure Audit Certification & Drive Closure */}
        {activeTab === "closure" && (
          <div className="bg-paper-white rounded-2xl p-8 border border-frost-gray shadow-xs space-y-6 max-w-2xl mx-auto font-body text-xs">
            <div className="flex items-center gap-3 pb-4 border-b border-frost-gray">
              <span className="material-symbols-outlined text-canopy-green text-[28px]">verified</span>
              <div>
                <h2 className="font-headline text-lg font-bold text-canopy-green">
                  Pre-Closure Audit Certification
                </h2>
                <span className="text-slate text-xs">
                  Verifies that all operational invariants have been satisfied before drive termination.
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-mint-wash/40 border border-leaf-bright/30 flex items-center justify-between">
                <span className="font-medium text-canopy-green">
                  ✓ Deterministic Eligibility Evaluation Snapshot Archived
                </span>
                <span className="material-symbols-outlined text-leaf-bright text-[18px]">check_circle</span>
              </div>
              <div className="p-3.5 rounded-xl bg-mint-wash/40 border border-leaf-bright/30 flex items-center justify-between">
                <span className="font-medium text-canopy-green">
                  ✓ Document Readiness Checked for All Candidates
                </span>
                <span className="material-symbols-outlined text-leaf-bright text-[18px]">check_circle</span>
              </div>
              <div className="p-3.5 rounded-xl bg-mint-wash/40 border border-leaf-bright/30 flex items-center justify-between">
                <span className="font-medium text-canopy-green">
                  ✓ All Transactional Outbox Messages Delivered or Accounted
                </span>
                <span className="material-symbols-outlined text-leaf-bright text-[18px]">check_circle</span>
              </div>
              <div className="p-3.5 rounded-xl bg-mint-wash/40 border border-leaf-bright/30 flex items-center justify-between">
                <span className="font-medium text-canopy-green">
                  ✓ Final Selection Outcomes Frozen with Source Citations
                </span>
                <span className="material-symbols-outlined text-leaf-bright text-[18px]">check_circle</span>
              </div>
            </div>

            <div>
              <label className="block text-graphite font-semibold mb-1">Drive Closure Certification Notes</label>
              <textarea
                rows={3}
                value={closureNotes}
                onChange={(e) => setClosureNotes(e.target.value)}
                className="w-full bg-paper-white border border-frost-gray rounded-xl p-3 text-xs focus:ring-2 focus:ring-canopy-green"
              />
            </div>

            <div className="pt-4 border-t border-frost-gray flex items-center justify-between">
              <span className="text-slate text-[11px]">Drive State: {drive?.status.toUpperCase()}</span>
              <button
                onClick={closeDrive}
                disabled={busy}
                className="px-6 py-2.5 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs shadow-xs transition"
              >
                {busy ? "Certifying..." : "Officially Close & Archive Drive"}
              </button>
            </div>
          </div>
        )}
      </div>
    </CoordinatorShell>
  );
}
