'use client';
import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import './index.css';

const TOOLS = [
  {
    href: '/disposition-sync-v2', name: 'Pre-Sales Sync',
    desc: 'Merge pre-sales AutoEngage Audience & Leads + Sessions exports into a Zoho Master Sheet-ready table. Process daily call batches.',
    color: 'red',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  },
  {
    href: '/post-sales-sync', name: 'Post-Sales Sync',
    desc: 'Process dealership-wise service reminder and feedback reminder batches, then export post-sales Zoho Master Sheet rows.',
    color: 'orange',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m2 7H7a2 2 0 01-2-2V7a2 2 0 012-2h3l2 2h5a2 2 0 012 2v3" /><path strokeLinecap="round" strokeLinejoin="round" d="M17 14l2 2 4-4" /></svg>,
  },
  {
    href: '/recording-renamer', name: 'Recording Renamer',
    desc: 'Upload the processed Pre-Sales Sync file, fetch links from the Recordings column, and download renamed call recordings as a ZIP.',
    color: 'green',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h5l2 2h7a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" /><path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6" /></svg>,
  },
  {
    href: '/formatter', name: 'Formatter',
    desc: 'Map client columns into dealership-wise AutoEngage upload format using predefined templates, with preview and download.',
    color: 'blue',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  },
  {
    href: '/campaign-generator', name: 'Campaign Generator',
    desc: 'Generate structured 20-field campaign objectives for voice AI outbound, service reminders, and WhatsApp messaging campaigns.',
    color: 'teal',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>,
  },
  {
    href: '/call-analysis', name: 'Call Summary',
    desc: 'Upload the processed Pre-Sales Sync export and generate the daily call analysis summary.',
    color: 'purple',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-6m4 6V7m4 10v-4M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>,
  },
  {
    href: '/reattempt-filter', name: 'Re-Attempt Filter',
    desc: 'Upload multi-day Zoho data, filter out leads already connected, and download a clean AutoEngage re-attempt list.',
    color: 'pink',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  },
  {
    href: '/master-lead-matcher', name: 'Master Matcher',
    desc: 'Club raw Client Lead Files (with full client columns) with processed Master Sheets based on Registration No. or Phone No.',
    color: 'indigo',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>,
  },
  {
    href: '/dashboard', name: 'Dashboard',
    desc: 'Upload Zoho exports to generate a visual call campaign summary with KPIs, charts, and follow-up insights.',
    color: 'yellow',
    icon: <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8"><path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>,
  },
];

export default function LandingPage() {
  const log = (...args: unknown[]) => console.log('[Landing]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  return (
    <div className="landing-page">
      <button className="signout-btn" onClick={logout} aria-label="Sign out">
        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
      </button>
      <ThemeToggle />
      <BrandLogo />
      <h1>Lead Operations</h1>
      <div className="subtitle">AutoEngage → Zoho Master Sheet</div>
      <div className="tools-grid">
        {TOOLS.map(t => (
          <Link key={t.href} href={t.href} className={`tool-card ${t.color}`} style={{ textDecoration: 'none' }}>
            <div className={`tool-icon ${t.color}`}>{t.icon}</div>
            <div className="tool-name">{t.name}</div>
            <div className="tool-desc">{t.desc}</div>
            <div className="tool-arrow">Open tool →</div>
          </Link>
        ))}
      </div>
      <footer>AutoNage - Lead Operations Automation</footer>
    </div>
  );
}
