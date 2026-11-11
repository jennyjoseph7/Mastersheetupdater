'use client';
import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/components/ThemeProvider';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import './index.css';

const TOOLS = [
  {
    href: '/disposition-sync-v2', name: 'Pre-Sales Sync',
    desc: 'Merge AutoEngage pre-sales exports into a Zoho Master Sheet-ready table.',
    color: 'red',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  },
  {
    href: '/post-sales-sync', name: 'Post-Sales Sync',
    desc: 'Process service and feedback reminder batches, then export post-sales Zoho Master Sheet rows.',
    color: 'orange',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m2 7H7a2 2 0 01-2-2V7a2 2 0 012-2h3l2 2h5a2 2 0 012 2v3" /><path strokeLinecap="round" strokeLinejoin="round" d="M17 14l2 2 4-4" /></svg>,
  },
  {
    href: '/formatter', name: 'Formatter',
    desc: 'Map client columns into dealership-wise AutoEngage upload format using predefined templates.',
    color: 'yellow',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  },
  {
    href: '/recording-renamer', name: 'Recording Renamer',
    desc: 'Fetch audio from the Recordings column and download renamed call recordings as a ZIP.',
    color: 'green',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h5l2 2h7a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" /><path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6" /></svg>,
  },
  {
    href: '/call-analysis', name: 'Call Summary',
    desc: 'Upload processed Pre-Sales Sync exports and generate daily call analysis summaries.',
    color: 'purple',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-6m4 6V7m4 10v-4M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>,
  },
  {
    href: '/credit-report', name: 'Credit Report',
    desc: 'Upload bot credit billing CSV to generate objective-wise Voice and WhatsApp spend workbooks.',
    color: 'lime',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>,
  },
];

export default function LandingPage() {
  const log = (...args: unknown[]) => console.log('[Landing]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading, logout } = useAuth();
  const router = useRouter();
  const { theme } = useTheme();

  useEffect(() => {
    document.title = 'Lead Operations Hub — AutoNage Lead Operations';
    const isDark = theme !== 'light';
    const defAccent = isDark ? '#ef4444' : '#dc2626';
    const defSoft = isDark ? 'rgba(239,68,68,0.13)' : 'rgba(220,38,38,0.1)';
    document.documentElement.style.setProperty('--accent', defAccent);
    document.documentElement.style.setProperty('--accent-soft', defSoft);
    document.documentElement.style.setProperty('--accent-p', defAccent);
    document.documentElement.style.setProperty('--accent-soft-p', defSoft);
  }, [theme]);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  return (
    <div className="landing-page">
      {isAuthenticated && (
        <button className="signout-btn" onClick={logout} aria-label="Sign out">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
        </button>
      )}
      <ThemeToggle />
      <BrandLogo />
      <h1>Lead Operations</h1>
      <div className="subtitle">{TOOLS.length} tools for AutoEngage ↔ Zoho lead operations</div>
      <div className="tools-grid">
        {TOOLS.map(t => (
          <Link key={t.href} href={t.href} prefetch={false} className={`tool-card ${t.color}`} style={{ textDecoration: 'none' }}>
            <div className={`tool-icon ${t.color}`}>{t.icon}</div>
            <div className="tool-name">{t.name}</div>
            <div className="tool-desc">{t.desc}</div>
            <div className="tool-arrow">Open tool →</div>
          </Link>
        ))}
      </div>
      <footer>AutoNage Lead Operations v2.4 • &copy; {new Date().getFullYear()} AutoNage</footer>
    </div>
  );
}
