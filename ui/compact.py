"""compact.py - shorten a long report to its plain-words explanations (pure Python, no Kivy).

Used by the Compact reading mode (ui/reading_mode.py) and by the PDF report."""
import re

_HEADING = ("===", "---")
_BRACKET = re.compile(r"\[([^\[\]]+)\]")


def first_sentence(text, limit=240):
    text = " ".join(text.split())
    m = re.search(r"(?<=[.!?])\s", text)
    sentence = text[:m.start()] if m else text
    return sentence if len(sentence) <= limit else sentence[:limit].rsplit(" ", 1)[0] + " ..."


def compact_text(text):
    """Shorten a report (paragraphs separated by blank lines; headings start with --- or ===)."""
    out, section = [], []

    def flush():
        if not section:
            return
        gists = [g.strip() for p in section for g in _BRACKET.findall(p)]
        if gists:
            out.extend(gists)
        else:
            out.append(first_sentence(section[0]))

    for para in (text or "").split("\n\n"):
        para = para.strip("\n")
        if not para.strip():
            continue
        lines = para.split("\n")
        if lines[0].lstrip().startswith(_HEADING):
            flush()
            section.clear()
            out.append(lines[0])
            rest = "\n".join(lines[1:]).strip()
            if rest:
                section.append(rest)
        else:
            section.append(para)
    flush()
    return "\n\n".join(out)


