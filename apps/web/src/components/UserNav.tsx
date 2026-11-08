"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { LogOut, ChevronDown, Building2, Shield, User, School, CheckCircle2 } from "lucide-react";

export function UserNav() {
  const { user, logout, loading, isCoordinator, isStudent } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    setIsOpen(false);
    await logout();
    router.push("/login");
  };

  if (!user) {
    return (
      <Link
        href="/login"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-canopy-green hover:bg-[#153427] text-paper-white text-xs font-semibold shadow-xs transition"
      >
        <User className="w-3.5 h-3.5" />
        Sign In
      </Link>
    );
  }

  const roleLabel =
    user.role === "placement_coordinator" || user.role === "coordinator"
      ? "Placement Coordinator"
      : user.role === "institution_admin"
      ? "Institution Admin"
      : user.role === "student"
      ? "Student Candidate"
      : user.role.toUpperCase();

  const roleBadgeColor = isStudent
    ? "bg-mint-wash text-canopy-green border-leaf-bright/30"
    : "bg-sky-wash text-deep-teal border-sky-signal/30";

  const avatarBg = isStudent ? "bg-canopy-green" : "bg-deep-teal";

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 p-1.5 pr-3 rounded-2xl bg-paper-white hover:bg-surface-container border border-frost-gray shadow-xs transition cursor-pointer"
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="User Account Menu"
      >
        <div
          className={`h-8 w-8 rounded-xl ${avatarBg} text-paper-white flex items-center justify-center font-bold text-xs shadow-xs`}
        >
          {user.full_name?.charAt(0) || "U"}
        </div>
        <div className="text-left hidden sm:block">
          <div className="font-headline text-xs font-bold text-ink-black flex items-center gap-1.5 leading-tight">
            {user.full_name}
          </div>
          <div className="text-[10px] text-graphite flex items-center gap-1">
            <span className="font-medium text-canopy-green">{roleLabel}</span>
            <span>•</span>
            <span className="font-mono uppercase text-slate-400">{user.institution_slug}</span>
          </div>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-graphite transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-paper-white border border-frost-gray shadow-xl p-2 z-50 animate-in fade-in zoom-in-95 duration-100">
          {/* User Profile Header in Menu */}
          <div className="px-3 py-3 border-b border-frost-gray mb-1 bg-surface-container/40 rounded-xl">
            <div className="font-headline text-sm font-bold text-ink-black">{user.full_name}</div>
            <div className="text-xs text-graphite font-body mt-0.5 truncate">{user.email}</div>
            <div className="mt-2.5 flex items-center gap-1.5">
              <span
                className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${roleBadgeColor}`}
              >
                {roleLabel}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono uppercase">
                {user.institution_slug}
              </span>
            </div>
          </div>

          {/* Scope and Capabilities Info */}
          <div className="px-3 py-2 text-[11px] text-graphite space-y-1">
            <div className="flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-canopy-green" />
              <span className="truncate">
                {user.institution_slug === "beacon-state"
                  ? "Beacon Engineering College"
                  : "Apex Institute of Technology"}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-leaf-bright" />
              <span>RBAC Scoped • {user.capabilities.length} capabilities</span>
            </div>
          </div>

          <div className="border-t border-frost-gray my-1.5" />

          {/* Role-Specific Portal Quick Link */}
          {isCoordinator && (
            <Link
              href="/coordinator/drives"
              onClick={() => setIsOpen(false)}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-ink-black hover:bg-mint-wash hover:text-canopy-green transition"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Coordinator Drives Console</span>
            </Link>
          )}

          {isStudent && (
            <Link
              href="/student/portal"
              onClick={() => setIsOpen(false)}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-ink-black hover:bg-mint-wash hover:text-canopy-green transition"
            >
              <School className="w-3.5 h-3.5" />
              <span>My Student Portal</span>
            </Link>
          )}

          <div className="border-t border-frost-gray my-1.5" />

          {/* Sign Out Button */}
          <button
            onClick={handleSignOut}
            disabled={loading}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-coral-pulse hover:bg-red-50 dark:hover:bg-red-950/20 transition cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
}

