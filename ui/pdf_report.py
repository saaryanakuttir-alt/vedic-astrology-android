"""
pdf_report.py - builds the PDF report for one profile. DETAILED: cover and birth details, panchang,
the birth chart, planet table, a good/mixed/needs-care verdict for every planet, doshas and Sade Sati,
planet friendships and aspects, all 14 divisional charts plus the Shodashvarga table, Chalit,
Ashtakvarga, the full Vimshottari table, the Medical Astrology body map and every reading. COMPACT: the
same opening, doshas at a glance and the short readings. Pure Python (no Kivy); text follows the
Compact / Detailed choice (ui/compact.py).

    data = build_pdf(chart, reading, style="North Indian", mode="detailed")   # -> bytes of a .pdf
"""
import datetime

import chart_geometry as cg
from astrology_tables import PLANET_ABBR, SIGN_ABBR, get_dignity
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
def document_text(reading, planet_glosses=True):
    """The readings in the same convention as the on-screen reports: '--- Heading ---' paragraphs
    followed by body paragraphs, separated by blank lines."""
    r, parts = reading, []

    if planet_glosses:
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


TINT = (0.96, 0.88, 0.72)          # shading for houses that hold a planet linked with strain (body map)
STRAIN = {"Su", "Ma", "Sa", "Ra", "Ke"}


def _draw_chart_at(pdf, chart, style, varga, x0, ytop, size, body=None):
    """One chart with its top-left corner at (x0, ytop). `varga` is 'D1', 'D9', ...; `body` is
    {house: short body-area name} for the Medical Astrology map (labels every house and shades
    the houses holding Sun, Mars, Saturn, Rahu or Ketu)."""
    sy = ytop - size
    fs = 8 if size >= 220 else 6.8
    asc = cg.ascendant_sign_for_varga(chart, varga)
    if style == "South Indian":
        cell = size / 4.0
        sign_planets = cg.build_sign_planet_map(chart, varga)
        for sign, (row, col) in cg.SOUTH_INDIAN_GRID.items():
            if body and any(n in STRAIN for n in sign_planets[sign]):
                pdf.rect(x0 + col * cell, sy + (3 - row) * cell, cell, cell, width=0, fill=TINT)
        for i in range(5):
            pdf.line(x0, sy + i * cell, x0 + size, sy + i * cell, width=0.8, color=GOLD)
            pdf.line(x0 + i * cell, sy, x0 + i * cell, sy + size, width=0.8, color=GOLD)
        for sign, (row, col) in cg.SOUTH_INDIAN_GRID.items():
            cx0, cy0 = x0 + col * cell, sy + (3 - row) * cell
            house = (SIGNS.index(sign) - SIGNS.index(asc)) % 12 + 1
            label = SIGN_ABBR.get(sign, sign[:3]) + (f" {house} {body.get(house, '')}" if body else "")
            pdf.text(cx0 + 3, cy0 + cell - fs - 1, label, size=fs - 1.3, color=MUTED)
            names = (["ASC"] if sign == asc else []) + sign_planets[sign]
            lines = _pairs(names)
            for n, line in enumerate(lines):
                pdf.text(cx0 + cell / 2 - text_width(line, fs, True) / 2,
                         cy0 + cell / 2 + (len(lines) - 1) * fs * 0.6 - n * (fs + 2) - 3, line, size=fs, bold=True)
        return
    house_planets = cg.build_house_planet_map(chart, varga)

    def pt(p):
        return x0 + p[0] * size, ytop - p[1] * size

    if body:
        for house, hd in cg.NORTH_INDIAN_HOUSES.items():
            if any(n in STRAIN for n in house_planets[house]):
                pdf.polygon([pt(v) for v in hd["polygon"]], TINT)
    for a, b in cg.NORTH_INDIAN_FRAME_LINES:
        (ax, ay), (bx, by) = pt(a), pt(b)
        pdf.line(ax, ay, bx, by, width=0.8, color=GOLD)
    sign_map = cg.north_indian_sign_map(asc)
    for house, hd in cg.NORTH_INDIAN_HOUSES.items():
        cen = cg.polygon_centroid(hd["polygon"])
        ov = hd["outer_vertex"]
        nx, ny = pt((ov[0] + (cen[0] - ov[0]) * 0.4, ov[1] + (cen[1] - ov[1]) * 0.4))
        num = str(SIGNS.index(sign_map[house]) + 1)
        pdf.text(nx - text_width(num, fs - 1.3) / 2, ny - 3, num, size=fs - 1.3, color=MUTED)
        cx, cy = pt(cen)
        names = (["ASC"] if house == 1 else []) + house_planets[house]
        lines = _pairs(names)
        if body:
            label = f"{house} {body.get(house, '')}".strip()
            pdf.text(cx - text_width(label, fs - 1.5) / 2, cy + (len(lines) * (fs + 2)) / 2 + 1, label, size=fs - 1.5, color=MUTED)
            cy -= 3
        for n, line in enumerate(lines):
            pdf.text(cx - text_width(line, fs, True) / 2, cy + (len(lines) - 1) * (fs + 2) / 2 - n * (fs + 2) - 3, line,
                     size=fs, bold=True)


def _draw_chart(doc, chart, style, size=250, varga="D1", body=None):
    doc.ensure(size + 12)
    x0 = MARGIN + (doc.width - size) / 2
    _draw_chart_at(doc.pdf, chart, style, varga, x0, doc.y, size, body)
    doc.y -= size + 10


def _pairs(names):
    """Planet abbreviations, one per line up to two, then two per line."""
    if len(names) <= 2:
        return list(names)
    return [" ".join(names[i:i + 2]) for i in range(0, len(names), 2)]


# ---------------------------------------------------------------- the extra sections
def _fmt_date(value):
    if isinstance(value, str):
        value = datetime.datetime.fromisoformat(value)
    return f"{value:%d %b %Y}"


def _heading_para(doc, text):
    """A block in the '--- Heading ---' convention: heading, then its paragraphs."""
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


def _kundli_facts(doc, chart):
    p, d, av = chart["panchang"], chart["day_details"], chart["avkahada_chakra"]
    pairs = [
        ("Weekday", chart["day_of_week"]), ("Tithi", f"{p['tithi']['name']} ({p['tithi']['paksha']} paksha)"),
        ("Yoga", p["yoga"]["name"]), ("Karana", p["karana"]["name"]),
        ("Sunrise / Sunset", f"{d['sunrise_local']} / {d['sunset_local']}"), ("Day length", d["day_duration"]),
        ("Ayanamsa (Lahiri)", f"{chart['resolved_datetime']['ayanamsa_value_deg']:.4f} deg"),
        ("Varna", av["varna"]), ("Vashya", av["vasya"]), ("Yoni", av["yoni"]), ("Gana", av["gana"]), ("Nadi", av["nadi"]),
    ]
    rows = []
    for i in range(0, len(pairs), 2):
        a, b = pairs[i], pairs[i + 1]
        rows.append([a[0], str(a[1]), b[0], str(b[1])])
    doc.heading("Panchang and birth classifications")
    doc.table(["Item", "Value", "Item", "Value"], rows, [90, 157, 90, 158])


def _age_span(r):
    a, b = f"{max(r['start_age'], 0):.0f}", f"{r['end_age']:.0f}"
    return a if a == b else f"{a} - {b}"


def _sade_sati_rows(rows):
    return [[r["kind"].split(" (")[0], r["phase"].replace("Saturn in the ", "Saturn "), r["sign"],
             f"{r['start']:%d %b %Y}", f"{r['end']:%d %b %Y}", _age_span(r)]
            for r in rows]


def _doshas_section(doc, chart, mode, ex):
    import extras
    if mode == "compact":
        doc.heading("Doshas at a glance")
        doc.table(["Dosha", "Verdict", "Status"], [[d["name"], d["tone"], d["status"]] for d in ex["doshas"]], [200, 90, 205])
        _heading_para(doc, compact_text(extras.sade_sati_detail_text(chart)))
        return
    _heading_para(doc, "--- Doshas and Sade Sati ---\nDoshas are classical 'watch points'. Each one below says whether it is present, "
                       "what it may mean, and what can help. They describe tendencies, not fixed fate - many people with a "
                       "dosha live very happily, and the rest of the chart matters more.")
    _heading_para(doc, extras.doshas_text(chart))
    _heading_para(doc, extras.sade_sati_detail_text(chart))
    doc.heading("Sade Sati and Dhaiya through your life")
    doc.paragraph("Sade Sati is Saturn's roughly 7.5-year walk over the sign before, the sign of and the sign after your Moon. "
                  "Dhaiya (Small Panoti) is its 2.5-year stay in the 4th or 8th sign from your Moon. These are times that test "
                  "patience and reward steady work - not fixed bad news. Saturn sometimes steps back into the earlier sign for a "
                  "few months, so a phase can appear twice. Dates are approximate (a day or two either way).")
    doc.table(["Type", "Phase", "Saturn in", "From", "To", "Age"], _sade_sati_rows(ex["sade_sati"]), [70, 130, 65, 78, 78, 74])


def _friend_and_aspect_section(doc, chart, ex):
    from astrology_tables import PLANET_ABBR
    code = {"Adhi Mitra": "++", "Mitra": "+", "Sama": "=", "Shatru": "-", "Adhi Shatru": "--",
            "friend": "+", "neutral": "=", "enemy": "-"}
    fr = ex["friendship"]
    seven = list(fr["compound"])
    doc.heading("Which planets get along")
    doc.paragraph("Each row shows how that planet feels about the planet in the column. Natural friendship is permanent; temporary "
                  "friendship depends on how close the planets sit in YOUR chart; the combined table joins the two. Key: ++ great "
                  "friend, + friend, = neutral, - enemy, -- great enemy. [In simple terms: it shows which planets help each other "
                  "in your chart and which tend to work against each other.]")
    for title, key in (("Natural friendship", "natural"), ("Temporary friendship (this chart)", "temporary"),
                       ("Combined (five-fold) friendship", "compound")):
        doc.paragraph(title, bold=True, color=GOLD)
        rows = [[a] + ["." if a == b else code[fr[key][a][b]] for b in seven] for a in seven]
        doc.table(["From"] + [PLANET_ABBR[p] for p in seven], rows, [59] + [62] * 7)
    doc.heading("Angles between the planets (Western-style aspects)")
    doc.paragraph("Conjunction (together) blends two planets, sextile and trine support each other, square and opposition pull "
                  "against each other. A smaller orb means a stronger link. [In simple terms: 'easy' pairs tend to help you, "
                  "'tense' pairs push you to act.]")
    rows = [[f"{a['a']} - {a['b']}", a["aspect"], f"{a['orb']:.1f}", a["flow"].capitalize(), a["meaning"]] for a in ex["aspects"]]
    doc.table(["Planets", "Angle", "Orb", "Feels", "What it means"], rows or [["None found", "", "", "", ""]], [90, 65, 35, 45, 260])


def _divisional_section(doc, chart, style, reading):
    import extras
    doc.heading("All divisional charts (Shodashvarga)")
    doc.paragraph("A divisional chart is a 'zoom-in' on one life area. Each is read like your main chart: see which sign every "
                  "planet falls in and whether it looks comfortable there. They add detail to the main chart and never override it.")
    size = 190
    entries = [e for e in extras.SHODASHVARGA if e[0] != "D1"]
    for i in range(0, len(entries), 2):
        doc.ensure(size + 36)
        top = doc.y
        for col, (key, name, purpose) in enumerate(entries[i:i + 2]):
            x0 = MARGIN + 27 + col * (size + 60)
            doc.pdf.text(x0, top - 10, f"{key} {name}", size=9.5, bold=True, color=GOLD)
            doc.pdf.text(x0, top - 21, purpose, size=7.5, color=MUTED)
            _draw_chart_at(doc.pdf, chart, style, key, x0, top - 28, size)
        doc.y = top - size - 36
    doc.heading("Shodashvarga table - the sign of every planet in every chart")
    head = ["Chart", "Asc"] + [PLANET_ABBR[p] for p in extras.BODIES]
    rows = []
    for r in extras.shodashvarga_table(chart):
        s = r["signs"]
        rows.append([f"{r['key']} {r['name']}", SIGN_ABBR[s["Lagna"]]] + [SIGN_ABBR[s[p]] for p in extras.BODIES])
    doc.table(head, rows, [115, 34] + [38.5] * 9)
    descs = (reading or {}).get("chart_descriptions") or {}
    parts = ["--- What each divisional chart tells you ---"]
    for key, name, purpose in extras.SHODASHVARGA:
        if key == "D1":
            continue
        cd = descs.get(key)
        parts.append(f"{key} {name} ({purpose}): " + ((cd.get("plain_explanation") or "").strip() if cd else
                     "a zoom-in on this area of life; read the sign of each planet here like in your main chart."))
    _heading_para(doc, "\n\n".join(parts))


def _chalit_ashtak_section(doc, chart):
    doc.heading("Bhava Chalit (house boundaries)")
    by_house = {i: [] for i in range(1, 13)}
    for planet, d in chart["planets"].items():
        if d.get("chalit_house"):
            by_house[d["chalit_house"]].append(PLANET_ABBR[planet])
    rows = [[str(r["bhava"]), f"{r['begin_sign']} {r['begin_degree_in_sign']:.1f}", f"{r['madhya_sign']} {r['madhya_degree_in_sign']:.1f}",
             ", ".join(by_house[r["bhava"]])] for r in chart["chalit"]]
    doc.table(["House", "Begins", "Midpoint", "Planets"], rows, [50, 150, 150, 145])
    doc.paragraph("[In simple terms: this is a finer map of where each house really starts and ends. If a planet sits close to a "
                  "boundary, its results may be felt in the neighbouring house too.]", size=9)
    doc.heading("Ashtakvarga (support points by sign)")
    doc.paragraph("Each planet scores every sign from 0 to 8 - higher means that sign supports the planet more. 'Total' adds every "
                  "planet's score for the sign. Signs with about 28 or more total points are usually the comfortable ones; "
                  "under 25 the sign tends to need more effort. [In simple terms: when a planet or a period passes through a "
                  "high-scoring sign, things tend to go easier; a low-scoring sign asks for more patience.]")
    avk = chart["ashtakavarga"]
    rows = []
    for planet in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        rows.append([planet] + [str(avk["bhinnashtakavarga"][planet][s]) for s in SIGNS])
    rows.append(["Total"] + [str(avk["sarvashtakavarga"][s]) for s in SIGNS])
    doc.table(["Planet"] + [s[:3] for s in SIGNS], rows, [55] + [36.7] * 12)


def _dasha_section(doc, chart):
    birth = datetime.datetime.fromisoformat(chart["resolved_datetime"]["utc"]).replace(tzinfo=None)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    doc.heading("Vimshottari Dasha - the planetary periods of your life")
    doc.paragraph("Life is divided into long periods (Mahadasha), each ruled by one planet, and each split into shorter "
                  "sub-periods (Antardasha). The ruling planet colours that time: a well-placed planet tends to bring its good "
                  "side, a stressed one may bring its lessons. [In simple terms: think of it as seasons of life - each planet's "
                  "season has its own mood, and the sub-period is the weather within it.] Dates are approximate (a few days "
                  "either way).")
    rows = []
    for m in chart["dasha"]["timeline"]:
        s, e = _naive(m["start"]), _naive(m["end"])
        rows.append([m["lord"] + (" (now)" if s <= now < e else ""), _fmt_date(s if s > birth else birth), _fmt_date(e),
                     f"{max((s - birth).days, 0) / 365.25:.0f} - {(e - birth).days / 365.25:.0f}"])
    doc.table(["Mahadasha", "From", "To", "Age"], rows, [150, 130, 130, 85])
    for m in chart["dasha"]["timeline"]:
        s, e = _naive(m["start"]), _naive(m["end"])
        doc.paragraph(f"{m['lord']} Mahadasha ({_fmt_date(max(s, birth))} to {_fmt_date(e)}) - sub-periods", bold=True, color=GOLD)
        ants = m["antardashas"]
        half = (len(ants) + 1) // 2
        rows = []
        for i in range(half):
            row = []
            for a in (ants[i], ants[i + half] if i + half < len(ants) else None):
                if a is None:
                    row += ["", "", ""]
                else:
                    row += [a["lord"] + (" (now)" if _naive(a["start"]) <= now < _naive(a["end"]) else ""),
                            _fmt_date(_naive(a["start"])), _fmt_date(_naive(a["end"]))]
            rows.append(row)
        doc.table(["Sub-period", "From", "To", "Sub-period", "From", "To"], rows, [70, 88, 88, 70, 88, 88], size=8)


def _naive(v):
    v = datetime.datetime.fromisoformat(v) if isinstance(v, str) else v
    return v.replace(tzinfo=None) if v.tzinfo else v



def _planet_effects_section(doc, chart, reading):
    import planet_effects
    doc.heading("Planet by planet - effects on your houses and signs")
    doc.paragraph("One block per planet: what its house does, what its sign does, how it gets on with the ruler of its sign, "
                  "any special conditions, what it rules and looks at, and a plain-words verdict. [In simple terms: read each block "
                  "as the story of one planet in your chart - good, mixed or needing care - with what may happen.]", size=9)
    for e in planet_effects.planet_effects(chart, reading):
        doc.ensure(90)
        doc.heading(e["banner"].replace("  -  ", " - "), size=12)
        for label, text in e["sections"]:
            doc.ensure(50)
            doc.paragraph(label, size=9.5, bold=True, color=GOLD)
            for para in text.split("\n\n"):
                if para.strip():
                    doc.paragraph(para.strip())


def _more_dashas_section(doc, chart, style):
    import more_dashas as md
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    _heading_para(doc, md.mahadasha_text(chart, now))
    doc.heading("Yogini Dasha (a 36-year cycle of eight periods)")
    doc.paragraph("[In simple terms: each 'yogini' colours a stretch of life - Mangala for good fortune, Pingala for effort, Dhanya "
                  "for money and comfort, Bhramari for change, Bhadrika for steady gains, Ulka for pressure, Siddha for achievement "
                  "and Sankata for obstacles that ask for patience. Dates are approximate, a couple of days either way.]", size=9)
    yog = md.yogini_dasha(chart)
    doc.table(["Yogini", "From", "To", "Years", "Feels like"],
              [[y["name"] + (" (now)" if y["start"] <= now < y["end"] else ""), _fmt_date(y["start"]), _fmt_date(y["end"]),
                str(y["years"]), md._YOGINI_MEANING[y["name"]]] for y in yog], [80, 75, 75, 35, 230])
    for y in yog[:6]:
        doc.paragraph(f"{y['name']} period - sub-periods", bold=True, color=GOLD, size=9.5)
        doc.table(["Sub-period", "From", "To"], [[a["name"], _fmt_date(a["start"]), _fmt_date(a["end"])] for a in y["antardashas"]],
                  [165, 165, 165], size=8)
    doc.heading("Char Dasha (Jaimini - periods of zodiac signs from your Lagna)")
    doc.paragraph("[In simple terms: instead of planets, each period belongs to a zodiac sign, starting with your rising sign. The "
                  "sign's house in your chart shows which area of life is in focus.]", size=9)
    chd = md.char_dasha(chart)
    doc.table(["Sign", "Years", "From", "To"], [[c["sign"] + (" (now)" if c["start"] <= now < c["end"] else ""), str(c["years"]),
                                                  _fmt_date(c["start"]), _fmt_date(c["end"])] for c in chd], [150, 60, 140, 145])
    for c in chd[:4]:
        doc.paragraph(f"{c['sign']} period - sub-periods", bold=True, color=GOLD, size=9.5)
        rows = []
        half = len(c["antardashas"]) // 2
        for i in range(half):
            a, b = c["antardashas"][i], c["antardashas"][i + half]
            rows.append([a["sign"], _fmt_date(a["start"]), _fmt_date(a["end"]), b["sign"], _fmt_date(b["start"]), _fmt_date(b["end"])])
        doc.table(["Sub-period", "From", "To", "Sub-period", "From", "To"], rows, [70, 88, 88, 70, 88, 88], size=8)
    doc.heading("Jaimini significators (Chara Karakas) and Karakamsa")
    doc.table(["Role", "Planet", "Stands for"], [[k["role"], k["chara"], k["meaning"]] for k in md.karakas(chart)], [130, 90, 275])
    doc.paragraph(md.karakamsa_text(chart))
    doc.ensure(280)
    doc.paragraph("Karakamsa chart (birth-chart planets counted from the Karakamsa sign)", bold=True, color=GOLD, size=9.5)
    _draw_chart(doc, md.with_karakamsa(chart), style, size=230, varga="KM")



def _nature_section(doc, chart, detailed):
    import life_profile
    text = life_profile.profile_text(chart)
    _heading_para(doc, "--- Your nature: character, career, learning and hobbies ---\nIn plain words, drawn from your rising sign, "
                       "Moon and the planets that rule these areas. These are tendencies, not rules.")
    _heading_para(doc, text if detailed else compact_text(text))


def _advanced_section(doc, chart, style):
    """Detailed PDF only: Varshaphal for the current year, KP tables, planet strength and Prastharashtakvarga."""
    import kp
    import prastara
    import shadbala
    import varshaphal
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    birth_year = int(chart["birth_input"]["birth_date"][:4])
    year = max(now.year if varshaphal.return_moment(chart, now.year) <= now else now.year - 1, birth_year + 1)
    vp = varshaphal.varshaphal(chart, year)
    doc.heading(f"Varshaphal - your year from {vp['local']:%d %b %Y} (age {vp['age']})")
    _heading_para(doc, varshaphal.varshaphal_text(vp))
    doc.table(["Period", "From", "To", "House", "Feels"], [[p["lord"], _fmt_date(p["start"]), _fmt_date(p["end"]), str(p["house"]), p["tone"]]
                                                         for p in vp["mudda"]], [90, 100, 100, 50, 155])
    doc.ensure(280)
    doc.paragraph("The yearly chart", bold=True, color=GOLD, size=9.5)
    _draw_chart(doc, vp["varsha"], style, size=230)

    sb = shadbala.compute_shadbala(chart)
    doc.heading("Planet strength")
    _heading_para(doc, shadbala.shadbala_text(chart))
    head = ["Source"] + [p[:3] for p in shadbala.SEVEN]
    rows = [[label.split(" (")[0]] + [f"{sb[p][key]:.0f}" for p in shadbala.SEVEN] for key, label in shadbala.COMPONENTS]
    rows.append(["Total"] + [f"{sb[p]['total']:.0f}" for p in shadbala.SEVEN])
    doc.table(head, rows, [125] + [52.8] * 7)
    doc.paragraph("Not counted: the year and month lords, planetary speed, aspect strength and planetary war. Read the scores as "
                  "comparisons between your own planets, not as the traditional 'rupa' totals.", size=8, color=MUTED)

    t = kp.kp_tables(chart)
    ab = lambda p: p[:3]
    doc.heading("KP system (Krishnamurti Paddhati)")
    doc.paragraph(f"Placidus houses with the KP ayanamsa ({t['ayanamsa_dms']}). The star lord shows the kind of result a house or planet is "
                  "linked to and the sub lord decides whether it is likely to come through. Positions can differ from the main chart by a "
                  "few arc-minutes, which may change a sub lord. [In simple terms: extra detail for KP astrologers, not a verdict.]", size=9)
    doc.table(["House", "Degree", "Sign lord", "Star", "Sub", "Sub-sub"],
              [[str(c["cusp"]), c["dms"], ab(c["sign_lord"]), ab(c["star_lord"]), ab(c["sub_lord"]), ab(c["subsub_lord"])] for c in t["cusps"]],
              [50, 110, 85, 80, 85, 85])
    doc.table(["Planet", "Degree", "House", "Sign lord", "Star", "Sub", "Sub-sub"],
              [[p["planet"][:3] + ("R" if p["retrograde"] else ""), p["dms"], str(p["house"]), ab(p["sign_lord"]), ab(p["star_lord"]),
                ab(p["sub_lord"]), ab(p["subsub_lord"])] for p in t["planets"]], [55, 110, 45, 75, 70, 70, 70])
    r = t["ruling"]
    doc.paragraph("Ruling planets - Lagna (sign, star, sub lord): " + ", ".join(r["Lagna"]) + ". Moon: " + ", ".join(r["Moon"]) +
                  f". Weekday lord: {r['Day lord']}.")
    doc.table(["House", "Signified by (strongest first)"], [[str(h), ", ".join(x[:3] for x in pl)] for h, pl in t["significators"].items()], [60, 435])

    doc.heading("Ashtakvarga detail (Prastharashtakvarga)")
    doc.paragraph("For each planet, who gives each point: 1 means that helper gives a point to the sign. The last row is the planet's usual "
                  "Ashtakvarga row.", size=9)
    for planet, grid in prastara.all_prastara(chart).items():
        doc.paragraph(planet, bold=True, color=GOLD, size=9.5)
        rows = [[c] + ["1" if v else "." for v in r_] for c, r_ in grid["rows"].items()]
        rows.append(["Total"] + [str(x) for x in grid["totals"]])
        doc.table(["From"] + [s[:3] for s in SIGNS], rows, [55] + [36.7] * 12, size=8)


# ---------------------------------------------------------------- the report
def build_pdf(chart, reading, style="North Indian", mode="detailed"):
    import extras
    name = chart.get("name") or "Birth chart"
    detailed = mode != "compact"
    doc = _Doc(f"Vedic Astrology report - {name}")
    pdf = doc.pdf
    ex = {"considerations": None, "friendship": None, "aspects": None, "doshas": extras.assess_doshas(chart),
          "sade_sati": None}
    if detailed:
        ex.update(friendship=extras.friendship_tables(chart), aspects=extras.western_aspects(chart),
                  sade_sati=extras.sade_sati_table(chart))

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
    doc.paragraph("How to read this report: every section says whether something looks good, mixed or in need of care, what may "
                  "happen because of it, and what usually helps. These are tendencies drawn from traditional Vedic astrology - "
                  "never fixed results - and your own choices and effort matter more than any chart.", size=9, color=MUTED)

    if detailed:
        _kundli_facts(doc, chart)

    doc.heading(f"Birth chart (D1) - {style}")
    _draw_chart(doc, chart, style)

    doc.heading("Planet positions")
    rows = []
    for planet, d in chart["planets"].items():
        rows.append([planet + (" (R)" if d.get("retrograde") else ""), d["sign"], f"{d['degree_in_sign']:.2f}",
                     str(d["house"]), d["nakshatra"], str(d["nakshatra_pada"]), get_dignity(planet, d["sign"])])
    doc.table(["Planet", "Sign", "Deg", "House", "Nakshatra", "Pada", "Dignity"], rows,
              [58, 62, 38, 36, 82, 32, 187])

    _nature_section(doc, chart, detailed)
    for block in (extras.period_text(chart), extras.houses_text(chart)):
        if block:
            _heading_para(doc, block if detailed else compact_text(block))
    planets_text = extras.planet_considerations_text(chart)
    if detailed:
        _planet_effects_section(doc, chart, reading)
    else:
        _heading_para(doc, "--- Planet by planet: good, mixed or needs care? ---\nFor each planet: how well it is placed in your "
                           "chart and what that may mean for you.")
        _heading_para(doc, compact_text(planets_text))
    _doshas_section(doc, chart, mode, ex)

    if detailed:
        _friend_and_aspect_section(doc, chart, ex)
        _divisional_section(doc, chart, style, reading)
        _chalit_ashtak_section(doc, chart)
        _dasha_section(doc, chart)
        _more_dashas_section(doc, chart, style)
        _advanced_section(doc, chart, style)

    text = document_text(reading, planet_glosses=not detailed)
    if not detailed:
        text = compact_text(text)
    medical = (reading or {}).get("medical_astrology")
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        lines = para.split("\n")
        if lines[0].startswith(("---", "===")):
            heading = lines[0].strip("-= ").strip()
            if heading.startswith("Medical Astrology") and medical:
                doc.ensure(330)
                doc.heading("Medical Astrology - body map")
                doc.paragraph("Each house stands for a part of the body, from the head (house 1) to the feet (house 12). Shaded "
                              "houses hold a planet that classical texts link with strain (Sun, Mars, Saturn, Rahu, Ketu). "
                              "[In simple terms: a symbolic map of where astrology says to take a little extra care - not a "
                              "scan, and nothing on it means something is wrong.]", size=9)
                _draw_chart(doc, chart, style, size=260, body={a["house"]: a["short"] for a in medical["body_areas"]})
            doc.heading(heading)
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
