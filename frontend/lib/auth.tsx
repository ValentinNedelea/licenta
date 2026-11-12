"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, clearTokens, getAccess, saveTokens } from "./api";

export type User = {
  id: number;
  username: string;
  email: string;
  avatar_url?: string;
  bio?: string;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
  ) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!getAccess()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api<User>("/api/auth/me/"));
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = async (username: string, password: string) => {
    const t = await api<{ access: string; refresh: string }>(
      "/api/auth/login/",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      },
    );
    saveTokens(t.access, t.refresh);
    await loadMe();
  };

  const register = async (
    username: string,
    email: string,
    password: string,
  ) => {
    await api("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
    await login(username, password);
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth trebuie folosit în AuthProvider");
  return c;
}
