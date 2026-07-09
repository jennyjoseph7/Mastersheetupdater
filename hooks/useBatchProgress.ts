'use client';
import { useState, useRef, useCallback, useEffect } from 'react';

export interface BatchProgressState {
  show: boolean;
  message: string;
  done: number;
  total: number;
  corrected: number;
  aborted: boolean;
  completed: boolean;
  elapsed: string;
}

export interface UseBatchProgressReturn {
  /** Current progress state — spread into BatchProgressBar props */
  state: BatchProgressState;
  /** Show the progress bar with initial message */
  begin: (total: number) => void;
  /** Advance progress by one item */
  tick: (message?: string) => void;
  /** Set done count directly (e.g. from a batch callback) */
  setDone: (done: number, message?: string) => void;
  /** Mark a correction */
  markCorrected: (count?: number) => void;
  /** Mark as completed */
  complete: (message?: string) => void;
  /** Mark as aborted */
  abort: (message?: string) => void;
  /** Reset to initial state */
  reset: () => void;
  /** Total items */
  total: number;
}

export function useBatchProgress(): UseBatchProgressReturn {
  const [show, setShow] = useState(false);
  const [message, setMessage] = useState('');
  const [done, setDoneState] = useState(0);
  const [total, setTotal] = useState(0);
  const [corrected, setCorrected] = useState(0);
  const [aborted, setAborted] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [elapsed, setElapsed] = useState('');

  const startTimeRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      const secs = Math.floor((Date.now() - startTimeRef.current) / 1000);
      setElapsed(secs > 60 ? `${Math.floor(secs / 60)}m ${secs % 60}s` : `${secs}s`);
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    // Final elapsed
    if (startTimeRef.current) {
      const secs = Math.floor((Date.now() - startTimeRef.current) / 1000);
      setElapsed(secs > 60 ? `${Math.floor(secs / 60)}m ${secs % 60}s` : `${secs}s`);
    }
  }, []);

  const begin = useCallback((totalItems: number) => {
    setShow(true);
    setMessage('Processing…');
    setDoneState(0);
    setTotal(totalItems);
    setCorrected(0);
    setAborted(false);
    setCompleted(false);
    setElapsed('');
    startTimer();
  }, [startTimer]);

  const tick = useCallback((msg?: string) => {
    setDoneState(prev => prev + 1);
    if (msg) setMessage(msg);
  }, []);

  const setDone = useCallback((count: number, msg?: string) => {
    setDoneState(count);
    if (msg) setMessage(msg);
  }, []);

  const markCorrected = useCallback((count?: number) => {
    setCorrected(prev => prev + (count ?? 1));
  }, []);

  const complete = useCallback((msg?: string) => {
    setCompleted(true);
    setMessage(msg || 'Complete.');
    stopTimer();
  }, [stopTimer]);

  const abort = useCallback((msg?: string) => {
    setAborted(true);
    setMessage(msg || 'Cancelled.');
    stopTimer();
  }, [stopTimer]);

  const reset = useCallback(() => {
    setShow(false);
    setMessage('');
    setDoneState(0);
    setTotal(0);
    setCorrected(0);
    setAborted(false);
    setCompleted(false);
    setElapsed('');
    stopTimer();
  }, [stopTimer]);

  return {
    state: { show, message, done, total, corrected, aborted, completed, elapsed },
    begin, tick, setDone, markCorrected, complete, abort, reset,
    total,
  };
}
