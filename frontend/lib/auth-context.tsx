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
import { setCookie, getCookie, deleteCookie } from "@/lib/cookies";
import { isDealershipSetupComplete as checkDealershipSetupComplete } from "@/lib/dealership-utils";

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
  isDealershipSetupComplete: boolean | null; // null = not checked yet
  checkDealershipSetup: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateCredits: (credits: number) => void;
  updateVerificationStatus: (
    isVerified: boolean,
    verificationStatus?: "pending" | "verified" | "rejected"
  ) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDealershipSetupComplete, setIsDealershipSetupComplete] = useState<
    boolean | null
  >(null);
  const router = useRouter();

  const checkDealershipSetup = async (): Promise<void> => {
    try {
      console.log("[Auth Context] Checking dealership setup status...");

      // Check if we just completed setup - if so, trust localStorage first
      const justCompleted =
        sessionStorage.getItem("just_completed_setup") === "true";
      if (justCompleted) {
        const cachedStatus = localStorage.getItem("dealership_setup_complete");
        if (cachedStatus === "true") {
          console.log(
            "[Auth Context] Just completed setup, using cached true status"
          );
          setIsDealershipSetupComplete(true);
          return;
        }
      }

      const setupComplete = await checkDealershipSetupComplete();
      console.log("[Auth Context] Setup complete status:", setupComplete);
      // Force update state immediately
      setIsDealershipSetupComplete(setupComplete);
      localStorage.setItem("dealership_setup_complete", String(setupComplete));
      console.log(
        "[Auth Context] Updated setup status in state and localStorage:",
        setupComplete
      );
    } catch (error) {
      console.error(
        "[Auth Context] Failed to check dealership setup status:",
        error
      );
      // On error, check localStorage as fallback
      const cachedStatus = localStorage.getItem("dealership_setup_complete");
      if (cachedStatus === "true") {
        console.log("[Auth Context] Using cached true status due to error");
        setIsDealershipSetupComplete(true);
        return;
      }
      setIsDealershipSetupComplete(false);
      localStorage.setItem("dealership_setup_complete", "false");
    }
  };

  useEffect(() => {
    const checkSession = async () => {
      const token = localStorage.getItem("auth_token");
      const userData = localStorage.getItem("user_data");
      const authData = localStorage.getItem("auth_data");

      if (token && userData) {
        try {
          setUser(JSON.parse(userData));

          // Fetch dealership_id if not already stored
          const storedDealershipId = localStorage.getItem("dealership_id");
          if (!storedDealershipId) {
            try {
              const dealershipDetails = await getDealershipDetails();
              const dealershipId =
                dealershipDetails?.dealership_id ||
                dealershipDetails?.dealership_slug;
              if (dealershipId) {
                localStorage.setItem("dealership_id", dealershipId);
                console.log(
                  "Stored dealership_id from session check:",
                  dealershipId
                );
              }
            } catch (error) {
              console.error(
                "Failed to fetch dealership details in session check:",
                error
              );
              // Don't throw - dealership_id might be available later
            }
          }

          // Check setup status from localStorage first
          const storedSetupStatus = localStorage.getItem(
            "dealership_setup_complete"
          );
          if (storedSetupStatus !== null) {
            setIsDealershipSetupComplete(storedSetupStatus === "true");
          } else {
            // If not stored, check from API
            await checkDealershipSetup();
          }
        } catch (error) {
          console.error("[autoNgage] Failed to parse user data:", error);
          localStorage.removeItem("auth_token");
          localStorage.removeItem("user_data");
          localStorage.removeItem("auth_data");
        }
      }
      setIsLoading(false);
    };

    checkSession();
  }, []);

  const login = async (email: string, password: string) => {
    console.log("Attempting login with:", { email });

    try {
      // Call the dealer login API
      const response: DealerLoginResponse = await dealerLogin({
        email,
        password,
      });

      // Extract name from email (part before @)
      const nameFromEmail = email.split("@")[0].replace(/[.+]/g, " ");

      // Create user object from API response
      const user = {
        id: response.user_id || response.session_id,
        email: response.user_id,
        name: nameFromEmail || "Dealer",
        credits: 5000, // Default credits, can be updated later
        isVerified: false,
        verificationStatus: "pending" as const,
      };

      console.log("Login successful, user:", user);
      console.log("Auth response:", response);

      // Store authentication data in localStorage
      localStorage.setItem("auth_token", response.token);
      localStorage.setItem("user_data", JSON.stringify(user));
      localStorage.setItem(
        "auth_data",
        JSON.stringify({
          role: response.role,
          token: response.token,
          expiry: response.expiry,
          user_id: response.user_id,
          enterprise_id: response.enterprise_id,
          application_id: response.application_id,
          session_id: response.session_id,
        })
      );

      // Store session_id, token, user_id, and application_id in cookies
      // IMPORTANT: Always use "autocrm" for application_id, even if backend returns "gryd"
      const applicationId = response.application_id === "autocrm" 
        ? "autocrm" 
        : "autocrm"; // Force "autocrm" to prevent "gryd" errors
      
      setCookie("gryd_session_id", response.session_id, 7);
      setCookie("gryd_token", response.token, 7);
      setCookie("gryd_user_id", response.user_id, 7);
      setCookie("gryd_application_id", applicationId, 7);
      
      console.log("[Auth] Setting application_id cookie:", applicationId);
      console.log("[Auth] Login response application_id:", response.application_id);

      setUser(user);

      // Fetch dealership details to get dealership_id
      try {
        const dealershipDetails = await getDealershipDetails();
        const dealershipId =
          dealershipDetails?.dealership_id ||
          dealershipDetails?.dealership_slug;
        if (dealershipId) {
          localStorage.setItem("dealership_id", dealershipId);
          console.log("Stored dealership_id:", dealershipId);
        }
      } catch (error) {
        console.error("Failed to fetch dealership details:", error);
        // Don't throw - dealership_id might be available later
      }

      // Check dealership setup status after login
      try {
        const setupComplete = await checkDealershipSetupComplete();
        setIsDealershipSetupComplete(setupComplete);
        // Store in localStorage for quick access
        localStorage.setItem(
          "dealership_setup_complete",
          String(setupComplete)
        );
      } catch (error) {
        console.error("Failed to check dealership setup status:", error);
        setIsDealershipSetupComplete(false);
      }
    } catch (error) {
      console.error("Login error:", error);
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Invalid email or password");
    }
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    localStorage.removeItem("auth_data");
    localStorage.removeItem("dealership_setup_complete");
    localStorage.removeItem("dealership_id");

    // Delete cookies
    deleteCookie("gryd_session_id");
    deleteCookie("gryd_token");
    deleteCookie("gryd_user_id");
    deleteCookie("gryd_application_id");

    setUser(null);
    setIsDealershipSetupComplete(null);

    router.push("/login");
  };

  const updateCredits = (credits: number) => {
    if (user) {
      const updatedUser = { ...user, credits };
      setUser(updatedUser);
      localStorage.setItem("user_data", JSON.stringify(updatedUser));
    }
  };

  const updateVerificationStatus = (
    isVerified: boolean,
    verificationStatus?: "pending" | "verified" | "rejected"
  ) => {
    if (user) {
      const updatedUser = { ...user, isVerified, verificationStatus };
      setUser(updatedUser);
      localStorage.setItem("user_data", JSON.stringify(updatedUser));
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
