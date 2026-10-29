"use client";

import { useCallback, useEffect, useState } from "react";
import type { DocumentRevisionResponse, DocumentType, StudentDriveResponse } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

const statusStyle: Record<string, string> = {
  eligible: "bg-emerald-100 text-emerald-800",
  ready: "bg-emerald-100 text-emerald-800",
  submitted: "bg-indigo-100 text-indigo-800",
  pending: "bg-amber-100 text-amber-800",
  needs_review: "bg-amber-100 text-amber-800",
  blocked: "bg-rose-100 text-rose-800",
  ineligible: "bg-rose-100 text-rose-800",
  eligibility_hold: "bg-rose-100 text-rose-800",
  withdrawn: "bg-slate-100 text-slate-700",
};

export default function StudentDrivesPage() {
  const { client, user } = useAuth();
  const [drives, setDrives] = useState<StudentDriveResponse[]>([]);
  const [documents, setDocuments] = useState<DocumentRevisionResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (user?.role !== "student") return;
    try {
      const [publishedDrives, history] = await Promise.all([
        client.listStudentDrives(),
        client.listMyDocuments(),
      ]);
      setDrives(publishedDrives);
      setDocuments(history);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load published drives");
    }
  }, [client, user]);

  useEffect(() => { void load(); }, [load]);

  async function upload(driveId: string, type: DocumentType, file: File) {
    setBusy(`${driveId}:${type}`);
    try {
      await client.uploadStudentDocument(type, file);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Document upload failed");
    } finally {
      setBusy(null);
    }
  }

  async function submit(driveId: string) {
    setBusy(`${driveId}:submit`);
    try {
      await client.submitRegistration(driveId);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Registration failed");
    } finally {
      setBusy(null);
    }
  }

  async function withdraw(item: StudentDriveResponse) {
    if (!item.registration) return;
    const reason = window.prompt("Reason for withdrawal (recorded in the audit trail):");
    if (!reason || reason.trim().length < 3) return;
    setBusy(`${item.drive_id}:withdraw`);
    try {
      await client.withdrawRegistration(item.registration.id, item.registration.concurrency_revision, reason);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Withdrawal failed");
    } finally {
      setBusy(null);
    }
  }

  async function download(revisionId: string) {
    try {
      const item = await client.getMyDocumentDownloadUrl(revisionId);
      window.open(item.download_url, "_blank", "noopener,noreferrer");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to prepare private download");
    }
  }

  if (!user || user.role !== "student") {
    return <main className="rounded-xl border bg-white p-8">Select a student development persona to participate in drives.</main>;
  }

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-slate-500">Published opportunities and personal evidence</p>
        <h1 className="text-3xl font-bold">My recruitment drives</h1>
        <p className="mt-2 text-slate-600">Eligibility, document readiness, and registration are separate statuses. All deadlines are enforced by the server.</p>
      </header>
      {error && <div role="alert" className="rounded border border-rose-300 bg-rose-50 p-3 text-rose-800">{error}</div>}
      {drives.length === 0 && <section className="rounded-xl border bg-white p-8 text-center text-slate-600">No published drive currently includes your evaluated profile.</section>}
      {drives.map((drive) => {
        const registrationState = drive.registration?.state;
        const canSubmit = drive.eligibility_status === "eligible" && drive.document_readiness.requirements
          .filter((item) => item.required_stage === "registration")
          .every((item) => item.status === "ready") && !registrationState;
        return (
          <article key={drive.drive_id} className="rounded-xl border bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-indigo-700">{drive.company_name}</p>
                <h2 className="text-2xl font-semibold">{drive.role_title}</h2>
                <p className="text-sm text-slate-600">{drive.location || "Location not supplied"} · {drive.work_mode.replace("_", " ")}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusStyle[drive.eligibility_status]}`}>Eligibility: {drive.eligibility_status.replace("_", " ")}</span>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusStyle[drive.document_readiness.status]}`}>Documents: {drive.document_readiness.status.replace("_", " ")}</span>
                {registrationState && <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusStyle[registrationState]}`}>Registration: {registrationState.replace("_", " ")}</span>}
              </div>
            </div>
            <div className="mt-4 rounded bg-slate-50 p-3 text-sm">
              <p>Registration opens {new Date(drive.registration_start_at).toLocaleString()}</p>
              <p>Exclusive deadline {new Date(drive.registration_end_at).toLocaleString()}</p>
              {drive.registration?.hold_reason && <p className="mt-2 font-medium text-rose-700">Hold: {drive.registration.hold_reason}</p>}
            </div>
            <section className="mt-5">
              <h3 className="font-semibold">Document checklist</h3>
              <div className="mt-2 grid gap-3 md:grid-cols-2">
                {drive.document_readiness.requirements.map((requirement) => (
                  <div key={requirement.requirement_id} className="rounded border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{requirement.display_label}</p>
                      <span className={`rounded px-2 py-1 text-xs font-semibold ${statusStyle[requirement.status]}`}>{requirement.status.replace("_", " ")}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">Required before {requirement.required_stage}</p>
                    {requirement.current_document && <p className="mt-2 text-xs">Revision {requirement.current_document.revision_number}: {requirement.current_document.original_filename}</p>}
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-600">
                      {requirement.findings.map((finding) => <li key={finding.code}>{finding.message}</li>)}
                    </ul>
                    <label className="mt-3 inline-block cursor-pointer rounded border px-3 py-2 text-xs font-medium hover:bg-slate-50">
                      {busy === `${drive.drive_id}:${requirement.document_type}` ? "Validating…" : requirement.current_document ? "Replace document" : "Upload document"}
                      <input
                        className="sr-only"
                        type="file"
                        accept=".pdf,.docx"
                        disabled={busy !== null}
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) void upload(drive.drive_id, requirement.document_type, file);
                        }}
                      />
                    </label>
                  </div>
                ))}
              </div>
            </section>
            <div className="mt-5 flex flex-wrap gap-3">
              {!registrationState && (
                <button disabled={!canSubmit || busy !== null} onClick={() => void submit(drive.drive_id)} className="rounded bg-indigo-700 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50">Submit registration</button>
              )}
              {registrationState && ["submitted", "eligibility_hold"].includes(registrationState) && (
                <button disabled={busy !== null} onClick={() => void withdraw(drive)} className="rounded border border-rose-300 px-4 py-2 text-rose-700 disabled:opacity-50">Withdraw</button>
              )}
              {!canSubmit && !registrationState && <p className="self-center text-sm text-slate-600">Submission unlocks only when current eligibility is eligible and registration-stage documents are ready.</p>}
            </div>
          </article>
        );
      })}
      <section className="rounded-xl border bg-white p-5">
        <h2 className="text-xl font-semibold">My document revision history</h2>
        <p className="mt-1 text-sm text-slate-500">Original files are retained privately. Replacements create new revisions rather than rewriting earlier bytes.</p>
        {documents.length === 0 ? <p className="mt-3 text-sm text-slate-600">No accepted document revisions.</p> : (
          <ul className="mt-3 divide-y">{documents.map((document) => (
            <li key={document.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
              <div><strong>{document.document_type.replace("_", " ")} v{document.revision_number}</strong><br/><span className="text-xs text-slate-500">{document.original_filename} · {document.text_status.replace("_", " ")}</span></div>
              <button onClick={() => void download(document.id)} className="rounded border px-3 py-1.5">Private download</button>
            </li>
          ))}</ul>
        )}
      </section>
    </main>
  );
}
