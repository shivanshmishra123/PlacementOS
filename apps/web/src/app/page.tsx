"use client";

import { useCallback, useEffect, useState } from "react";
import { PlacementOSClient, type HealthResponse } from "@placementos/api-client";
import { CheckCircle2, ShieldCheck, Activity, Users, FileText, ArrowRight } from "lucide-react";

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    const client = new PlacementOSClient("http://localhost:8000");
    setLoading(true);
    setError(null);
    try {
      const res = await client.getHealth();
      setHealth(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect to PlacementOS API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return (
    <div className="space-y-10">
      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
          <ShieldCheck className="w-3.5 h-3.5" />
          Deterministic Rules &bull; Human-Supervised AI Execution
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Campus Recruitment Operations Platform
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-300">
          Automating the end-to-end recruitment lifecycle from raw JD intake and deterministic eligibility to verified registrations, interview schedules, and drive closure.
        </p>
      </div>

      {/* Backend API Connection Status Widget */}
      <div className="max-w-xl mx-auto glass-panel rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-brand-600 dark:text-brand-400" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Backend Service Liveness
            </h2>
          </div>
          <button
            onClick={checkHealth}
            disabled={loading}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition font-medium disabled:opacity-50"
          >
            {loading ? "Checking..." : "Re-check"}
          </button>
        </div>

        {health && (
          <div className="space-y-2 text-sm bg-emerald-50/60 dark:bg-emerald-950/30 p-4 rounded-xl border border-emerald-200 dark:border-emerald-900">
            <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Connected: FastAPI v{health.version} ({health.environment})
            </div>
            {health.correlation_id && (
              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                Correlation ID: {health.correlation_id}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="text-sm bg-amber-50 dark:bg-amber-950/30 p-4 rounded-xl border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 space-y-1">
            <div className="font-semibold">Backend Unreachable:</div>
            <div className="text-xs font-mono">{error}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 pt-1">
              Run <code className="bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded">pnpm dev</code> and <code className="bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded">uv run uvicorn placementos.main:app</code>
            </div>
          </div>
        )}
      </div>

      {/* Role Navigation Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-3 hover:shadow-md transition">
          <div className="h-10 w-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <Users className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-lg text-slate-900 dark:text-white">
            Placement Coordinator
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Manage drives, review AI-extracted criteria, evaluate student cohorts, approve outbound proposals, and schedule interviews.
          </p>
          <div className="pt-2 text-xs font-medium text-brand-600 dark:text-brand-400 flex items-center gap-1">
            Available in Phase P02/P03 <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-3 hover:shadow-md transition">
          <div className="h-10 w-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <FileText className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-lg text-slate-900 dark:text-white">
            Student Portal
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            View eligible drives with transparent reason codes, upload verification documents, submit registrations, and track selection rounds.
          </p>
          <div className="pt-2 text-xs font-medium text-brand-600 dark:text-brand-400 flex items-center gap-1">
            Available in Phase P02/P06 <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-3 hover:shadow-md transition">
          <div className="h-10 w-10 rounded-xl bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center text-purple-600 dark:text-purple-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-lg text-slate-900 dark:text-white">
            Institutional Admin
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Manage coordinator capabilities, configure branch aliases, grading scales, email transports, and inspect audit logs.
          </p>
          <div className="pt-2 text-xs font-medium text-brand-600 dark:text-brand-400 flex items-center gap-1">
            Available in Phase P02 <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>
    </div>
  );
}
