import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app import diffing, exporters, llm, scoring
from app.config import settings
from app.main import app
from app.parser import ResumeParseError, extract_text
from app.schemas import LLMResult, Resume

JD = ("We need a Python backend engineer with FastAPI, PostgreSQL and AWS experience. "
      "You will design REST APIs, write tests and mentor engineers on Docker deployments.")

RESUME_TEXT = (
    "Jane Doe\njane@example.com | +1 555 123 4567\nSUMMARY\nSoftware developer.\n"
    "SKILLS\nPython, SQL, Docker\nEXPERIENCE\nDeveloper - Acme 2020-2024\n"
    "• Built services in Python serving 10k users\n• Wrote tests for APIs\n"
)


def make_docx(text: str) -> bytes:
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


FAKE = LLMResult.model_validate({
    "resume": {
        "name": "Jane Doe", "contact": ["jane@example.com", "+1 555 123 4567"],
        "summary": "Python developer focused on REST APIs and Docker deployments.",
        "skills": [{"category": "Backend", "items": ["Python", "FastAPI", "Docker"]}],
        "experience": [{"title": "Developer", "company": "Acme", "dates": "2020-2024",
                        "bullets": ["Built REST APIs in Python serving 10k users", "Wrote automated tests for APIs"]}],
        "education": ["B.Tech, XYZ University"],
    },
    "analysis": {"missing_keywords": ["AWS", "PostgreSQL"], "suggestions": ["Add AWS if you used it"]},
})


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 0)

    async def fake(jd, text, sections):
        return FAKE

    monkeypatch.setattr(llm, "customize_resume", fake)
    return TestClient(app)


def test_docx_parsing():
    assert "Jane Doe" in extract_text("cv.docx", make_docx(RESUME_TEXT))


def test_rejects_bad_types():
    with pytest.raises(ResumeParseError):
        extract_text("cv.txt", b"hello")
    with pytest.raises(ResumeParseError):
        extract_text("cv.pdf", b"not a pdf")


def test_match_score_improves_with_keywords():
    kws = scoring.jd_keywords(JD)
    assert scoring.match_score("Python FastAPI PostgreSQL AWS Docker REST APIs tests", kws) > scoring.match_score("Cooking", kws)


def test_diff_marks_additions():
    seg = diffing.word_diff("built services", "built REST services")
    assert any(s["t"] == "add" and "REST" in s["text"] for s in seg)


def test_exports_are_valid_files():
    r = FAKE.resume
    assert exporters.to_pdf(r).startswith(b"%PDF")
    assert exporters.to_docx(r).startswith(b"PK")
    assert "SUMMARY" in exporters.resume_to_text(r)


def test_customize_happy_path(client):
    res = client.post("/api/customize", data={"jd": JD}, files={"resume": ("cv.docx", make_docx(RESUME_TEXT))})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["scores"]["match_after"] >= body["scores"]["match_before"]
    assert body["resume"]["name"] == "Jane Doe"
    assert body["diff"]


@pytest.mark.parametrize("data,files,code", [
    ({"jd": ""}, {"resume": ("cv.docx", b"x")}, 400),
    ({"jd": "too short"}, {"resume": ("cv.docx", b"x")}, 400),
    ({"jd": JD}, {}, 400),
    ({"jd": JD}, {"resume": ("cv.txt", b"hello world")}, 415),
    ({"jd": JD, "sections": "nonsense"}, {"resume": ("cv.docx", b"x")}, 400),
])
def test_validation_errors(client, data, files, code):
    assert client.post("/api/customize", data=data, files=files).status_code == code


def test_large_file_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    res = client.post("/api/customize", data={"jd": JD}, files={"resume": ("cv.docx", b"PK" + b"0" * 500)})
    assert res.status_code == 413


def test_llm_failure_is_graceful(client, monkeypatch):
    async def boom(*a, **k):
        raise llm.LLMError("The AI service is rate-limited right now.", 429)

    monkeypatch.setattr(llm, "customize_resume", boom)
    res = client.post("/api/customize", data={"jd": JD}, files={"resume": ("cv.docx", make_docx(RESUME_TEXT))})
    assert res.status_code == 429 and "rate-limited" in res.json()["detail"]


def test_download_formats(client):
    for fmt in ("pdf", "docx", "txt"):
        res = client.post("/api/download", json={"resume": FAKE.resume.model_dump(), "format": fmt})
        assert res.status_code == 200 and fmt in res.headers["content-disposition"]
