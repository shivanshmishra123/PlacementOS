"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import type {
  GoogleConnectorFeature,
  IntegrationConnectionResponse,
  IntegrationOperationResponse,
  IntegrationProposalResponse,
  SheetImportPreviewResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

const FEATURES: Array<{ key: GoogleConnectorFeature; label: string; detail: string }> = [
  { key: "gmail_intake", label: "Gmail JD intake", detail: "Read only the message or attachment ID you select." },
  { key: "sheets_import", label: "Sheets roster import", detail: "Read a selected spreadsheet range for preview and commit." },
  { key: "sheets_export", label: "Sheets report export", detail: "Write an approved frozen report snapshot to an exact range." },
  { key: "calendar_events", label: "Calendar events", detail: "Create or update an approved event on an owned calendar." },
];

export default function IntegrationsPage() {
  const { client, user, loading: authLoading } = useAuth();
  const [connections, setConnections] = useState<IntegrationConnectionResponse[]>([]);
  const [operations, setOperations] = useState<IntegrationOperationResponse[]>([]);
  const [features, setFeatures] = useState<GoogleConnectorFeature[]>([]);
  const [preview, setPreview] = useState<SheetImportPreviewResponse | null>(null);
  const [proposal, setProposal] = useState<IntegrationProposalResponse | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [justConnected, setJustConnected] = useState(false);

  const activeConnections = useMemo(
    () => connections.filter((connection) => connection.status === "active"),
    [connections]
  );
  const defaultConnectionId = activeConnections[0]?.id ?? "";

  const refresh = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [nextConnections, nextOperations] = await Promise.all([
        client.listIntegrationConnections(),
        client.listIntegrationOperations(),
      ]);
      setConnections(nextConnections);
      setOperations(nextOperations);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load connector status");
    } finally {
      setLoading(false);
    }
  }, [client, user]);

  useEffect(() => {
    setJustConnected(new URLSearchParams(window.location.search).get("google") === "connected");
    void refresh();
  }, [refresh]);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connector action failed");
    } finally {
      setBusy(false);
    }
  };

  const submitGmail = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run(async () => {
      const result = await client.captureGmailSource(String(data.get("drive_id")), {
        connection_id: String(data.get("connection_id")),
        message_id: String(data.get("message_id")),
        attachment_id: String(data.get("attachment_id") || "") || undefined,
      });
      setNotice(`Captured immutable source ${result.source_artifact_id}; extraction is queued.`);
    });
  };

  const submitSheetPreview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run(async () => {
      const result = await client.previewSheetImport({
        connection_id: String(data.get("connection_id")),
        spreadsheet_id: String(data.get("spreadsheet_id")),
        selected_range: String(data.get("selected_range")),
      });
      setPreview(result);
      setNotice("Preview created. The source and academic revisions will be checked again at commit.");
    });
  };

  const submitSheetExport = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run(async () => {
      const result = await client.proposeSheetExport(String(data.get("drive_id")), {
        connection_id: String(data.get("connection_id")),
        report_id: String(data.get("report_id")),
        spreadsheet_id: String(data.get("spreadsheet_id")),
        target_range: String(data.get("target_range")),
      });
      setProposal(result);
      setNotice("Exact Sheets write proposal created. Review the frozen payload before approval.");
    });
  };

  const submitCalendar = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run(async () => {
      const result = await client.proposeCalendarEvent(String(data.get("revision_id")), {
        connection_id: String(data.get("connection_id")),
        calendar_id: String(data.get("calendar_id")),
        send_updates: String(data.get("send_updates")) as "none" | "externalOnly" | "all",
      });
      setProposal(result);
      setNotice("Exact Calendar proposal created. Invite behavior is frozen in the payload below.");
    });
  };

  if (authLoading || loading) return <p role="status">Loading Google Workspace connectors...</p>;
  if (!user) return <p role="alert">Select an authorized coordinator persona.</p>;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Google Workspace connectors</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-300">
            Connections are optional. Tokens stay encrypted on the backend; PlacementOS does not scan an inbox or write to Sheets or Calendar without a specific action.
          </p>
        </div>
        <button onClick={() => void refresh()} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium" disabled={busy}>
          Refresh
        </button>
      </header>

      {justConnected && (
        <p className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">Google connection completed.</p>
      )}
      {notice && <p className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">{notice}</p>}
      {error && <p className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900" role="alert">{error}</p>}

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">Connect only the features you need</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {FEATURES.map((feature) => (
            <label key={feature.key} className="flex gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <input
                type="checkbox"
                checked={features.includes(feature.key)}
                onChange={(event) => setFeatures((current) => event.target.checked ? [...current, feature.key] : current.filter((item) => item !== feature.key))}
              />
              <span><span className="block text-sm font-medium">{feature.label}</span><span className="block text-xs text-slate-500">{feature.detail}</span></span>
            </label>
          ))}
        </div>
        <button
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={busy || features.length === 0}
          onClick={() => void run(async () => {
            const result = await client.beginGoogleAuthorization(features);
            window.location.assign(result.authorization_url);
          })}
        >
          Continue to Google consent
        </button>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">Connections</h2>
        {connections.length === 0 ? <p className="mt-3 text-sm text-slate-500">No Google account is connected.</p> : (
          <ul className="mt-3 space-y-2">
            {connections.map((connection) => (
              <li key={connection.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <div><p className="text-sm font-medium">{connection.external_account_email}</p><p className="text-xs text-slate-500">{connection.status} - revision {connection.connection_revision} - {connection.granted_scopes.length} scopes</p></div>
                {connection.status === "active" && <button className="rounded-lg border border-red-300 px-3 py-1.5 text-xs text-red-700" disabled={busy} onClick={() => void run(async () => { await client.disconnectIntegrationConnection(connection.id); await refresh(); setNotice("Connection disabled; queued work was invalidated."); })}>Disconnect</button>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {activeConnections.length > 0 && (
        <div className="grid gap-6 xl:grid-cols-2">
          <ConnectorForm title="Capture an explicit Gmail source" onSubmit={submitGmail} busy={busy} connectionId={defaultConnectionId} fields={[
            ["drive_id", "Drive ID", "UUID of the authorized drive"], ["message_id", "Gmail message ID", "Exact selected message"], ["attachment_id", "Attachment ID (optional)", "Leave blank to capture the text body"],
          ]} />
          <ConnectorForm title="Preview a Sheets roster import" onSubmit={submitSheetPreview} busy={busy} connectionId={defaultConnectionId} fields={[
            ["spreadsheet_id", "Spreadsheet ID", "Provider spreadsheet identifier"], ["selected_range", "Selected range", "Roster!A:G"],
          ]} />
          <ConnectorForm title="Propose a frozen report export" onSubmit={submitSheetExport} busy={busy} connectionId={defaultConnectionId} fields={[
            ["drive_id", "Drive ID", "Authorized drive UUID"], ["report_id", "Frozen report ID", "Immutable report revision UUID"], ["spreadsheet_id", "Spreadsheet ID", "Exact export destination"], ["target_range", "Target range", "Closure!A1"],
          ]} />
          <form onSubmit={submitCalendar} className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-lg font-semibold">Propose a Calendar event</h2>
            <input type="hidden" name="connection_id" value={defaultConnectionId} />
            <Field name="revision_id" label="Published session revision ID" placeholder="UUID" />
            <Field name="calendar_id" label="Owned calendar ID" placeholder="primary" />
            <label className="mt-3 block text-sm font-medium">Invite notifications<select name="send_updates" className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2"><option value="none">None</option><option value="externalOnly">External attendees only</option><option value="all">All attendees</option></select></label>
            <button disabled={busy} className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Create approval proposal</button>
          </form>
          <form onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); void run(async () => { const channel = await client.registerCalendarWatch(defaultConnectionId, String(data.get("calendar_id"))); setNotice(`Calendar reconciliation channel registered${channel.expires_at ? ` until ${new Date(channel.expires_at).toLocaleString()}` : ""}.`); }); }} className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-lg font-semibold">Register Calendar reconciliation</h2>
            <p className="mt-1 text-xs text-slate-500">Creates a provider webhook channel at the configured HTTPS callback. External edits are discrepancy signals; they never overwrite internal facts.</p>
            <Field name="calendar_id" label="Owned calendar ID" placeholder="primary" />
            <button disabled={busy} className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Register watch</button>
          </form>
        </div>
      )}

      {preview && (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950">
          <h2 className="font-semibold">Sheets preview ready</h2>
          <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-white/70 p-3 text-xs">{JSON.stringify(preview.report, null, 2)}</pre>
          <button disabled={busy} className="mt-3 rounded-lg bg-amber-800 px-4 py-2 text-sm font-medium text-white" onClick={() => void run(async () => { const result = await client.commitSheetImport(preview.id); setNotice(`Sheets import ${result.status}.`); setPreview(null); })}>Commit this unchanged preview</button>
        </section>
      )}

      {proposal && (
        <section className="rounded-xl border border-indigo-300 bg-indigo-50 p-5 text-indigo-950">
          <h2 className="font-semibold">Approval proposal: {proposal.action_type}</h2>
          <pre className="mt-3 max-h-72 overflow-auto rounded-lg bg-white/70 p-3 text-xs">{JSON.stringify(proposal.payload, null, 2)}</pre>
          <div className="mt-3 flex gap-2"><button disabled={busy} className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white" onClick={() => void run(async () => { await client.decideIntegrationProposal(proposal, "approved"); setProposal(null); await refresh(); setNotice("Approved exact operation queued for controlled execution."); })}>Approve exact action</button><button disabled={busy} className="rounded-lg border border-indigo-400 px-4 py-2 text-sm" onClick={() => void run(async () => { await client.decideIntegrationProposal(proposal, "rejected"); setProposal(null); setNotice("Proposal rejected; no provider write was queued."); })}>Reject</button></div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">Controlled operations</h2>
        {operations.length === 0 ? <p className="mt-3 text-sm text-slate-500">No provider writes have been queued.</p> : <ul className="mt-3 space-y-2">{operations.map((operation) => <li key={operation.id} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700"><span className="font-medium">{operation.operation_kind}</span> - {operation.status} - attempts {operation.attempt_count}{operation.last_error_code ? ` - ${operation.last_error_code}` : ""}</li>)}</ul>}
      </section>
    </div>
  );
}

function ConnectorForm({ title, onSubmit, busy, connectionId, fields }: { title: string; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean; connectionId: string; fields: Array<[string, string, string]> }) {
  return <form onSubmit={onSubmit} className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"><h2 className="text-lg font-semibold">{title}</h2><input type="hidden" name="connection_id" value={connectionId} />{fields.map(([name, label, placeholder]) => <Field key={name} name={name} label={label} placeholder={placeholder} />)}<button disabled={busy} className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Continue</button></form>;
}

function Field({ name, label, placeholder }: { name: string; label: string; placeholder: string }) {
  return <label className="mt-3 block text-sm font-medium">{label}<input required={name !== "attachment_id"} name={name} placeholder={placeholder} className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2" /></label>;
}
