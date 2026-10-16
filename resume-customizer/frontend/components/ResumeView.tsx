import type { DiffSegment, Resume } from "@/lib/types";

export function ResumePaper({ resume }: { resume: Resume }) {
  return (
    <article className="paper" aria-label="Tailored resume">
      {resume.name && <h2 className="p-name">{resume.name}</h2>}
      {resume.contact.length > 0 && <p className="p-contact">{resume.contact.join("  |  ")}</p>}

      {resume.summary && (
        <section>
          <h3>Summary</h3>
          <p>{resume.summary}</p>
        </section>
      )}
      {resume.skills.length > 0 && (
        <section>
          <h3>Skills</h3>
          {resume.skills.map((g, i) => (
            <p key={i}>
              {g.category && <strong>{g.category}: </strong>}
              {g.items.join(", ")}
            </p>
          ))}
        </section>
      )}
      {resume.experience.length > 0 && (
        <section>
          <h3>Experience</h3>
          {resume.experience.map((e, i) => (
            <div key={i} className="p-role">
              <p className="p-role-head">
                <strong>{[e.title, e.company].filter(Boolean).join(" – ")}{e.location ? `, ${e.location}` : ""}</strong>
                {e.dates && <span className="p-dates">{e.dates}</span>}
              </p>
              <ul>{e.bullets.map((b, j) => <li key={j}>{b}</li>)}</ul>
            </div>
          ))}
        </section>
      )}
      {resume.projects.length > 0 && (
        <section>
          <h3>Projects</h3>
          {resume.projects.map((p, i) => (
            <div key={i} className="p-role">
              <p className="p-role-head"><strong>{p.name}</strong></p>
              <ul>{p.bullets.map((b, j) => <li key={j}>{b}</li>)}</ul>
            </div>
          ))}
        </section>
      )}
      {resume.education.length > 0 && (
        <section>
          <h3>Education</h3>
          {resume.education.map((l, i) => <p key={i}>{l}</p>)}
        </section>
      )}
      {resume.certifications.length > 0 && (
        <section>
          <h3>Certifications</h3>
          {resume.certifications.map((l, i) => <p key={i}>{l}</p>)}
        </section>
      )}
    </article>
  );
}

export function DiffPaper({ segments }: { segments: DiffSegment[] }) {
  return (
    <article className="paper diff" aria-label="Changes from your original resume">
      <p className="legend">
        <mark className="add">Added or reworded</mark> <del className="del">Removed</del>
      </p>
      <div className="diff-body">
        {segments.map((s, i) => {
          if (s.t === "br") return <br key={i} />;
          if (s.t === "add") return <mark key={i} className="add">{s.text} </mark>;
          if (s.t === "del") return <del key={i} className="del">{s.text} </del>;
          return <span key={i}>{s.text} </span>;
        })}
      </div>
    </article>
  );
}

export function EmptyPaper() {
  return (
    <div className="paper ghost" aria-hidden="true">
      <div className="g-line w40 tall" />
      <div className="g-line w60" />
      {[1, 2, 3].map((n) => (
        <div key={n} className="g-block">
          <div className="g-line w25" />
          <div className="g-line" />
          <div className="g-line w90" />
          <div className="g-line w75" />
        </div>
      ))}
    </div>
  );
}
