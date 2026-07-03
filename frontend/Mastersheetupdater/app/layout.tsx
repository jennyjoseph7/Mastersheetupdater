import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/ThemeProvider';
import { ToastProvider } from '@/components/Toast';

export const metadata: Metadata = {
  title: 'AutoNage — Lead Operations',
  description: 'AutoNage Lead Operations Automation tools.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script src={process.env.NODE_ENV === 'development' ? '/jejo-config.js' : '/Mastersheetupdater/jejo-config.js'} />
          <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('jejo-theme')||'dark';document.documentElement.setAttribute('data-theme',t);})()`
          }}
        />
      </head>
      <body>
        <ThemeProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
