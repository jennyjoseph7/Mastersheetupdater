'use client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useEffect } from 'react';

const ACCENT_MAP: Record<string, { dark: string; light: string; softDark: string; softLight: string }> = {
  'disposition-sync-v2': { dark: '#ef4444', light: '#dc2626', softDark: 'rgba(239,68,68,0.13)', softLight: 'rgba(220,38,38,0.1)' },
  'post-sales-sync':     { dark: '#f97316', light: '#ea580c', softDark: 'rgba(249,115,22,0.13)', softLight: 'rgba(234,88,12,0.1)' },
  'reattempt-filter':    { dark: '#ec4899', light: '#db2777', softDark: 'rgba(236,72,153,0.13)', softLight: 'rgba(219,39,119,0.1)' },
  'dashboard':           { dark: '#3b82f6', light: '#2563eb', softDark: 'rgba(59,130,246,0.13)', softLight: 'rgba(37,99,235,0.1)' },
  'call-analysis':       { dark: '#a855f7', light: '#7c3aed', softDark: 'rgba(168,85,247,0.12)', softLight: 'rgba(124,58,237,0.1)' },
  'formatter':           { dark: '#eab308', light: '#ca8a04', softDark: 'rgba(234,179,8,0.13)', softLight: 'rgba(202,138,4,0.1)' },
  'campaign-generator':  { dark: '#5eead4', light: '#0d9488', softDark: 'rgba(94,234,212,0.1)', softLight: 'rgba(13,148,136,0.08)' },
  'recording-renamer':   { dark: '#22c55e', light: '#16a34a', softDark: 'rgba(34,197,94,0.13)', softLight: 'rgba(22,163,74,0.1)' },
};

const LINKS = [
  { href: '/disposition-sync-v2', label: 'Pre-Sales Sync' },
  { href: '/post-sales-sync', label: 'Post-Sales Sync' },
  { href: '/reattempt-filter', label: 'Re-Attempt Filter' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/call-analysis', label: 'Call Summary' },
  { href: '/formatter', label: 'Formatter' },
  { href: '/campaign-generator', label: 'Campaign Gen' },
  { href: '/recording-renamer', label: 'Recording Renamer' },
];

export default function Nav() {
  const pathname = usePathname();
  const pageKey = pathname.replace(/^\//, '');

  useEffect(() => {
    const c = ACCENT_MAP[pageKey];
    if (!c) return;
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    document.documentElement.style.setProperty('--accent-p', isDark ? c.dark : c.light);
    document.documentElement.style.setProperty('--accent-soft-p', isDark ? c.softDark : c.softLight);
  }, [pageKey]);

  return (
    <nav className="header-nav">
      {LINKS.map(l => (
        <Link key={l.href} href={l.href}
          className={`nav-link${pathname === l.href ? ' active' : ''}`}
          data-page={l.href.slice(1)}>
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
