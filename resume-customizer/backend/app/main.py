"""FastAPI application: resume parsing, LLM customization, scoring, export."""
import logging
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import diffing, exporters, llm, scoring
from .config import settings
from .parser import ResumeParseError, extract_text
from .schemas import Resume

log = logging.getLogger("resume-customizer")

JD_MIN, JD_MAX = 50, 12_000
VALID_SECTIONS = {"summary", "skills", "experience", "projects"}

app = FastAPI(title="Resume Customizer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ------------------------------------------------------------------ simple in-memory rate limit
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    now, q = time.monotonic(), _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
    q.append(now)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "model": settings.gemini_model}


# ------------------------------------------------------------------ customize
@app.post("/api/customize", dependencies=[Depends(rate_limit)])
async def customize(
    jd: str = Form(""),
    resume: UploadFile | None = File(None),
    sections: str = Form("summary,skills,experience,projects"),
) -> dict:
    jd = jd.strip()
    if not jd:
        raise HTTPException(400, "Paste the job description before generating.")
    if len(jd) < JD_MIN:
        raise HTTPException(400, f"The job description is too short ({len(jd)} characters). Paste the full posting (at least {JD_MIN}).")
    if len(jd) > JD_MAX:
        raise HTTPException(400, f"The job description is too long ({len(jd):,} characters). The limit is {JD_MAX:,}.")
    if resume is None or not resume.filename:
        raise HTTPException(400, "Upload your resume as a PDF or DOCX file.")

    chosen = [s for s in (x.strip() for x in sections.split(",")) if s in VALID_SECTIONS]
    if not chosen:
        raise HTTPException(400, "Select at least one section to customize.")

    data = await resume.read(settings.max_upload_bytes + 1)
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"The file is too large. The limit is {settings.max_upload_bytes // (1024 * 1024)} MB.")

    try:
        original_text = await run_in_threadpool(extract_text, resume.filename, data)
    except ResumeParseError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    original_text = original_text[:20_000]

    try:
        result = await llm.customize_resume(jd, original_text, chosen)
    except llm.LLMError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

    tailored = result.resume
    tailored_text = exporters.resume_to_text(tailored)

    kws = scoring.jd_keywords(jd)
    before = scoring.match_score(original_text, kws)
    after = scoring.match_score(tailored_text, kws)
    matched, missing = scoring.keyword_gap(tailored_text, kws)
    ats, ats_checks = scoring.ats_score(tailored_text, tailored, after)

    # Keep the LLM's "missing" keywords only if they really are absent from the tailored resume.
    llm_missing = [k for k in result.analysis.missing_keywords if k.lower() not in tailored_text.lower()]
    merged_missing = list(dict.fromkeys([*llm_missing, *missing]))[:15]

    analysis = result.analysis.model_copy(update={"matched_keywords": matched[:20], "missing_keywords": merged_missing})
    return {
        "resume": tailored.model_dump(),
        "analysis": analysis.model_dump(),
        "scores": {"match_before": before, "match_after": after, "ats": ats},
        "ats_checks": ats_checks,
        "diff": diffing.word_diff(original_text, tailored_text),
        "original_text": original_text,
        "customized_text": tailored_text,
        "file": {"name": resume.filename, "size": len(data)},
    }


# ------------------------------------------------------------------ cover letter
class CoverLetterRequest(BaseModel):
    jd: str = Field(min_length=JD_MIN, max_length=JD_MAX)
    resume: Resume


@app.post("/api/cover-letter", dependencies=[Depends(rate_limit)])
async def cover_letter(body: CoverLetterRequest) -> dict:
    try:
        text = await llm.generate_cover_letter(body.jd, exporters.resume_to_text(body.resume))
    except llm.LLMError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return {"cover_letter": text.strip()}


# ------------------------------------------------------------------ download
class DownloadRequest(BaseModel):
    resume: Resume
    format: Literal["pdf", "docx", "txt"]


MEDIA = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
}


@app.post("/api/download")
async def download(body: DownloadRequest) -> Response:
    r = body.resume
    if body.format == "pdf":
        content = await run_in_threadpool(exporters.to_pdf, r)
    elif body.format == "docx":
        content = await run_in_threadpool(exporters.to_docx, r)
    else:
        content = exporters.resume_to_text(r).encode("utf-8")
    filename = f"{exporters.safe_filename(r.name)}.{body.format}"
    return Response(content, media_type=MEDIA[body.format],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
