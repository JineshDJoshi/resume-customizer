"""Turn a structured Resume into plain text, DOCX or PDF (single-column, ATS-friendly)."""
import io
import re
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from .schemas import Resume


def _exp_heading(e) -> str:
    left = " - ".join(p for p in (e.title, e.company) if p)
    if e.location:
        left += f", {e.location}"
    return left


def resume_to_text(r: Resume) -> str:
    out: list[str] = []
    if r.name:
        out.append(r.name)
    if r.contact:
        out.append(" | ".join(r.contact))
    if r.summary:
        out += ["", "SUMMARY", r.summary]
    if r.skills:
        out += ["", "SKILLS"]
        for g in r.skills:
            items = ", ".join(g.items)
            out.append(f"{g.category}: {items}" if g.category else items)
    if r.experience:
        out += ["", "EXPERIENCE"]
        for e in r.experience:
            head = _exp_heading(e)
            out.append(f"{head} | {e.dates}" if e.dates else head)
            out += [f"• {b}" for b in e.bullets]
    if r.projects:
        out += ["", "PROJECTS"]
        for p in r.projects:
            out.append(p.name)
            out += [f"• {b}" for b in p.bullets]
    if r.education:
        out += ["", "EDUCATION", *r.education]
    if r.certifications:
        out += ["", "CERTIFICATIONS", *r.certifications]
    return "\n".join(out).strip() + "\n"


# --------------------------------------------------------------------------- DOCX

def to_docx(r: Resume) -> bytes:
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(0.8)
        s.top_margin = s.bottom_margin = Inches(0.7)
    base = doc.styles["Normal"]
    base.font.name = "Calibri"
    base.font.size = Pt(10.5)

    def para(text="", bold=False, size=None, align=None, space_after=2, space_before=0):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(space_before)
        if align:
            p.alignment = align
        run = p.add_run(text)
        run.bold = bold
        if size:
            run.font.size = Pt(size)
        return p

    def heading(text):
        para(text, bold=True, size=11.5, space_before=10, space_after=3)

    def bullets(items):
        for b in items:
            p = doc.add_paragraph(b, style="List Bullet")
            p.paragraph_format.space_after = Pt(1)

    if r.name:
        para(r.name, bold=True, size=20, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    if r.contact:
        para(" | ".join(r.contact), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    if r.summary:
        heading("SUMMARY")
        para(r.summary)
    if r.skills:
        heading("SKILLS")
        for g in r.skills:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            if g.category:
                p.add_run(f"{g.category}: ").bold = True
            p.add_run(", ".join(g.items))
    if r.experience:
        heading("EXPERIENCE")
        for e in r.experience:
            p = para(_exp_heading(e), bold=True, space_before=4, space_after=0)
            if e.dates:
                p.add_run(f"  |  {e.dates}").bold = False
            bullets(e.bullets)
    if r.projects:
        heading("PROJECTS")
        for pr in r.projects:
            para(pr.name, bold=True, space_before=4, space_after=0)
            bullets(pr.bullets)
    if r.education:
        heading("EDUCATION")
        for line in r.education:
            para(line)
    if r.certifications:
        heading("CERTIFICATIONS")
        for line in r.certifications:
            para(line)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------- PDF

_ASCII_MAP = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-",
              "\u2014": "-", "\u2022": "-", "\u2026": "...", "\u00a0": " ", "\u2192": "->"}


def _safe(text: str) -> str:
    """Built-in PDF fonts only cover Latin-1; map common typography and drop the rest."""
    for k, v in _ASCII_MAP.items():
        text = text.replace(k, v)
    return escape(text.encode("latin-1", "replace").decode("latin-1"))


def to_pdf(r: Resume) -> bytes:
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=13)
    name = ParagraphStyle("name", parent=body, fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=TA_CENTER)
    contact = ParagraphStyle("contact", parent=body, alignment=TA_CENTER, spaceAfter=6)
    head = ParagraphStyle("head", parent=body, fontName="Helvetica-Bold", fontSize=11.5, spaceBefore=10, spaceAfter=3)
    role = ParagraphStyle("role", parent=body, fontName="Helvetica-Bold", spaceBefore=5)

    def bullets(items):
        return ListFlowable(
            [ListItem(Paragraph(_safe(b), body), leftIndent=12) for b in items],
            bulletType="bullet", start="-", leftIndent=12, bulletFontSize=9,
        )

    story = []
    if r.name:
        story.append(Paragraph(_safe(r.name), name))
    if r.contact:
        story.append(Paragraph(_safe(" | ".join(r.contact)), contact))
    if r.summary:
        story += [Paragraph("SUMMARY", head), Paragraph(_safe(r.summary), body)]
    if r.skills:
        story.append(Paragraph("SKILLS", head))
        for g in r.skills:
            label = f"<b>{_safe(g.category)}:</b> " if g.category else ""
            story.append(Paragraph(label + _safe(", ".join(g.items)), body))
    if r.experience:
        story.append(Paragraph("EXPERIENCE", head))
        for e in r.experience:
            line = _safe(_exp_heading(e)) + (f" &nbsp;|&nbsp; {_safe(e.dates)}" if e.dates else "")
            story.append(Paragraph(line, role))
            if e.bullets:
                story.append(bullets(e.bullets))
    if r.projects:
        story.append(Paragraph("PROJECTS", head))
        for p in r.projects:
            story.append(Paragraph(_safe(p.name), role))
            if p.bullets:
                story.append(bullets(p.bullets))
    if r.education:
        story.append(Paragraph("EDUCATION", head))
        story += [Paragraph(_safe(x), body) for x in r.education]
    if r.certifications:
        story.append(Paragraph("CERTIFICATIONS", head))
        story += [Paragraph(_safe(x), body) for x in r.certifications]
    story.append(Spacer(1, 1))

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                      topMargin=0.7 * inch, bottomMargin=0.7 * inch, title=r.name or "Resume").build(story)
    return buf.getvalue()


def safe_filename(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return f"{slug or 'resume'}_tailored"
