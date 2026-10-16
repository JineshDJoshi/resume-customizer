"""Word-level diff between the original resume text and the customized text."""
import difflib
import re

_WORD = re.compile(r"\n|[^\s]+")


def _norm(tok: str) -> str:
    return re.sub(r"^\W+|\W+$", "", tok.lower())


def word_diff(original: str, customized: str) -> list[dict]:
    """Return segments [{"t": "equal"|"add"|"del"|"br", "text": str}] describing customized vs original."""
    a_words = [w for w in _WORD.findall(original) if w != "\n" and _norm(w)]
    b_tokens = _WORD.findall(customized)

    b_words: list[str] = []
    newline_before: list[int] = []
    pending = 0
    for tok in b_tokens:
        if tok == "\n":
            pending += 1
        elif _norm(tok):
            b_words.append(tok)
            newline_before.append(pending)
            pending = 0

    sm = difflib.SequenceMatcher(None, [_norm(w) for w in a_words], [_norm(w) for w in b_words], autojunk=False)
    segments: list[dict] = []

    def push(kind: str, text: str) -> None:
        if segments and segments[-1]["t"] == kind and kind != "br":
            segments[-1]["text"] += " " + text
        else:
            segments.append({"t": kind, "text": text})

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("delete", "replace"):
            push("del", " ".join(a_words[i1:i2]))
        if op in ("insert", "replace", "equal"):
            kind = "equal" if op == "equal" else "add"
            for j in range(j1, j2):
                if newline_before[j]:
                    segments.append({"t": "br", "text": "\n" * min(newline_before[j], 2)})
                push(kind, b_words[j])
    return segments
