"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import {
  Shield,
  School,
  Lock,
  Mail,
  Building2,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

interface PresetAccount {
  name: string;
  email: string;
  role: "placement_coordinator" | "student" | "institution_admin";
  roleLabel: string;
  institutionName: string;
  institutionSlug: string;
  description: string;
  avatarBg: string;
}

const PRESET_ACCOUNTS: PresetAccount[] = [
  {
    name: "Priya Sharma",
    email: "priya.sharma@apex.edu",
    role: "placement_coordinator",
    roleLabel: "Placement Coordinator",
    institutionName: "Apex Institute of Technology",
    institutionSlug: "apex-tech",
    description: "Full recruitment controls: create drives, approve AI extractions, dispatch notices, resolve exceptions",
    avatarBg: "bg-canopy-green text-paper-white",
  },
  {
    name: "Aarav Sharma",
    email: "student.a@apex.edu",
    role: "student",
    roleLabel: "Student Candidate",
    institutionName: "Apex Institute of Technology",
    institutionSlug: "apex-tech",
    description: "Student portal access: view verified drives, check eligibility, register, and track results",
    avatarBg: "bg-deep-teal text-paper-white",
  },
  {
    name: "Ananya Das",
    email: "ananya.das@beacon.edu",
    role: "placement_coordinator",
    roleLabel: "Placement Coordinator",
    institutionName: "Beacon Engineering College",
    institutionSlug: "beacon-state",
    description: "Placement coordinator controls isolated to Beacon tenant",
    avatarBg: "bg-canopy-green text-paper-white",
  },
  {
    name: "Aditi Rao",
    email: "student.a@beacon.edu",
    role: "student",
    roleLabel: "Student Candidate",
    institutionName: "Beacon Engineering College",
    institutionSlug: "beacon-state",
    description: "Beacon student candidate portal with isolated profile",
    avatarBg: "bg-deep-teal text-paper-white",
  },
  {
    name: "Rajesh Verma",
    email: "rajesh.verma@apex.edu",
    role: "institution_admin",
    roleLabel: "Institution Admin",
    institutionName: "Apex Institute of Technology",
    institutionSlug: "apex-tech",
    description: "Institutional governance, tenant onboarding & audit logs",
    avatarBg: "bg-slate-700 text-paper-white",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { user, login, isAuthenticated, isStudent, isCoordinator } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("••••••••");
  const [institutionSlug, setInstitutionSlug] = useState("apex-tech");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"preset" | "custom">("preset");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already logged in, redirect to the appropriate portal
  useEffect(() => {
    if (isAuthenticated && user) {
      if (user.role === "student") {
        router.push("/student/portal");
      } else {
        router.push("/coordinator/drives");
      }
    }
  }, [isAuthenticated, user, router]);

  const handleLoginSubmit = async (targetEmail: string, targetSlug?: string) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const loggedUser = await login(targetEmail, password, targetSlug || institutionSlug);
      // Redirect based on authoritative role
      if (loggedUser.role === "student") {
        router.push("/student/portal");
      } else {
        router.push("/coordinator/drives");
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Authentication failed. Check institutional credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-lavender-mist flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-canopy-green text-paper-white font-bold text-2xl shadow-md mb-4">
          P
        </div>
        <h1 className="font-headline text-3xl font-extrabold text-canopy-green tracking-tight">
          Placement<span className="text-coral-pulse">OS</span>
        </h1>
        <p className="font-body text-sm text-graphite mt-1.5 max-w-sm mx-auto">
          Campus Recruitment Operations & Student Placement Self-Service Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl px-4">
        <div className="bg-paper-white rounded-3xl p-6 sm:p-8 border border-frost-gray shadow-md">
          {/* Mode Tabs */}
          <div className="flex items-center gap-2 p-1.5 bg-lavender-mist rounded-2xl mb-6">
            <button
              onClick={() => {
                setActiveTab("preset");
                setErrorMessage(null);
              }}
              className={`flex-1 py-2.5 px-4 rounded-xl font-body text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 ${
                activeTab === "preset"
                  ? "bg-paper-white text-canopy-green shadow-xs"
                  : "text-graphite hover:text-ink-black"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-coral-pulse" />
              <span>Role-Based Single Click Login</span>
            </button>
            <button
              onClick={() => {
                setActiveTab("custom");
                setErrorMessage(null);
              }}
              className={`flex-1 py-2.5 px-4 rounded-xl font-body text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 ${
                activeTab === "custom"
                  ? "bg-paper-white text-canopy-green shadow-xs"
                  : "text-graphite hover:text-ink-black"
              }`}
            >
              <Lock className="w-3.5 h-3.5 text-deep-teal" />
              <span>Institutional Credentials</span>
            </button>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="mb-6 p-4 rounded-2xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5 animate-in fade-in">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Authentication Error</p>
                <p className="mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Tab 1: Single-Click Role Presets */}
          {activeTab === "preset" && (
            <div className="space-y-3">
              <div className="text-xs font-semibold text-graphite mb-2 uppercase tracking-wider flex items-center gap-1.5">
                <span>Select Your Institutional Role:</span>
              </div>

              {PRESET_ACCOUNTS.map((acc) => {
                const isStudentAcc = acc.role === "student";
                return (
                  <button
                    key={acc.email}
                    onClick={() => handleLoginSubmit(acc.email, acc.institutionSlug)}
                    disabled={loading}
                    className="w-full text-left p-4 rounded-2xl border border-frost-gray hover:border-canopy-green/50 bg-paper-white hover:bg-surface-container/50 transition shadow-2xs group cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`h-10 w-10 rounded-xl ${acc.avatarBg} flex items-center justify-center font-bold text-sm shrink-0 shadow-xs`}
                      >
                        {acc.name.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-headline text-sm font-bold text-ink-black group-hover:text-canopy-green transition">
                            {acc.name}
                          </span>
                          <span
                            className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                              isStudentAcc
                                ? "bg-mint-wash text-canopy-green border border-leaf-bright/30"
                                : "bg-sky-wash text-deep-teal border border-sky-signal/30"
                            }`}
                          >
                            {acc.roleLabel}
                          </span>
                        </div>
                        <div className="text-xs text-graphite font-body mt-0.5">{acc.email}</div>
                        <div className="text-[11px] text-slate-500 mt-1">{acc.description}</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 text-xs font-semibold text-canopy-green group-hover:translate-x-1 transition shrink-0 self-end sm:self-center">
                      <span>Sign in as {acc.role === "student" ? "Student" : "Coordinator"}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Tab 2: Custom Institutional Credentials */}
          {activeTab === "custom" && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleLoginSubmit(email, institutionSlug);
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-semibold text-ink-black mb-1.5">
                  Institutional Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-graphite">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="e.g. priya.sharma@apex.edu or student.a@apex.edu"
                    required
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-frost-gray text-xs text-ink-black focus:outline-none focus:border-canopy-green focus:ring-1 focus:ring-canopy-green transition"
                  />
                </div>
                <p className="text-[11px] text-graphite mt-1">
                  Emails containing <code className="bg-slate-100 px-1 py-0.5 rounded">student</code> automatically route to the Student Portal.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-black mb-1.5">
                  Institutional Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-graphite">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-frost-gray text-xs text-ink-black focus:outline-none focus:border-canopy-green focus:ring-1 focus:ring-canopy-green transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-black mb-1.5">
                  Institution
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-graphite">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <select
                    value={institutionSlug}
                    onChange={(e) => setInstitutionSlug(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-frost-gray text-xs text-ink-black focus:outline-none focus:border-canopy-green focus:ring-1 focus:ring-canopy-green transition bg-paper-white"
                  >
                    <option value="apex-tech">Apex Institute of Technology (apex-tech)</option>
                    <option value="beacon-state">Beacon Engineering College (beacon-state)</option>
                  </select>
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading || !email}
                  className="w-full py-3 px-4 rounded-xl bg-canopy-green hover:bg-[#153427] text-paper-white font-body text-xs font-bold transition shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <span className="inline-block animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <>
                      <span>Sign In with Institutional Account</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* RBAC Notice Footer */}
          <div className="mt-8 pt-6 border-t border-frost-gray text-center text-xs text-graphite space-y-1">
            <div className="flex items-center justify-center gap-1.5 font-medium text-canopy-green">
              <Shield className="w-3.5 h-3.5" />
              <span>Strict Role-Based Access Control (RBAC) Active</span>
            </div>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              Placement coordinators and students operate on separate view permissions and authorization boundaries.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
