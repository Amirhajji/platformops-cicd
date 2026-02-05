// src/auth/auth.store.ts
import { createContext, useContext, useMemo, useState, createElement } from "react";
import type { UserInfo } from "./auth.api";




type AuthState = {
  token: string | null;
  user: UserInfo | null;
  setSession: (token: string, user: UserInfo) => void;
  clearSession: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("access_token")
  );

  const [user, setUser] = useState<UserInfo | null>(() => {
    const raw = localStorage.getItem("user");
    return raw ? (JSON.parse(raw) as UserInfo) : null;
  });

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      setSession: (t, u) => {
        setToken(t);
        setUser(u);
        localStorage.setItem("access_token", t);
        localStorage.setItem("user", JSON.stringify(u));
      },
      clearSession: () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
      },
    }),
    [token, user]
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
