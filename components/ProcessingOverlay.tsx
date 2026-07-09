interface Props { show: boolean; message?: string; progress?: number; }

export default function ProcessingOverlay({ show, message, progress }: Props) {
  if (!show) return null;
  return (
    <div className="processing-overlay">
      <div className="processing-card">
        <div className="spinner" />
        <span>{message || 'Processing…'}</span>
        {typeof progress === 'number' && (
          <>
            <div className="progress-track"><div className="progress-fill" style={{ width: progress + '%' }} /></div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{progress}%</span>
          </>
        )}
      </div>
    </div>
  );
}
