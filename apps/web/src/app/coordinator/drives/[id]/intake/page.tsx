"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  api,
  DriveResponse,
  SourceArtifactResponse,
  TextExtractionResponse,
  TextLocator,
} from "@placementos/api-client";
import { useAuth } from "../../../../../context/AuthContext";

export default function DriveIntakePage() {
  const { id: driveId } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [drive, setDrive] = useState<DriveResponse | null>(null);
  const [activeArtifact, setActiveArtifact] = useState<SourceArtifactResponse | null>(null);
  const [extraction, setExtraction] = useState<TextExtractionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab State: "upload" | "paste"
  const [activeTab, setActiveTab] = useState<"upload" | "paste">("upload");

  // Upload Form State
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Pasted Text State
  const [pasteTitle, setPasteTitle] = useState("Job Description Intake");
  const [pasteText, setPasteText] = useState("");
  const [pasting, setPasting] = useState(false);
  const [pasteError, setPasteError] = useState<string | null>(null);

  // Selected Locator Highlight State
  const [selectedLocatorIndex, setSelectedLocatorIndex] = useState<number | null>(null);
  const paragraphRefs = useRef<Record<number, HTMLParagraphElement | null>>({});

  const fetchDriveAndSource = useCallback(async () => {
    if (!driveId) return;
    try {
      setLoading(true);
      setError(null);
      const d = await api.getDrive(driveId);
      setDrive(d);

      if (d.source_artifacts.length > 0) {
        const latestArtifactSummary = d.source_artifacts[0];
        const artifactRes = await api.getSourceArtifact(latestArtifactSummary.id);
        setActiveArtifact(artifactRes);

        if (artifactRes.status === "extracted") {
          try {
            const extRes = await api.getTextExtraction(artifactRes.id);
            setExtraction(extRes);
          } catch (extErr) {
            console.warn("Extraction record could not be fetched", extErr);
          }
        }
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load drive intake details");
    } finally {
      setLoading(false);
    }
  }, [driveId]);

  useEffect(() => {
    fetchDriveAndSource();
  }, [fetchDriveAndSource]);

  useEffect(() => {
    if (activeArtifact?.status !== "processing") return;
    const timer = window.setInterval(() => void fetchDriveAndSource(), 2000);
    return () => window.clearInterval(timer);
  }, [activeArtifact?.status, fetchDriveAndSource]);

  // Handle Drag & Drop / File Select
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.size > 15 * 1024 * 1024) {
        setUploadError("File exceeds 15MB limit. Please select a smaller document.");
        return;
      }
      setFileToUpload(selected);
      setUploadError(null);
    }
  };

  // Perform S3 Quarantine Upload Flow
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileToUpload || !driveId) return;

    try {
      setUploadProgress("Creating quarantine upload session...");
      setUploadError(null);

      // Step 1: Request presigned quarantine upload session
      const session = await api.createUploadSession({
        drive_id: driveId,
        purpose: "jd_intake",
        original_filename: fileToUpload.name,
        content_type: fileToUpload.type || "application/octet-stream",
        byte_size: fileToUpload.size,
      });

      // Step 2: PUT raw bytes to presigned URL
      setUploadProgress("Transferring bytes directly to secure private storage...");
      const putRes = await fetch(session.upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": fileToUpload.type || "application/octet-stream",
        },
        body: fileToUpload,
      });

      if (!putRes.ok) {
        throw new Error(`S3 upload failed with status ${putRes.status}`);
      }

      // Step 3: Complete upload session, promote to accepted, scan and extract
      setUploadProgress("Promoting accepted bytes and scanning document...");
      const artifact = await api.completeUploadSession(session.id);
      setActiveArtifact(artifact);
      setFileToUpload(null);
      setUploadProgress(null);

      // Refresh drive and extraction
      await fetchDriveAndSource();
    } catch (err: any) {
      setUploadProgress(null);
      setUploadError(err?.message || "File upload failed");
    }
  };

  // Handle Pasted Text Intake Flow
  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteText.trim() || !driveId) return;

    try {
      setPasting(true);
      setPasteError(null);
      const artifact = await api.createPastedSource(driveId, {
        title: pasteTitle.trim(),
        raw_text: pasteText.trim(),
      });
      setActiveArtifact(artifact);
      setPasteText("");
      await fetchDriveAndSource();
    } catch (err: any) {
      setPasteError(err?.message || "Failed to submit pasted text");
    } finally {
      setPasting(false);
    }
  };

  // Handle Presigned Download
  const handleDownload = async () => {
    if (!activeArtifact) return;
    try {
      const res = await api.getDownloadUrl(activeArtifact.id);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      alert("Failed to generate download URL: " + err?.message);
    }
  };

  // Click Locator to Scroll and Highlight
  const handleLocatorClick = (locator: TextLocator, idx: number) => {
    setSelectedLocatorIndex(idx);
    const targetRef = paragraphRefs.current[locator.paragraph_index];
    if (targetRef) {
      targetRef.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-slate-500">
        <div className="animate-spin inline-block w-8 h-8 border-4 border-current border-t-transparent text-brand-600 rounded-full" />
        <p className="mt-3 text-sm">Loading recruitment drive intake...</p>
      </div>
    );
  }

  if (error || !drive) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="p-6 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 rounded-xl text-red-700 dark:text-red-400">
          <h2 className="text-lg font-bold">Error Loading Drive</h2>
          <p className="mt-1 text-sm">{error || "Drive not found"}</p>
          <Link
            href="/coordinator/drives"
            className="inline-block mt-4 text-xs font-semibold uppercase text-brand-600 dark:text-brand-400"
          >
            ← Return to drives list
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
      {/* Top Breadcrumb & Drive Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link href="/coordinator/drives" className="hover:text-slate-700 dark:hover:text-slate-200">
              Recruitment Drives
            </Link>
            <span>/</span>
            <span className="font-semibold text-slate-800 dark:text-slate-200">{drive.company_name}</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              {drive.title}
            </h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800">
              {drive.status}
            </span>
            <span className="text-xs font-mono text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
              Rev #{drive.current_revision_number}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {extraction && (
            <Link
              href={`/coordinator/drives/${driveId}/review`}
              className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium rounded-lg transition"
            >
              Review facts and rules →
            </Link>
          )}
          <Link
            href="/coordinator/drives"
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition"
          >
            ← Back to Drives
          </Link>
        </div>
      </div>

      {/* Main Grid: Left Intake Panel (5 cols) & Right Viewer (7 cols) */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Intake Controls & File Metadata */}
        <div className="lg:col-span-5 space-y-6">
          {/* Active Artifact Summary Card if already attached */}
          {activeArtifact && (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 rounded-lg">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate max-w-[200px]">
                      {activeArtifact.original_filename || "Document Artifact"}
                    </h3>
                    <p className="text-xs text-slate-500 capitalize">{activeArtifact.source_type.replace("_", " ")}</p>
                  </div>
                </div>

                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider ${
                    activeArtifact.status === "extracted"
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300"
                      : activeArtifact.status === "failed"
                      ? "bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300"
                      : "bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300"
                  }`}
                >
                  {activeArtifact.status}
                </span>
              </div>

              {/* Parsing Error Box if Failed */}
              {activeArtifact.status === "failed" && (
                <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-lg text-xs text-red-700 dark:text-red-400 space-y-1">
                  <div className="font-semibold uppercase tracking-wider">
                    Error Code: {String(activeArtifact.metadata_json?.error_code || "PARSE_FAILURE")}
                  </div>
                  <p>{String(activeArtifact.metadata_json?.error_message || "Document could not be processed")}</p>
                  <p className="text-[11px] text-red-600 dark:text-red-400/80 pt-1">
                    Please review document format and upload a clean replacement below.
                  </p>
                </div>
              )}

              {/* Metadata details */}
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-50 dark:border-slate-800/60">
                  <span className="text-slate-500">SHA-256 Digest:</span>
                  <span className="font-mono text-slate-700 dark:text-slate-300" title={activeArtifact.hash_sha256}>
                    {activeArtifact.hash_sha256.substring(0, 16)}...
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50 dark:border-slate-800/60">
                  <span className="text-slate-500">Payload Size:</span>
                  <span className="text-slate-700 dark:text-slate-300 font-mono">
                    {(activeArtifact.byte_size / 1024).toFixed(1)} KB
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Attached:</span>
                  <span className="text-slate-700 dark:text-slate-300">
                    {new Date(activeArtifact.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleDownload}
                  className="flex-1 py-2 px-3 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium rounded-lg text-center transition"
                >
                  Download Original
                </button>
              </div>
            </div>
          )}

          {/* Intake Submission Card (Upload or Paste) */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              {activeArtifact ? "Replace / Supersede Document" : "Intake Job Description"}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Upload recruiter documents (PDF, DOCX) or paste recruiter communications directly.
            </p>

            {/* Tab Switcher */}
            <div className="mt-4 flex border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setActiveTab("upload")}
                className={`pb-2.5 px-3 border-b-2 transition ${
                  activeTab === "upload"
                    ? "border-brand-600 text-brand-600 dark:text-brand-400"
                    : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                }`}
              >
                Upload File (PDF / DOCX)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("paste")}
                className={`pb-2.5 px-3 border-b-2 transition ${
                  activeTab === "paste"
                    ? "border-brand-600 text-brand-600 dark:text-brand-400"
                    : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                }`}
              >
                Paste Text / Email
              </button>
            </div>

            {/* Tab 1: Upload Dropzone Form */}
            {activeTab === "upload" && (
              <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
                {uploadError && (
                  <div className="p-3 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-xs rounded-lg border border-red-200 dark:border-red-900">
                    {uploadError}
                  </div>
                )}

                {uploadProgress && (
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-xs rounded-lg border border-blue-200 dark:border-blue-900 flex items-center gap-2">
                    <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                    <span>{uploadProgress}</span>
                  </div>
                )}

                <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-6 text-center hover:border-brand-500 transition cursor-pointer relative bg-slate-50/50 dark:bg-slate-800/30">
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    onChange={handleFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="space-y-1 text-slate-600 dark:text-slate-300">
                    <svg className="w-8 h-8 mx-auto text-slate-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    {fileToUpload ? (
                      <div>
                        <p className="text-sm font-semibold text-brand-600 dark:text-brand-400">{fileToUpload.name}</p>
                        <p className="text-xs text-slate-500">{(fileToUpload.size / 1024).toFixed(1)} KB</p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-xs font-semibold">Drop PDF or Word document here, or click to browse</p>
                        <p className="text-[11px] text-slate-400">PDF, DOCX, TXT up to 15MB</p>
                      </div>
                    )}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={!fileToUpload || !!uploadProgress}
                  className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold uppercase tracking-wider rounded-lg shadow-sm transition disabled:opacity-50"
                >
                  {uploadProgress ? "Processing Intake..." : "Start Intake & Extraction"}
                </button>
              </form>
            )}

            {/* Tab 2: Pasted Text Form */}
            {activeTab === "paste" && (
              <form onSubmit={handlePasteSubmit} className="mt-4 space-y-4">
                {pasteError && (
                  <div className="p-3 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-xs rounded-lg border border-red-200 dark:border-red-900">
                    {pasteError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                    Document Title / Recipient Subject
                  </label>
                  <input
                    type="text"
                    value={pasteTitle}
                    onChange={(e) => setPasteTitle(e.target.value)}
                    placeholder="e.g. Campus Recruitment JD - Google 2026"
                    className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                    Raw Text or Email Body
                  </label>
                  <textarea
                    rows={8}
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                    placeholder="Paste full job description, eligibility terms, CTC breakdown, or recruiter correspondence here..."
                    className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={!pasteText.trim() || pasting}
                  className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold uppercase tracking-wider rounded-lg shadow-sm transition disabled:opacity-50"
                >
                  {pasting ? "Extracting Text..." : "Extract Text & Generate Locators"}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Right Column: Extracted Source Viewer & Interactive Locators Panel */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-[600px]">
            {/* Viewer Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50 dark:bg-slate-800/40">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  Source Document Viewer
                </h2>
                {extraction && (
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
                    Parser v{extraction.parser_version}
                  </span>
                )}
              </div>

              {extraction && (
                <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                  {extraction.page_count !== null && (
                    <span>
                      Pages: <strong className="text-slate-800 dark:text-slate-200">{extraction.page_count}</strong>
                    </span>
                  )}
                  <span>
                    Paragraphs: <strong className="text-slate-800 dark:text-slate-200">{extraction.paragraph_count}</strong>
                  </span>
                  <span>
                    Chars: <strong className="text-slate-800 dark:text-slate-200">{extraction.char_count}</strong>
                  </span>
                </div>
              )}
            </div>

            {/* Empty State when no extraction is available */}
            {!extraction ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-slate-400">
                <svg className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">No Extracted Source Available</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Upload a PDF/Word document or paste text on the left to extract plain text and generate source locators.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-12 flex-1 divide-y md:divide-y-0 md:divide-x divide-slate-200 dark:divide-slate-800">
                {/* Extracted Text Pane (7 cols) */}
                <div className="md:col-span-7 p-6 overflow-y-auto max-h-[700px] space-y-4 font-sans text-sm leading-relaxed text-slate-800 dark:text-slate-200">
                  {extraction.is_empty_or_scanned && (
                    <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-800 rounded-lg text-xs text-amber-800 dark:text-amber-300">
                      ⚠️ Scanned or Image-only Document detected. Extracted text may be incomplete.
                    </div>
                  )}

                  {extraction.locators.map((loc, idx) => {
                    const isSelected = selectedLocatorIndex === idx;
                    return (
                      <p
                        key={idx}
                        ref={(el) => {
                          paragraphRefs.current[loc.paragraph_index] = el;
                        }}
                        className={`p-2.5 rounded-lg transition text-xs leading-normal border ${
                          isSelected
                            ? "bg-brand-50/80 border-brand-400 dark:bg-brand-950/50 dark:border-brand-600 shadow-sm"
                            : "border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/40"
                        }`}
                      >
                        <span className="block text-[10px] font-mono font-semibold text-slate-400 dark:text-slate-500 mb-1">
                          {loc.page_number ? `P.${loc.page_number} ` : ""}¶{loc.paragraph_index} [offset {loc.char_offset_start}:{loc.char_offset_end}]
                        </span>
                        {loc.preview}
                      </p>
                    );
                  })}
                </div>

                {/* Locators Panel (5 cols) */}
                <div className="md:col-span-5 bg-slate-50/40 dark:bg-slate-900/40 p-4 overflow-y-auto max-h-[700px] space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
                    Source Locators ({extraction.locators.length})
                  </div>

                  {extraction.locators.map((loc, idx) => {
                    const isSelected = selectedLocatorIndex === idx;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleLocatorClick(loc, idx)}
                        className={`w-full text-left p-2.5 rounded-lg border text-xs transition ${
                          isSelected
                            ? "bg-brand-600 text-white border-brand-600 shadow-sm"
                            : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-brand-400"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className={`font-mono text-[11px] font-semibold ${isSelected ? "text-white" : "text-brand-600 dark:text-brand-400"}`}>
                            {loc.page_number ? `Page ${loc.page_number}` : `Paragraph ${loc.paragraph_index}`}
                          </span>
                          <span className={`text-[10px] font-mono ${isSelected ? "text-brand-100" : "text-slate-400"}`}>
                            ¶{loc.paragraph_index}
                          </span>
                        </div>
                        <p className={`line-clamp-2 text-[11px] ${isSelected ? "text-brand-50" : "text-slate-500 dark:text-slate-400"}`}>
                          {loc.preview}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
