"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  api,
  DriveResponse,
  SourceArtifactResponse,
  TextExtractionResponse,
  TextLocator,
} from "@placementos/api-client";
import { CoordinatorShell } from "../../../../../components/CoordinatorShell";
import { DriveWorkspaceHeader } from "../../../../../components/DriveWorkspaceHeader";

export default function DriveIntakePage() {
  const params = useParams();
  const driveId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";
  const router = useRouter();

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

      if (d.source_artifacts && d.source_artifacts.length > 0) {
        const latestArtifactSummary = d.source_artifacts[0];
        const artifactRes = await api.getSourceArtifact(latestArtifactSummary.id);
        setActiveArtifact(artifactRes);

        if (artifactRes.status === "extracted") {
          try {
            const extRes = await api.getTextExtraction(artifactRes.id);
            setExtraction(extRes);
          } catch (extErr) {
            console.error("Text extraction load error:", extErr);
          }
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load drive intake workspace");
    } finally {
      setLoading(false);
    }
  }, [driveId]);

  useEffect(() => {
    fetchDriveAndSource();
  }, [fetchDriveAndSource]);

  const handleUploadFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileToUpload || !driveId) return;

    try {
      setUploadError(null);
      setUploadProgress("Initiating owner-bound quarantine session...");

      const session = await api.createUploadSession({
        original_filename: fileToUpload.name,
        byte_size: fileToUpload.size,
        content_type: fileToUpload.type || "application/pdf",
        drive_id: driveId,
        purpose: "job_description",
      });

      setUploadProgress("Uploading encrypted bytes to secure storage...");
      const putRes = await fetch(session.upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": fileToUpload.type || "application/pdf",
        },
        body: fileToUpload,
      });

      if (!putRes.ok) {
        throw new Error(`Upload failed with storage status ${putRes.status}`);
      }

      setUploadProgress("Verifying checksum & promoting to accepted storage...");
      const artifact = await api.completeUploadSession(session.id);

      setActiveArtifact(artifact);
      setFileToUpload(null);
      setUploadProgress(null);
      fetchDriveAndSource();
    } catch (err: unknown) {
      setUploadProgress(null);
      setUploadError(err instanceof Error ? err.message : "Document upload failed");
    }
  };

  const handlePasteText = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteText.trim() || !driveId) return;

    try {
      setPasting(true);
      setPasteError(null);

      const artifact = await api.createPastedSource(driveId, {
        title: pasteTitle.trim() || "Pasted Source",
        raw_text: pasteText.trim(),
      });

      setActiveArtifact(artifact);
      setPasteText("");
      fetchDriveAndSource();
    } catch (err: unknown) {
      setPasteError(err instanceof Error ? err.message : "Pasted text intake failed");
    } finally {
      setPasting(false);
    }
  };

  const handleReExtract = async (artifactId: string) => {
    try {
      await api.retriggerExtraction(artifactId);
      fetchDriveAndSource();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to trigger re-extraction");
    }
  };

  const handleDownload = async (artifactId: string) => {
    try {
      const res = await api.getDownloadUrl(artifactId);
      window.open(res.download_url, "_blank");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to generate download URL");
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
            currentStepTitle="Intake Workspace"
            actions={
              activeArtifact && activeArtifact.status === "extracted" ? (
                <Link
                  href={`/coordinator/drives/${drive.id}/review`}
                  className="inline-flex items-center gap-2 bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-body text-xs font-semibold px-5 py-2.5 rounded-full shadow-xs transition"
                >
                  <span>Proceed to Rule Review</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </Link>
              ) : undefined
            }
          />
        )}

        {/* 2-Column Responsive Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (5 cols): Ingestion Forms */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            {/* Upload & Paste Tab Container */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div>
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Intake Recruitment Information
                  </h2>
                  <p className="font-body text-xs text-graphite">
                    Support PDF, DOCX, or direct email body text (INV-03).
                  </p>
                </div>

                <div className="flex items-center bg-cloud-gray p-1 rounded-full text-xs font-body font-medium">
                  <button
                    onClick={() => setActiveTab("upload")}
                    className={`px-3 py-1 rounded-full transition ${
                      activeTab === "upload"
                        ? "bg-canopy-green text-paper-white shadow-2xs font-semibold"
                        : "text-graphite hover:text-ink-black"
                    }`}
                  >
                    File Upload
                  </button>
                  <button
                    onClick={() => setActiveTab("paste")}
                    className={`px-3 py-1 rounded-full transition ${
                      activeTab === "paste"
                        ? "bg-canopy-green text-paper-white shadow-2xs font-semibold"
                        : "text-graphite hover:text-ink-black"
                    }`}
                  >
                    Paste Text
                  </button>
                </div>
              </div>

              {activeTab === "upload" ? (
                <form onSubmit={handleUploadFile} className="space-y-4">
                  {uploadError && (
                    <div className="p-3 rounded-xl bg-error-container text-on-error-container font-body text-xs">
                      {uploadError}
                    </div>
                  )}

                  {/* Drop-zone */}
                  <label className="border-2 border-dashed border-frost-gray hover:border-canopy-green rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition bg-surface-container-low/50 hover:bg-surface-container-low block">
                    <span className="material-symbols-outlined text-[36px] text-coral-pulse mb-2">
                      cloud_upload
                    </span>
                    <span className="font-body text-sm font-semibold text-canopy-green block">
                      Choose PDF / DOCX file
                    </span>
                    <span className="font-body text-xs text-slate mt-1 block">
                      Max file size 20MB • Sniffed signature checks enforced
                    </span>
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setFileToUpload(e.target.files[0]);
                        }
                      }}
                      className="hidden"
                    />
                  </label>

                  {fileToUpload && (
                    <div className="p-3 rounded-xl bg-mint-wash border border-leaf-bright/30 flex items-center justify-between text-xs font-body">
                      <div className="flex items-center gap-2 truncate">
                        <span className="material-symbols-outlined text-canopy-green text-[18px]">
                          description
                        </span>
                        <span className="font-medium text-canopy-green truncate">
                          {fileToUpload.name} ({(fileToUpload.size / 1024 / 1024).toFixed(2)} MB)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setFileToUpload(null)}
                        className="text-slate hover:text-error"
                      >
                        <span className="material-symbols-outlined text-[16px]">close</span>
                      </button>
                    </div>
                  )}

                  {uploadProgress && (
                    <div className="p-3 rounded-xl bg-sky-wash text-deep-teal font-body text-xs flex items-center gap-2">
                      <span className="material-symbols-outlined text-[16px] animate-spin">
                        progress_activity
                      </span>
                      <span>{uploadProgress}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={!fileToUpload || !!uploadProgress}
                    className="w-full py-2.5 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs disabled:opacity-50 transition cursor-pointer"
                  >
                    Ingest & Validate Source
                  </button>
                </form>
              ) : (
                <form onSubmit={handlePasteText} className="space-y-4">
                  {pasteError && (
                    <div className="p-3 rounded-xl bg-error-container text-on-error-container font-body text-xs">
                      {pasteError}
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-semibold text-graphite mb-1">Source Title</label>
                    <input
                      type="text"
                      value={pasteTitle}
                      onChange={(e) => setPasteTitle(e.target.value)}
                      placeholder="e.g. Email from Campus Recruiter"
                      className="w-full bg-paper-white border border-frost-gray rounded-xl p-2.5 text-xs focus:ring-2 focus:ring-canopy-green"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-graphite mb-1">
                      Raw Job Description / Email Content
                    </label>
                    <textarea
                      rows={8}
                      required
                      value={pasteText}
                      onChange={(e) => setPasteText(e.target.value)}
                      placeholder="Paste complete JD text including requirements, compensation, and selection rounds..."
                      className="w-full bg-paper-white border border-frost-gray rounded-xl p-3 text-xs font-mono focus:ring-2 focus:ring-canopy-green"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={pasting || !pasteText.trim()}
                    className="w-full py-2.5 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-body text-xs font-semibold shadow-xs disabled:opacity-50 transition cursor-pointer"
                  >
                    {pasting ? "Extracting Text..." : "Ingest Pasted Content"}
                  </button>
                </form>
              )}
            </div>

            {/* Ingested Documents List */}
            <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
                <div className="flex items-center gap-2">
                  <h2 className="font-headline text-base font-bold text-canopy-green">
                    Ingested Source Artifacts
                  </h2>
                  <span className="bg-mint-wash text-canopy-green font-body text-xs px-2.5 py-0.5 rounded-full font-bold">
                    {drive?.source_artifacts?.length || 0}
                  </span>
                </div>
                <button
                  onClick={fetchDriveAndSource}
                  className="text-xs font-body text-canopy-green hover:underline flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[14px]">refresh</span>
                  <span>Sync</span>
                </button>
              </div>

              {!drive?.source_artifacts || drive.source_artifacts.length === 0 ? (
                <div className="py-6 text-center text-xs font-body text-slate">
                  No source documents uploaded yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {drive.source_artifacts.map((art) => (
                    <div
                      key={art.id}
                      className={`p-3 rounded-xl border transition ${
                        activeArtifact?.id === art.id
                          ? "bg-mint-wash/30 border-leaf-bright"
                          : "bg-surface-container-low border-frost-gray hover:border-canopy-green"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="material-symbols-outlined text-coral-pulse text-[20px]">
                            description
                          </span>
                          <div className="min-w-0">
                            <span className="font-body text-xs font-semibold text-canopy-green block truncate">
                              {art.original_filename || art.source_type}
                            </span>
                            <span className="font-mono text-[10px] text-slate block">
                              sha256:{art.hash_sha256?.slice(0, 10)}...
                            </span>
                          </div>
                        </div>

                        <span className="bg-mint-wash text-canopy-green px-2 py-0.5 rounded-full font-body text-[10px] font-bold uppercase shrink-0">
                          {art.status}
                        </span>
                      </div>

                      <div className="mt-3 pt-2 border-t border-frost-gray flex items-center justify-between text-xs font-body">
                        <span className="text-[11px] text-slate">
                          {(art.byte_size / 1024).toFixed(1)} KB
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleDownload(art.id)}
                            className="text-canopy-green hover:underline text-[11px] font-medium"
                          >
                            Download
                          </button>
                          <span className="text-ash">•</span>
                          <button
                            onClick={() => handleReExtract(art.id)}
                            className="text-coral-pulse hover:underline text-[11px] font-medium"
                          >
                            Re-Extract
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column (7 cols): Extracted Text Preview with Provenance Locators */}
          <div className="lg:col-span-7 bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
              <div>
                <h2 className="font-headline text-base font-bold text-canopy-green">
                  Source Provenance & Text Extraction
                </h2>
                <span className="font-body text-xs text-slate">
                  Clickable page/paragraph locators guarantee traceability (INV-03).
                </span>
              </div>

              {extraction && (
                <span className="bg-sky-wash text-deep-teal font-body text-xs px-2.5 py-0.5 rounded-full font-semibold">
                  Parser v{extraction.parser_version}
                </span>
              )}
            </div>

            {loading ? (
              <div className="py-24 text-center font-body text-sm text-slate animate-pulse">
                Parsing document structure...
              </div>
            ) : !extraction ? (
              <div className="py-24 text-center font-body text-slate">
                <span className="material-symbols-outlined text-[48px] text-ash mb-2 block">
                  find_in_page
                </span>
                <p className="text-sm">No extracted text available yet.</p>
                <p className="text-xs text-slate mt-1">Upload a PDF or paste text to generate verifiable locators.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Locators Navigation Bar */}
                {extraction.locators && extraction.locators.length > 0 && (
                  <div className="p-3 bg-surface-container-low rounded-xl border border-frost-gray">
                    <span className="font-body text-[11px] font-semibold text-graphite uppercase tracking-wider block mb-2">
                      Traceable Fact Locators ({extraction.locators.length})
                    </span>
                    <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                      {extraction.locators.map((loc: TextLocator, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSelectedLocatorIndex(idx);
                            const el = paragraphRefs.current[loc.paragraph_index];
                            if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                          }}
                          className={`shrink-0 px-3 py-1 rounded-full text-xs font-body transition ${
                            selectedLocatorIndex === idx
                              ? "bg-coral-pulse text-paper-white font-semibold shadow-2xs"
                              : "bg-paper-white text-graphite hover:bg-lavender-mist border border-frost-gray"
                          }`}
                        >
                          P.{loc.page_number} §{loc.paragraph_index}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Parsed Text Viewer */}
                <div className="bg-surface-container-lowest p-6 rounded-2xl border border-frost-gray max-h-[550px] overflow-y-auto space-y-3 font-body text-xs text-ink-black leading-relaxed">
                  {extraction.extracted_text ? (
                    extraction.extracted_text
                      .split(/\n\s*\n/)
                      .filter(Boolean)
                      .map((p: string, pIdx: number) => {
                        const isHighlighted =
                          selectedLocatorIndex !== null &&
                          extraction.locators[selectedLocatorIndex]?.paragraph_index === pIdx;

                        return (
                          <p
                            key={pIdx}
                            ref={(el) => {
                              paragraphRefs.current[pIdx] = el;
                            }}
                            className={`p-2.5 rounded-lg transition-colors ${
                              isHighlighted
                                ? "bg-peach-wash border-l-4 border-coral-pulse font-medium text-canopy-green"
                                : "hover:bg-lavender-mist/40"
                            }`}
                          >
                            <span className="font-mono text-[10px] text-slate mr-2 select-none">
                              [§{pIdx}]
                            </span>
                            {p}
                          </p>
                        );
                      })
                  ) : (
                    <pre className="whitespace-pre-wrap font-mono text-xs">{extraction.extracted_text}</pre>
                  )}
                </div>

                <div className="pt-2 flex items-center justify-between text-[11px] text-slate font-body">
                  <span>Character count: {extraction.extracted_text?.length || 0}</span>
                  <span className="flex items-center gap-1 text-canopy-green font-semibold">
                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                    Verified Source Bytes Immutable
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </CoordinatorShell>
  );
}
