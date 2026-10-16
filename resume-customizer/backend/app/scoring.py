"""Deterministic keyword match score and ATS-friendliness estimate (no LLM involved)."""
import re
from collections import Counter

from .schemas import Resume

STOP = set("""
a about above after again all also am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers
him his how i if in into is it its just me more most my no nor not now of off on once only or other our out
over own same she should so some such than that the their them then there these they this those through to
too under until up us very was we were what when where which while who whom why will with would you your
experience work working team teams ability able years year role job strong skills skill required preferred
must etc including include includes responsibilities responsibility requirements requirement looking
candidate candidates company join across using use used within plus well good great excellent knowledge
understanding minimum least related relevant new need needs make help etc ensure like opportunity position
bachelor degree equivalent proven demonstrated environment day based high
""".split())

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]*")


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[: -len(suf)]
            break
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]
    return w


def _tokens(text: str):
    for m in TOKEN_RE.finditer(text):
        raw = m.group().strip("./-")
        if len(raw) >= 2:
            yield raw


def jd_keywords(jd: str, top: int = 35) -> dict[str, tuple[str, float]]:
    """Return {stem: (display_word, weight)} for the most important JD terms."""
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    boost: dict[str, float] = {}
    for raw in _tokens(jd):
        low = raw.lower()
        if low in STOP or len(low) < 3 and low not in {"c", "r", "go", "ai", "ml", "qa", "ui", "ux"}:
            continue
        stem = _stem(low)
        counts[stem] += 1
        display.setdefault(stem, raw if raw.isupper() or any(ch in raw for ch in "+#.") else low)
        if any(c.isupper() for c in raw[1:]) or any(ch in raw for ch in "+#."):
            boost[stem] = 2.0
    ranked = sorted(counts, key=lambda s: -(counts[s] + boost.get(s, 0)))[:top]
    return {s: (display[s], counts[s] + boost.get(s, 0)) for s in ranked}


def _stems(text: str) -> set[str]:
    return {_stem(t.lower()) for t in _tokens(text)}


def match_score(text: str, kws: dict[str, tuple[str, float]]) -> int:
    if not kws:
        return 0
    have = _stems(text)
    total = sum(w for _, w in kws.values())
    hit = sum(w for s, (_, w) in kws.items() if s in have)
    return round(100 * hit / total)


def keyword_gap(text: str, kws: dict[str, tuple[str, float]]) -> tuple[list[str], list[str]]:
    have = _stems(text)
    matched = [d for s, (d, _) in kws.items() if s in have]
    missing = [d for s, (d, _) in kws.items() if s not in have]
    return matched, missing


def ats_score(text: str, r: Resume, keyword_pct: int) -> tuple[int, list[dict]]:
    checks: list[dict] = []

    def add(label: str, passed: bool, pts: int, tip: str) -> int:
        checks.append({"label": label, "passed": passed, "tip": "" if passed else tip})
        return pts if passed else 0

    bullets = [b for e in r.experience for b in e.bullets] + [b for p in r.projects for b in p.bullets]
    words = len(text.split())
    avg_len = sum(len(b.split()) for b in bullets) / len(bullets) if bullets else 0
    quantified = sum(1 for b in bullets if re.search(r"\d", b)) / len(bullets) if bullets else 0

    score = 0
    score += add("Email address present", bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)), 8,
                 "Add a professional email address in the header.")
    score += add("Phone number present", bool(re.search(r"\+?\d[\d\s().-]{8,}\d", text)), 7,
                 "Add a phone number in the header.")
    score += add("Professional summary", bool(r.summary.strip()), 10, "Add a 2-3 sentence summary.")
    score += add("Skills section", any(g.items for g in r.skills), 10, "Add a dedicated Skills section.")
    score += add("Dated work experience", bool(r.experience) and all(e.dates for e in r.experience), 10,
                 "Give every role a start and end date.")
    score += add("Education listed", bool(r.education), 5, "Add an Education section.")
    score += add("Concise bullets (8-28 words)", 8 <= avg_len <= 28, 10,
                 "Keep experience bullets between 8 and 28 words.")
    score += add("Quantified achievements", quantified >= 0.3, 10,
                 "Add numbers (%, $, users, time saved) to at least a third of your bullets.")
    score += add("Length 300-900 words", 300 <= words <= 900, 10,
                 "Aim for one to two pages (roughly 300-900 words).")
    kw_pts = round(20 * keyword_pct / 100)
    score += kw_pts
    checks.append({"label": f"Job keyword coverage ({keyword_pct}%)", "passed": keyword_pct >= 60,
                   "tip": "" if keyword_pct >= 60 else "Work in more of the job's keywords where they are truthful."})
    return min(score, 100), checks
