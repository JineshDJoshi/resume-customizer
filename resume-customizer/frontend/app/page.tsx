"use client";
import { useState } from "react";
import ScoreRing from "@/components/ScoreRing";
import UploadBox from "@/components/UploadBox";
import { DiffPaper, EmptyPaper, ResumePaper } from "@/components/ResumeView";
import { customizeResume, downloadResume, generateCoverLetter } from "@/lib/api";
import type { DownloadFormat, Version } from "@/lib/types";

const JD_MIN = 20;
const JD_MAX = 12000;
const SECTIONS = [
  { id: "summary", label: "Summary" },
  { id: "skills", label: "Skills" },
  { id: "experience", label: "Experience" },
  { id: "projects", label: "Projects" },
];
type View = "tailored" | "changes" | "compare";

export default function Home() {
  const [jd, setJd] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sections, setSections] = useState<string[]>(SECTIONS.map((s) => s.id));
  const [versions, setVersions] = useState<Version[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [compareId, setCompareId] = useState<number | null>(null);
  const [view, setView] = useState<View>("tailored");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const active = versions.find((v) => v.id === activeId) ?? null;
  const other = versions.find((v) => v.id === compareId) ?? versions.find((v) => v.id !== activeId) ?? null;
  const jdLen = jd.trim().length;

  const toggleSection = (id: string) =>
    setSections((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  async function onGenerate() {
    setError(null);
    if (!jdLen) return setError("Paste the job description before generating.");
    if (jdLen < JD_MIN) return setError(`The job description is too short. Paste the full posting (at least ${JD_MIN} characters).`);
    if (jdLen > JD_MAX) return setError(`The job description is too long. The limit is ${JD_MAX.toLocaleString()} characters.`);
    if (!file) return setError("Upload your resume as a PDF or DOCX file.");
    if (!sections.length) return setError("Select at least one section to customize.");

    setLoading(true);
    try {
      const result = await customizeResume(jd.trim(), file, sections);
      const id = (versions.at(-1)?.id ?? 0) + 1;
      const version: Version = { id, label: `Version ${id}`, sections: [...sections], result };
      setVersions((v) => [...v, version]);
      setActiveId(id);
      setView("tailored");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function onDownload(format: DownloadFormat) {
    if (!active) return;
    setBusy(format);
    setError(null);
    try {
      await downloadResume(active.result.resume, format);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setBusy(null);
    }
  }

  async function onCoverLetter() {
    if (!active) return;
    setBusy("cover");
    setError(null);
    try {
      const text = await generateCoverLetter(jd.trim(), active.result.resume);
      setVersions((vs) => vs.map((v) => (v.id === active.id ? { ...v, coverLetter: text } : v)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate the cover letter.");
    } finally {
      setBusy(null);
    }
  }

  async function copyLetter() {
    if (!active?.coverLetter) return;
    await navigator.clipboard.writeText(active.coverLetter);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  const r = active?.result;

  return (
    <main className="shell">
      <header className="top">
        <h1>Resume Customizer</h1>
        <p>Paste a job description, upload your resume, and get a version rewritten for that role. Nothing is invented — only what your resume already supports.</p>
      </header>

      <div className="grid">
        {/* ------------------------------------------------ inputs */}
        <section className="panel inputs" aria-label="Inputs">
          <div className="field">
            <label htmlFor="jd">Job description</label>
            <textarea
              id="jd"
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job posting, including requirements and responsibilities."
              rows={11}
            />
            <p className={`hint ${jdLen > 0 && jdLen < JD_MIN ? "warn" : ""}`}>
              {jdLen.toLocaleString()} / {JD_MAX.toLocaleString()} characters{jdLen < JD_MIN ? ` (minimum ${JD_MIN})` : ""}
            </p>
          </div>

          <div className="field">
            <span className="label" id="resume-label">Resume</span>
            <UploadBox file={file} onFile={(f, err) => { setFile(f); setError(err); }} />
          </div>

          <fieldset className="field">
            <legend>Sections to customize</legend>
            <div className="chips">
              {SECTIONS.map((s) => (
                <label key={s.id} className={`chip ${sections.includes(s.id) ? "on" : ""}`}>
                  <input type="checkbox" checked={sections.includes(s.id)} onChange={() => toggleSection(s.id)} />
                  {s.label}
                </label>
              ))}
            </div>
            <p className="hint">Unchecked sections stay exactly as you wrote them.</p>
          </fieldset>

          {error && <p className="error" role="alert">{error}</p>}

          <button className="primary" onClick={onGenerate} disabled={loading}>
            {loading ? (<><span className="spinner" aria-hidden="true" /> Tailoring your resume…</>) : versions.length ? "Generate another version" : "Tailor my resume"}
          </button>
          {loading && <p className="hint">This usually takes 10–30 seconds.</p>}
        </section>

        {/* ------------------------------------------------ results */}
        <section className="results" aria-live="polite" aria-label="Results">
          {!r || !active ? (
            <>
              <EmptyPaper />
              <p className="empty-note">Your tailored resume will appear here, with a before/after match score and a view of every change.</p>
            </>
          ) : (
            <>
              <div className="bar">
                <div className="tabs" role="tablist" aria-label="Versions">
                  {versions.map((v) => (
                    <button key={v.id} role="tab" aria-selected={v.id === activeId} className={v.id === activeId ? "tab on" : "tab"} onClick={() => { setActiveId(v.id); setCompareId(null); }}>
                      {v.label}
                    </button>
                  ))}
                </div>
                <div className="seg" role="group" aria-label="View">
                  {(["tailored", "changes", "compare"] as View[]).map((v) => (
                    <button key={v} className={view === v ? "on" : ""} onClick={() => setView(v)} disabled={v === "compare" && versions.length < 2} title={v === "compare" && versions.length < 2 ? "Generate a second version to compare" : undefined}>
                      {v === "tailored" ? "Tailored" : v === "changes" ? "Changes" : "Compare"}
                    </button>
                  ))}
                </div>
              </div>

              <div className="scores">
                <ScoreRing value={r.scores.match_before} label="Match before" tone="muted" />
                <ScoreRing value={r.scores.match_after} label="Match after" />
                <ScoreRing value={r.scores.ats} label="ATS score" />
                <p className="scores-note">
                  Customized: {active.sections.join(", ")}. Match score is the weighted share of the job&apos;s key terms found in the resume.
                </p>
              </div>

              {view === "tailored" && <ResumePaper resume={r.resume} />}
              {view === "changes" && <DiffPaper segments={r.diff} />}
              {view === "compare" && other && (
                <div className="compare">
                  <div>
                    <p className="cmp-title">{active.label}</p>
                    <ResumePaper resume={r.resume} />
                  </div>
                  <div>
                    <label className="cmp-title">
                      <span className="sr-only">Compare with</span>
                      <select value={other.id} onChange={(e) => setCompareId(Number(e.target.value))}>
                        {versions.filter((v) => v.id !== activeId).map((v) => <option key={v.id} value={v.id}>{v.label} (match {v.result.scores.match_after}%)</option>)}
                      </select>
                    </label>
                    <ResumePaper resume={other.result.resume} />
                  </div>
                </div>
              )}

              <div className="downloads">
                <span>Download {active.label}:</span>
                {(["pdf", "docx", "txt"] as DownloadFormat[]).map((f) => (
                  <button key={f} className="secondary" onClick={() => onDownload(f)} disabled={busy !== null}>
                    {busy === f ? "Preparing…" : f === "txt" ? "Text" : f.toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="insights">
                <div className="card">
                  <h3>What changed</h3>
                  <ul>{r.analysis.changes_summary.map((c, i) => <li key={i}>{c}</li>)}</ul>
                </div>
                <div className="card">
                  <h3>Keywords to consider adding</h3>
                  {r.analysis.missing_keywords.length ? (
                    <p className="tags">{r.analysis.missing_keywords.map((k) => <span key={k} className="tag miss">{k}</span>)}</p>
                  ) : <p className="hint">Your resume already covers the main terms.</p>}
                  <ul>{r.analysis.suggestions.map((c, i) => <li key={i}>{c}</li>)}</ul>
                  <p className="hint">Only add a keyword if you have genuinely used that skill.</p>
                </div>
                <div className="card">
                  <h3>Keywords matched</h3>
                  <p className="tags">{r.analysis.matched_keywords.map((k) => <span key={k} className="tag hit">{k}</span>)}</p>
                </div>
                <div className="card">
                  <h3>ATS checklist</h3>
                  <ul className="checks">
                    {r.ats_checks.map((c) => (
                      <li key={c.label} className={c.passed ? "ok" : "no"}>
                        <span className="mark" aria-label={c.passed ? "Passed" : "Needs work"}>{c.passed ? "✓" : "!"}</span>
                        <span>{c.label}{!c.passed && c.tip ? <em> — {c.tip}</em> : null}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="card letter">
                <div className="letter-head">
                  <h3>Cover letter</h3>
                  <button className="secondary" onClick={onCoverLetter} disabled={busy !== null}>
                    {busy === "cover" ? "Writing…" : active.coverLetter ? "Rewrite" : "Generate cover letter"}
                  </button>
                </div>
                {active.coverLetter ? (
                  <>
                    <pre>{active.coverLetter}</pre>
                    <button className="link" onClick={copyLetter}>{copied ? "Copied" : "Copy to clipboard"}</button>
                  </>
                ) : <p className="hint">Write a short letter for this role from the facts in {active.label}.</p>}
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
