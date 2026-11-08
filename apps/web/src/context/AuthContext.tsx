"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import {
  PlacementOSClient,
  UserProfileResponse,
  PersonaInfo,
} from "@placementos/api-client";

interface AuthContextType {
  client: PlacementOSClient;
  user: UserProfileResponse | null;
  personas: PersonaInfo[];
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isStudent: boolean;
  isCoordinator: boolean;
  isAdmin: boolean;
  login: (email: string, password?: string, institutionSlug?: string) => Promise<UserProfileResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const defaultClient = new PlacementOSClient(
  typeof window !== "undefined"
    ? window.location.origin.includes("localhost")
      ? "http://localhost:8000"
      : window.location.origin
    : "http://localhost:8000"
);

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [client] = useState<PlacementOSClient>(defaultClient);
  const [user, setUser] = useState<UserProfileResponse | null>(null);
  const [personas, setPersonas] = useState<PersonaInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    try {
      const me = await client.getMe();
      setUser(me);
      setError(null);
    } catch {
      // User is unauthenticated; normal initial state
      setUser(null);
    }
  }, [client]);

  const loadPersonas = useCallback(async () => {
    try {
      const list = await client.listPersonas();
      setPersonas(list);
    } catch (err: unknown) {
      console.warn("Could not fetch personas:", err);
    }
  }, [client]);

  const login = useCallback(
    async (email: string, password?: string, institutionSlug?: string): Promise<UserProfileResponse> => {
      setLoading(true);
      setError(null);
      try {
        const resp = await client.login({
          email,
          password: password || undefined,
          institution_slug: institutionSlug || undefined,
        });
        setUser(resp.user);
        return resp.user;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to sign in";
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [client]
  );

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await client.logout();
      setUser(null);
    } catch (err: unknown) {
      console.warn("Logout error:", err);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      setLoading(true);
      await Promise.all([refreshUser(), loadPersonas()]);
      if (mounted) setLoading(false);
    };
    init();
    return () => {
      mounted = false;
    };
  }, [refreshUser, loadPersonas]);

  const isAuthenticated = !!user;
  const isStudent = user?.role === "student";
  const isCoordinator =
    user?.role === "placement_coordinator" ||
    user?.role === "coordinator" ||
    user?.role === "institution_admin" ||
    user?.role === "super_admin";
  const isAdmin = user?.role === "institution_admin" || user?.role === "super_admin";

  return (
    <AuthContext.Provider
      value={{
        client,
        user,
        personas,
        loading,
        error,
        isAuthenticated,
        isStudent,
        isCoordinator,
        isAdmin,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
