"use client";

import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { UserCheck, LogOut, ChevronDown, Building2, Shield, User } from "lucide-react";

export function PersonaSwitcher() {
  const { user, personas, loginAsPersona, logout, loading } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative inline-block text-left">
      {user ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs">
            <div className="h-6 w-6 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold">
              {user.full_name.charAt(0)}
            </div>
            <div className="text-left">
              <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                {user.full_name}
                <span className="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase bg-brand-100 dark:bg-brand-950 text-brand-700 dark:text-brand-300">
                  {user.institution_slug}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 capitalize">
                {user.role}
              </div>
            </div>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="ml-1 p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition text-slate-500"
              title="Switch Persona"
              aria-label="Switch Persona"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={() => logout()}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium shadow-sm transition"
        >
          <UserCheck className="w-3.5 h-3.5" />
          Select Dev Persona
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
      )}

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl glass-panel shadow-2xl border border-slate-200 dark:border-slate-700 p-2 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-800 mb-1">
            <div className="text-xs font-semibold text-slate-900 dark:text-white">
              Switch Development Persona
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              Instantly switch identities to test tenant isolation and permissions.
            </div>
          </div>

          <div className="space-y-1 max-h-72 overflow-y-auto">
            {personas.map((p) => {
              const isCurrent = user?.email.toLowerCase() === p.email.toLowerCase();
              return (
                <button
                  key={p.key}
                  onClick={async () => {
                    await loginAsPersona(p.key);
                    setIsOpen(false);
                  }}
                  disabled={loading}
                  className={`w-full text-left p-2.5 rounded-xl text-xs transition flex items-start gap-2.5 ${
                    isCurrent
                      ? "bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800"
                      : "hover:bg-slate-100 dark:hover:bg-slate-800/60 border border-transparent"
                  }`}
                >
                  <div
                    className={`mt-0.5 p-1.5 rounded-lg ${
                      p.role === "coordinator"
                        ? "bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300"
                        : p.role === "student"
                        ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {p.role === "coordinator" ? (
                      <Building2 className="w-3.5 h-3.5" />
                    ) : p.role === "student" ? (
                      <User className="w-3.5 h-3.5" />
                    ) : (
                      <Shield className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white flex items-center justify-between">
                      <span className="truncate">{p.name}</span>
                      <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 uppercase">
                        {p.institution_slug}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                      {p.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
