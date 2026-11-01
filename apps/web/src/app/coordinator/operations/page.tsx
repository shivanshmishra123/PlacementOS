"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  OperationalHealthResponse,
  PilotReadinessResponse,
} from "@placementos/api-client";
import { useAuth } from "../../../context/AuthContext";

const LABELS: Record<string, string> = {
  oidc_identity: "OIDC identity and membership ownership",
  permissions_review: "Permission matrix review",
  academic_configuration: "Academic scales, branches and timezone",
  real_malware_scanner: "Real malware scanner",
  model_policy: "Model provider and data-use policy",
  production_sender: "Verified production sender",
  private_object_storage: "Private production object storage",
  retention_and_deletion: "Retention and deletion ownership",
  backup_restore: "Encrypted backup restore drill",
  hosting_region: "Approved hosting region",
  operational_ownership: "Named operational owners",
};

export default function OperationsPage() {
  const { client, user, loading: authLoading } = useAuth();
  const [readiness, setReadiness] = useState<PilotReadinessResponse | null>(null);
  const [health, setHealth] = useState<OperationalHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [nextReadiness, nextHealth] = await Promise.all([
        client.getPilotReadiness(),
        client.getOperationalHealth(),
      ]);
      setReadiness(nextReadiness);
      setHealth(nextHealth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load operational status");
    } finally {
      setLoading(false);
    }
  }, [client, user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (authLoading || loading) {
    return <p role="status">Loading operational readiness…</p>;
  }
  if (!user) {
    return <p role="alert">Select an authorized coordinator or administrator persona.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Operations and pilot readiness</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Aggregate operational signals only. Student records, document text, message bodies and secrets are never shown here.
          </p>
        </div>
        <button onClick={() => void refresh()} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Refresh status
        </button>
      </div>

      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">{error}</div>}

      {readiness && (
        <section aria-labelledby="readiness-heading" className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="readiness-heading" className="text-lg font-semibold">Release {readiness.release_version}</h2>
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${readiness.real_data_pilot_ready ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>
              {readiness.real_data_pilot_ready ? "Real-data pilot ready" : "Synthetic demo only"}
            </span>
          </div>
          {!readiness.real_data_pilot_ready && (
            <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
              Do not load real student data or enable live sending until every implementation and institution configuration gate below is complete.
            </p>
          )}
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {readiness.checks.map((check) => (
              <li key={check.key} className="flex items-center gap-2 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
                <span aria-hidden="true">{check.ready ? "✓" : "○"}</span>
                <span>{LABELS[check.key] ?? check.key}</span>
                <span className="sr-only">
                  {check.ready
                    ? "configured"
                    : check.classification === "implementation_required"
                      ? "implementation required"
                      : "institution configuration required"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {health && (
        <section aria-labelledby="health-heading" className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <h2 id="health-heading" className="text-lg font-semibold">Work queues and recovery signals</h2>
          <p className="mt-1 text-xs text-slate-500">Snapshot {new Date(health.generated_at).toLocaleString()}</p>
          {health.alerts.length ? (
            <ul className="mt-4 space-y-2" aria-label="Active operational alerts">
              {health.alerts.map((alert) => (
                <li key={alert.code} className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">
                  {alert.severity.toUpperCase()}: {alert.code.replaceAll("_", " ")}
                  {alert.count !== undefined ? ` (${alert.count})` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-900">No threshold alerts in this institutional scope.</p>
          )}
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label="Pending approvals" value={health.approvals.pending} />
            <Summary label="Pending workflow commands" value={health.workflows.pending_commands} />
            <Summary label="Open exception cases" value={health.exception_cases.open_or_acknowledged} />
            <Summary label="Oldest outbox age (seconds)" value={health.outbox.oldest_age_seconds ?? 0} />
          </dl>
        </section>
      )}
    </div>
  );
}

function Summary({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
      <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="mt-1 text-xl font-semibold">{value}</dd>
    </div>
  );
}
