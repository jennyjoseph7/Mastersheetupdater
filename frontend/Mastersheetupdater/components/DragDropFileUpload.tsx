'use client';
import { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { validateFile } from '@/lib/data-pipeline';

interface Props {
  onFile: (file: File) => void;
  onError?: (error: string) => void;
  accept?: string;
  label?: string;
  disabled?: boolean;
}

export default function DragDropFileUpload({ onFile, onError, accept = '.xlsx,.xls,.csv', label = 'Drop your file here or click to browse', disabled }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  async function validateAndAccept(file: File) {
    setErrorMsg('');
    const result = await validateFile(file);
    if (!result.valid) {
      setErrorMsg(result.error!);
      onError?.(result.error!);
      return;
    }
    setFileName(file.name);
    onFile(file);
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndAccept(file);
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndAccept(file);
  };

  return (
    <div
      className={`drop-zone${isDragging ? ' drag-over' : ''}${errorMsg ? ' drop-zone-error' : ''}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      style={{ opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? 'none' : 'auto' }}
    >
      <svg className="dz-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      <div className="dz-text">{fileName || label}</div>
      {errorMsg && <div className="dz-error">{errorMsg}</div>}
      <input ref={inputRef} type="file" accept={accept} onChange={handleChange} style={{ display: 'none' }} />
    </div>
  );
}
