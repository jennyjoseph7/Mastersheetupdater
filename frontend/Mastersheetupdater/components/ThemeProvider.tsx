'use client';
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getStoredTheme, applyTheme } from '@/lib/theme';

type Theme = 'dark' | 'light';
interface ThemeContextValue { theme: Theme; toggleTheme: () => void; }

const ThemeCtx = createContext<ThemeContextValue>({ theme: 'dark', toggleTheme: () => {} });
export const useTheme = () => useContext(ThemeCtx);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('dark');
  
  useEffect(() => { setTheme(getStoredTheme()); }, []);
  useEffect(() => { applyTheme(theme); }, [theme]);
  
  const toggle = () => setTheme(p => p === 'dark' ? 'light' : 'dark');
  
  return <ThemeCtx.Provider value={{ theme, toggleTheme: toggle }}>{children}</ThemeCtx.Provider>;
}
