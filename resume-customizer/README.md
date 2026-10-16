# Resume Customizer

Paste a job description, upload a resume (PDF or DOCX), and get a version of that resume rewritten for the role, with a match score, a diff of every change, keyword suggestions, an ATS checklist, a cover letter, and downloads in PDF / DOCX / text.

**Live app:** `https://<your-app>.vercel.app`  ·  **API:** `https://<your-api>.onrender.com/docs`
*(Replace these after you deploy — see [Deployment](#deployment).)*

## Features

**Core (all required items)**
- JD textarea with validation (non-empty, 50–12,000 characters, live counter)
- PDF **and** DOCX upload, shows file name and size, validated on client and server (type, magic bytes, 5 MB cap, empty file, scanned/unreadable PDFs)
- Server-side text extraction (`pdfplumber`, `python-docx`)
- LLM customization: rewritten summary, JD-relevant skills first, experience bullets reordered/rephrased with the JD's wording, and missing keywords suggested
- Clean "paper" rendering of the result and downloads as **PDF, DOCX or TXT**
- Error handling: bad file types, large files, empty inputs, LLM timeouts / rate limits / malformed output, network failures, server-side rate limiting

**Bonus features implemented**
- Match score, before vs. after (deterministic keyword coverage, not LLM-guessed)
- Diff view (word-level: additions highlighted, removals struck through)
- Multiple resume versions with side-by-side compare
- Section-wise customization (Summary / Skills / Experience / Projects; unchecked sections stay verbatim)
- Cover letter generator
- ATS score with a pass/fail checklist and fix tips

*Not implemented:* authentication and streaming (see [Limitations](#known-limitations-and-trade-offs)).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, plain CSS |
| Backend | Python 3.12, FastAPI, Pydantic v2, httpx |
| Parsing / export | pdfplumber, python-docx, reportlab |
| **LLM** | **Google Gemini — `gemini-2.5-flash`** (free tier via Google AI Studio), called over REST with JSON-mode output. Model is configurable with `GEMINI_MODEL`. |
| Hosting | Vercel (frontend) + Render (backend) — `render.yaml` and a `Dockerfile` (Cloud Run) are included |

## Architecture

```
┌──────────────────────────────┐
│ Next.js frontend (Vercel)    │  JD textarea · file upload · section picker
│  - validates inputs          │  result view · diff · compare · downloads
└──────────────┬───────────────┘
               │ REST (multipart / JSON)
┌──────────────▼───────────────┐
│ FastAPI backend (Render)     │
│  1. validate + rate limit    │  POST /api/customize   (JD + file → tailored resume + scores + diff)
│  2. parse PDF/DOCX → text    │  POST /api/cover-letter
│  3. prompt + call LLM        │  POST /api/download    (pdf | docx | txt)
│  4. validate JSON (Pydantic) │  GET  /health
│  5. score, diff, ATS check   │
└──────────────┬───────────────┘
               │ HTTPS (retries + backoff)
┌──────────────▼───────────────┐
│ Gemini API                   │
└──────────────────────────────┘
```

**Request flow for `/api/customize`:** validate inputs → extract text → send JD + resume text to Gemini with a strict system prompt → parse the JSON into a typed `Resume` model (one automatic repair retry if the JSON is malformed) → compute match scores, keyword gap, ATS checks and the diff in plain Python → return everything in one response.

### Prompt design
The system prompt (`backend/app/llm.py`) is the core of the quality:
- **Truthfulness rules first:** never invent employers, dates, tools or metrics; unsupported JD keywords go into `missing_keywords` instead of the resume.
- **Per-section instructions** (summary length and tone, skill grouping, bullet length, how many bullets may be dropped, never drop a role).
- **Scoped edits:** only sections in `SECTIONS_TO_CUSTOMIZE` may change; others are copied verbatim.
- **Prompt-injection guard:** JD and resume are wrapped in tags and declared to be data, not instructions.
- **Structured output:** JSON mode plus an explicit schema, validated with Pydantic (tolerates nulls and flat skill lists).
- Scores are computed in code, so they are consistent and not hallucinated.

## Local setup

Prerequisites: Python 3.11+, Node.js 18.18+, and a free Gemini API key from <https://aistudio.google.com/apikey>.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000              # docs at http://localhost:8000/docs

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local                             # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                                            # http://localhost:3000
```

Run the backend tests (no API key needed — the LLM is mocked):

```bash
cd backend && python -m pytest -q
```

### Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | backend | Gemini key (never commit; `.env` is git-ignored) |
| `GEMINI_MODEL` | backend | Defaults to `gemini-2.5-flash` |
| `CORS_ORIGINS` | backend | Comma-separated allowed frontend origins |
| `MAX_UPLOAD_MB` | backend | Upload cap, default 5 |
| `RATE_LIMIT_PER_MINUTE` | backend | Per-IP limit on LLM endpoints, default 10 |
| `NEXT_PUBLIC_API_URL` | frontend | Backend base URL |

## Deployment

**1. Backend → Render**
1. Push this repo to GitHub.
2. In Render: *New → Blueprint*, select the repo (it reads `render.yaml`). Or *New → Web Service* with root directory `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Set `GEMINI_API_KEY`. Leave `CORS_ORIGINS` for step 3 below.
4. Verify `https://<your-api>.onrender.com/health` returns `{"status":"ok"}`.

*(Alternative: `cd backend && gcloud run deploy resume-api --source . --allow-unauthenticated --set-env-vars GEMINI_API_KEY=...` uses the included Dockerfile.)*

**2. Frontend → Vercel**
1. *Add New Project*, import the repo, set **Root Directory = `frontend`**.
2. Add env var `NEXT_PUBLIC_API_URL=https://<your-api>.onrender.com`.
3. Deploy.

**3. Connect them:** set `CORS_ORIGINS=https://<your-app>.vercel.app` on the backend and redeploy. Then put both URLs at the top of this README.

## Known limitations and trade-offs

- **No streaming.** The result arrives in one response (typically 10–30 s) because the backend must validate a complete JSON document before scoring and diffing it. A spinner and clear status are shown instead.
- **No authentication / history.** Versions live in browser memory for the session only; no database keeps user resumes (a privacy plus, but nothing persists across reloads).
- **Render free tier cold starts.** The first request after idle can take ~30–60 s.
- **Scanned (image-only) PDFs** are rejected with a helpful message; there is no OCR.
- **Layout is not preserved.** The resume is re-generated into a clean single-column, ATS-friendly template, so fancy original formatting (columns, graphics) is lost. Complex multi-column PDFs may extract in a jumbled reading order.
- **PDF export uses built-in Latin-1 fonts**, so non-Latin scripts will not render in the PDF (use DOCX/TXT for those).
- **Match/ATS scores are heuristics** (keyword coverage + structural checks), useful as guidance, not a replica of any real ATS.
- **In-memory rate limiter** is per-instance; use Redis or an API gateway if you scale to multiple instances.
- The LLM can still occasionally misread a messy resume — always review the output before sending it.

## Project structure

```
backend/
  app/
    main.py        # routes, validation, rate limit
    llm.py         # prompts, Gemini client, retries, JSON repair
    parser.py      # PDF / DOCX text extraction
    schemas.py     # Pydantic resume + analysis models
    scoring.py     # keyword match score, ATS checks
    diffing.py     # word-level diff
    exporters.py   # text / DOCX / PDF generation
    config.py
  tests/test_core.py
  Dockerfile  requirements.txt  .env.example
frontend/
  app/             # layout, page, styles
  components/      # UploadBox, ResumeView (paper + diff), ScoreRing
  lib/             # API client, types
  .env.example
render.yaml  README.md  .gitignore
```
