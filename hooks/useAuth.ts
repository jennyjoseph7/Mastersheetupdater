'use client';
import { useState, useEffect, useCallback } from 'react';

interface AuthState {
  token: string | null;
  sessionId: string | null;
  enterpriseId: string | null;
  userId: string | null;
  expiry: number;
  isAuthenticated: boolean;
  loading: boolean;
}

function storage(key: string): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(key);
}
function setStorage(key: string, value: string | null) {
  if (typeof window === 'undefined') return;
  if (value) { sessionStorage.setItem(key, value); }
  else { sessionStorage.removeItem(key); }
}

function parseExpiry(val: unknown): number {
  if (!val) return 0;
  const n = Number(val);
  if (!isNaN(n)) {
    if (n > 30000000000) return Math.floor(n / 1000);
    if (n < 31536000) return Math.floor(Date.now() / 1000) + n;
    return n;
  }
  const d = Date.parse(String(val));
  return isNaN(d) ? 0 : Math.floor(d / 1000);
}

function grydEndpoint(): string {
  if (typeof window !== 'undefined' && (window as any).JEJO_CONFIG?.grydEndpoint) return (window as any).JEJO_CONFIG.grydEndpoint;
  return 'https://autobot-webapp-dev.gryd.in';
}
function grydSignupToken(): string {
  if (typeof window !== 'undefined' && (window as any).JEJO_CONFIG?.grydSignupToken) return (window as any).JEJO_CONFIG.grydSignupToken;
  return '';
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    token: null, sessionId: null, enterpriseId: null, userId: null,
    expiry: 0, isAuthenticated: false, loading: true,
  });

  const checkSession = useCallback(async () => {
    const token = storage('gryd_token');
    const sessionId = storage('gryd_session_id');
    const enterpriseId = storage('gryd_enterprise_id') || 'autocrm';
    const userId = storage('gryd_user_id');
    const expiry = parseInt(storage('gryd_expiry') || '0');
    const now = Math.floor(Date.now() / 1000);
    const clientValid = Boolean(token) && expiry > now;
    let serverValid = clientValid;
    if (clientValid && token) {
      try {
        const res = await fetch(`${grydEndpoint()}/auth/check`, {
          headers: { 'X-GRYD-TOKEN': token, 'X-GRYD-SESSION-ID': sessionId || '' },
        });
        if (!res.ok) serverValid = false;
      } catch {
        /* worker unreachable, trust client check */
      }
    }
    if (!serverValid) {
      setStorage('gryd_token', null);
      setStorage('gryd_session_id', null);
      setStorage('gryd_expiry', null);
    }
    setState({
      token: serverValid ? token : null,
      sessionId: serverValid ? sessionId : null,
      enterpriseId, userId,
      expiry, isAuthenticated: serverValid, loading: false,
    });
  }, []);

  useEffect(() => { checkSession(); }, [checkSession]);

  const login = async (userId: string, password: string, role: string = 'human_agent'): Promise<{ ok: boolean; error?: string }> => {
    try {
      const res = await fetch(`${grydEndpoint()}/gryd/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-GRYD-ENTERPRISE-ID': 'autocrm',
          'X-GRYD-SIGNUP-TOKEN': grydSignupToken(),
        },
        body: JSON.stringify({ user_id: userId, password, role, attribute: 'email', application_id: 'autocrm' }),
      });
      const data = await res.json();
      if (!res.ok) return { ok: false, error: data.error || data.message || 'Login failed' };
      const expiry = parseExpiry(data.expiry);
      setStorage('gryd_token', data.token);
      setStorage('gryd_session_id', data.session_id || '');
      setStorage('gryd_enterprise_id', data.enterprise_id || 'autocrm');
      setStorage('gryd_user_id', data.user_id || '');
      setStorage('gryd_expiry', String(expiry));
      document.cookie = `gryd_token=${data.token}; path=/; max-age=${Math.max(expiry, 86400)}; SameSite=Lax`;
      document.cookie = `gryd_expiry=${expiry}; path=/; max-age=${Math.max(expiry, 86400)}; SameSite=Lax`;
      checkSession();
      return { ok: true };
    } catch (err: unknown) {
      return { ok: false, error: 'Login failed. Check connection.' };
    }
  };

  const logout = () => {
    setStorage('gryd_token', null);
    setStorage('gryd_session_id', null);
    setStorage('gryd_enterprise_id', null);
    setStorage('gryd_user_id', null);
    setStorage('gryd_expiry', null);
    document.cookie = 'gryd_token=; path=/; max-age=0; SameSite=Lax';
    document.cookie = 'gryd_expiry=; path=/; max-age=0; SameSite=Lax';
    // Clear AI cache entries that may contain PII from call data
    if (typeof window !== 'undefined') {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.startsWith('disp-validate-') || key.startsWith('ps-disp-validate-') ||
            key === 'dashAiCache' || key === 'jejo-ae-batch-export-v1')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(k => { try { localStorage.removeItem(k); } catch {} });
    }
    setState({ token: null, sessionId: null, enterpriseId: null, userId: null, expiry: 0, isAuthenticated: false, loading: false });
  };

  return { ...state, login, logout, checkSession };
}