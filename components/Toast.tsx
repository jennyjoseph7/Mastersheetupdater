'use client';
import { createContext, useContext, useState, ReactNode, useCallback } from 'react';

interface ToastCtx { showToast: (msg: string, duration?: number) => void; }
const ToastCtx = createContext<ToastCtx>({ showToast: () => {} });
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState('');
  const [visible, setVisible] = useState(false);
  
  const showToast = useCallback((message: string, duration = 2000) => {
    setMsg(message);
    setVisible(true);
    setTimeout(() => setVisible(false), duration);
  }, []);
  
  return (
    <ToastCtx.Provider value={{ showToast }}>
      {children}
      {visible && <div className="toast show">{msg}</div>}
    </ToastCtx.Provider>
  );
}
