"use client";

import type {
  ExceptionCaseResponse,
  ExceptionImpactCategory,
  ExceptionImpactCreate,
  ExceptionImpactResponse,
  RecoveryExecutionResponse,
  RecoveryPlanResponse,
} from "@placementos/api-client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../../../../context/AuthContext";

const categories: Array<{ value: ExceptionImpactCategory; label: string }> = [
  { value: "criteria_change", label: "Eligibility criteria change" },
  { value: "academic_correction", label: "Verified academic correction" },
  { value: "deadline_schedule_change", label: "Deadline or schedule revision" },
  { value: "notification_failure", label: "Notification failure or uncertainty" },
];

const statusTone: Record<string, string> = {
  succeeded: "bg-emerald-100 text-emerald-800",
  completed: "bg-emerald-100 text-emerald-800",
  approved: "bg-emerald-100 text-emerald-800",
  partial: "bg-amber-100 text-amber-900",
  pending_approval: "bg-amber-100 text-amber-900",
  queued: "bg-blue-100 text-blue-800",
  executing: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  stale: "bg-red-100 text-red-800",
  rejected: "bg-slate-200 text-slate-800",
};

type ReferenceFields = Record<string, string>;

export default function ExceptionRecoveryPage() {
  const { id } = useParams<{ id: string }>();
  const { client } = useAuth();
  const [exceptionCase, setExceptionCase] = useState<ExceptionCaseResponse | null>(null);
  const [impacts, setImpacts] = useState<ExceptionImpactResponse[]>([]);
  const [plans, setPlans] = useState<RecoveryPlanResponse[]>([]);
  const [executions, setExecutions] = useState<RecoveryExecutionResponse[]>([]);
  const [category, setCategory] = useState<ExceptionImpactCategory>("criteria_change");
  const [references, setReferences] = useState<ReferenceFields>({ change_kind: "deadline" });
  const [rationale, setRationale] = useState("Review deterministic impact and prepare bounded recovery steps");
  const [manualNote, setManualNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [cases, nextImpacts, nextPlans, nextExecutions] = await Promise.all([
        client.listExceptionCases(),
        client.listExceptionImpacts(id),
        client.listRecoveryPlans(id),
        client.listRecoveryExecutions(id),
      ]);
      const currentCase = cases.find((item) => item.id === id) ?? null;
      setExceptionCase(currentCase);
      setImpacts(nextImpacts);
      setPlans(nextPlans);
      setExecutions(nextExecutions);
      if (!currentCase) setError("Exception case is unavailable in this institutional scope.");
      else setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load exception recovery evidence");
    } finally {
      setLoading(false);
    }
  }, [client, id]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const field = (name: string) => references[name] ?? "";
  const changeField = (name: string, value: string) =>
    setReferences((current) => ({ ...current, [name]: value }));

  const analyze = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("impact");
    setError(null);
    try {
      let request: ExceptionImpactCreate;
      if (category === "criteria_change") {
        request = {
          category,
          old_evaluation_run_id: field("old_evaluation_run_id"),
          new_evaluation_run_id: field("new_evaluation_run_id"),
        };
      } else if (category === "academic_correction") {
        request = {
          category,
          student_profile_id: field("student_profile_id"),
          old_academic_revision_id: field("old_academic_revision_id"),
          new_academic_revision_id: field("new_academic_revision_id"),
          old_evaluation_run_id: field("old_evaluation_run_id"),
          new_evaluation_run_id: field("new_evaluation_run_id"),
        };
      } else if (category === "deadline_schedule_change") {
        request = {
          category,
          change_kind: field("change_kind") === "schedule" ? "schedule" : "deadline",
          old_revision_id: field("old_revision_id"),
          new_revision_id: field("new_revision_id"),
        };
      } else {
        request = { category, dispatch_operation_id: field("dispatch_operation_id") };
      }
      await client.analyzeExceptionImpact(id, request);
      setNotice("A revisioned deterministic impact analysis was recorded. No recovery action has run.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze the exception impact");
    } finally {
      setBusy(null);
    }
  };

  const createPlan = async (mode: "fixture" | "manual") => {
    const analysis = impacts.find((item) => item.status === "current") ?? impacts[0];
    if (!analysis) return;
    setBusy(`plan-${mode}`);
    setError(null);
    try {
      if (mode === "fixture") {
        await client.createRecoveryPlan(analysis.id, { planner_mode: "fixture", rationale });
      } else {
        await client.createRecoveryPlan(analysis.id, {
          planner_mode: "manual",
          rationale,
          manual_steps: [
            {
              operation_type: "record_manual_followup",
              exact_payload: { note: manualNote },
              expected_effects: ["Record the coordinator's manual recovery requirement"],
              approval_type: "manual_evidence",
              irreversible_effects: [],
            },
          ],
        });
      }
      setNotice("Recovery steps were frozen into a review proposal. Nothing executes before approval.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the recovery proposal");
    } finally {
      setBusy(null);
    }
  };

  const decide = async (
    plan: RecoveryPlanResponse,
    decision: "approved" | "rejected" | "revision_requested"
  ) => {
    setBusy(`${plan.id}-${decision}`);
    setError(null);
    try {
      const execution = await client.decideRecoveryPlan(plan, decision, "Coordinator reviewed exact P12 recovery steps");
      setNotice(
        execution
          ? "Approval recorded. The frozen plan is queued for bounded, freshness-checked execution."
          : `Recovery plan ${decision.replaceAll("_", " ")}.`
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record the recovery decision");
    } finally {
      setBusy(null);
    }
  };

  const cancelExecution = async (executionId: string) => {
    setBusy(`cancel-${executionId}`);
    setError(null);
    try {
      await client.cancelRecoveryExecution(
        executionId,
        "Coordinator cancelled remaining recovery steps after review"
      );
      setNotice("Remaining recovery steps were cancelled. Completed steps and their evidence were preserved.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel the recovery execution");
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <p role="status">Loading exception impact and recovery evidence...</p>;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/coordinator/exceptions" className="text-sm text-brand-700 underline">Exception inbox</Link>
          <h1 className="mt-2 text-2xl font-semibold">Adaptive exception recovery</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Deterministic impact first, exact proposed steps second, human approval third. The planner cannot send messages or write calendars.
          </p>
        </div>
        {exceptionCase && <Status value={`${exceptionCase.severity} · ${exceptionCase.status}`} />}
      </header>

      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{notice}</div>}

      {exceptionCase && (
        <section className="rounded-xl border bg-white p-5 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase text-slate-500">{exceptionCase.category.replaceAll("_", " ")}</p>
          <h2 className="mt-1 text-lg font-semibold">{exceptionCase.proposed_next_action}</h2>
          <p className="mt-2 text-sm text-slate-600">Case {exceptionCase.id} · Drive {exceptionCase.drive_id}</p>
        </section>
      )}

      <section className="rounded-xl border bg-white p-5 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">1. Analyze a supported exception</h2>
        <p className="mt-1 text-sm text-slate-600">Reference immutable before-and-after records. Unknown or mismatched evidence fails closed.</p>
        <form onSubmit={analyze} className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="text-sm">Exception type
            <select value={category} onChange={(event) => setCategory(event.target.value as ExceptionImpactCategory)} className="mt-1 w-full rounded-lg border bg-transparent p-2">
              {categories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          {category === "deadline_schedule_change" && (
            <label className="text-sm">Revision kind
              <select value={field("change_kind") || "deadline"} onChange={(event) => changeField("change_kind", event.target.value)} className="mt-1 w-full rounded-lg border bg-transparent p-2">
                <option value="deadline">Drive deadline</option><option value="schedule">Published schedule</option>
              </select>
            </label>
          )}
          {referenceFields(category).map((item) => (
            <label key={item.name} className="text-sm">{item.label}
              <input required value={field(item.name)} onChange={(event) => changeField(item.name, event.target.value)} placeholder="UUID" className="mt-1 w-full rounded-lg border bg-transparent px-3 py-2 font-mono text-xs" />
            </label>
          ))}
          <div className="md:col-span-2"><button disabled={busy !== null} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white">{busy === "impact" ? "Analyzing..." : "Record impact analysis"}</button></div>
        </form>
      </section>

      <section className="rounded-xl border bg-white p-5 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">2. Prepare a recovery proposal</h2>
        {impacts.length === 0 ? <p className="mt-3 text-sm text-slate-500">Record an impact analysis before proposing recovery.</p> : (
          <>
            <ImpactCard impact={impacts[0]} />
            <label className="mt-4 block text-sm">Proposal rationale
              <textarea required minLength={3} value={rationale} onChange={(event) => setRationale(event.target.value)} className="mt-1 min-h-20 w-full rounded-lg border bg-transparent p-3" />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button disabled={busy !== null} onClick={() => void createPlan("fixture")} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white">Prepare deterministic fixture plan</button>
            </div>
            <div className="mt-4 border-t pt-4">
              <label className="text-sm">Manual fallback note
                <input value={manualNote} onChange={(event) => setManualNote(event.target.value)} placeholder="Evidence to collect or authorized manual follow-up" className="mt-1 w-full rounded-lg border bg-transparent px-3 py-2" />
              </label>
              <button disabled={busy !== null || manualNote.trim().length < 3} onClick={() => void createPlan("manual")} className="mt-2 rounded-lg border px-4 py-2 text-sm font-semibold">Prepare manual follow-up plan</button>
            </div>
          </>
        )}
      </section>

      <section className="space-y-4" aria-labelledby="plans-heading">
        <h2 id="plans-heading" className="text-lg font-semibold">3. Review exact steps and decide</h2>
        {plans.length === 0 && <p className="rounded-xl border border-dashed p-6 text-sm text-slate-500">No recovery proposals yet.</p>}
        {plans.map((plan) => <PlanCard key={plan.id} plan={plan} busy={busy} onDecide={decide} />)}
      </section>

      <section className="rounded-xl border bg-white p-5 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">Execution evidence</h2>
        <p className="mt-1 text-sm text-slate-600">Partial means completed steps remain recorded and later steps stopped. Retry never replays a completed operation.</p>
        <div className="mt-4 space-y-3">
          {executions.length === 0 && <p className="text-sm text-slate-500">No approved plan has been queued.</p>}
          {executions.map((item) => (
            <article key={item.id} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-mono text-xs">{item.id}</p><Status value={item.status} /></div>
              <p className="mt-2 text-sm">{item.completed_step_count} completed · {item.pending_step_count} pending · {item.failed_step_count} failed</p>
              {item.last_error_code && <p className="mt-1 text-sm text-red-700">Stopped: {item.last_error_code.replaceAll("_", " ")}</p>}
              {["queued", "executing"].includes(item.status) && (
                <button disabled={busy !== null} onClick={() => void cancelExecution(item.id)} className="mt-3 rounded-lg border border-red-300 px-3 py-2 text-sm text-red-700">Cancel remaining steps</button>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function referenceFields(category: ExceptionImpactCategory) {
  if (category === "criteria_change") return [
    { name: "old_evaluation_run_id", label: "Previous evaluation run" },
    { name: "new_evaluation_run_id", label: "Revised evaluation run" },
  ];
  if (category === "academic_correction") return [
    { name: "student_profile_id", label: "Student profile" },
    { name: "old_academic_revision_id", label: "Previous academic revision" },
    { name: "new_academic_revision_id", label: "Verified corrected revision" },
    { name: "old_evaluation_run_id", label: "Previous evaluation run" },
    { name: "new_evaluation_run_id", label: "Revised evaluation run" },
  ];
  if (category === "deadline_schedule_change") return [
    { name: "old_revision_id", label: "Previous revision" },
    { name: "new_revision_id", label: "Revised record" },
  ];
  return [{ name: "dispatch_operation_id", label: "Dispatch operation" }];
}

function Status({ value }: { value: string }) {
  const key = value.split(" · ").at(-1) ?? value;
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${statusTone[key] ?? "bg-slate-100 text-slate-800"}`}>{value.replaceAll("_", " ")}</span>;
}

function ImpactCard({ impact }: { impact: ExceptionImpactResponse }) {
  return (
    <article className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
      <div className="flex flex-wrap justify-between gap-2"><strong>Impact revision {impact.revision_number}</strong><Status value={impact.status} /></div>
      <p className="mt-2">{impact.affected_students.length} affected students · {impact.affected_resources.length} affected resources</p>
      <pre className="mt-3 overflow-auto whitespace-pre-wrap rounded bg-white/70 p-3 text-xs">{JSON.stringify(impact.impact_summary, null, 2)}</pre>
      <p className="mt-3"><strong>Manual fallback:</strong> {impact.manual_fallback}</p>
    </article>
  );
}

function PlanCard({
  plan,
  busy,
  onDecide,
}: {
  plan: RecoveryPlanResponse;
  busy: string | null;
  onDecide: (plan: RecoveryPlanResponse, decision: "approved" | "rejected" | "revision_requested") => Promise<void>;
}) {
  return (
    <article className="rounded-xl border bg-white p-5 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs uppercase text-slate-500">{plan.planner_mode} · {plan.planner_id} {plan.planner_version}</p><h3 className="mt-1 font-semibold">Plan revision {plan.revision_number}</h3></div><Status value={plan.status} /></div>
      <p className="mt-3 text-sm">{plan.rationale}</p>
      <ol className="mt-4 space-y-3">
        {plan.steps.map((step) => (
          <li key={step.id} className="rounded-lg border p-4 text-sm">
            <div className="flex flex-wrap justify-between gap-2"><strong>{step.step_number}. {step.operation_type.replaceAll("_", " ")}</strong><Status value={step.status} /></div>
            <p className="mt-2 text-xs text-slate-500">Approval: {step.approval_type.replaceAll("_", " ")} · Depends on: {step.dependencies.length ? step.dependencies.join(", ") : "none"}</p>
            <p className="mt-2"><strong>Expected:</strong> {step.expected_effects.join("; ")}</p>
            <pre className="mt-2 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs dark:bg-slate-800">{JSON.stringify(step.exact_payload, null, 2)}</pre>
            {step.irreversible_effects.length > 0 && <p className="mt-2 rounded bg-red-50 p-2 text-red-900"><strong>Irreversible:</strong> {step.irreversible_effects.join("; ")}</p>}
            {step.error_detail && <p className="mt-2 text-red-700">{step.error_code}: {step.error_detail}</p>}
          </li>
        ))}
      </ol>
      {plan.status === "pending_approval" && (
        <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
          <button disabled={busy !== null} onClick={() => void onDecide(plan, "approved")} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white">Approve exact plan</button>
          <button disabled={busy !== null} onClick={() => void onDecide(plan, "revision_requested")} className="rounded-lg border px-4 py-2 text-sm">Request revision</button>
          <button disabled={busy !== null} onClick={() => void onDecide(plan, "rejected")} className="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-700">Reject</button>
        </div>
      )}
    </article>
  );
}
