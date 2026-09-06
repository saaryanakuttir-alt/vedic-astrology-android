"""
rule_engine.py — joins a computed birth chart (from birth_chart.py) against
this project's knowledge-base JSON files (bundled in kb/) to produce a full,
readable chart interpretation.

This is the "core feature" module: birth_chart.py answers WHAT is placed
where; yogas.py answers WHICH classical combinations are formed; this module
answers WHAT IT MEANS, by looking up the right pre-written KB entry for
every computed fact using the exact ID conventions the KB files themselves
use:

    planet_in_sign            PS-{PlanetAbbr}-{SignAbbr}       e.g. PS-Su-Ari
    planet_in_house            PH-{PlanetAbbr}-H{house}         e.g. PH-Su-H1
    house_lord_placement       HL-{lord_house}-in-{placed_house} e.g. HL-1-in-1
    vimshottari_mahadasha      MD-{PlanetAbbr}                  e.g. MD-Su
    vimshottari_antardasha     AD-{MahaAbbr}-{AntarAbbr}         e.g. AD-Su-Mo
    divisional_charts          DIV-{Varga}                      e.g. DIV-D9
    divisional_*_planet_in_sign D{n}-PS-{PlanetAbbr}-{SignAbbr}  e.g. D9-PS-Su-Ari
    classical_yogas            YOGA-01 .. YOGA-24 (fixed IDs, from yogas.py)

USAGE:
    from birth_chart import compute_birth_chart
    from rule_engine import generate_reading

    chart = compute_birth_chart(...)
    reading = generate_reading(chart)
"""
import json
import os

import chara_karaka
from astrology_tables import PLANET_ABBR, SIGN_ABBR, SIGN_LORD
from yogas import detect_all_yogas

_CLASSICAL_SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

KB_DIR = os.path.join(os.path.dirname(__file__), "kb")

# All 19 bundled KB files, keyed by the same name rule_engine uses internally.
_KB_FILENAMES = {
    "planet_in_sign": "planet_in_sign.json",
    "planet_in_house": "planet_in_house.json",
    "house_lord_placement": "house_lord_placement.json",
    "classical_yogas": "classical_yogas.json",
    "vimshottari_mahadasha": "vimshottari_mahadasha.json",
    "vimshottari_antardasha": "vimshottari_antardasha.json",
    "divisional_charts": "divisional_charts.json",
    "divisional_D2_planet_in_sign": "divisional_D2_planet_in_sign.json",
    "divisional_D3_planet_in_sign": "divisional_D3_planet_in_sign.json",
    "divisional_D4_planet_in_sign": "divisional_D4_planet_in_sign.json",
    "divisional_D7_planet_in_sign": "divisional_D7_planet_in_sign.json",
    "divisional_D9_planet_in_sign": "divisional_D9_planet_in_sign.json",
    "divisional_D10_planet_in_sign": "divisional_D10_planet_in_sign.json",
    "divisional_D12_planet_in_sign": "divisional_D12_planet_in_sign.json",
    "divisional_D16_planet_in_sign": "divisional_D16_planet_in_sign.json",
    "divisional_D20_planet_in_sign": "divisional_D20_planet_in_sign.json",
    "divisional_D24_planet_in_sign": "divisional_D24_planet_in_sign.json",
    "divisional_D30_planet_in_sign": "divisional_D30_planet_in_sign.json",
    "divisional_D60_planet_in_sign": "divisional_D60_planet_in_sign.json",
}

DIVISIONAL_VARGAS = [2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 30, 60]

_cache = {}


def _load(kb_name):
    """Loads (and caches) one KB file, returning {id: item} for O(1) lookup."""
    if kb_name in _cache:
        return _cache[kb_name]
    path = os.path.join(KB_DIR, _KB_FILENAMES[kb_name])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    by_id = {item["id"]: item for item in data["items"]}
    _cache[kb_name] = by_id
    return by_id


def load_all_kb():
    """Eagerly loads every bundled KB file (useful to fail fast if kb/ is
    missing or a file is malformed, e.g. right after packaging a release)."""
    return {name: _load(name) for name in _KB_FILENAMES}


# ---------------------------------------------------------------------------
# ID builders — the single source of truth for every lookup key convention.
# ---------------------------------------------------------------------------
def planet_in_sign_id(planet, sign):
    return f"PS-{PLANET_ABBR[planet]}-{SIGN_ABBR[sign]}"


def planet_in_house_id(planet, house):
    return f"PH-{PLANET_ABBR[planet]}-H{house}"


def house_lord_id(lord_of_house, placed_in_house):
    return f"HL-{lord_of_house}-in-{placed_in_house}"


def mahadasha_id(planet):
    return f"MD-{PLANET_ABBR[planet]}"


def antardasha_id(maha_planet, antar_planet):
    return f"AD-{PLANET_ABBR[maha_planet]}-{PLANET_ABBR[antar_planet]}"


def divisional_chart_id(varga_number):
    return f"DIV-D{varga_number}"


def divisional_planet_in_sign_id(varga_number, planet, sign):
    return f"D{varga_number}-PS-{PLANET_ABBR[planet]}-{SIGN_ABBR[sign]}"


# ---------------------------------------------------------------------------
# Lookup helpers (return None + note a miss rather than raising, since a
# missing KB entry should degrade gracefully, not crash a chart reading).
# ---------------------------------------------------------------------------
def _lookup(kb_name, item_id, warnings):
    item = _load(kb_name).get(item_id)
    if item is None:
        warnings.append(f"No '{kb_name}' entry found for id '{item_id}'.")
    return item


def _planet_reading(chart, planet, warnings):
    detail = chart["planets"][planet]
    sign, house = detail["sign"], detail["house"]

    reading = {
        "sign": sign,
        "house": house,
        "nakshatra": detail["nakshatra"],
        "nakshatra_pada": detail["nakshatra_pada"],
        "in_sign": _lookup("planet_in_sign", planet_in_sign_id(planet, sign), warnings),
        "in_house": _lookup("planet_in_house", planet_in_house_id(planet, house), warnings),
        "vargas": {},
    }
    for n in DIVISIONAL_VARGAS:
        varga_sign = detail["vargas"].get(f"D{n}")
        if varga_sign is None:
            continue
        kb_name = f"divisional_D{n}_planet_in_sign"
        entry = _lookup(kb_name, divisional_planet_in_sign_id(n, planet, varga_sign), warnings)
        reading["vargas"][f"D{n}"] = {"sign": varga_sign, "reading": entry}
    return reading


def _house_lord_readings(chart, warnings):
    houses = chart["houses"]
    readings = {}
    for house_num in range(1, 13):
        sign = houses.get(house_num, houses.get(str(house_num)))
        lord = SIGN_LORD[sign]
        placed_in = chart["planets"][lord]["house"]
        readings[house_num] = {
            "lord": lord,
            "lord_sign": sign,
            "placed_in_house": placed_in,
            "reading": _lookup("house_lord_placement", house_lord_id(house_num, placed_in), warnings),
        }
    return readings


def _yoga_readings(chart, warnings):
    detected = detect_all_yogas(chart)
    yogas_kb = _load("classical_yogas")
    readings = []
    for result in detected:
        kb_entry = yogas_kb.get(result["id"])
        if kb_entry is None:
            warnings.append(f"No 'classical_yogas' entry found for id '{result['id']}'.")
        readings.append({
            "id": result["id"],
            "name": kb_entry["name"] if kb_entry else result["id"],
            "present": result["present"],
            "details": result["details"],
            "kb_entry": kb_entry,
        })
    return readings


def _dasha_readings(chart, warnings):
    running = chart["dasha"]["running_at_birth"]
    maha_reading, antar_reading = None, None
    if running:
        maha_reading = _lookup("vimshottari_mahadasha", mahadasha_id(running["mahadasha_lord"]), warnings)
        antar_reading = _lookup(
            "vimshottari_antardasha",
            antardasha_id(running["mahadasha_lord"], running["antardasha_lord"]),
            warnings,
        )

    timeline_readings = []
    for maha in chart["dasha"]["timeline"]:
        maha_entry = _lookup("vimshottari_mahadasha", mahadasha_id(maha["lord"]), warnings)
        antardashas = []
        for antar in maha["antardashas"]:
            antar_entry = _lookup("vimshottari_antardasha", antardasha_id(maha["lord"], antar["lord"]), warnings)
            antardashas.append({
                "lord": antar["lord"], "start": antar["start"], "end": antar["end"], "reading": antar_entry,
            })
        timeline_readings.append({
            "lord": maha["lord"], "start": maha["start"], "end": maha["end"],
            "is_partial_at_birth": maha["is_partial_at_birth"],
            "reading": maha_entry, "antardashas": antardashas,
        })

    return {
        "running_at_birth": {
            "mahadasha_lord": running["mahadasha_lord"] if running else None,
            "antardasha_lord": running["antardasha_lord"] if running else None,
            "mahadasha_reading": maha_reading,
            "antardasha_reading": antar_reading,
        },
        "timeline": timeline_readings,
    }


def _divisional_chart_overviews(warnings):
    return {f"D{n}": _lookup("divisional_charts", divisional_chart_id(n), warnings) for n in DIVISIONAL_VARGAS}


# ---------------------------------------------------------------------------
# Karmic & Past-Life section
# ---------------------------------------------------------------------------
# IMPORTANT — read before trusting this as more than it is: "karmic and
# past-life analysis" has no single agreed classical formula the way, say,
# a planet's house placement does. What follows uses the significators most
# consistently cited across classical/traditional sources for this specific
# lens — Ketu (past-life imprint/mastery), Rahu (this-life karmic direction),
# the 5th house (Purva Punya, "past-life merit"), the 9th house (Dharma,
# fortune, higher purpose), the 12th house (Moksha, endings, past
# attachments), Saturn (karma-karaka, consequences of past action), and the
# Jaimini Atmakaraka/Darakaraka/Putrakaraka (see chara_karaka.py — a real,
# independently well-established classical ranking technique, not invented
# for this purpose) — and assembles them from THIS PROJECT'S OWN
# already-verified KB content (the exact same planet_in_house /
# planet_in_sign / house_lord_placement entries the rest of a reading
# already draws on, not a new or separately invented interpretive layer).
# It is presented as a traditional lens for reflection, not a definitive or
# unique reading, and NOT a factual claim about a literal past incarnation
# — a different astrologer or text may reasonably weight these
# significators differently, or add others. No specific past-life
# identity, era, or occupation is asserted; only the SYMBOLIC theme classical
# texts associate with each significator.
_KARMIC_CAVEAT = (
    "Karmic/past-life analysis has no single agreed classical formula, and none of what "
    "follows is a factual claim about a literal past incarnation. This section reuses this "
    "project's own verified planet, house-lord, and Chara Karaka (Jaimini) readings — Ketu, "
    "Rahu, Saturn, the 5th/9th/12th houses, and the Atmakaraka/Darakaraka/Putrakaraka "
    "significators — the combination most consistently cited for this lens across classical "
    "and traditional sources — and presents them together as a traditional, symbolic "
    "perspective for reflection, not a unique, definitive, or literal reading."
)


def _significator_snapshot(planet, planets_reading):
    r = planets_reading[planet]
    return {
        "planet": planet,
        "sign": r["sign"],
        "house": r["house"],
        "nakshatra": r["nakshatra"],
        "nakshatra_pada": r["nakshatra_pada"],
        "in_sign_summary": r["in_sign"]["summary"] if r["in_sign"] else None,
        "in_sign_effects": r["in_sign"]["effects"] if r["in_sign"] else None,
        "in_house_summary": r["in_house"]["summary"] if r["in_house"] else None,
        "in_house_effects": r["in_house"]["effects"] if r["in_house"] else None,
        "dignity_note": r["in_house"].get("dignity_note") if r["in_house"] else None,
    }


def _house_significator_snapshot(house_num, role, house_lords):
    hl = house_lords[house_num]
    return {
        "house": house_num,
        "role": role,
        "lord": hl["lord"],
        "lord_sign": hl["lord_sign"],
        "placed_in_house": hl["placed_in_house"],
        "summary": hl["reading"]["summary"] if hl["reading"] else None,
        "effects": hl["reading"]["effects"] if hl["reading"] else None,
    }


def _compute_chara_karakas(chart):
    degrees = {p: chart["planets"][p]["degree_in_sign"] for p in _CLASSICAL_SEVEN}
    return chara_karaka.compute_chara_karakas(degrees)


def _karaka_snapshot(karakas, abbr, planets_reading):
    entry = chara_karaka.get_karaka(karakas, abbr)
    planet_snap = _significator_snapshot(entry["planet"], planets_reading)
    return {**entry, **planet_snap}


def _build_karmic_and_past_life(chart, planets_reading, house_lords, karakas):
    ketu = _significator_snapshot("Ketu", planets_reading)
    rahu = _significator_snapshot("Rahu", planets_reading)
    saturn = _significator_snapshot("Saturn", planets_reading)
    purva_punya = _house_significator_snapshot(5, "Purva Punya (past-life merit)", house_lords)
    dharma = _house_significator_snapshot(9, "Dharma (fortune / higher purpose)", house_lords)
    moksha = _house_significator_snapshot(12, "Moksha (endings / past attachments)", house_lords)
    atmakaraka = _karaka_snapshot(karakas, "AK", planets_reading)
    darakaraka = _karaka_snapshot(karakas, "DK", planets_reading)
    putrakaraka = _karaka_snapshot(karakas, "PK", planets_reading)

    paragraphs = []

    # --- Paragraph 1: the soul's core nature (Atmakaraka) ---
    ak_text = (
        f"In Jaimini astrology, the planet holding the highest degree among the seven classical "
        f"grahas is the Atmakaraka — literally the 'significator of the soul' — read as the "
        f"planet whose themes the soul itself is most identified with in this incarnation. Here "
        f"that planet is {atmakaraka['planet']}, placed in {atmakaraka['sign']} in house "
        f"{atmakaraka['house']} ({atmakaraka['nakshatra']} nakshatra, pada {atmakaraka['nakshatra_pada']})."
    )
    if atmakaraka.get("in_sign_effects"):
        ak_text += f" By sign, this classically reads as: {atmakaraka['in_sign_effects']}"
    if atmakaraka.get("in_house_effects"):
        ak_text += f" By house, its themes play out through the domain it occupies: {atmakaraka['in_house_effects']}"
    if atmakaraka.get("dignity_note"):
        ak_text += f" {atmakaraka['dignity_note']}"
    ak_text += (
        " Traditionally, whatever this planet governs is treated as the soul's central "
        "preoccupation across lifetimes — the quality it keeps returning to develop, express, "
        "or master — rather than a peripheral trait."
    )
    paragraphs.append(ak_text)

    # --- Paragraph 2: what was carried forward (Ketu) ---
    if ketu.get("in_house_effects") or ketu.get("in_sign_effects"):
        ketu_text = (
            f"Ketu is the classical significator of past-life imprint — skills, instincts, and "
            f"unfinished business already carried into this birth, experienced less as something "
            f"learned and more as something simply KNOWN. It sits in {ketu['sign']} in house "
            f"{ketu['house']} ({ketu['nakshatra']} nakshatra)."
        )
        if ketu.get("in_sign_effects"):
            ketu_text += f" {ketu['in_sign_effects']}"
        if ketu.get("in_house_effects"):
            ketu_text += f" In the domain of house {ketu['house']} specifically: {ketu['in_house_effects']}"
        ketu_text += (
            " Classically, a strong or prominent Ketu placement often shows up as an area where "
            "the native feels an odd, hard-to-explain fluency or detachment — as if this "
            "particular ground has already been covered before."
        )
        paragraphs.append(ketu_text)

    # --- Paragraph 3: the direction of growth (Rahu) ---
    if rahu.get("in_house_effects") or rahu.get("in_sign_effects"):
        rahu_text = (
            f"Rahu sits opposite Ketu by definition and is read as the direction this life's "
            f"karmic growth pulls toward — unfamiliar territory the soul is drawn to reach for, "
            f"often with more hunger than comfort at first. It is placed in {rahu['sign']} in "
            f"house {rahu['house']} ({rahu['nakshatra']} nakshatra)."
        )
        if rahu.get("in_sign_effects"):
            rahu_text += f" {rahu['in_sign_effects']}"
        if rahu.get("in_house_effects"):
            rahu_text += f" In the domain of house {rahu['house']}: {rahu['in_house_effects']}"
        rahu_text += (
            " Where Ketu describes what already feels familiar, Rahu describes what this "
            "incarnation is reaching to build — often the area of greatest ambition, "
            "restlessness, and eventual growth once its excesses are tempered by experience."
        )
        paragraphs.append(rahu_text)

    # --- Paragraph 4: karma and consequence (Saturn) ---
    if saturn.get("in_house_effects") or saturn.get("in_sign_effects"):
        saturn_text = (
            f"Saturn is the classical karaka for karma itself — structure, discipline, delay, "
            f"and the working-out of consequence over time. It sits in {saturn['sign']} in house "
            f"{saturn['house']} ({saturn['nakshatra']} nakshatra)."
        )
        if saturn.get("in_sign_effects"):
            saturn_text += f" {saturn['in_sign_effects']}"
        if saturn.get("in_house_effects"):
            saturn_text += f" In that house's domain: {saturn['in_house_effects']}"
        saturn_text += (
            " Saturn's placement is traditionally read as showing exactly where patience, "
            "responsibility, and the slow, unglamorous accumulation of effort become the "
            "vehicle through which karma is actually resolved rather than merely felt."
        )
        paragraphs.append(saturn_text)

    # --- Paragraph 5: life's higher purpose (5th/9th/12th houses) ---
    purpose_bits = []
    if purva_punya.get("summary"):
        purpose_bits.append(
            f"The 5th house — Purva Punya, the storehouse of past-life merit — is ruled by "
            f"{purva_punya['lord']} (in {purva_punya['lord_sign']}), placed in house "
            f"{purva_punya['placed_in_house']}: {purva_punya.get('effects') or purva_punya['summary']}"
        )
    if dharma.get("summary"):
        purpose_bits.append(
            f"The 9th house — Dharma, higher purpose and fortune — is ruled by {dharma['lord']} "
            f"(in {dharma['lord_sign']}), placed in house {dharma['placed_in_house']}: "
            f"{dharma.get('effects') or dharma['summary']}"
        )
    if moksha.get("summary"):
        purpose_bits.append(
            f"The 12th house — Moksha, release and the letting-go of past attachments — is "
            f"ruled by {moksha['lord']} (in {moksha['lord_sign']}), placed in house "
            f"{moksha['placed_in_house']}: {moksha.get('effects') or moksha['summary']}"
        )
    if purpose_bits:
        paragraphs.append(
            "Three houses classically frame this life's overarching purpose. " + " ".join(purpose_bits)
        )

    # --- Paragraph 6: this soul's disposition toward partnership and children ---
    disposition_bits = []
    if darakaraka.get("in_house_effects") or darakaraka.get("in_sign_effects"):
        dk_text = (
            f"Darakaraka — the Jaimini significator of the spouse/life partner, held here by "
            f"{darakaraka['planet']} in {darakaraka['sign']}, house {darakaraka['house']} "
            f"({darakaraka['nakshatra']} nakshatra) — describes this soul's own disposition "
            f"toward partnership, prior to comparing charts with anyone specific."
        )
        if darakaraka.get("in_sign_effects"):
            dk_text += f" {darakaraka['in_sign_effects']}"
        disposition_bits.append(dk_text)
    if putrakaraka.get("in_house_effects") or putrakaraka.get("in_sign_effects"):
        pk_text = (
            f"Putrakaraka — the significator of children, held here by {putrakaraka['planet']} in "
            f"{putrakaraka['sign']}, house {putrakaraka['house']} ({putrakaraka['nakshatra']} "
            f"nakshatra) — describes this soul's own disposition toward children and creative "
            f"legacy."
        )
        if putrakaraka.get("in_sign_effects"):
            pk_text += f" {putrakaraka['in_sign_effects']}"
        disposition_bits.append(pk_text)
    if disposition_bits:
        paragraphs.append(
            " ".join(disposition_bits) +
            " (A specific two-chart comparison with an actual partner or child's own Atmakaraka "
            "and Moon placement — not just this soul's own disposition — is what the Family "
            "Compatibility tab's Karmic Connection sections cover.)"
        )

    # --- Closing synthesis ---
    closing = (
        f"Read together, these significators sketch one coherent traditional narrative: a soul "
        f"whose defining focus (Atmakaraka in {atmakaraka['sign']}, house {atmakaraka['house']}) "
        f"arrives already carrying the imprint described by Ketu, is pulled to grow in the "
        f"direction Rahu points toward, works through consequence via Saturn's placement, and "
        f"orients its deeper purpose around the 5th/9th/12th houses described above. None of "
        f"this specifies a literal former life, era, or identity — it is a symbolic framework "
        f"this project's own verified KB entries already support, reassembled under a "
        f"traditional karmic lens for reflection."
    )
    paragraphs.append(closing)

    soul_narrative = "\n\n".join(paragraphs)
    # Backward-compatible short "synthesis" (single-sentence-per-significator
    # summary, as this field read before the expansion above) — some
    # callers (e.g. the GUI's one-line status text) still use this.
    short_bits = []
    if ketu.get("in_house_summary"):
        short_bits.append(f"Ketu in {ketu['sign']} (house {ketu['house']}): {ketu['in_house_summary']}")
    if rahu.get("in_house_summary"):
        short_bits.append(f"Rahu in {rahu['sign']} (house {rahu['house']}): {rahu['in_house_summary']}")
    if purva_punya.get("summary"):
        short_bits.append(f"5th house (Purva Punya): {purva_punya['summary']}")
    if dharma.get("summary"):
        short_bits.append(f"9th house (Dharma): {dharma['summary']}")
    if moksha.get("summary"):
        short_bits.append(f"12th house (Moksha): {moksha['summary']}")
    short_synthesis = " ".join(short_bits)

    return {
        "atmakaraka": atmakaraka,
        "darakaraka": darakaraka,
        "putrakaraka": putrakaraka,
        "ketu": ketu,
        "rahu": rahu,
        "saturn": saturn,
        "purva_punya_house_5": purva_punya,
        "dharma_house_9": dharma,
        "moksha_house_12": moksha,
        "soul_narrative": soul_narrative,
        "synthesis": short_synthesis,
        "caveat": _KARMIC_CAVEAT,
    }


# ---------------------------------------------------------------------------
# Life Predictions — original, per-life-area synthesis built from this
# project's own already-verified KB entries (house-lord placements, planet
# placements, yogas, and the running dasha). This is NOT a reproduction of
# any third-party astrology report's wording; it's freshly composed prose
# that cites the same classical significations already used throughout
# this project (see README.md's "Life predictions" note for the full list
# of which houses/planets feed each area).
# ---------------------------------------------------------------------------
_LIFE_PREDICTIONS_CAVEAT = (
    "These are classical tendencies read from house/planet significations and the current "
    "dasha — general traditional themes to consider, not guaranteed or literal predictions of "
    "specific events."
)


def _hl(house_lords, house_num):
    return house_lords[house_num]


def _hl_text(house_lords, house_num, prefer="effects"):
    hl = house_lords[house_num]
    r = hl["reading"]
    if not r:
        return None
    text = r.get(prefer) or r.get("summary")
    return f"the {house_num}th house's lord {hl['lord']} (in {hl['lord_sign']}, placed in house {hl['placed_in_house']}): {text}"


def _planet_text(planets_reading, planet, prefer="in_house"):
    r = planets_reading.get(planet)
    if not r:
        return None
    entry = r.get(prefer)
    if not entry:
        return None
    return f"{planet} in {r['sign']} (house {r['house']}): {entry.get('effects') or entry.get('summary')}"


def _build_life_predictions(chart, planets_reading, house_lords, yogas, dasha, karakas):
    running = dasha["running_at_birth"]
    dasha_note = ""
    if running.get("mahadasha_lord"):
        dasha_note = (
            f" The Mahadasha running at birth is {running['mahadasha_lord']}"
            + (f" / {running['antardasha_lord']} Antardasha" if running.get("antardasha_lord") else "")
            + ", which colors the timing and flavor of this area for the corresponding period of life."
        )

    def area(title, house_nums, planet_names, extra_yoga_ids=(), closing=""):
        bits = []
        for h in house_nums:
            t = _hl_text(house_lords, h)
            if t:
                bits.append(f"Through {t}")
        for p in planet_names:
            t = _planet_text(planets_reading, p)
            if t:
                bits.append(t)
        present_yogas = [y for y in yogas if y["present"] and y["id"] in extra_yoga_ids]
        for y in present_yogas:
            bits.append(f"{y['name']} is present in this chart: {y['details']}")
        text = " ".join(bits)
        if closing:
            text = text + " " + closing
        return {"title": title, "houses_considered": list(house_nums), "planets_considered": list(planet_names), "text": text.strip()}

    predictions = {
        "career_and_profession": area(
            "Career & Profession",
            [10, 6, 2, 11], ["Sun", "Saturn"],
            closing=(
                f"The Amatyakaraka (Jaimini's career significator) here is "
                f"{chara_karaka.get_karaka(karakas, 'AmK')['planet']}, in "
                f"{planets_reading[chara_karaka.get_karaka(karakas, 'AmK')['planet']]['sign']} — "
                "classically read as the planet whose qualities most shape vocational direction."
                + dasha_note
            ),
        ),
        "wealth_and_finances": area("Wealth & Finances", [2, 11, 9], ["Jupiter", "Venus"]),
        "marriage_and_relationships": area(
            "Marriage & Relationships",
            [7], ["Venus"],
            closing=(
                f"The Darakaraka (Jaimini's spouse significator) is "
                f"{chara_karaka.get_karaka(karakas, 'DK')['planet']}, in "
                f"{planets_reading[chara_karaka.get_karaka(karakas, 'DK')['planet']]['sign']} — "
                "see the Karmic & Past Life tab for this soul's own relational disposition, and "
                "Family Compatibility for an actual two-chart comparison if a partner profile "
                "has been generated."
            ),
        ),
        "health_and_vitality": area("Health & Vitality", [1, 6, 8], []),
        "education_and_learning": area("Education & Learning", [4, 5], ["Mercury", "Jupiter"]),
        "family_and_home": area("Family & Home", [2, 4], ["Moon"]),
        "children": area(
            "Children",
            [5], ["Jupiter"],
            closing=(
                f"The Putrakaraka (Jaimini's children significator) is "
                f"{chara_karaka.get_karaka(karakas, 'PK')['planet']}, in "
                f"{planets_reading[chara_karaka.get_karaka(karakas, 'PK')['planet']]['sign']}."
            ),
        ),
        "spirituality_and_inner_growth": area("Spirituality & Inner Growth", [9, 12], ["Jupiter", "Ketu"]),
        "travel_and_foreign_connections": area("Travel & Foreign Connections", [3, 9, 12], []),
    }
    predictions["caveat"] = _LIFE_PREDICTIONS_CAVEAT
    return predictions


def generate_reading(chart):
    """Builds the full readable chart interpretation for a chart produced by
    birth_chart.compute_birth_chart(). Returns a dict:

        {
          "name": ..., "ascendant": {sign, degree_in_sign},
          "planets": {planet: {sign, house, nakshatra, in_sign: {...KB...},
                                in_house: {...KB...},
                                vargas: {"D2": {sign, reading}, ...}}},
          "house_lords": {1: {lord, placed_in_house, reading}, ...},
          "yogas": [{id, name, present, details, kb_entry}, ...],   # all 24
          "yogas_present": [...same, filtered to present == True...],
          "dasha": {"running_at_birth": {...}, "timeline": [...]},
          "divisional_chart_overviews": {"D2": {...KB DIV-D2...}, ...},
          "chara_karakas": [ {rank, karaka, abbr, domain, planet, ...}, ... ],  # 7, see chara_karaka.py
          "karmic_and_past_life": {"atmakaraka": {...}, "darakaraka": {...}, "putrakaraka": {...},
                                    "ketu": {...}, "rahu": {...}, "saturn": {...},
                                    "purva_punya_house_5": {...}, "dharma_house_9": {...},
                                    "moksha_house_12": {...}, "soul_narrative": "... (long-form)",
                                    "synthesis": "... (short)", "caveat": "..."},
          "life_predictions": {"career_and_profession": {...}, "wealth_and_finances": {...},
                                "marriage_and_relationships": {...}, "health_and_vitality": {...},
                                "education_and_learning": {...}, "family_and_home": {...},
                                "children": {...}, "spirituality_and_inner_growth": {...},
                                "travel_and_foreign_connections": {...}, "caveat": "..."},
          "warnings": [ "..." ]   # any KB ids that couldn't be found
        }

    Every sub-reading is looked up from the bundled kb/ files by ID — this
    function does no interpretation of its own beyond selecting which
    pre-written KB entry applies to each computed fact.
    """
    warnings = []
    planets_reading = {p: _planet_reading(chart, p, warnings) for p in chart["planets"]}
    house_lords = _house_lord_readings(chart, warnings)
    yogas = _yoga_readings(chart, warnings)
    dasha = _dasha_readings(chart, warnings)
    divisional_overviews = _divisional_chart_overviews(warnings)
    karakas = _compute_chara_karakas(chart)
    karmic_and_past_life = _build_karmic_and_past_life(chart, planets_reading, house_lords, karakas)
    life_predictions = _build_life_predictions(chart, planets_reading, house_lords, yogas, dasha, karakas)

    return {
        "name": chart.get("name"),
        "ascendant": {
            "sign": chart["ascendant"]["sign"],
            "degree_in_sign": chart["ascendant"]["degree_in_sign"],
        },
        "planets": planets_reading,
        "house_lords": house_lords,
        "yogas": yogas,
        "yogas_present": [y for y in yogas if y["present"]],
        "dasha": dasha,
        "divisional_chart_overviews": divisional_overviews,
        "chara_karakas": karakas,
        "karmic_and_past_life": karmic_and_past_life,
        "life_predictions": life_predictions,
        "warnings": warnings,
    }


def reading_to_json_string(reading):
    import datetime

    def default(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError(f"Not JSON serializable: {type(obj)}")

    return json.dumps(reading, indent=2, ensure_ascii=False, default=default)
