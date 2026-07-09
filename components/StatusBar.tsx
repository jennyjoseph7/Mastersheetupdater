'use client';
import { useState, useEffect, useRef } from 'react';

interface Props {
  total: number;
  done: number;
  message?: string;
  correctedCount?: number;
  onCancel?: () => void;
  onDismiss?: () => void;
  onRerun?: () => void;
  aborted?: boolean;
  completed?: boolean;
}

export default function StatusBar({ total, done, message, correctedCount, onCancel, onDismiss, onRerun, aborted, completed }: Props) {
  const [elapsed, setElapsed] = useState('');
  const startTime = useRef(Date.now());
  
  useEffect(() => {
    const interval = setInterval(() => {
      const secs = Math.floor((Date.now() - startTime.current) / 1000);
      const m = Math.floor(secs / 60);
      const s = secs % 60;
      setElapsed(m > 0 ? `${m}m ${s}s` : `${s}s`);
    }, 1000);
    return () => clearInterval(interval);
  }, []);
  
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const className = `ai-status-bar${aborted ? ' aborted' : ''}${completed ? ' completed' : ''}`;
  const msgClass = `ai-status-msg${aborted ? ' err' : completed ? ' ok' : ''}`;
  
  return (
    <div className={className} style={{ display: 'block' }}>
      <span className={msgClass}>{message || (aborted ? 'AI validation cancelled.' : completed ? 'AI validation complete.' : 'AI validating…')}</span>
      <span className="ai-status-badge">{done}/{total}</span>
      {correctedCount !== undefined && correctedCount > 0 && <span className="ai-status-corrected">{correctedCount} corrected</span>}
      <span className="ai-status-elapsed">{elapsed}</span>
      <div className="ai-status-track"><div className="ai-status-fill" style={{ width: pct + '%' }} /></div>
      <div className="ai-status-actions">
        {aborted && onDismiss && <button className="ai-status-btn" onClick={onDismiss}>Dismiss</button>}
        {aborted && onRerun && <button className="ai-status-btn primary" onClick={onRerun}>↻ Run again</button>}
        {completed && onDismiss && <button className="ai-status-btn" onClick={onDismiss}>Dismiss</button>}
        {completed && onRerun && <button className="ai-status-btn primary" onClick={onRerun}>↻ Re-run AI</button>}
        {!completed && !aborted && onCancel && <button className="ai-status-btn cancel" onClick={onCancel}>Cancel</button>}
      </div>
    </div>
  );
}
