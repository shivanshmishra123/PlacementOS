"use client";

import { useCallback, useEffect, useState } from "react";
import type { DocumentRevisionResponse, DocumentType } from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";
import { StudentShell } from "../../../components/StudentShell";

interface DocumentSlot {
  type: DocumentType;
  title: string;
  stage: string;
  allowedFormats: string;
  maxSize: string;
}

const DOCUMENT_SLOTS: DocumentSlot[] = [
  {
    type: "resume",
    title: "Resume / Curriculum Vitae",
    stage: "REQUIRED AT REGISTRATION",
    allowedFormats: "PDF, DOCX",
    maxSize: "10.0 MB",
  },
  {
    type: "marksheet",
    title: "Latest Consolidated Marksheet",
    stage: "REQUIRED BEFORE INTERVIEWS",
    allowedFormats: "PDF Only",
    maxSize: "10.0 MB",
  },
  {
    type: "college_id",
    title: "College Photo Identity Card",
    stage: "REQUIRED BEFORE INTERVIEWS",
    allowedFormats: "PDF, JPEG, PNG",
    maxSize: "5.0 MB",
  },
];

export default function StudentDocumentsPage() {
  const { client, user } = useAuth();
  const [documents, setDocuments] = useState<DocumentRevisionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.listMyDocuments();
      setDocuments(res || []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load document checklist");
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleUpload = async (type: DocumentType, file: File) => {
    setUploadingType(type);
    setError(null);
    setSuccessNotice(null);
    try {
      await client.uploadStudentDocument(type, file);
      setSuccessNotice(`Document "${file.name}" uploaded, scanned, and verified!`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to upload document");
    } finally {
      setUploadingType(null);
    }
  };

  const completedCount = documents.filter((d) => d.scan_status !== "failed").length;
  const progressPct = Math.round((completedCount / DOCUMENT_SLOTS.length) * 100);

  return (
    <StudentShell>
      <div className="flex flex-col w-full space-y-6">
        {/* Header Strip */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="font-headline text-2xl font-bold text-canopy-green tracking-tight">
                Mandatory Verification Documents Checklist
              </h1>
              <p className="font-body text-xs text-graphite mt-1">
                Upload verified academic and identity documents required for drive registration and employer interview rounds (INV-06).
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="bg-mint-wash text-canopy-green font-body text-xs px-3 py-1 rounded-full font-bold border border-leaf-bright/30">
                {completedCount} of {DOCUMENT_SLOTS.length} Complete ({progressPct}%)
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-cloud-gray h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-leaf-bright h-full rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {successNotice && (
          <div className="p-3.5 rounded-xl bg-mint-wash text-canopy-green font-body text-xs font-semibold border border-leaf-bright/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-leaf-bright">check_circle</span>
            <span>{successNotice}</span>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* Document Requirement Cards Stack */}
        <div className="space-y-4">
          {DOCUMENT_SLOTS.map((slot) => {
            const uploadedDoc = documents.find((d) => d.document_type === slot.type);
            const isReady = !!uploadedDoc && uploadedDoc.scan_status !== "failed";
            const isBusy = uploadingType === slot.type;

            return (
              <div
                key={slot.type}
                className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs"
              >
                {/* Title & Stage Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-canopy-green text-[26px]">
                      {slot.type === "resume" ? "description" : slot.type === "marksheet" ? "school" : "badge"}
                    </span>
                    <div>
                      <h2 className="font-headline text-base font-bold text-canopy-green">
                        {slot.title}
                      </h2>
                      <span className="text-[10px] font-mono text-slate uppercase">
                        {slot.stage}
                      </span>
                    </div>
                  </div>

                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold uppercase border ${
                      isReady
                        ? "bg-mint-wash text-canopy-green border-leaf-bright/40"
                        : "bg-peach-wash text-coral-pulse border-coral-pulse/40"
                    }`}
                  >
                    {isReady ? "READY" : "PENDING UPLOAD"}
                  </span>
                </div>

                {/* Specs Box */}
                <div className="p-3 rounded-xl bg-cloud-gray/60 flex items-center gap-4 text-graphite text-[11px] flex-wrap">
                  <span><strong>Format:</strong> {slot.allowedFormats}</span>
                  <span className="text-ash">•</span>
                  <span><strong>Max Size:</strong> {slot.maxSize}</span>
                  <span className="text-ash">•</span>
                  <span><strong>Storage:</strong> Private Encrypted S3</span>
                </div>

                {/* Uploaded File Info or Upload Button */}
                {uploadedDoc ? (
                  <div className="p-4 rounded-xl bg-mint-wash/30 border border-leaf-bright/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-canopy-green text-[22px]">
                        verified
                      </span>
                      <div>
                        <span className="font-semibold text-canopy-green block text-xs">
                          {uploadedDoc.original_filename}
                        </span>
                        <span className="text-[11px] text-slate font-mono">
                          Revision #{uploadedDoc.revision_number} • {(uploadedDoc.file_size_bytes / 1024 / 1024).toFixed(2)} MB • Checked Clean
                        </span>
                      </div>
                    </div>

                    <label className="cursor-pointer">
                      <span className="px-4 py-1.5 rounded-full border border-frost-gray bg-paper-white hover:bg-surface-container font-semibold text-xs text-graphite inline-block transition">
                        {isBusy ? "Replacing..." : "Replace File"}
                      </span>
                      <input
                        type="file"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleUpload(slot.type, e.target.files[0]);
                          }
                        }}
                      />
                    </label>
                  </div>
                ) : (
                  <div className="p-6 rounded-xl border-2 border-dashed border-frost-gray hover:border-canopy-green transition text-center bg-surface-container-low/40">
                    <label className="cursor-pointer block">
                      <span className="material-symbols-outlined text-[32px] text-coral-pulse mb-1 block">
                        upload_file
                      </span>
                      <span className="font-semibold text-canopy-green text-xs block">
                        {isBusy ? "Uploading & Scanning..." : `Click to Upload ${slot.title}`}
                      </span>
                      <span className="text-[11px] text-slate mt-0.5 block">
                        Select file from your device ({slot.allowedFormats})
                      </span>
                      <input
                        type="file"
                        disabled={isBusy}
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleUpload(slot.type, e.target.files[0]);
                          }
                        }}
                      />
                    </label>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Security Invariant Guarantee Banner */}
        <div className="p-5 rounded-2xl bg-canopy-green text-paper-white shadow-xs space-y-2">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-leaf-bright text-[20px]">lock</span>
            <span className="font-headline text-sm font-bold">Encrypted Document Boundary (INV-06)</span>
          </div>
          <p className="text-xs text-paper-white/80 font-body leading-relaxed">
            Your uploaded documents are isolated by student owner ID in encrypted storage. Only authenticated hiring panels and assigned placement coordinators are granted short-lived download authorization.
          </p>
        </div>
      </div>
    </StudentShell>
  );
}

