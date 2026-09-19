"""
pdf_report.py - builds the PDF report for one profile: cover page with the birth details, the
chart diagram (drawn as vector lines), the planet table, then the readings. Pure Python (no Kivy);
the readings follow the Compact / Detailed choice (ui/compact.py).

    data = build_pdf(chart, reading, style="North Indian", mode="detailed")   # -> bytes of a .pdf
"""
import datetime

import chart_geometry as cg
from astrology_tables import SIGN_ABBR, get_dignity
from panchanga import SIGNS
from ui.compact import compact_text
from ui.pdf_writer import PAGE_H, PAGE_W, Pdf, text_width, wrap

CREDIT = "Created by Sammya Das"
MARGIN = 50
BODY = 10.0
LEAD = 13.5
GOLD = (0.71, 0.51, 0.21)
INK = (0.13, 0.12, 0.11)
MUTED = (0.45, 0.44, 0.43)


# ---------------------------------------------------------------- the text of the report
def document_text(reading):
    """The readings in the same convention as the on-screen reports: '--- Heading ---' paragraphs
    followed by body paragraphs, separated by blank lines."""
    r, parts = reading, []

    parts.append("--- What each planet means ---")
    for planet, detail in r["planets"].items():
        gloss = detail.get("plain_gloss")
        if gloss:
            parts.append(gloss)

    parts.append("--- Yogas in this chart ---")
    if r.get("yogas_plain_summary"):
        parts.append(r["yogas_plain_summary"])
    present = [y for y in r.get("yogas", []) if y.get("present")]
    for y in present:
        parts.append(f"{y['name']}: {y['details']}")
    if not present:
        parts.append("None of the 24 classical yogas checked are formed in this chart.")

    running = r["dasha"]["running_at_birth"]
    parts.append(f"--- Planetary period running at birth: {running['mahadasha_lord']} / {running['antardasha_lord']} ---")
    if running.get("mahadasha_reading"):
        parts.append(running["mahadasha_reading"]["general_effects"])
    if running.get("antardasha_reading"):
        parts.append(running["antardasha_reading"]["summary"])

    lp = r["life_predictions"]
    parts.append("--- Life areas ---")
    parts.append(lp["caveat"])
    for entry in lp.values():
        if isinstance(entry, dict) and entry.get("title"):
            parts.append(f"--- {entry['title']} ---")
            parts.append(entry.get("text") or "(not enough data to describe this area for this chart)")

    k = r["karmic_and_past_life"]
    parts.append("--- Karmic & Past Life (a symbolic lens) ---")
    parts.append(k["caveat"])
    parts.append(k["soul_narrative"])

    m = r.get("medical_astrology")
    if m:
        parts.append("--- Medical Astrology (symbolic, not medical advice) ---")
        parts.append(m["caveat"])
        parts.append(m["text"])

    rel = r.get("relationship_themes")
    if rel:
        parts.append("--- Relationship Themes ---")
        parts.append(rel["caveat"])
        if rel.get("plain_summary"):
            parts.append(rel["plain_summary"])
        if rel.get("deep_discussion"):
            parts.append(rel["deep_discussion"])
    return "\n\n".join(p for p in parts if p and p.strip())


# ---------------------------------------------------------------- drawing helpers
class _Doc:
    """Flowing layout on top of Pdf: a cursor, page breaks, wrapped paragraphs."""

    def __init__(self, title):
        self.pdf = Pdf(title=title, author="Vedic Astrology app")
        self.pdf.new_page()
        self.y = PAGE_H - MARGIN
        self.width = PAGE_W - 2 * MARGIN

    def ensure(self, needed):
        if self.y - needed < MARGIN + 18:
            self.pdf.new_page()
            self.y = PAGE_H - MARGIN

    def heading(self, text, size=13):
        self.ensure(size + 40)
        self.y -= 10
        self.pdf.text(MARGIN, self.y - size, text, size=size, bold=True, color=GOLD)
        self.y -= size + 4
        self.pdf.line(MARGIN, self.y, MARGIN + self.width, self.y, width=0.5, color=GOLD)
        self.y -= 8

    def paragraph(self, text, size=BODY, bold=False, color=INK, indent=0):
        lines = wrap(text, size, self.width - indent, bold)
        lead = size * 1.36
        for i, line in enumerate(lines):
            self.ensure(lead * min(len(lines) - i, 2))     # avoid a single stranded line
            self.y -= lead
            if line:
                self.pdf.text(MARGIN + indent, self.y, line, size=size, bold=bold, color=color)
        self.y -= lead * 0.55

    def table(self, headers, rows, widths, size=8.5):
        pad = 3
        heights = []
        for row in [headers] + rows:
            cells = [wrap(str(c), size, w - 2 * pad) for c, w in zip(row, widths)]
            heights.append(max(len(c) for c in cells) * (size + 2) + 2 * pad)
        for idx, row in enumerate([headers] + rows):
            self.ensure(heights[idx])
            top = self.y
            x = MARGIN
            if idx == 0:
                self.pdf.rect(MARGIN, top - heights[idx], sum(widths), heights[idx], width=0, fill=(0.93, 0.92, 0.9))
            for cell, w in zip(row, widths):
                for n, line in enumerate(wrap(str(cell), size, w - 2 * pad)):
                    self.pdf.text(x + pad, top - pad - (n + 1) * (size + 2) + 2, line, size=size,
                                  bold=(idx == 0), color=GOLD if idx == 0 else INK)
                x += w
            self.y -= heights[idx]
            self.pdf.line(MARGIN, self.y, MARGIN + sum(widths), self.y, width=0.3, color=(0.8, 0.79, 0.77))
        self.y -= 8


def _draw_chart(doc, chart, style, size=250):
    pdf = doc.pdf
    x0 = MARGIN + (doc.width - size) / 2
    ytop = doc.y
    sy = ytop - size
    house_planets = cg.build_house_planet_map(chart, "D1")
    if style == "South Indian":
        cell = size / 4.0
        for i in range(5):
            pdf.line(x0, sy + i * cell, x0 + size, sy + i * cell, width=0.8, color=GOLD)
            pdf.line(x0 + i * cell, sy, x0 + i * cell, sy + size, width=0.8, color=GOLD)
        sign_planets = cg.build_sign_planet_map(chart, "D1")
        asc = chart["ascendant"]["sign"]
        for sign, (row, col) in cg.SOUTH_INDIAN_GRID.items():
            cx0, cy0 = x0 + col * cell, sy + (3 - row) * cell
            pdf.text(cx0 + 3, cy0 + cell - 9, SIGN_ABBR.get(sign, sign[:3]), size=6.5, color=MUTED)
            names = (["ASC"] if sign == asc else []) + sign_planets[sign]
            for n, line in enumerate(_pairs(names)):
                pdf.text(cx0 + cell / 2 - text_width(line, 8, True) / 2, cy0 + cell / 2 + 6 - n * 10, line, size=8, bold=True)
    else:
        def pt(p):
            return x0 + p[0] * size, ytop - p[1] * size
        for a, b in cg.NORTH_INDIAN_FRAME_LINES:
            (ax, ay), (bx, by) = pt(a), pt(b)
            pdf.line(ax, ay, bx, by, width=0.8, color=GOLD)
        sign_map = cg.north_indian_sign_map(chart["ascendant"]["sign"])
        for house, hd in cg.NORTH_INDIAN_HOUSES.items():
            cen = cg.polygon_centroid(hd["polygon"])
            ov = hd["outer_vertex"]
            nx, ny = pt((ov[0] + (cen[0] - ov[0]) * 0.4, ov[1] + (cen[1] - ov[1]) * 0.4))
            num = str(SIGNS.index(sign_map[house]) + 1)
            pdf.text(nx - text_width(num, 6.5) / 2, ny - 3, num, size=6.5, color=MUTED)
            cx, cy = pt(cen)
            names = (["ASC"] if house == 1 else []) + house_planets[house]
            lines = _pairs(names)
            for n, line in enumerate(lines):
                pdf.text(cx - text_width(line, 8, True) / 2, cy + (len(lines) - 1) * 5 - n * 10 - 3, line, size=8, bold=True)
    doc.y = sy - 10


def _pairs(names):
    """Planet abbreviations, one per line up to two, then two per line."""
    if len(names) <= 2:
        return list(names)
    return [" ".join(names[i:i + 2]) for i in range(0, len(names), 2)]


# ---------------------------------------------------------------- the report
def build_pdf(chart, reading, style="North Indian", mode="detailed"):
    name = chart.get("name") or "Birth chart"
    doc = _Doc(f"Vedic Astrology report - {name}")
    pdf = doc.pdf

    doc.y -= 6
    pdf.text(MARGIN, doc.y - 22, "Vedic Astrology Report", size=22, bold=True, color=GOLD)
    doc.y -= 30
    pdf.text(MARGIN, doc.y - 16, name, size=16, bold=True, color=INK)
    doc.y -= 22
    pdf.text(MARGIN, doc.y - 10, f"Prepared {datetime.date.today():%d %B %Y}   -   "
             f"{'Compact' if mode == 'compact' else 'Detailed'} reading", size=9, color=MUTED)
    doc.y -= 24

    bi, loc = chart["birth_input"], chart["resolved_location"]
    moon, sun = chart["planets"]["Moon"], chart["planets"]["Sun"]
    facts = [
        ("Date of birth", str(bi["birth_date"])), ("Time of birth", str(bi["birth_time_local"])),
        ("Place of birth", bi["place_name"] or "(exact coordinates entered)"),
        ("Latitude / Longitude", f"{loc['latitude']:.4f}, {loc['longitude']:.4f}"),
        ("Time zone", loc["tz_name"]),
        ("Ascendant (Lagna)", f"{chart['ascendant']['sign']} {chart['ascendant']['degree_in_sign']:.2f} deg"),
        ("Moon sign / Nakshatra", f"{moon['sign']} / {moon['nakshatra']} (pada {moon['nakshatra_pada']})"),
        ("Sun sign (sidereal)", sun["sign"]),
    ]
    for label, value in facts:
        pdf.text(MARGIN, doc.y - 10, label, size=9, bold=True, color=MUTED)
        pdf.text(MARGIN + 130, doc.y - 10, value, size=9.5, color=INK)
        doc.y -= 14
    doc.y -= 8

    doc.heading(f"Birth chart (D1) - {style}")
    _draw_chart(doc, chart, style)

    doc.heading("Planet positions")
    rows = []
    for planet, d in chart["planets"].items():
        rows.append([planet + (" (R)" if d.get("retrograde") else ""), d["sign"], f"{d['degree_in_sign']:.2f}",
                     str(d["house"]), d["nakshatra"], str(d["nakshatra_pada"]), get_dignity(planet, d["sign"])])
    doc.table(["Planet", "Sign", "Deg", "House", "Nakshatra", "Pada", "Dignity"], rows,
              [58, 62, 38, 36, 82, 32, 187])

    text = document_text(reading)
    if mode == "compact":
        text = compact_text(text)
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        lines = para.split("\n")
        if lines[0].startswith(("---", "===")):
            doc.heading(lines[0].strip("-= ").strip())
            para = "\n".join(lines[1:]).strip()
            if not para:
                continue
        doc.paragraph(para)

    doc.paragraph("This report is based on traditional Vedic astrology. It describes classical tendencies, not "
                  "certainties, and is not medical, legal or financial advice.", size=8, color=MUTED)

    # footers, now that the page count is known
    total = len(pdf.pages)
    for n, ops in enumerate(pdf.pages, start=1):
        pdf._ops = ops
        pdf.line(MARGIN, MARGIN - 6, PAGE_W - MARGIN, MARGIN - 6, width=0.3, color=(0.8, 0.79, 0.77))
        pdf.text(MARGIN, MARGIN - 18, f"Vedic Astrology  -  {CREDIT}", size=7.5, color=MUTED)
        label = f"Page {n} of {total}"
        pdf.text(PAGE_W - MARGIN - text_width(label, 7.5), MARGIN - 18, label, size=7.5, color=MUTED)
    return pdf.output()


def safe_filename(name):
    keep = "".join(c if c.isalnum() else "_" for c in (name or "chart")).strip("_") or "chart"
    return f"VedicReport_{keep}_{datetime.date.today():%Y%m%d}.pdf"
