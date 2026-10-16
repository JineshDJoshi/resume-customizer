import type { CustomizeResult, DownloadFormat, Resume } from "./types";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join(" ");
  } catch {
    /* fall through */
  }
  return `The server returned an error (${res.status}). Please try again.`;
}

async function request(path: string, init: RequestInit, timeoutMs = 120_000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API}${path}`, { ...init, signal: controller.signal });
    if (!res.ok) throw new Error(await errorMessage(res));
    return res;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("The request took too long. Please try again.");
    }
    if (err instanceof TypeError) {
      throw new Error("Can't reach the server. Check your connection and try again.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function customizeResume(jd: string, file: File, sections: string[]): Promise<CustomizeResult> {
  const form = new FormData();
  form.append("jd", jd);
  form.append("resume", file);
  form.append("sections", sections.join(","));
  return (await request("/api/customize", { method: "POST", body: form })).json();
}

export async function generateCoverLetter(jd: string, resume: Resume): Promise<string> {
  const res = await request("/api/cover-letter", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd, resume }),
  });
  return (await res.json()).cover_letter;
}

export async function downloadResume(resume: Resume, format: DownloadFormat): Promise<void> {
  const res = await request("/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume, format }),
  });
  const blob = await res.blob();
  const match = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "");
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = match?.[1] || `resume.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
