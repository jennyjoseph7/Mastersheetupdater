"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

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

      if (token && userData) {
        try {
          setUser(JSON.parse(userData));
        } catch (error) {
          console.error("[autoNgage] Failed to parse user data:", error);
          localStorage.removeItem("auth_token");
          localStorage.removeItem("user_data");
        }
      }
      setIsLoading(false);
    };

    checkSession();
  }, []);

  const login = async (email: string, password: string) => {
    console.log("Attempting login with:", { email });

    // Client-side authentication for static export compatibility
    // In production, this should point to your backend API
    if (email === "user@iamdave.ai" && password === "12345678") {
      const user = {
        id: "dealer_001",
        email: "user@iamdave.ai",
        name: "Dave AI Dealer",
        credits: 5000,
        isVerified: false,
        verificationStatus: "pending" as const,
      };

      const token = `token_${Date.now()}_${Math.random()
        .toString(36)
        .substring(7)}`;

      console.log("Login successful, user:", user);

      localStorage.setItem("auth_token", token);
      localStorage.setItem("user_data", JSON.stringify(user));

      setUser(user);
    } else {
      throw new Error("Invalid email or password");
    }
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");

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
