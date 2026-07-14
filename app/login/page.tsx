'use client';
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/components/ThemeProvider';
import './login.css';

const ASSET_PREFIX = process.env.NODE_ENV === 'development' ? '' : '/Mastersheetupdater';

export default function LoginPage() {
  const log = (...args) => console.log('[Login]', ...args);
  log('Page mounted');
  const router = useRouter();
  const { login, checkSession, loading: authLoading } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('human_agent');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionInfo, setSessionInfo] = useState('');
  const [flashSuccess, setFlashSuccess] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const t = localStorage.getItem('jejo-theme') || 'dark';
      document.documentElement.setAttribute('data-theme', t);
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!userId.trim()) { setError('Please enter your email or user ID.'); return; }
    if (!password) { setError('Please enter your password.'); return; }
    setLoading(true);
    try {
      const result = await login(userId.trim(), password, role);
      if (result.ok) {
        setFlashSuccess(true);
        setTimeout(() => { router.push('/'); }, 1200);
      } else {
        setError(result.error || 'Login failed. Check your credentials.');
        setLoading(false);
      }
    } catch {
      setError('Network error. Check your connection.');
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <button className="login-theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
        <svg className="icon-moon" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
        <svg className="icon-sun" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
      </button>

      <div className="login-container">
        <div className="login-card">
          <Link href="/" className="brand-mark" aria-label="Home">
            <img className="login-logo login-logo-dark" src={`${ASSET_PREFIX}/images/AN Dark.png`} alt="AutoNage" />
            <img className="login-logo login-logo-light" src={`${ASSET_PREFIX}/images/AN.png`} alt="AutoNage" />
          </Link>

          <div id="loginForm">
            {flashSuccess ? (
              <div className="flash-success">
                <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                Signed in as {userId} — redirecting&hellip;
              </div>
            ) : (
              <>
                <div className="login-title">Welcome back</div>
                <div className="login-subtitle">Sign in with your autoNgage account</div>

                {error && <div className="err-msg show">{error}</div>}
                {warning && <div className="warn-msg show">{warning}</div>}

                <form onSubmit={handleSubmit}>
                  <div className="form-group">
                    <label className="form-label" htmlFor="role">Role</label>
                    <select className="form-input" id="role" value={role} onChange={e => setRole(e.target.value)} disabled={loading}>
                      <option value="human_agent">Human Agent</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="userId">Email or User ID</label>
                    <input className="form-input" id="userId" type="text" value={userId} onChange={e => setUserId(e.target.value)} placeholder="dealership@iamdave.ai" autoComplete="username" spellCheck="false" disabled={loading} />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="password">Password</label>
                    <div className="password-wrapper">
                      <input className="form-input" id="password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="•••••••••" autoComplete="current-password" disabled={loading} />
                      <button className="password-toggle" type="button" onClick={() => setShowPassword(!showPassword)} aria-label="Toggle password">
                        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          {showPassword ? (
                            <><path strokeLinecap="round" strokeLinejoin="round" d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><path strokeLinecap="round" strokeLinejoin="round" d="M1 1l22 22"/></>
                          ) : (
                            <><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></>
                          )}
                        </svg>
                      </button>
                    </div>
                  </div>

                  <button className={`btn-login${loading ? ' loading' : ''}`} type="submit" disabled={loading}>
                    <span className="spinner"></span>
                    <span id="btnText">{loading ? 'Signing in…' : 'Sign In'}</span>
                  </button>
                </form>

                {sessionInfo && <div className="session-info">{sessionInfo}</div>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
