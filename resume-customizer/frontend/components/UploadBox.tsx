"use client";
import { useRef, useState } from "react";

export const MAX_MB = 5;

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function validateFile(file: File): string | null {
  const ext = file.name.toLowerCase().split(".").pop();
  if (ext !== "pdf" && ext !== "docx") return "Unsupported file type. Upload a PDF or DOCX resume.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `That file is ${formatSize(file.size)}. The limit is ${MAX_MB} MB.`;
  return null;
}

interface Props {
  file: File | null;
  onFile: (file: File | null, error: string | null) => void;
}

export default function UploadBox({ file, onFile }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const pick = (f?: File | null) => {
    if (!f) return;
    const err = validateFile(f);
    onFile(err ? null : f, err);
    if (input.current) input.current.value = "";
  };

  return (
    <div
      className={`drop ${over ? "over" : ""} ${file ? "has-file" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files?.[0]); }}
    >
      <input
        ref={input}
        id="resume-file"
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={(e) => pick(e.target.files?.[0])}
        className="sr-only"
      />
      {file ? (
        <div className="file-row">
          <div>
            <p className="file-name">{file.name}</p>
            <p className="hint">{formatSize(file.size)}</p>
          </div>
          <button type="button" className="link" onClick={() => onFile(null, null)}>Remove</button>
        </div>
      ) : (
        <label htmlFor="resume-file" className="drop-label">
          <span className="drop-title">Drop your resume here or choose a file</span>
          <span className="hint">PDF or DOCX, up to {MAX_MB} MB</span>
        </label>
      )}
    </div>
  );
}
