'use client';
import type { BatchProgressState } from '@/hooks/useBatchProgress';

interface Props {
  state: BatchProgressState;
  onDismiss?: () => void;
  onRetry?: () => void;
  onCancel?: () => void;
  /** Label for the retry button (default: "↻ Run again") */
  retryLabel?: string;
}

export default function BatchProgressBar({ state, onDismiss, onRetry, onCancel, retryLabel = '↻ Run again' }: Props) {
  if (!state.show) return null;

  const pct = state.total > 0 ? Math.round((state.done / state.total) * 100) : 0;
  const isErr = state.aborted;
  const isOk = state.completed;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: '0.5rem',
      padding: '0.65rem 0.85rem',
      border: `1px solid ${isErr ? 'rgba(239,68,68,0.2)' : isOk ? 'rgba(99,214,163,0.2)' : 'var(--border)'}`,
      borderRadius: '12px',
      background: isErr ? 'rgba(239,68,68,0.04)' : isOk ? 'rgba(99,214,163,0.04)' : 'var(--accent-soft)',
      marginBottom: '1rem',
      fontFamily: 'var(--body)',
    }}>
      {/* Row 1: Message + badges */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
        <span style={{
          fontSize: '0.82rem', fontWeight: 500,
          color: isErr ? '#ef4444' : isOk ? 'var(--text)' : 'var(--text-dim)',
        }}>
          {state.message || (isErr ? 'Cancelled.' : isOk ? 'Complete.' : 'Processing…')}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '0.72rem', fontWeight: 700,
            padding: '0.15rem 0.45rem',
            borderRadius: '6px',
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            color: 'var(--text-dim)',
            fontFamily: 'var(--mono)',
          }}>
            {state.done}/{state.total}
          </span>
          {state.corrected > 0 && (
            <span style={{
              fontSize: '0.72rem', fontWeight: 700,
              padding: '0.15rem 0.45rem',
              borderRadius: '6px',
              background: 'rgba(99,214,163,0.1)',
              border: '1px solid rgba(99,214,163,0.3)',
              color: '#63d6a3',
              fontFamily: 'var(--mono)',
            }}>
              {state.corrected} corrected
            </span>
          )}
          {state.elapsed && (
            <span style={{
              fontSize: '0.7rem', color: 'var(--text-muted)',
              fontFamily: 'var(--mono)',
            }}>
              {state.elapsed}
            </span>
          )}
        </div>
      </div>

      {/* Progress bar track */}
      <div style={{
        height: '4px', borderRadius: '99px',
        background: 'var(--bg)',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          borderRadius: '99px',
          background: isErr
            ? '#ef4444'
            : isOk
              ? 'linear-gradient(90deg, #63d6a3, #4ade80)'
              : 'linear-gradient(90deg, var(--accent), var(--accent-dim))',
          transition: 'width 0.3s ease',
        }} />
      </div>

      {/* Row 2: Action buttons */}
      {(onDismiss || onRetry || onCancel) && (
        <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
          {!state.completed && !state.aborted && onCancel && (
            <button onClick={onCancel} style={btnStyle('#ef4444')}>Cancel</button>
          )}
          {state.aborted && onDismiss && (
            <button onClick={onDismiss} style={btnStyle('var(--text-muted)')}>Dismiss</button>
          )}
          {(state.aborted || state.completed) && onRetry && (
            <button onClick={onRetry} style={{ ...btnStyle('var(--accent)'), background: 'var(--accent-soft)' }}>
              {retryLabel}
            </button>
          )}
          {state.completed && onDismiss && (
            <button onClick={onDismiss} style={btnStyle('var(--text-muted)')}>Dismiss</button>
          )}
        </div>
      )}
    </div>
  );
}

function btnStyle(color: string): React.CSSProperties {
  return {
    padding: '0.3rem 0.7rem',
    fontSize: '0.75rem',
    fontWeight: 600,
    borderRadius: '8px',
    border: `1px solid ${color}`,
    background: 'transparent',
    color,
    cursor: 'pointer',
    fontFamily: 'var(--body)',
  };
}
