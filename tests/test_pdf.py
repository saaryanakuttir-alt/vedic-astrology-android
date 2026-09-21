"""PDF writer / report and Compact-mode checks (pure Python, no Kivy).
Run from android_app/:  python -m pytest tests/test_pdf.py"""
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402

from ui import pdf_report  # noqa: E402
from ui.compact import compact_text  # noqa: E402
from ui.pdf_writer import Pdf, text_width, wrap  # noqa: E402


@pytest.fixture(scope="module")
def sample():
    from birth_chart import compute_birth_chart
    from rule_engine import generate_reading
    chart = compute_birth_chart(name="Asha Rao", birth_date=(1990, 6, 15), birth_time=(14, 30, 0),
                                place_name="Mumbai", country_hint="IN", sex="Female")
    return chart, generate_reading(chart)


def _page_count(data):
    return int(re.search(rb"/Type /Pages /Kids \[[^\]]*\] /Count (\d+)", data).group(1))


def test_writer_makes_a_structurally_valid_pdf():
    pdf = Pdf(title="t")
    pdf.new_page()
    pdf.text(50, 780, "Hello (world) \\ café — “quoted”", size=12)
    pdf.line(50, 770, 300, 770)
    pdf.rect(50, 700, 100, 40, fill=(0.9, 0.9, 0.9))
    data = pdf.output()
    assert data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF")
    assert _page_count(data) == 1
    # every object offset in the xref points at "N 0 obj"
    xref = int(re.search(rb"startxref\n(\d+)", data).group(1))
    entries = re.findall(rb"(\d{10}) 00000 n ", data[xref:])
    for n, off in enumerate(entries, start=1):
        assert data[int(off):].startswith(b"%d 0 obj" % n)


def test_wrap_respects_width_and_keeps_all_words():
    text = "one two three four five six seven eight nine ten " * 8
    lines = wrap(text, 10, 200)
    assert all(text_width(line, 10) <= 200 + 1 for line in lines)
    assert " ".join(lines).split() == text.split()


def test_compact_keeps_headings_and_plain_explanations_only():
    text = ("=== Title ===\n\nIntro sentence one. Second sentence.\n\n--- Career ---\nDense classical paragraph. "
            "More detail. [In simple terms: plain career words.]\n\nAnother dense paragraph without a summary.\n\n"
            "--- Health ---\nOnly dense text here. Another sentence.")
    out = compact_text(text)
    assert "=== Title ===" in out and "--- Career ---" in out and "--- Health ---" in out
    assert "In simple terms: plain career words." in out
    assert "Dense classical paragraph" not in out and "Another dense paragraph" not in out
    assert "Only dense text here." in out and "Another sentence." not in out     # no summary -> first sentence
    assert len(out) < len(text)


def test_report_builds_in_both_modes_and_styles(sample):
    chart, reading = sample
    detailed = pdf_report.build_pdf(chart, reading, style="North Indian", mode="detailed")
    compact = pdf_report.build_pdf(chart, reading, style="South Indian", mode="compact")
    for data in (detailed, compact):
        assert data.startswith(b"%PDF-1.4") and _page_count(data) >= 2
    assert _page_count(compact) < _page_count(detailed)
    assert len(compact) < len(detailed) / 2


def test_compact_report_is_short_but_keeps_doshas_and_verdicts(sample):
    pypdf = pytest.importorskip("pypdf")
    import io
    chart, reading = sample
    r = pypdf.PdfReader(io.BytesIO(pdf_report.build_pdf(chart, reading, mode="compact")))
    text = "\n".join(p.extract_text() for p in r.pages)
    assert "Doshas at a glance" in text and "Planet by planet" in text and "Your nature" in text
    assert "All divisional charts" not in text and "Vimshottari Dasha" not in text


def test_report_text_content(sample):
    pypdf = pytest.importorskip("pypdf")
    import io
    chart, reading = sample
    r = pypdf.PdfReader(io.BytesIO(pdf_report.build_pdf(chart, reading, mode="detailed")))
    text = "\n".join(p.extract_text() for p in r.pages)
    assert "Asha Rao" in text and "Created by Sammya Das" in text and f"Page 1 of {len(r.pages)}" in text
    assert "Planet positions" in text and "Life areas" in text
    for section in ("Planet by planet", "Doshas and Sade Sati", "Sade Sati and Dhaiya", "Which planets get along",
                    "All divisional charts", "Shodashvarga table", "D27 Saptavimshamsha", "D45 Akshavedamsha",
                    "Bhava Chalit", "Ashtakvarga", "Vimshottari Dasha", "Medical Astrology - body map",
                    "effects on your houses and signs", "Yogini Dasha", "Char Dasha", "Jaimini significators",
                    "What each Mahadasha may feel like", "Your nature", "Sade Sati for you", "Varshaphal", "KP system",
                    "Planet strength", "Prastharashtakvarga"):
        assert section in text, section
    for forbidden in ("Longevity", "lifespan", "Children"):     # the removed sections must not come back via the PDF
        assert forbidden not in text
