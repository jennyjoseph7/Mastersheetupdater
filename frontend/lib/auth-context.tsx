"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { dealerLogin, type DealerLoginResponse } from "@/lib/api";

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
  const router = useRouter();

  useEffect(() => {
    const checkSession = async () => {
      const token = localStorage.getItem("auth_token");
      const userData = localStorage.getItem("user_data");
      const authData = localStorage.getItem("auth_data");

      if (token && userData) {
        try {
          setUser(JSON.parse(userData));
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

      // Store authentication data
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

      setUser(user);
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

    setUser(null);

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
