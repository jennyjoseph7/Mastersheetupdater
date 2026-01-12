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

// --- Types ---
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

// --- 1. SIMPLIFIED LOGOUT HELPER (Run outside React) ---

const clearSessionData = () => {
  if (typeof window === "undefined") return;

  console.log("[Auth] Clearing session data...");

  // 1. Clear LocalStorage
  localStorage.removeItem("auth_token");
  localStorage.removeItem("user_data");
  localStorage.removeItem("auth_data");
  localStorage.removeItem("dealership_setup_complete");
  localStorage.removeItem("dealership_id");
  localStorage.clear();

  // 2. Clear SessionStorage
  sessionStorage.clear();

  // 3. Delete Cookies
  const deleteCookie = (name: string) => {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
  };
  deleteCookie("gryd_session_id");
  deleteCookie("gryd_token");
  deleteCookie("gryd_user_id");
  deleteCookie("gryd_application_id");
};

/**
 * 🚀 GLOBAL LOGOUT TRIGGER
 * Call this from anywhere (api.ts, components, etc.)
 * It effectively hard-reloads the app to the login screen.
 */
export const triggerGlobalLogout = () => {
  console.log("🚨 [Auth] Global Logout Triggered - Redirecting...");
  
  clearSessionData();

  // Force a hard redirect. This is simpler than state updates 
  // and guarantees the app resets completely.
  if (typeof window !== "undefined") {
    window.location.replace("/login");
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDealershipSetupComplete, setIsDealershipSetupComplete] = useState<
    boolean | null
  >(null);
  const router = useRouter();

  // --- Core Actions ---

  // The internal logout just calls the global one
  const logout = () => {
    triggerGlobalLogout();
  };

  const checkDealershipSetup = async (): Promise<void> => {
    try {
      const justCompleted = sessionStorage.getItem("just_completed_setup") === "true";
      if (justCompleted) {
        if (localStorage.getItem("dealership_setup_complete") === "true") {
          setIsDealershipSetupComplete(true);
          return;
        }
      }

      const setupComplete = await checkDealershipSetupComplete();
      setIsDealershipSetupComplete(setupComplete);
      localStorage.setItem("dealership_setup_complete", String(setupComplete));
    } catch (error) {
      console.error("[Auth] Failed setup check:", error);
      // Fallback
      if (localStorage.getItem("dealership_setup_complete") === "true") {
        setIsDealershipSetupComplete(true);
        return;
      }
      setIsDealershipSetupComplete(false);
    }
  };

  useEffect(() => {
    const checkSession = async () => {
      const token = localStorage.getItem("auth_token");
      const userData = localStorage.getItem("user_data");

      if (token && userData) {
        try {
          setUser(JSON.parse(userData));

          // Load dealership ID if missing
          if (!localStorage.getItem("dealership_id")) {
            getDealershipDetails()
              .then((d) => {
                const id = d?.dealership_id || d?.dealership_slug;
                if (id) localStorage.setItem("dealership_id", id);
              })
              .catch((e) => console.error(e));
          }

          // Check setup status
          const storedSetup = localStorage.getItem("dealership_setup_complete");
          if (storedSetup !== null) {
            setIsDealershipSetupComplete(storedSetup === "true");
          } else {
            await checkDealershipSetup();
          }
        } catch (error) {
          console.error("[Auth] Data corrupt, logging out...");
          triggerGlobalLogout();
        }
      }
      setIsLoading(false);
    };

    checkSession();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response: DealerLoginResponse = await dealerLogin({ email, password });

      const nameFromEmail = email.split("@")[0].replace(/[.+]/g, " ");
      const user = {
        id: response.user_id || response.session_id,
        email: response.user_id,
        name: nameFromEmail || "Dealer",
        credits: 5000,
        isVerified: false,
        verificationStatus: "pending" as const,
      };

      // Store Data
      localStorage.setItem("auth_token", response.token);
      localStorage.setItem("user_data", JSON.stringify(user));
      localStorage.setItem("auth_data", JSON.stringify(response));

      // Store Cookies
      const appId = response.application_id === "autocrm" ? "autocrm" : "autocrm";
      setCookie("gryd_session_id", response.session_id, 7);
      setCookie("gryd_token", response.token, 7);
      setCookie("gryd_user_id", response.user_id, 7);
      setCookie("gryd_application_id", appId, 7);

      setUser(user);

      // Post-login checks
      try {
        const d = await getDealershipDetails();
        const dId = d?.dealership_id || d?.dealership_slug;
        if (dId) localStorage.setItem("dealership_id", dId);
        
        const setup = await checkDealershipSetupComplete();
        setIsDealershipSetupComplete(setup);
        localStorage.setItem("dealership_setup_complete", String(setup));
      } catch (e) {
        console.error(e);
      }
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    }
  };

  const updateCredits = (credits: number) => {
    if (user) {
      const u = { ...user, credits };
      setUser(u);
      localStorage.setItem("user_data", JSON.stringify(u));
    }
  };

  const updateVerificationStatus = (
    isVerified: boolean,
    verificationStatus?: "pending" | "verified" | "rejected"
  ) => {
    if (user) {
      const u = { ...user, isVerified, verificationStatus };
      setUser(u);
      localStorage.setItem("user_data", JSON.stringify(u));
    }
  };

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

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}