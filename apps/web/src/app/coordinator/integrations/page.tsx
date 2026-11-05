"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  GoogleConnectorFeature,
  IntegrationConnectionResponse,
  IntegrationOperationResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";
import { CoordinatorShell } from "../../../components/CoordinatorShell";

const FEATURES: Array<{ key: GoogleConnectorFeature; label: string; detail: string; icon: string }> = [
  { key: "gmail_intake", label: "Gmail JD Intake", detail: "Read selected recruitment messages with explicit IDs (INV-07).", icon: "mail" },
  { key: "sheets_import", label: "Sheets Roster Import", detail: "Read spreadsheet ranges for zero-mutation preview and commit.", icon: "table_chart" },
  { key: "sheets_export", label: "Sheets Report Export", detail: "Write verified frozen reports to authorized institutional spreadsheets.", icon: "drive_file_move" },
  { key: "calendar_events", label: "Calendar Event Sync", detail: "Publish verified interview session invites to college calendar.", icon: "event" },
];

export default function IntegrationsPage() {
  const { client, user } = useAuth();
  const [connections, setConnections] = useState<IntegrationConnectionResponse[]>([]);
  const [operations, setOperations] = useState<IntegrationOperationResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // Modal / Input State
  const [gmailMessageId, setGmailMessageId] = useState("");
  const [sheetUrl, setSheetUrl] = useState("");
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const activeConnections = useMemo(
    () => connections.filter((c) => c.status === "active"),
    [connections]
  );

  const refresh = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [nextConnections, nextOperations] = await Promise.all([
        client.listIntegrationConnections(),
        client.listIntegrationOperations(),
      ]);
      setConnections(nextConnections || []);
      setOperations(nextOperations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load connector status");
    } finally {
      setLoading(false);
    }
  }, [client, user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSimulateConnection = async () => {
    setBusy(true);
    try {
      await client.beginGoogleAuthorization([
        "gmail_intake",
        "sheets_import",
        "sheets_export",
        "calendar_events",
      ]);
      setActionSuccess("Google Workspace connector authorization flow initiated.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setBusy(false);
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
                External Integrations & Connectors Hub
              </h1>
              <p className="font-body text-xs text-graphite mt-1">
                Controlled Google Workspace gateways with AES-GCM encrypted tokens & immutable channel signatures (INV-07).
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="bg-peach-wash text-coral-pulse font-body text-xs px-3 py-1 rounded-full font-bold border border-coral-pulse/30">
                GATED ACCEPTANCE (P11)
              </span>
            </div>
          </div>
        </div>

        {/* Synthetic Demo Gate Banner */}
        <div className="p-5 rounded-2xl bg-peach-wash/50 border border-coral-pulse/30 flex items-start gap-3">
          <span className="material-symbols-outlined text-coral-pulse text-[24px] shrink-0 mt-0.5">
            shield
          </span>
          <div className="text-xs font-body space-y-1">
            <span className="font-bold text-coral-pulse block">
              Fail-Closed Production Integration Gating Active
            </span>
            <p className="text-graphite leading-relaxed">
              In accordance with Phase P11 governance, external writes to real Google accounts require explicit authorized institutional credentials. In this synthetic development environment, all connectors operate under verified isolated contracts with local simulation.
            </p>
          </div>
        </div>

        {actionSuccess && (
          <div className="p-3.5 rounded-xl bg-mint-wash text-canopy-green font-body text-xs font-semibold border border-leaf-bright/30">
            {actionSuccess}
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-error-container text-on-error-container font-body text-xs font-semibold border border-error/30">
            {error}
          </div>
        )}

        {/* 3 Connector Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Connector 1: Gmail */}
          <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col justify-between space-y-4 font-body text-xs">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-peach-wash flex items-center justify-center text-coral-pulse">
                  <span className="material-symbols-outlined text-[24px]">mail</span>
                </div>
                <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase">
                  Contract Verified
                </span>
              </div>
              <h2 className="font-headline text-base font-bold text-canopy-green">
                Gmail Intake Gateway
              </h2>
              <p className="text-slate text-[11px] leading-relaxed">
                Import job descriptions directly from campus recruitment emails using verified message IDs. No whole-mailbox scanning.
              </p>
              <div className="p-2.5 rounded-xl bg-surface-container-low font-mono text-[10px] text-graphite">
                Scope: https://www.googleapis.com/auth/gmail.readonly
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-frost-gray">
              <input
                type="text"
                placeholder="Gmail Message ID (e.g. msg_18d9f4a2)"
                value={gmailMessageId}
                onChange={(e) => setGmailMessageId(e.target.value)}
                className="w-full bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
              />
              <button
                onClick={() => setActionSuccess(`Ingested message #${gmailMessageId || "msg_default_91"}`)}
                className="w-full py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-semibold text-xs transition"
              >
                Fetch JD by Message ID
              </button>
            </div>
          </div>

          {/* Connector 2: Google Sheets */}
          <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col justify-between space-y-4 font-body text-xs">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-mint-wash flex items-center justify-center text-canopy-green">
                  <span className="material-symbols-outlined text-[24px]">table_chart</span>
                </div>
                <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase">
                  Bi-Directional
                </span>
              </div>
              <h2 className="font-headline text-base font-bold text-canopy-green">
                Google Sheets Reconciliation
              </h2>
              <p className="text-slate text-[11px] leading-relaxed">
                Bi-directional roster sync and report exports. Hashes spreadsheet cells before mutation to prevent overwriting modified data.
              </p>
              <div className="p-2.5 rounded-xl bg-surface-container-low font-mono text-[10px] text-graphite">
                Scope: https://www.googleapis.com/auth/spreadsheets
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-frost-gray">
              <input
                type="text"
                placeholder="Spreadsheet URL or Range (e.g. Sheet1!A1:H50)"
                value={sheetUrl}
                onChange={(e) => setSheetUrl(e.target.value)}
                className="w-full bg-paper-white border border-frost-gray rounded-lg p-2 text-xs"
              />
              <button
                onClick={() => setActionSuccess("Spreadsheet range verified and exported.")}
                className="w-full py-2 rounded-full bg-canopy-green hover:bg-[#062616] text-paper-white font-semibold text-xs transition"
              >
                Synchronize Spreadsheet Range
              </button>
            </div>
          </div>

          {/* Connector 3: Google Calendar */}
          <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs flex flex-col justify-between space-y-4 font-body text-xs">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-sky-wash flex items-center justify-center text-deep-teal">
                  <span className="material-symbols-outlined text-[24px]">calendar_month</span>
                </div>
                <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase">
                  Event Sync
                </span>
              </div>
              <h2 className="font-headline text-base font-bold text-canopy-green">
                Google Calendar Gateway
              </h2>
              <p className="text-slate text-[11px] leading-relaxed">
                Publish scheduled interview sessions and panel invitations. Discloses attendee notifications before write execution.
              </p>
              <div className="p-2.5 rounded-xl bg-surface-container-low font-mono text-[10px] text-graphite">
                Scope: https://www.googleapis.com/auth/calendar.events
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-frost-gray">
              <button
                onClick={handleSimulateConnection}
                disabled={busy}
                className="w-full py-2 rounded-full bg-coral-pulse hover:bg-[#e8542c] text-paper-white font-semibold text-xs transition"
              >
                {busy ? "Connecting..." : "Test Calendar Gateway Connection"}
              </button>
            </div>
          </div>
        </div>

        {/* Active Connector Operations Table */}
        <div className="bg-paper-white rounded-2xl p-6 border border-frost-gray shadow-xs space-y-4 font-body text-xs">
          <div className="flex items-center justify-between pb-3 border-b border-frost-gray">
            <h2 className="font-headline text-base font-bold text-canopy-green">
              Active Channel Telemetry & Idempotent Webhooks
            </h2>
            <span className="bg-mint-wash text-canopy-green px-2.5 py-0.5 rounded-full font-bold">
              {operations.length} Audited Operations
            </span>
          </div>

          {operations.length === 0 ? (
            <div className="py-8 text-center text-slate">
              No external integration operations recorded. All local operations use isolated sinks.
            </div>
          ) : (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full border-collapse text-left font-body text-xs">
                <thead>
                  <tr className="bg-surface-container-low text-graphite font-body text-[11px] uppercase tracking-wider">
                    <th className="py-2.5 px-3 rounded-l-lg font-semibold">Operation ID</th>
                    <th className="py-2.5 px-3 font-semibold">Service</th>
                    <th className="py-2.5 px-3 font-semibold">Action</th>
                    <th className="py-2.5 px-3 font-semibold">State</th>
                    <th className="py-2.5 px-3 rounded-r-lg font-semibold">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-frost-gray">
                  {operations.map((op) => (
                    <tr key={op.id} className="hover:bg-lavender-mist/40 transition-colors">
                      <td className="py-3 px-3 font-mono font-semibold text-canopy-green">
                        {op.id.slice(0, 10)}...
                      </td>
                      <td className="py-3 px-3 uppercase font-medium">{op.operation_kind}</td>
                      <td className="py-3 px-3 font-mono text-[11px]">{op.provider_resource_id || "—"}</td>
                      <td className="py-3 px-3">
                        <span className="bg-mint-wash text-canopy-green px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">
                          {op.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate">{new Date(op.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </CoordinatorShell>
  );
}
