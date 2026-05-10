"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  getCurrentUser,
  logoutAccount,
  type CurrentUser,
} from "@/lib/auth-api";

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  refreshUser: () => Promise<CurrentUser | null>;
  logout: () => Promise<void>;
};

export const publicPaths = ["/login", "/register"];

const AuthContext = createContext<AuthContextValue | null>(null);

function isPublicRoute(pathname: string | null) {
  return publicPaths.some(
    (path) => pathname === path || pathname?.startsWith(`${path}/`),
  );
}

function nextPath(pathname: string | null) {
  const path = pathname || "/";
  const query = typeof window === "undefined" ? "" : window.location.search;
  return `${path}${query}`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublicPath = isPublicRoute(pathname);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    setIsLoading(true);
    try {
      const envelope = await getCurrentUser();
      setUser(envelope.user);
      return envelope.user;
    } catch {
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await logoutAccount();
    setUser(null);
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    let isActive = true;

    async function loadUser() {
      setIsLoading(true);
      try {
        const envelope = await getCurrentUser();
        if (isActive) {
          setUser(envelope.user);
        }
      } catch {
        if (isActive) {
          setUser(null);
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadUser();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (!isLoading && !user && !isPublicPath) {
      router.replace(`/login?next=${encodeURIComponent(nextPath(pathname))}`);
    }
  }, [isLoading, isPublicPath, pathname, router, user]);

  const value = useMemo(
    () => ({ user, isLoading, refreshUser, logout }),
    [user, isLoading, refreshUser, logout],
  );

  if (isLoading && !isPublicPath) {
    return (
      <AuthContext.Provider value={value}>
        <div className="grid min-h-screen place-items-center bg-paper text-sm font-semibold text-ink-light">
          Loading account...
        </div>
      </AuthContext.Provider>
    );
  }

  if (!user && !isPublicPath) {
    return <AuthContext.Provider value={value}>{null}</AuthContext.Provider>;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
