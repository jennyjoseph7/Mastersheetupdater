"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  dealerLogin,
  type DealerLoginResponse,
  getDealershipDetails,
} from "@/lib/api";
import { setCookie } from "@/lib/cookies";
import { isDealershipSetupComplete as checkDealershipSetupComplete } from "@/lib/dealership-utils";

/* -------------------------------------------------------------------------- */
/*                                   TYPES                                    */
/* -------------------------------------------------------------------------- */

interface User {
  id: string;
  email: string;
  name: string;
  credits: number;
  avatar?: string;
  isVerified: boolean;
  verificationStatus?: "pending" | "verified" | "rejected";
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isDealershipSetupComplete: boolean | null;
  checkDealershipSetup: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateCredits: (credits: number) => void;
  updateVerificationStatus: (
    isVerified: boolean,
    verificationStatus?: "pending" | "verified" | "rejected"
  ) => void;
}

/* -------------------------------------------------------------------------- */
/*                             GLOBAL LOGOUT SAFE                              */
/* -------------------------------------------------------------------------- */

let isLoggingOut = false;

const clearSessionData = () => {
  if (typeof window === "undefined") return;

  console.log("[Auth] Clearing session data");

  // LocalStorage (ONLY auth keys)
  localStorage.removeItem("auth_token");
  localStorage.removeItem("user_data");
  localStorage.removeItem("auth_data");
  localStorage.removeItem("dealership_setup_complete");
  localStorage.removeItem("dealership_id");

  // SessionStorage
  sessionStorage.clear();

  // Cookies
  const deleteCookie = (name: string) => {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
  };

  deleteCookie("gryd_session_id");
  deleteCookie("gryd_token");
  deleteCookie("gryd_user_id");
  deleteCookie("gryd_application_id");
};

export const triggerGlobalLogout = () => {
  if (typeof window === "undefined") return;
  if (isLoggingOut) return;

  isLoggingOut = true;
  console.warn("🚨 [Auth] Global Logout Triggered");

  clearSessionData();

  // Prevent infinite refresh on login page
  if (window.location.pathname !== "/login") {
    window.location.replace("/login");
  }
};

/* -------------------------------------------------------------------------- */
/*                                CONTEXT SETUP                                */
/* -------------------------------------------------------------------------- */

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDealershipSetupComplete, setIsDealershipSetupComplete] =
    useState<boolean | null>(null);

  const router = useRouter();

  /* -------------------------------------------------------------------------- */
  /*                            SESSION INITIAL CHECK                            */
  /* -------------------------------------------------------------------------- */

  useEffect(() => {
    if (typeof window === "undefined") return;

    // 🚫 Skip auth check on login page
    if (window.location.pathname === "/login") {
      setIsLoading(false);
      return;
    }

    const initSession = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const userData = localStorage.getItem("user_data");

        if (!token || !userData) {
          setIsLoading(false);
          return;
        }

        const parsedUser = JSON.parse(userData);
        setUser(parsedUser);

        // Load dealership ID if missing
        if (!localStorage.getItem("dealership_id")) {
          try {
            const d = await getDealershipDetails();
            const id = d?.dealership_id || d?.dealership_slug;
            if (id) localStorage.setItem("dealership_id", id);
          } catch {}
        }

        // Setup status
        const stored = localStorage.getItem("dealership_setup_complete");
        if (stored !== null) {
          setIsDealershipSetupComplete(stored === "true");
        } else {
          await checkDealershipSetup();
        }
      } catch (err) {
        console.error("[Auth] Session corrupted", err);
        triggerGlobalLogout();
      } finally {
        setIsLoading(false);
      }
    };

    initSession();
  }, []);

  
/* -------------------------------------------------------------------------- */
/*                        AUTO SESSION REFRESH (5 MIN)                        */
/* -------------------------------------------------------------------------- */

useEffect(() => {
  if (typeof window === "undefined") return;

  // Skip login page
  if (window.location.pathname === "/login") return;

  const token = localStorage.getItem("auth_token");
  if (!token) return; // not logged in

  const autoRefresh = async () => {
    try {
      const d = await getDealershipDetails();

      const credits_balance = d?.credits_balance || 0;
      const dealershipId = d?.dealership_id || d?.dealership_slug;

      if (dealershipId) {
        localStorage.setItem("dealership_id", dealershipId);
      }

      // Update user ONLY if credits changed (prevents re-renders)
      setUser((prev) => {
        if (!prev) return prev;
        if (prev.credits === credits_balance) return prev;

        const updated = {
          ...prev,
          credits: credits_balance,
        };

        localStorage.setItem("user_data", JSON.stringify(updated));
        return updated;
      });

      console.log("🔄 [Auth] Session auto refreshed");
    } catch (error: any) {
      console.error("Auto refresh failed", error);

      // Auto logout if token expired
      if (error?.response?.status === 401) {
        triggerGlobalLogout();
      }
    }
  };

  const interval = setInterval(autoRefresh, 5 * 60 * 1000); // 5 min

  return () => clearInterval(interval);
}, []); // ✅ IMPORTANT: empty dependency

  /* -------------------------------------------------------------------------- */
  /*                                   ACTIONS                                   */
  /* -------------------------------------------------------------------------- */

const login = async (email: string, password: string) => {
  const response: DealerLoginResponse = await dealerLogin({ email, password });

  // Store auth first
  localStorage.setItem("auth_token", response.token);
  localStorage.setItem("auth_data", JSON.stringify(response));

  setCookie("gryd_session_id", response.session_id, 7);
  setCookie("gryd_token", response.token, 7);
  setCookie("gryd_user_id", response.user_id, 7);
  setCookie("gryd_application_id", "autocrm", 7);

  let credits_balance = 0;
  let dealershipId = null;
  let setupComplete = false;

  try {
    const d = await getDealershipDetails();
    dealershipId = d?.dealership_id || d?.dealership_slug;
    credits_balance = d?.credits_balance || 0;

    if (dealershipId) {
      localStorage.setItem("dealership_id", dealershipId);
    }

    setupComplete = await checkDealershipSetupComplete();
    localStorage.setItem("dealership_setup_complete", String(setupComplete));
    setIsDealershipSetupComplete(setupComplete);

    console.log("[Auth] Login successful:", d);
  } catch (error) {
    console.error("Dealership fetch failed:", error);
  }

  // Now create user AFTER getting credits
  const user: User = {
    id: response.user_id || response.session_id,
    email: response.user_id,
    name: email.split("@")[0],
    credits: credits_balance,
    isVerified: false,
    verificationStatus: "pending",
  };

  localStorage.setItem("user_data", JSON.stringify(user));
  setUser(user);

  router.replace("/");
};


  const logout = () => {
    triggerGlobalLogout();
  };

  const checkDealershipSetup = async () => {
    try {
      const setup = await checkDealershipSetupComplete();
      setIsDealershipSetupComplete(setup);
      localStorage.setItem("dealership_setup_complete", String(setup));
    } catch {
      setIsDealershipSetupComplete(false);
    }
  };

  const updateCredits = (credits: number) => {
    if (!user) return;
    const updated = { ...user, credits };
    setUser(updated);
    localStorage.setItem("user_data", JSON.stringify(updated));
  };

  const updateVerificationStatus = (
    isVerified: boolean,
    verificationStatus?: "pending" | "verified" | "rejected"
  ) => {
    if (!user) return;
    const updated = { ...user, isVerified, verificationStatus };
    setUser(updated);
    localStorage.setItem("user_data", JSON.stringify(updated));
  };

  /* -------------------------------------------------------------------------- */

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isDealershipSetupComplete,
        checkDealershipSetup,
        login,
        logout,
        updateCredits,
        updateVerificationStatus,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* -------------------------------------------------------------------------- */
/*                                   HOOK                                     */
/* -------------------------------------------------------------------------- */

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
