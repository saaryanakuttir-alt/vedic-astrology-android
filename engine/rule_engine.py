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
    nakshatra                  looked up by nakshatra NAME, not an id scheme
                                (see _load_nakshatra_kb/_nakshatra_reading below) -
                                every nakshatra name is already a unique, stable
                                join key (matches panchanga.NAKSHATRAS exactly),
                                so there's no need for a second ID convention here.

USAGE:
    from birth_chart import compute_birth_chart
    from rule_engine import generate_reading

    chart = compute_birth_chart(...)
    reading = generate_reading(chart)
"""
import json
import os

import datetime as _dt

import chara_karaka
import combustion
import maitri
import upaya
import relationship_themes
import doshas
import life_timeline
from astrology_tables import PLANET_ABBR, SIGN_ABBR, SIGN_LORD, get_dignity, ordinal
from yogas import detect_all_yogas
from i18n import is_english, t_text, tbl, tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

_CLASSICAL_SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

KB_DIR = os.path.join(os.path.dirname(__file__), "kb")

# All 25 bundled KB files, keyed by the same name rule_engine uses internally.
_KB_FILENAMES = {
    "planet_in_sign": "planet_in_sign.json",
    "planet_in_house": "planet_in_house.json",
    "house_lord_placement": "house_lord_placement.json",
    "nakshatra": "nakshatra.json",
    "nakshatra_pada": "nakshatra_pada.json",
    "panchadha_maitri": "panchadha_maitri.json",
    "combustion": "combustion.json",
    "retrograde": "retrograde.json",
    "vargottama": "vargottama.json",
    "relationship_themes": "relationship_themes.json",
    "doshas": "doshas.json",
    "classical_yogas": "classical_yogas.json",
    "vimshottari_mahadasha": "vimshottari_mahadasha.json",
    "vimshottari_antardasha": "vimshottari_antardasha.json",
    "divisional_charts": "divisional_charts.json",
    "divisional_D2_planet_in_sign": "divisional_D2_planet_in_sign.json",
    "divisional_D3_planet_in_sign": "divisional_D3_planet_in_sign.json",
    "divisional_D4_planet_in_sign": "divisional_D4_planet_in_sign.json",
    "divisional_D9_planet_in_sign": "divisional_D9_planet_in_sign.json",
    "divisional_D10_planet_in_sign": "divisional_D10_planet_in_sign.json",
    "divisional_D12_planet_in_sign": "divisional_D12_planet_in_sign.json",
    "divisional_D16_planet_in_sign": "divisional_D16_planet_in_sign.json",
    "divisional_D20_planet_in_sign": "divisional_D20_planet_in_sign.json",
    "divisional_D24_planet_in_sign": "divisional_D24_planet_in_sign.json",
    "divisional_D30_planet_in_sign": "divisional_D30_planet_in_sign.json",
    "divisional_D60_planet_in_sign": "divisional_D60_planet_in_sign.json",
}

DIVISIONAL_VARGAS = [2, 3, 4, 9, 10, 12, 16, 20, 24, 30, 60]   # D7 (Saptamsha, the children chart) intentionally omitted

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


_nakshatra_by_name = None


def _load_nakshatra_kb():
    """nakshatra.json's natural join key is each entry's own 'name' field
    (Ashwini, Bharani, ...), which already matches panchanga.NAKSHATRAS
    exactly - unlike every other KB file here, there's no need to build a
    separate {Planet}-{Sign}/{House}-style id to look an entry up, so this
    gets its own tiny name-keyed cache instead of going through _load()."""
    global _nakshatra_by_name
    if _nakshatra_by_name is None:
        path = os.path.join(KB_DIR, _KB_FILENAMES["nakshatra"])
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _nakshatra_by_name = {item["name"]: item for item in data["items"]}
    return _nakshatra_by_name


def _nakshatra_reading(nakshatra_name, warnings=None):
    entry = _load_nakshatra_kb().get(nakshatra_name)
    if entry is None and warnings is not None:
        warnings.append(tr("No 'nakshatra' entry found for '{0}'.", nakshatra_name))
    return entry


_pada_by_key = None


def _load_pada_kb():
    """nakshatra_pada.json's natural join key is (nakshatra name, pada
    number) - same reasoning as _load_nakshatra_kb above, its own tiny
    cache rather than going through the generic id-based _load()."""
    global _pada_by_key
    if _pada_by_key is None:
        path = os.path.join(KB_DIR, _KB_FILENAMES["nakshatra_pada"])
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _pada_by_key = {(item["nakshatra"], item["pada"]): item for item in data["items"]}
    return _pada_by_key


def _pada_reading(nakshatra_name, pada, warnings=None):
    entry = _load_pada_kb().get((nakshatra_name, pada))
    if entry is None and warnings is not None:
        warnings.append(tr("No 'nakshatra_pada' entry found for '{0}' pada {1}.", nakshatra_name, pada))
    return entry


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
    return tr('DIV-D{0}', varga_number)


def divisional_planet_in_sign_id(varga_number, planet, sign):
    return f"D{varga_number}-PS-{PLANET_ABBR[planet]}-{SIGN_ABBR[sign]}"


# ---------------------------------------------------------------------------
# Lookup helpers (return None + note a miss rather than raising, since a
# missing KB entry should degrade gracefully, not crash a chart reading).
# ---------------------------------------------------------------------------
def _lookup(kb_name, item_id, warnings):
    item = _load(kb_name).get(item_id)
    if item is None:
        warnings.append(tr("No '{0}' entry found for id '{1}'.", kb_name, item_id))
    return item


def _sign_lord_relationship(chart, planet, sign, house, warnings):
    """Panchadha Maitri between `planet` and the lord of the sign it
    occupies (in Rasi/D1) - how welcome a guest it is in that sign, a
    layer ADDITIONAL to (not a replacement for) exaltation/own/
    debilitation dignity. None when not computable: Rahu/Ketu aren't
    covered by the natural-friendship table (see maitri.py's docstring),
    and a planet in its OWN sign has no "relationship to the lord" to
    speak of (it IS the lord)."""
    lord = SIGN_LORD[sign]
    if planet not in maitri.CLASSICAL_SEVEN or lord == planet:
        return None
    lord_house = chart["planets"][lord]["house"]
    result = maitri.panchadha_maitri(planet, lord, house, lord_house)
    grade_entry = _lookup("panchadha_maitri", f"PM-{result['grade'].replace(' ', '')}", warnings)
    return {"lord": lord, **result, "reading": grade_entry}


def _combustion_reading(chart, planet, warnings):
    """None for the Sun itself and for Rahu/Ketu (no standard combustion
    rule - see combustion.py's module docstring)."""
    if planet not in combustion.ORB_DIRECT:
        return None
    detail = chart["planets"][planet]
    sun_lon = chart["planets"]["Sun"]["longitude"]
    sep = combustion.sun_separation(sun_lon, detail["longitude"])
    orb = combustion.combustion_orb(planet, detail.get("retrograde", False))
    combust = sep <= orb
    entry = _lookup("combustion", tr('CMB-{0}', planet[:2]), warnings) if combust else None
    return {"combust": combust, "orb": orb, "separation": round(sep, 2), "reading": entry}


def _relationship_themes_reading(chart, warnings):
    """Attaches KB reference text (title/summary/effects) to each raw
    indicator relationship_themes.assess_relationship_themes() computes.
    Deliberately mirrors the "raw facts + KB text, no combined verdict"
    shape used everywhere else in this module - see that module's own
    docstring for why this topic in particular avoids a single verdict."""
    raw = relationship_themes.assess_relationship_themes(chart)

    def attach(indicator, kb_id):
        entry = _lookup("relationship_themes", kb_id, warnings)
        return dict(indicator, kb=entry)

    seventh = raw["seventh_house_lord"]
    venus_mars = raw["venus_mars"]
    rahu = raw["rahu"]

    return {
        "caveat": raw["caveat"],
        "seventh_house_lord": {
            "lord": seventh["lord"], "sign": seventh["sign"], "placed_in_house": seventh["placed_in_house"],
            "in_dusthana": attach(seventh["in_dusthana"], "REL-7L-DUSTHANA"),
            "malefic_conjunction": attach(seventh["malefic_conjunction"], "REL-7L-MALEFIC-CONJ"),
            "malefic_aspect": attach(seventh["malefic_aspect"], "REL-7L-MALEFIC-ASPECT"),
        },
        "venus_mars": {
            "conjunction": attach(venus_mars["conjunction"], "REL-VENUS-MARS-CONJ"),
            "mutual_aspect": attach(venus_mars["mutual_aspect"], "REL-VENUS-MARS-ASPECT"),
        },
        "rahu": {
            "conjunct_venus": attach(rahu["conjunct_venus"], "REL-RAHU-VENUS"),
            "in_seventh_house": attach(rahu["in_seventh_house"], "REL-RAHU-7TH"),
        },
        "crowded_seventh_house": attach(raw["crowded_seventh_house"], "REL-CROWDED-7TH"),
        "venus_afflicted": attach(raw["venus_afflicted"], "REL-VENUS-AFFLICTED"),
        "marriage_count_tendency": relationship_themes.marriage_count_tendency(chart),
    }


def _doshas_reading(chart, warnings):
    """Attaches KB reference text to each raw indicator doshas.py computes
    (Pitra, Guru Chandal, both Grahan Dosha forms, Shrapit) - same
    attach-KB-to-raw-fact shape as _relationship_themes_reading above."""
    def attach(indicator, kb_id):
        entry = _lookup("doshas", kb_id, warnings)
        return dict(indicator, kb=entry)

    pitra = doshas.assess_pitra_dosha(chart)
    grahan = doshas.assess_grahan_dosha(chart)

    return {
        "pitra": {
            "note": pitra["note"],
            "rahu_ketu_in_9th": attach(pitra["rahu_ketu_in_9th"], "PITRA-RAHU-KETU-9TH"),
            "sun_conjunct_rahu_ketu": attach(pitra["sun_conjunct_rahu_ketu"], "PITRA-SUN-CONJ-SHADOW"),
            "ninth_lord_afflicted": attach(pitra["ninth_lord_afflicted"], "PITRA-9L-AFFLICTED"),
        },
        "guru_chandal": attach(doshas.assess_guru_chandal_dosha(chart), "GURUCHANDAL"),
        "grahan": {
            "surya_grahan": attach(grahan["surya_grahan"], "GRAHAN-SURYA"),
            "chandra_grahan": attach(grahan["chandra_grahan"], "GRAHAN-CHANDRA"),
        },
        "shrapit": attach(doshas.assess_shrapit_dosha(chart), "SHRAPIT"),
    }


def _plain_planet_gloss(planet, sign, house, in_sign, in_house):
    """The full paragraph shown for one planet: the classical, denser
    planet_in_sign.json/planet_in_house.json `effects` text (falling back
    to `summary` if a KB entry has no `effects`) LEFT INTACT, followed by
    a short plain-language gist in [brackets] at the end - never
    replacing the professional writing, only adding an accessible
    takeaway after it (explicit user feedback: keep the dense text, put
    the gist in brackets at the end, not instead of it)."""
    paragraph_bits, gist_bits = [], []
    for entry in (in_sign, in_house):
        if not entry:
            continue
        text = entry.get("effects") or entry.get("summary")
        if text:
            paragraph_bits.append(text)
        if entry.get("summary"):
            gist_bits.append(entry["summary"])
    if not paragraph_bits:
        return None
    header = tr('Your {0} in {1} ({2} house):', planet, sign, ordinal(house))
    professional = " ".join(paragraph_bits)
    if gist_bits:
        return tr('{0} {1} [In simple terms: {2}]', header, professional, ' '.join(gist_bits))
    return tr('{0} {1}', header, professional)


def _planet_reading(chart, planet, warnings):
    detail = chart["planets"][planet]
    sign, house = detail["sign"], detail["house"]
    is_vargottama = detail["vargas"].get("D9") == sign
    in_sign_entry = _lookup("planet_in_sign", planet_in_sign_id(planet, sign), warnings)
    in_house_entry = _lookup("planet_in_house", planet_in_house_id(planet, house), warnings)

    reading = {
        "sign": sign,
        "house": house,
        "nakshatra": detail["nakshatra"],
        "nakshatra_pada": detail["nakshatra_pada"],
        "in_sign": in_sign_entry,
        "in_house": in_house_entry,
        "plain_gloss": _plain_planet_gloss(planet, sign, house, in_sign_entry, in_house_entry),
        "sign_lord_relationship": _sign_lord_relationship(chart, planet, sign, house, warnings),
        "combustion": _combustion_reading(chart, planet, warnings),
        "vargottama": (
            {"is_vargottama": True, "reading": _lookup("vargottama", "VGT-01", warnings)}
            if is_vargottama else {"is_vargottama": False, "reading": None}
        ),
        # Rahu/Ketu are always flagged retrograde (their mean motion is
        # always regressive by definition - see ephemeris.py's own note),
        # so "retrograde" isn't a meaningful VARIABLE state for them and
        # retrograde.json doesn't cover them - guard explicitly rather
        # than firing a spurious "no entry found" warning on every chart.
        "retrograde_reading": (
            _lookup("retrograde", f"RX-{planet[:2]}", warnings)
            if detail.get("retrograde") and planet not in ("Sun", "Moon", "Rahu", "Ketu")
            else None
        ),
        "vargas": {},
    }
    for n in DIVISIONAL_VARGAS:
        varga_sign = detail["vargas"].get(f"D{n}")
        if varga_sign is None:
            continue
        kb_name = tr('divisional_D{0}_planet_in_sign', n)
        entry = _lookup(kb_name, divisional_planet_in_sign_id(n, planet, varga_sign), warnings)
        reading["vargas"][f"D{n}"] = {"sign": varga_sign, "reading": entry}
    return reading


def _house_lord_readings(chart, warnings):
    """BUG FIX (found by auditing a third-party report that made the exact
    same mistake): `lord_sign` must be the sign the LORD PLANET itself
    occupies, not the sign of the house being described. Every downstream
    consumer of this dict (_hl_text and the Karmic prose) reads `lord_sign` expecting
    "what sign is this lord actually sitting in" - e.g. "the 10th house's
    lord Jupiter (in {lord_sign}, placed in house {placed_in_house})" only
    makes sense if lord_sign is Jupiter's own sign (Leo), not Pisces (the
    10th house's sign, which is what SIGN_LORD[sign] was keyed off of to
    find the lord in the first place - it was already available as
    houses[house_num] directly, so nothing downstream needed it repeated
    here under a name that implied something else)."""
    houses = chart["houses"]
    readings = {}
    for house_num in range(1, 13):
        sign = houses.get(house_num, houses.get(str(house_num)))
        lord = SIGN_LORD[sign]
        placed_in = chart["planets"][lord]["house"]
        readings[house_num] = {
            "lord": lord,
            "house_sign": sign,  # the sign THIS HOUSE itself is (e.g. for a Houses-tab "Sign" column)
            "lord_sign": chart["planets"][lord]["sign"],  # the sign the lord PLANET actually occupies
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
            warnings.append(tr("No 'classical_yogas' entry found for id '{0}'.", result['id']))
        # `details` (from detect_all_yogas) is a short, per-CHART computed
        # fact ("Jupiter is in house 4 from Moon, a kendra") - it was the
        # only text ever shown for a yoga in any UI, even though classical_
        # yogas.json's own `formation`/`effects`/`strength_modifiers_and_
        # cautions` fields (verified, richer classical explanations of what
        # the yoga actually MEANS) have been attached as `kb_entry` all
        # along and never surfaced. `explanation` below is new: the
        # computed fact plus that full classical explanation, additive
        # (kept `details` unchanged so nothing already reading it breaks).
        explanation = None
        if kb_entry:
            bits = []
            if kb_entry.get("formation"):
                bits.append(tr('Classical formation: {0}', kb_entry['formation']))
            if kb_entry.get("effects"):
                bits.append(kb_entry["effects"])
            if kb_entry.get("strength_modifiers_and_cautions"):
                bits.append(tr('Worth noting: {0}', kb_entry['strength_modifiers_and_cautions']))
            explanation = " ".join(bits) or None
        readings.append({
            "id": result["id"],
            "name": kb_entry["name"] if kb_entry else result["id"],
            "present": result["present"],
            "details": result["details"],
            "explanation": explanation,
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
            # No separate KB narrative for pratyantardasha (3rd level) -
            # same Vimshottari math already running, just one level deeper
            # timing precision; the mahadasha/antardasha readings above
            # already cover the interpretive content.
            "pratyantardasha_lord": running["pratyantardasha_lord"] if running else None,
            "mahadasha_reading": maha_reading,
            "antardasha_reading": antar_reading,
        },
        "timeline": timeline_readings,
    }


def _divisional_chart_overviews(warnings):
    return {f"D{n}": _lookup("divisional_charts", divisional_chart_id(n), warnings) for n in DIVISIONAL_VARGAS}


_CHART_DESCRIPTION_PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# ---------------------------------------------------------------------------
# Plain-language chart explanations - the SAME facts as the dense text above
# (sign, house, dignity), reworded in everyday language instead of classical
# terminology. No new astrology, just a second, simpler rendering of data
# already computed. NOTE: an earlier version of this framed it as a literal
# "story" (planets as characters walking on stage) - explicit user feedback
# was that this read as gimmicky, not simpler; what was actually wanted was
# just clearer, jargon-free wording. Rewritten accordingly - plain
# explanation, no theatrical framing.
# ---------------------------------------------------------------------------
_SIGN_PLAIN_FLAVOR = tbl({
    "Aries": "bold and eager to go first",
    "Taurus": "steady, comfort-loving, and patient",
    "Gemini": "curious, chatty, and quick to learn",
    "Cancer": "caring, emotional, and protective",
    "Leo": "proud, warm, and wanting to shine",
    "Virgo": "careful, practical, and detail-focused",
    "Libra": "fair, social, and looking for balance",
    "Scorpio": "intense, private, and drawn to deep change",
    "Sagittarius": "adventurous, honest, and big-picture",
    "Capricorn": "disciplined, ambitious, and patient",
    "Aquarius": "independent, original, and idea-driven",
    "Pisces": "dreamy, compassionate, and imaginative",
})

_PLANET_PLAIN_ROLE = tbl({
    "Sun": "your core sense of self",
    "Moon": "your inner feelings and what makes you comfortable",
    "Mars": "your drive, courage, and how you take action",
    "Mercury": "your voice, thinking, and how you communicate",
    "Jupiter": "your luck, wisdom, and how you grow",
    "Venus": "love, beauty, and what you enjoy",
    "Saturn": "the hard lessons, patience, and discipline in your life",
    "Rahu": "a hunger for something new and unfamiliar",
    "Ketu": "what you're already ready to let go of",
})

_DIGNITY_PLAIN_PHRASE = tbl({
    "exalted": "at its very best here",
    "own": "right at home here",
    "debilitated": "finding this a bit of a struggle here",
    "neutral": "doing okay here, nothing dramatic",
})


def _chart_plain_explanation(chart_label, primary_use, asc_sign, planet_placements):
    """planet_placements: list of (planet, sign, house, dignity). A plain-
    language, jargon-free explanation of the same D1/varga facts
    _build_chart_descriptions already assembled - everyday wording, no
    classical terms, no theatrical framing (see note above)."""
    asc_flavor = _SIGN_PLAIN_FLAVOR.get(asc_sign, "")
    opening = tr('In plain terms, this is your {0}', chart_label)
    if primary_use:
        opening += tr(', which is mainly about {0}', primary_use)
    opening += tr('. Your rising sign here is {0} ({1}).', asc_sign, asc_flavor)
    lines = [opening]
    for planet, sign, house, dignity in planet_placements:
        role = _PLANET_PLAIN_ROLE.get(planet, planet)
        flavor = _SIGN_PLAIN_FLAVOR.get(sign, "")
        where = _PLAIN_HOUSE.get(house, "another part of life")
        dignity_phrase = _DIGNITY_PLAIN_PHRASE.get(dignity, "")
        line = tr('{0} ({1}) is in {2} ({3}), showing up mainly in the part of life about {4}', planet, role, sign, flavor, where)
        if dignity_phrase:
            line += tr(' - {0}', dignity_phrase)
        line += "."
        lines.append(line)
    return " ".join(lines)


def _build_chart_descriptions(chart, planets_reading, divisional_overviews):
    """Per-PERSON synthesis for D1 and every computed varga: THIS chart's own
    Ascendant sign, what the chart is classically used for, and for each of
    the 9 planets - its sign, house (counted from that varga's OWN
    Ascendant, whole-sign style), classical DIGNITY there, and a one-line
    interpretive gist pulled from the already-verified KB entry for that
    exact planet/sign/varga combination (divisional_D{n}_planet_in_sign.json,
    already looked up once into planets_reading[p]["vargas"][key]["reading"]
    by _planet_reading above - not a fresh lookup, just finally USING data
    this app already computes but wasn't surfacing here). This is separate
    from divisional_chart_overviews, which is a generic "what this varga
    chart is FOR" blurb (same for everyone) - this function describes what
    THIS person's own chart looks like in it, in more than just placement."""
    from panchanga import SIGNS as _SIGNS

    def house_from(asc_sign, planet_sign):
        return (_SIGNS.index(planet_sign) - _SIGNS.index(asc_sign)) % 12 + 1

    descriptions = {}

    # D1 - the main Rasi chart itself, not a derived varga (not in
    # DIVISIONAL_VARGAS), built straight from chart["ascendant"]/["planets"]
    # plus the base in_sign/in_house KB readings already in planets_reading.
    asc_sign = chart["ascendant"]["sign"]
    bits = [tr('Your Ascendant (Lagna) is {0} - this is your main birth chart, the foundation every other '
               'divisional chart below refines.', asc_sign)]
    for p in _CHART_DESCRIPTION_PLANET_ORDER:
        detail = chart["planets"][p]
        pr = planets_reading[p]
        dignity = get_dignity(p, detail["sign"])
        gist_bits = []
        for entry in (pr.get("in_sign"), pr.get("in_house")):
            if entry and entry.get("summary"):
                gist_bits.append(entry["summary"])
        gist = " ".join(gist_bits)
        line = tr('{0} is in {1}, your {2} house - {3} here.', p, detail['sign'], ordinal(detail['house']), dignity)
        if gist:
            line += tr(' {0}', gist)
        bits.append(line)
    d1_placements = [(p, chart["planets"][p]["sign"], chart["planets"][p]["house"],
                       get_dignity(p, chart["planets"][p]["sign"])) for p in _CHART_DESCRIPTION_PLANET_ORDER]
    descriptions["D1"] = {
        "name": tx("Rasi (main birth chart)"), "ascendant_sign": asc_sign, "text": " ".join(bits),
        "plain_explanation": _chart_plain_explanation(tx("main birth chart"), None, asc_sign, d1_placements),
    }

    for n in DIVISIONAL_VARGAS:
        key = f"D{n}"
        varga_asc = chart["ascendant"]["vargas"].get(key)
        if varga_asc is None:
            continue
        overview = divisional_overviews.get(key) or {}
        name = overview.get("name", key)
        primary_use = overview.get("primary_use")
        intro = tr('In your {0} ({1}) chart', key, name)
        if primary_use:
            intro += tr(' - classically used for {0}', primary_use)
        intro += tr(', your Ascendant falls in {0}.', varga_asc)
        bits = [intro]
        placements = []
        for p in _CHART_DESCRIPTION_PLANET_ORDER:
            varga_entry = planets_reading[p]["vargas"].get(key)
            if not varga_entry:
                continue
            p_sign = varga_entry["sign"]
            house = house_from(varga_asc, p_sign)
            kb = varga_entry.get("reading") or {}
            dignity = kb.get("dignity") or get_dignity(p, p_sign)
            gist = kb.get("summary") or ""
            line = tr('{0} sits in {1}, your {2} house here - {3} in this chart.', p, p_sign, ordinal(house), dignity)
            if gist:
                line += tr(' {0}', gist)
            bits.append(line)
            placements.append((p, p_sign, house, dignity))
        descriptions[key] = {
            "name": name, "ascendant_sign": varga_asc, "text": " ".join(bits),
            "plain_explanation": _chart_plain_explanation(tr('{0} ({1}) chart', key, name), primary_use, varga_asc, placements),
        }

    return descriptions


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


# Ketu is the classical significator of the past-life imprint — the domain
# whose skills/tendencies were already heavily developed before this birth.
# Reading Ketu's HOUSE as "the arena the past life centered on" is a
# standard traditional interpretation; the phrasings below describe the
# symbolic ROLE/arena each house points to, never a literal identity claim.
_KETU_HOUSE_PAST_ARENA = tbl({
    1: "a life turned intensely inward on the self, the body, or a strongly individual identity — self-reliance developed to the point of over-identification with 'I' and 'my own way'",
    2: "a life organized around family, lineage, accumulated wealth, and the spoken word — resources and belonging mastered, perhaps clung to",
    3: "a hands-on life of courage, skill, and effort — a craftsperson, communicator, sibling-among-many, or someone who lived by their own initiative and daring",
    4: "a life rooted in home, land, mother, and emotional belonging — deeply domestic, tied to a place, property, or the inner emotional world",
    5: "a creative, devotional, or scholarly life — teaching, artistry, mantra, or speculative intelligence were the center of gravity",
    6: "a life of service, discipline, conflict, or healing — a soldier, healer, servant, or someone defined by daily toil and the overcoming of obstacles",
    7: "a life centered on others — partnership, trade, diplomacy, or public dealings — identity built through relationship and the marketplace",
    8: "a life marked by the hidden, the transformative, and the sudden — occult knowledge, research, crises, inheritance, or a preoccupation with what lies beneath the surface",
    9: "a philosophical, religious, or wandering life — a teacher, priest, pilgrim, or seeker of higher meaning, law, and distant horizons",
    10: "a life of authority, duty, and public standing — governance, command, career, or a strong preoccupation with status and worldly achievement",
    11: "a life of gains, networks, and community — commerce, alliances, elder siblings, and the pursuit of ambitions through the collective",
    12: "a secluded, foreign, or otherworldly life — monastery, exile, distant lands, imagination, or a withdrawal from the visible world toward the inner or the beyond",
})

# Broad temperament flavor of the past-life imprint, by the ELEMENT of the
# sign Ketu occupies — a coarse classical Tattva grouping, not a precise claim.
_ELEMENT_PAST_NATURE = tbl({
    "Fire": "with a zealous, assertive, leadership-driven temperament (fire signs)",
    "Earth": "with a practical, material, endurance-driven temperament (earth signs)",
    "Air": "with an intellectual, social, communicative temperament (air signs)",
    "Water": "with an emotional, intuitive, devotional temperament (water signs)",
})

_SIGN_ELEMENT = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

# Plain-English, jargon-free meaning of each of the 12 houses - used to
# turn "the 10th lord sits in the 9th" into "your career is tied to luck,
# higher learning and mentors". Deliberately everyday wording.
_PLAIN_HOUSE = tbl({
    1: "yourself - your body, health and personality",
    2: "money, family and what you say",
    3: "courage, siblings and your own effort",
    4: "home, your mother and inner peace",
    5: "creativity, romance and learning",
    6: "work, health and overcoming obstacles",
    7: "marriage and close partnerships",
    8: "big changes, shared money and hidden things",
    9: "luck, higher learning, teachers and father",
    10: "career, status and public life",
    11: "income, friendships and big goals",
    12: "letting go, foreign lands and spiritual life",
})
_ORDINAL_HOUSE = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th",
                  7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}
# Houses whose lord being placed there is classically supportive vs. effortful.
_STRONG_HOUSES = {1, 4, 5, 7, 9, 10, 11}
_WEAK_HOUSES = {6, 8, 12}


def _plain_life_gloss(house_lords, primary_house, area_word):
    """A genuinely simplified reading of the KEY placement behind a life
    area (not a description of the topic): which house rules it, where that
    ruler sits in plain words, and whether that's classically easy or
    effortful."""
    hl = house_lords.get(primary_house) or house_lords.get(str(primary_house))
    if not hl:
        return ""
    placed = hl["placed_in_house"]
    where = _PLAIN_HOUSE.get(placed) or tx("another part of life")
    if placed in _STRONG_HOUSES:
        senti = tx("That is usually a supportive, helpful placement for this part of life.")
    elif placed in _WEAK_HOUSES:
        senti = (tx("That placement tends to ask for extra effort here, or brings some ups and "
                 "downs before things settle."))
    else:
        senti = tx("That is a mixed, workable placement for this part of life.")
    return (tr('In simple terms: the planet in charge of your {0} sits in the part of your life about {1}, so '
               'your {2} is closely tied to {3}. {4}', area_word, where, area_word, where, senti))


# Archetypal past-life PROFESSIONS/deeds per house - deliberately plural and
# archetypal ("a craftsperson, a builder, a guildmaster") rather than one
# named occupation, since the classical signal here is an ARENA of life
# (Ketu's house), not a job title - these are illustrative professions that
# fit that arena, not a literal claim about a specific past occupation.
_PAST_LIFE_PROFESSION = tbl({
    1: "a warrior, athlete, or someone whose whole identity was built through sheer physical presence and self-reliance",
    2: "a merchant, treasurer, singer, or head of a family estate - someone who managed wealth, voice, or lineage",
    3: "a craftsperson, messenger, scout, or performer - someone who lived by hands-on skill, courage, and initiative",
    4: "a farmer, homemaker, landowner, or caretaker of a household - someone whose life centered on land, home, and family",
    5: "a teacher, priest, artist, or advisor to rulers - someone whose gifts were creative, devotional, or intellectual",
    6: "a soldier, healer, servant, or laborer - someone who lived through discipline, conflict, or care for others in need",
    7: "a trader, diplomat, matchmaker, or business partner - someone whose life was built through dealing with other people",
    8: "an occultist, researcher, undertaker, or inheritor of hidden knowledge - someone drawn to what lies beneath the surface",
    9: "a pilgrim, scholar, judge, or religious teacher - someone whose life revolved around law, faith, or long journeys",
    10: "a ruler, administrator, or person of public authority - someone whose identity was built through career and status",
    11: "a guild member, trader's network organizer, or elder sibling managing a large household - someone who worked through community and alliance",
    12: "a monk, exile, hospital worker, or someone who lived apart from ordinary society - a life of seclusion, service, or foreign lands",
})

# A short closing flavor, keyed by Atmakaraka (the planet with the highest
# degree in-sign - Jaimini's significator of the soul's core drive across
# lifetimes), added as a coda to root WHY that profession/arena mattered to
# this particular soul, not just which house it was.
_ATMAKARAKA_PAST_FLAVOR = tbl({
    "Sun": "and whatever the role, it was carried out in a way that sought recognition, authority, or being seen as the one in charge",
    "Moon": "and whatever the role, it was carried out with strong emotional investment - care for others, or a deep need to belong",
    "Mars": "and whatever the role, it was carried out with courage, competitiveness, and a willingness to fight for it",
    "Mercury": "and whatever the role, it was carried out through cleverness, communication, and adaptability",
    "Jupiter": "and whatever the role, it was carried out with a sense of purpose, teaching, or moral responsibility",
    "Venus": "and whatever the role, it was carried out with an eye for beauty, relationship, and pleasure",
    "Saturn": "and whatever the role, it was carried out through hard, patient, often thankless labor over a long stretch of time",
})


def _past_life_identity(ketu, atmakaraka=None):
    """From Ketu's house (the arena the past life centered on) and the
    element of Ketu's sign (its temperament), sketch WHAT the native may
    have been — a symbolic arena + temperament + illustrative profession,
    never a literal identity. atmakaraka (optional, from chara_karaka.py's
    already-computed ranking) adds a short closing flavor on HOW that role
    was carried out, rooted in the soul's core drive across lifetimes."""
    arena = _KETU_HOUSE_PAST_ARENA.get(ketu["house"]) or tx("an arena not cleanly captured by a single house theme")
    element = _SIGN_ELEMENT.get(ketu["sign"], None)
    nature = _ELEMENT_PAST_NATURE.get(element, "") if element else ""
    profession = _PAST_LIFE_PROFESSION.get(ketu["house"])
    summary = (
        tr('With Ketu in {0} (house {1}, {2} nakshatra), the strongest past-life imprint points to {3}', ketu['sign'], ketu['house'], ketu['nakshatra'], arena)
        + (tr(', {0}', nature) if nature else "")
        + "."
    )
    detail = (
        tx("Classically, Ketu marks what the soul had already 'finished' — a mastery so complete it "
        "was carried in as instinct rather than learned again. Wherever Ketu sits is therefore "
        "read as the life-arena that was over-developed to the point of diminishing returns: "
        "familiar, even effortless, but no longer where growth lies. That is precisely why this "
        "life pulls in the opposite direction (see the main karmic goal below), toward the house "
        "and sign Rahu occupies.")
    )
    profession_text = None
    if profession:
        profession_text = tr('In that kind of life, you may have been {0}.', profession)
        atmakaraka_planet = atmakaraka.get("planet") if atmakaraka else None
        flavor = _ATMAKARAKA_PAST_FLAVOR.get(atmakaraka_planet)
        if flavor:
            profession_text += tr(' Your Atmakaraka is {0}, {1}.', atmakaraka_planet, flavor)
    return {
        "house": ketu["house"], "sign": ketu["sign"], "summary": summary, "detail": detail,
        "profession": profession_text,
    }


def _karmic_actions(ketu, saturn, purva_punya):
    """What past actions plausibly led here: Ketu's over-developed arena (the
    comfort/attachment that must now be released), Saturn as the karma-karaka
    (debts and consequences being worked off), and the 5th house / Purva
    Punya (the store of past merit carried forward)."""
    bits = [
        tr('The over-reliance shown by Ketu in house {0} ({1}) is read as the past-life pattern most in '
           'need of release now — the very competence that once served the soul became a groove too deep, a '
           'comfort clung to past its usefulness.', ketu['house'], ketu['sign'])
    ]
    if saturn.get("in_house_effects") or saturn.get("in_sign_effects"):
        bits.append(
            tr('Saturn — the karaka of karma itself — sits in {0} (house {1}), marking where accumulated debts '
               'and consequences of past conduct are being steadily worked off through responsibility and delay '
               'in this life: {2}', saturn['sign'], saturn['house'], saturn.get('in_house_effects') or saturn.get('in_sign_effects'))
        )
    if purva_punya.get("summary"):
        bits.append(
            tr('The 5th house — Purva Punya, the storehouse of merit EARNED by good past-life action — is ruled '
               'by {0} (in {1}, placed in house {2}), describing the credit balance carried forward: {3}', purva_punya['lord'], purva_punya['lord_sign'], purva_punya['placed_in_house'], purva_punya.get('effects') or purva_punya['summary'])
        )
    return " ".join(bits)


# Rahu's house is read as the unfamiliar territory this life's karmic
# growth reaches toward — the mirror image of _KETU_HOUSE_PAST_ARENA above
# (same 12 houses, opposite pole: what is being BUILT, not what was already
# mastered). Phrased as a goal/direction rather than a past-tense identity.
_RAHU_HOUSE_GROWTH_GOAL = tbl({
    1: "building a confident, self-directed identity — learning to stand on one's own initiative rather than leaning on old, over-familiar support",
    2: "developing a stable relationship with resources, family, and one's own voice — learning to value and articulate what one has rather than taking it for granted",
    3: "growing into courage, self-effort, and communication — reaching for skills and initiative that must be earned firsthand, not inherited",
    4: "cultivating genuine inner and domestic security — building a home, emotional foundation, or sense of belonging that had to be consciously created rather than assumed",
    5: "developing creative, intellectual, or devotional expression — reaching toward legacy or original ideas rather than simply repeating what already came easily",
    6: "mastering discipline, service, and the resolution of conflict — learning to face obstacles directly and build competence through daily effort",
    7: "learning genuine partnership and reciprocity — reaching outward into relationship and negotiation rather than staying self-contained",
    8: "engaging transformation, shared resources, and the hidden directly — learning to sit with crisis, depth, and change instead of avoiding it",
    9: "reaching for higher meaning, belief, and far horizons — building a personal philosophy or sense of purpose rather than inheriting one unexamined",
    10: "stepping into public responsibility, career, and authority — building a reputation and standing earned through visible effort, not granted by birthright",
    11: "growing through community, ambition, and long-term gain — learning to work toward goals through networks and collective effort rather than solitary comfort",
    12: "developing surrender, imagination, and release — reaching toward the unseen, the spiritual, or the foreign, rather than clinging to the visible and familiar",
})


def _karmic_goal_statement(rahu, atmakaraka, dharma):
    """Synthesize the ONE central karmic goal of THIS life. Rahu marks the
    unfamiliar direction the soul is pulled to grow toward (opposite Ketu's
    over-developed past); the Atmakaraka is the soul's own core focus; the
    9th house (Dharma) frames higher purpose.

    Returns a 2-4 sentence statement naming the main karmic goal and how
    Rahu's direction and the Atmakaraka's nature combine to define it."""
    goal_arena = _RAHU_HOUSE_GROWTH_GOAL.get(
        rahu["house"], "an arena not cleanly captured by a single house theme"
    )
    sentences = [
        tr("This life's main karmic goal centers on {0} — the territory Rahu occupies in {1} (house {2}, "
           '{3} nakshatra), read as the direction the soul is here to stretch toward, however unfamiliar or '
           'effortful it may feel at first.', goal_arena, rahu['sign'], rahu['house'], rahu['nakshatra'])
    ]
    if rahu.get("in_house_effects") or rahu.get("in_sign_effects"):
        sentences.append(
            tx("Concretely, that stretch plays out as: ")
            + (rahu.get("in_house_effects") or rahu.get("in_sign_effects"))
        )
    sentences.append(
        tr('This growth is carried out through the lens of the Atmakaraka, {0} in {1} (house {2}) — the '
           "soul's central quality — meaning the goal is not simply to arrive in Rahu's territory, but to "
           "bring {3}'s own nature into it: ", atmakaraka['planet'], atmakaraka['sign'], atmakaraka['house'], atmakaraka['planet'])
        + (atmakaraka.get("in_sign_effects") or tr('the qualities {0} classically signifies', atmakaraka['sign']))
        + "."
    )
    if dharma.get("summary"):
        sentences.append(
            tr('The 9th house (Dharma) frames why this matters beyond the individual: ruled by {0} in {1}, '
               "placed in house {2}, it points to {3} — the larger sense of purpose this life's karmic stretch "
               'is ultimately in service of.', dharma['lord'], dharma['lord_sign'], dharma['placed_in_house'], dharma.get('effects') or dharma['summary'])
        )
    return " ".join(sentences)


def _build_karmic_and_past_life(chart, planets_reading, house_lords, karakas):
    ketu = _significator_snapshot("Ketu", planets_reading)
    rahu = _significator_snapshot("Rahu", planets_reading)
    saturn = _significator_snapshot("Saturn", planets_reading)
    purva_punya = _house_significator_snapshot(5, tx("Purva Punya (past-life merit)"), house_lords)
    dharma = _house_significator_snapshot(9, tx("Dharma (fortune / higher purpose)"), house_lords)
    moksha = _house_significator_snapshot(12, tx("Moksha (endings / past attachments)"), house_lords)
    atmakaraka = _karaka_snapshot(karakas, "AK", planets_reading)
    darakaraka = _karaka_snapshot(karakas, "DK", planets_reading)
    putrakaraka = _karaka_snapshot(karakas, "PK", planets_reading)

    paragraphs = []

    # --- Paragraph 0: the Janma Nakshatra (Moon's birth star) ---
    # The single most foundational personal-identity placement in Vedic
    # astrology alongside the Moon sign itself - and, per nakshatra.json's
    # own note, the one gap where pada was already computed and shown in
    # every table (Planets, Kundli Details) but never actually narrated
    # anywhere in the app until this KB file existed.
    moon_nakshatra_name = planets_reading["Moon"]["nakshatra"]
    moon_nakshatra_pada = planets_reading["Moon"]["nakshatra_pada"]
    moon_nakshatra = _nakshatra_reading(moon_nakshatra_name)
    moon_pada = _pada_reading(moon_nakshatra_name, moon_nakshatra_pada)
    if moon_nakshatra:
        janma_text = (
            tr('Your Janma Nakshatra — the lunar mansion the Moon occupied at birth, and traditionally read as '
               'foundational to personal identity in its own right — is {0}, ruled by {1} and presided over by '
               '{2}, symbolized by {3}. {4}', moon_nakshatra['name'], moon_nakshatra['ruling_planet'], moon_nakshatra['deity'], moon_nakshatra['symbol'].lower(), moon_nakshatra['effects'])
        )
        if moon_pada:
            # Not splicing moon_pada['summary'] into a lowercase mid-sentence
            # fragment: it starts with the nakshatra's own NAME (a proper
            # noun, e.g. "Revati's core theme...") - lowercasing its first
            # letter mangled that into "revati's" on the first pass. A colon
            # break avoids needing to touch the KB text's own capitalization.
            janma_text += (
                tr(' More specifically, the Moon sits in pada {0} of {1} (Navamsa: {2}): {3}', moon_nakshatra_pada, moon_nakshatra_name, moon_pada['navamsa_sign'], moon_pada['summary'])
            )
        paragraphs.append(janma_text)

    # --- Paragraph 1: the soul's core nature (Atmakaraka) ---
    ak_text = (
        tr('In Jaimini astrology, the planet holding the highest degree among the seven classical grahas is '
           "the Atmakaraka — literally the 'significator of the soul' — read as the planet whose themes the "
           'soul itself is most identified with in this incarnation. Here that planet is {0}, placed in {1} '
           'in house {2} ({3} nakshatra, pada {4}).', atmakaraka['planet'], atmakaraka['sign'], atmakaraka['house'], atmakaraka['nakshatra'], atmakaraka['nakshatra_pada'])
    )
    if atmakaraka.get("in_sign_effects"):
        ak_text += tr(' By sign, this classically reads as: {0}', atmakaraka['in_sign_effects'])
    if atmakaraka.get("in_house_effects"):
        ak_text += tr(' By house, its themes play out through the domain it occupies: {0}', atmakaraka['in_house_effects'])
    if atmakaraka.get("dignity_note"):
        ak_text += tr(' {0}', atmakaraka['dignity_note'])
    ak_text += (
        tx(" Traditionally, whatever this planet governs is treated as the soul's central "
        "preoccupation across lifetimes — the quality it keeps returning to develop, express, "
        "or master — rather than a peripheral trait.")
    )
    paragraphs.append(ak_text)

    # --- Paragraph 2: what was carried forward (Ketu) ---
    if ketu.get("in_house_effects") or ketu.get("in_sign_effects"):
        ketu_text = (
            tr('Ketu is the classical significator of past-life imprint — skills, instincts, and unfinished '
               'business already carried into this birth, experienced less as something learned and more as '
               'something simply KNOWN. It sits in {0} in house {1} ({2} nakshatra).', ketu['sign'], ketu['house'], ketu['nakshatra'])
        )
        if ketu.get("in_sign_effects"):
            ketu_text += tr(' {0}', ketu['in_sign_effects'])
        if ketu.get("in_house_effects"):
            ketu_text += tr(' In the domain of house {0} specifically: {1}', ketu['house'], ketu['in_house_effects'])
        ketu_text += (
            tx(" Classically, a strong or prominent Ketu placement often shows up as an area where "
            "the native feels an odd, hard-to-explain fluency or detachment — as if this "
            "particular ground has already been covered before.")
        )
        paragraphs.append(ketu_text)

    # --- Paragraph 3: the direction of growth (Rahu) ---
    if rahu.get("in_house_effects") or rahu.get("in_sign_effects"):
        rahu_text = (
            tr("Rahu sits opposite Ketu by definition and is read as the direction this life's karmic growth "
               'pulls toward — unfamiliar territory the soul is drawn to reach for, often with more hunger than '
               'comfort at first. It is placed in {0} in house {1} ({2} nakshatra).', rahu['sign'], rahu['house'], rahu['nakshatra'])
        )
        if rahu.get("in_sign_effects"):
            rahu_text += tr(' {0}', rahu['in_sign_effects'])
        if rahu.get("in_house_effects"):
            rahu_text += tr(' In the domain of house {0}: {1}', rahu['house'], rahu['in_house_effects'])
        rahu_text += (
            tx(" Where Ketu describes what already feels familiar, Rahu describes what this "
            "incarnation is reaching to build — often the area of greatest ambition, "
            "restlessness, and eventual growth once its excesses are tempered by experience.")
        )
        paragraphs.append(rahu_text)

    # --- Paragraph 4: karma and consequence (Saturn) ---
    if saturn.get("in_house_effects") or saturn.get("in_sign_effects"):
        saturn_text = (
            tr('Saturn is the classical karaka for karma itself — structure, discipline, delay, and the '
               'working-out of consequence over time. It sits in {0} in house {1} ({2} nakshatra).', saturn['sign'], saturn['house'], saturn['nakshatra'])
        )
        if saturn.get("in_sign_effects"):
            saturn_text += tr(' {0}', saturn['in_sign_effects'])
        if saturn.get("in_house_effects"):
            saturn_text += tr(" In that house's domain: {0}", saturn['in_house_effects'])
        saturn_text += (
            tx(" Saturn's placement is traditionally read as showing exactly where patience, "
            "responsibility, and the slow, unglamorous accumulation of effort become the "
            "vehicle through which karma is actually resolved rather than merely felt.")
        )
        paragraphs.append(saturn_text)

    # --- Paragraph 5: life's higher purpose (5th/9th/12th houses) ---
    purpose_bits = []
    if purva_punya.get("summary"):
        purpose_bits.append(
            tr('The 5th house — Purva Punya, the storehouse of past-life merit — is ruled by {0} (in {1}), '
               'placed in house {2}: {3}', purva_punya['lord'], purva_punya['lord_sign'], purva_punya['placed_in_house'], purva_punya.get('effects') or purva_punya['summary'])
        )
    if dharma.get("summary"):
        purpose_bits.append(
            tr('The 9th house — Dharma, higher purpose and fortune — is ruled by {0} (in {1}), placed in house '
               '{2}: {3}', dharma['lord'], dharma['lord_sign'], dharma['placed_in_house'], dharma.get('effects') or dharma['summary'])
        )
    if moksha.get("summary"):
        purpose_bits.append(
            tr('The 12th house — Moksha, release and the letting-go of past attachments — is ruled by {0} (in '
               '{1}), placed in house {2}: {3}', moksha['lord'], moksha['lord_sign'], moksha['placed_in_house'], moksha.get('effects') or moksha['summary'])
        )
    if purpose_bits:
        paragraphs.append(
            tx("Three houses classically frame this life's overarching purpose. ") + " ".join(purpose_bits)
        )

    # --- Paragraph 6: this soul's disposition toward partnership ---
    disposition_bits = []
    if darakaraka.get("in_house_effects") or darakaraka.get("in_sign_effects"):
        dk_text = (
            tr('Darakaraka — the Jaimini significator of the spouse/life partner, held here by {0} in {1}, '
               "house {2} ({3} nakshatra) — describes this soul's own disposition toward partnership, prior to "
               'comparing charts with anyone specific.', darakaraka['planet'], darakaraka['sign'], darakaraka['house'], darakaraka['nakshatra'])
        )
        if darakaraka.get("in_sign_effects"):
            dk_text += tr(' {0}', darakaraka['in_sign_effects'])
        disposition_bits.append(dk_text)
    if disposition_bits:
        paragraphs.append(
            " ".join(disposition_bits) +
            tx(" (A specific two-chart comparison with an actual partner or family member's own "
            "Atmakaraka and Moon placement — not just this soul's own disposition — is what the "
            "Family Compatibility tab's Karmic Connection sections cover.)")
        )

    # --- Past-life identity, the actions that led here, and this life's
    #     main karmic goal (the three things the user specifically asked to
    #     see spelled out) ---
    past_life = _past_life_identity(ketu, atmakaraka)
    karmic_actions = _karmic_actions(ketu, saturn, purva_punya)
    main_karmic_goal = _karmic_goal_statement(rahu, atmakaraka, dharma)

    ketu_where = _PLAIN_HOUSE.get(ketu["house"], "a familiar part of life")
    rahu_where = _PLAIN_HOUSE.get(rahu["house"], "a new part of life")
    past_life_text = past_life["summary"] + " " + past_life["detail"]
    if past_life.get("profession"):
        past_life_text += " " + past_life["profession"]
    paragraphs.append(
        tx("--- What you may have been (past-life imprint) ---\n")
        + past_life_text
        + tr('\n\nIn simple terms: you seem to have come into this life already comfortable with {0}. It feels '
             "natural, even over-familiar - so it's a strength you can lean on, but not where your growth is "
             'meant to happen this time.', ketu_where)
    )
    paragraphs.append(
        tx("--- What led here (the actions carried forward) ---\n") + karmic_actions
        + tx("\n\nIn simple terms: these are the old habits and duties your chart suggests you're "
        "still carrying - leaning too hard on what already came easily, which now has to be "
        "balanced out.")
    )
    if main_karmic_goal:
        paragraphs.append(
            tx("--- Your main karmic goal this life ---\n") + main_karmic_goal
            + tr('\n\nIn simple terms: your growth this life is mostly about {0}. Leaning into that - even when it '
                 'feels new or uncomfortable - is where the real meaning and progress tend to come from.', rahu_where)
        )

    # --- Closing synthesis ---
    closing = (
        tr('Read together, these significators sketch one coherent traditional narrative: a soul whose '
           'defining focus (Atmakaraka in {0}, house {1}) arrives already carrying the imprint described by '
           'Ketu, is pulled to grow in the direction Rahu points toward, works through consequence via '
           "Saturn's placement, and orients its deeper purpose around the 5th/9th/12th houses described "
           'above. None of this specifies a literal former life, era, or identity — it is a symbolic '
           "framework this project's own verified KB entries already support, reassembled under a "
           'traditional karmic lens for reflection.', atmakaraka['sign'], atmakaraka['house'])
    )
    paragraphs.append(closing)

    # --- Section-level plain-language closing (kept SEPARATE from, not a
    # replacement for, the dense "Closing synthesis" paragraph just above -
    # explicit user feedback: never erase the professional writing, add
    # the simple version alongside it. Intended to render in ITALICS as
    # the very last thing in this section - a UI-side formatting choice,
    # so this field holds plain text and each UI applies its own italic
    # styling to it (see gui_app.py/app.js/tabs_reports.py). ---
    plain_section_summary = (
        tr('In simple words: you seem to arrive already comfortable with {0}, and this life is asking you '
           'to grow into {1}. Your sense of self centers on {2} in {3}, and your wider sense of purpose is '
           'shaped by the 5th, 9th, and 12th houses covered above. None of this is a literal past life - '
           "it's a traditional lens for noticing patterns that might be worth paying attention to, not a "
           'fact about who you were.', ketu_where, rahu_where, atmakaraka['planet'], atmakaraka['sign'])
    )
    paragraphs.append(plain_section_summary)

    soul_narrative = "\n\n".join(paragraphs)
    # Backward-compatible short "synthesis" (single-sentence-per-significator
    # summary, as this field read before the expansion above) — some
    # callers (e.g. the GUI's one-line status text) still use this.
    short_bits = []
    if ketu.get("in_house_summary"):
        short_bits.append(tr('Ketu in {0} (house {1}): {2}', ketu['sign'], ketu['house'], ketu['in_house_summary']))
    if rahu.get("in_house_summary"):
        short_bits.append(tr('Rahu in {0} (house {1}): {2}', rahu['sign'], rahu['house'], rahu['in_house_summary']))
    if purva_punya.get("summary"):
        short_bits.append(tr('5th house (Purva Punya): {0}', purva_punya['summary']))
    if dharma.get("summary"):
        short_bits.append(tr('9th house (Dharma): {0}', dharma['summary']))
    if moksha.get("summary"):
        short_bits.append(tr('12th house (Moksha): {0}', moksha['summary']))
    short_synthesis = " ".join(short_bits)

    return {
        "moon_nakshatra": moon_nakshatra,
        "moon_nakshatra_pada": moon_pada,
        "atmakaraka": atmakaraka,
        "darakaraka": darakaraka,
        "putrakaraka": putrakaraka,
        "ketu": ketu,
        "rahu": rahu,
        "saturn": saturn,
        "purva_punya_house_5": purva_punya,
        "dharma_house_9": dharma,
        "moksha_house_12": moksha,
        "past_life_identity": past_life,
        "karmic_actions": karmic_actions,
        "main_karmic_goal": main_karmic_goal,
        "soul_narrative": soul_narrative,
        "synthesis": short_synthesis,
        "plain_section_summary": plain_section_summary,
        "caveat": tx(_KARMIC_CAVEAT),
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
    return tr("the {0} house's lord {1} (in {2}, placed in house {3}): {4}", ordinal(house_num), hl['lord'], hl['lord_sign'], hl['placed_in_house'], text)


def _planet_text(planets_reading, planet, prefer="in_house"):
    r = planets_reading.get(planet)
    if not r:
        return None
    entry = r.get(prefer)
    if not entry:
        return None
    return tr('{0} in {1} (house {2}): {3}', planet, r['sign'], r['house'], entry.get('effects') or entry.get('summary'))


# ---------------------------------------------------------------------------
# Shared health-theme tables and age helper, used by the Medical Astrology
# section below. (This app deliberately has NO lifespan / longevity /
# time-of-death output of any kind.)
# ---------------------------------------------------------------------------

# Classical body/ailment karaka themes per planet — used ONLY to describe the
# symbolic "area" a planet points at, never as a diagnosis.
_PLANET_HEALTH_THEME = tbl({
    "Sun": "heart, bones, general vitality, and the eyes",
    "Moon": "the mind and emotions, blood, bodily fluids, and the chest/lungs",
    "Mars": "blood, muscles, inflammation, accidents, wounds, and surgical events",
    "Mercury": "the nervous system, skin, and speech",
    "Jupiter": "the liver, weight/metabolism, and sugar regulation",
    "Venus": "the reproductive and urinary systems and the kidneys",
    "Saturn": "chronic and degenerative conditions, the joints, bones, and slow-developing ailments",
    "Rahu": "hard-to-diagnose, toxic, or unusual conditions",
    "Ketu": "sudden, undiagnosed, or accident-related conditions",
})

_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}


def _age_at(dt_value, birth_utc):
    """Age in years at a timeline datetime, relative to birth (both UTC)."""
    if isinstance(dt_value, str):
        dt_value = _dt.datetime.fromisoformat(dt_value)
    # Normalize both to naive for subtraction (timeline datetimes are UTC).
    a = dt_value.replace(tzinfo=None) if dt_value.tzinfo else dt_value
    b = birth_utc.replace(tzinfo=None) if birth_utc.tzinfo else birth_utc
    return (a - b).days / 365.25


# ---------------------------------------------------------------------------
# Medical Astrology - a SEPARATE section (its own tab), not folded into
# Life Predictions' Health & Vitality card. Reuses _PLANET_HEALTH_THEME and
# _MALEFICS/_BENEFICS (defined above). Strong "not medical advice" framing.
# ---------------------------------------------------------------------------
_MEDICAL_CAVEAT = (
    "IMPORTANT: This is a traditional, symbolic health-THEMES indication from classical Vedic "
    "astrology - it is NOT a medical diagnosis, NOT medical advice, and NOT a substitute for a "
    "doctor. Astrology can describe symbolic tendencies at best; it cannot detect, confirm, or "
    "predict any actual medical condition. For any real health concern, please see a doctor."
)

_MEDICAL_OVERVIEW = (
    "Classical Vedic 'medical astrology' (Ayurvedic/Jyotish health analysis) reads the body onto "
    "the chart through the idea of the Kalapurusha, the 'cosmic body' - each of the 12 houses maps "
    "to a body region (see the table below), so a planet sitting in a house classically colors that "
    "body area. Four placements matter most: the Ascendant (Lagna) and its lord for overall "
    "vitality and constitution; the 6th house and its lord for disease, immunity, and daily health "
    "battles; the 8th house and its lord for chronic, hidden, or long-developing conditions; and "
    "Saturn, the classical significator of the body's endurance and of chronic, "
    "slow-onset conditions, wherever it sits. The Moon is read separately as the significator of "
    "the mind and emotional wellbeing, since Ayurveda and Jyotish both treat mental and physical "
    "health as linked, not separate."
)

# Personalized (house-from-Ascendant, not fixed-sign) Kalapurusha body map -
# the standard way this is applied to an individual chart: house 1 is
# always "the head" for THIS person regardless of which sign occupies it.
_HOUSE_BODY_PART = tbl({
    1: "the head and brain",
    2: "the face, mouth, and throat",
    3: "the throat, arms, shoulders, and ears",
    4: "the chest and lungs",
    5: "the heart, upper back, and stomach",
    6: "the lower abdomen and intestines (the classical 'disease house' itself)",
    7: "the kidneys and lower back",
    8: "the reproductive and excretory organs, and chronic or hidden conditions",
    9: "the hips and thighs",
    10: "the knees and joints",
    11: "the calves and ankles",
    12: "the feet and the immune system",
})

# One-word names for the body-map chart (the full wording above stays in the text).
_HOUSE_BODY_SHORT = tbl({
    1: "Head", 2: "Face", 3: "Arms", 4: "Chest", 5: "Heart", 6: "Belly",
    7: "Kidneys", 8: "Pelvis", 9: "Thighs", 10: "Knees", 11: "Calves", 12: "Feet",
})

# "How I'd say it to a friend" versions, appended in [brackets] after the classical wording.
_DOSHA_FRIEND = tbl({
    "Pitta": "you run a bit 'hot' - lots of drive and a strong appetite, but when you are stressed it tends "
             "to show up as irritability, heat or acidity",
    "Kapha": "you are steady and sturdy, with good stamina, but you can get sluggish or put on weight if "
             "you sit still for too long",
    "Vata": "you are quick and creative with a lot of nervous energy, so worry, dry skin or uneven sleep "
            "and eating are your usual signs that you are run down",
    "Kapha-Vata": "you are a mix of calm-and-steady and light-and-restless, so both slowing down too much "
                  "and overthinking can affect you",
})
_DOSHA_FRIEND_TOUCH = tbl({"Pitta": "some heat and intensity", "Kapha": "some steadiness", "Vata": "some restlessness",
                       "Kapha-Vata": "a mix of steadiness and restlessness"})
_GOOD_DIGNITY = ("exalted", "own", "moolatrikona")
_WEAK_DIGNITY = ("debilitated", "enemy", "great enemy")


def _friend_asc_lord(dignity):
    if dignity in _GOOD_DIGNITY:
        return tx("it is well supported and bounces back quickly, so you tend to recover well.")
    if dignity in _WEAK_DIGNITY:
        return (tx("it can dip more easily, so sleep, routine and not over-pushing yourself matter "
                "a bit more for you than for most."))
    return tx("it is ordinary and dependable - no big plus or minus.")


def _friend_moon(dignity, afflicted, supported):
    if afflicted:
        return (tx("your mind can feel busier or more pressured than most at times - calm routines, good sleep "
                "and talking things through help."))
    if supported:
        return tx("your mind has some built-in support, so you tend to settle and calm down fairly easily.")
    if dignity in _GOOD_DIGNITY:
        return tx("your emotional side is well supported, so you tend to stay level.")
    if dignity in _WEAK_DIGNITY:
        return tx("your feelings can swing a bit more easily, so give your mind proper rest and downtime.")
    return tx("your emotional side is neither a strong point nor a weak spot.")


def _friend_saturn(dignity):
    if dignity in _GOOD_DIGNITY:
        return tx("Saturn is about staying power, and yours is strong, so you tend to wear well over the years.")
    if dignity in _WEAK_DIGNITY:
        return (tx("Saturn is about staying power and it is a bit strained here, so bones, joints and slow-building "
                "niggles deserve steady care and regular check-ups."))
    return (tx("Saturn is about staying power and yours is average - just look after your joints and bones as you "
            "get older, like anyone."))


# Ayurvedic constitution (Prakriti) by element - Jyotish and Ayurveda share
# the same classical roots, and this is the standard bridge between them:
# Fire signs -> Pitta, Earth -> Kapha, Air -> Vata, Water -> a Kapha/Vata
# blend (some sources call water purely Kapha; the blend is the more widely
# cited version and is flagged as such below rather than asserted flatly).
_ELEMENT_DOSHA = tbl({
    "Fire": ("Pitta", "a fire-driven constitution - sharp digestion, strong drive, and a tendency "
                       "toward heat, inflammation, or irritability when out of balance"),
    "Earth": ("Kapha", "an earth-driven constitution - steady, well-built, and resilient, with a "
                        "tendency toward sluggishness, weight gain, or congestion when out of balance"),
    "Air": ("Vata", "an air-driven constitution - quick, light, and creative, with a tendency toward "
                     "anxiety, dryness, or irregular digestion/sleep when out of balance"),
    "Water": ("Kapha-Vata", "a water-driven constitution (sources vary between calling this Kapha or "
                              "a Kapha-Vata blend) - emotionally sensitive and fluid-retentive, with a "
                              "tendency toward congestion or emotional overwhelm when out of balance"),
})

_DOSHA_BALANCE_TIP = tbl({
    "Pitta": "Pitta-leaning constitutions are classically said to benefit from cooling foods, "
             "moderation in heat/spice, and avoiding overexertion - general wellness framing, not a diet plan.",
    "Kapha": "Kapha-leaning constitutions are classically said to benefit from regular movement, "
             "lighter meals, and avoiding excess rest - general wellness framing, not a diet plan.",
    "Vata": "Vata-leaning constitutions are classically said to benefit from routine, warmth, and "
            "grounding habits - general wellness framing, not a diet plan.",
    "Kapha-Vata": "This blended constitution is classically said to benefit from both routine/warmth "
                  "(Vata) and regular movement (Kapha) - general wellness framing, not a diet plan.",
})


def _build_medical_astrology(chart, planets_reading, house_lords, dasha):
    birth_utc = _dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"])
    planets = chart["planets"]

    body_areas = []
    for house_num in range(1, 13):
        occupants = [p for p, d in planets.items() if d["house"] == house_num]
        benefic_occ = [p for p in occupants if p in _BENEFICS]
        malefic_occ = [p for p in occupants if p in _MALEFICS]
        # A short WHY for each occupant, not just a supportive/caution flag -
        # the classical body/ailment theme that planet brings to this
        # specific body area, plus its dignity here (which modulates how
        # strongly that theme actually shows up).
        occupant_notes = []
        for p in occupants:
            dignity = get_dignity(p, planets[p]["sign"])
            theme = _PLANET_HEALTH_THEME.get(p, "")
            occupant_notes.append({"planet": p, "dignity": dignity, "theme": theme})
        body_areas.append({
            "house": house_num,
            "body_part": _HOUSE_BODY_PART[house_num],
            "short": _HOUSE_BODY_SHORT[house_num],
            "occupants": occupants,
            "benefic_occupants": benefic_occ,
            "malefic_occupants": malefic_occ,
            "occupant_notes": occupant_notes,
        })

    # --- 1st house/lord: overall vitality and constitution ---
    first = house_lords[1]
    first_dignity = get_dignity(first["lord"], first["lord_sign"])
    ascendant_lord_text = _hl_text(house_lords, 1) or ""

    # --- Ayurvedic constitution (Prakriti): Ascendant element = primary
    #     (the body's baseline constitution), Moon element = secondary (the
    #     mind's own temperament) - the standard Jyotish-Ayurveda bridge. ---
    asc_element = _SIGN_ELEMENT.get(chart["ascendant"]["sign"])
    moon_element = _SIGN_ELEMENT.get(planets["Moon"]["sign"])
    primary_dosha = _ELEMENT_DOSHA.get(asc_element)
    secondary_dosha = _ELEMENT_DOSHA.get(moon_element)
    dosha = None
    if primary_dosha:
        dosha = {
            "primary": primary_dosha[0], "primary_description": primary_dosha[1],
            "secondary": secondary_dosha[0] if secondary_dosha else None,
            "secondary_description": secondary_dosha[1] if secondary_dosha else None,
            "balance_tip": _DOSHA_BALANCE_TIP.get(primary_dosha[0], ""),
        }

    # --- Moon: mind and emotional wellbeing, read separately from the
    #     body-area table above since Jyotish/Ayurveda both treat mental
    #     and physical health as linked, not separate. ---
    moon_detail = planets["Moon"]
    moon_dignity = get_dignity("Moon", moon_detail["sign"])
    moon_house_mates = [p for p, d in planets.items() if d["house"] == moon_detail["house"] and p != "Moon"]
    moon_afflicted = [p for p in moon_house_mates if p in _MALEFICS]
    moon_supported = [p for p in moon_house_mates if p in _BENEFICS]
    moon_text = (
        tr('Moon (mind and emotional wellbeing) is in {0}, your {1} house - classically {2} there.', moon_detail['sign'], ordinal(moon_detail['house']), moon_dignity)
    )
    if moon_afflicted:
        moon_text += (
            tr(' Sharing that house with {0} classically suggests the mind may feel more pressure or '
               'restlessness at times - not a diagnosis, just a theme worth gentle awareness.', ', '.join(moon_afflicted))
        )
    if moon_supported:
        moon_text += tr(' {0} sharing that house is classically calming and supportive for it.', ', '.join(moon_supported))

    # --- Saturn: significator of endurance, read on its own regardless of which
    #     house it occupies, since it governs the body's endurance broadly. ---
    saturn_detail = planets.get("Saturn")
    saturn_dignity = get_dignity("Saturn", saturn_detail["sign"]) if saturn_detail else None
    saturn_text = _planet_text(planets_reading, "Saturn") or ""

    # --- 6th (disease) and 8th (chronic/hidden) house lords, with their
    #     full classical placement reading (the same house_lord_placement
    #     KB text _build_life_predictions's area() helper already uses),
    #     not just a bare dignity word. ---
    sixth = house_lords[6]
    eighth = house_lords[8]
    sixth_dignity = get_dignity(sixth["lord"], sixth["lord_sign"])
    eighth_dignity = get_dignity(eighth["lord"], eighth["lord_sign"])
    sixth_text = _hl_text(house_lords, 6) or ""
    eighth_text = _hl_text(house_lords, 8) or ""

    # Age-window cautions: Mahadashas ruled by the 6th lord (disease), the
    # 8th lord (chronic/hidden) or Saturn (chronic/slow-developing conditions).
    flagged = {sixth["lord"], eighth["lord"], "Saturn"}
    age_windows = []
    for maha in dasha["timeline"]:
        if maha["lord"] in flagged:
            start_age = _age_at(maha["start"], birth_utc)
            end_age = _age_at(maha["end"], birth_utc)
            if end_age < 0:
                continue
            roles = []
            if maha["lord"] == sixth["lord"]:
                roles.append(tx("6th-house (disease) lord"))
            if maha["lord"] == eighth["lord"]:
                roles.append(tx("8th-house (chronic/hidden) lord"))
            if maha["lord"] == "Saturn":
                roles.append(tx("Saturn, classical significator of chronic conditions"))
            sa, ea = max(0, int(round(start_age))), int(round(end_age))
            age_windows.append({
                "lord": maha["lord"], "role": " / ".join(roles),
                "start_age": sa, "end_age": ea,
                "start_year": birth_utc.year + sa, "end_year": birth_utc.year + ea,
                "theme": _PLANET_HEALTH_THEME.get(maha["lord"], ""),
            })

    def friend(text):
        return tr(' [In simple terms: {0}]', text)

    text_bits = [tx(_MEDICAL_OVERVIEW) + friend(
        tx("astrology lays your body over your birth chart like a map - each of the 12 houses is a body area, "
        "from the head (1st house) down to the feet (12th), and the planets sitting in a house colour that "
        "area. It is a way of spotting themes to look after, not a check-up."))]
    if dosha:
        dosha_line = tr('Ayurvedic constitution (Prakriti): primarily {0} - {1}.', dosha['primary'], dosha['primary_description'])
        if dosha["secondary"] and dosha["secondary"] != dosha["primary"]:
            dosha_line += tr(' Your Moon adds a {0} flavor - {1}.', dosha['secondary'], dosha['secondary_description'])
        if dosha["balance_tip"]:
            dosha_line += tr(' {0}', dosha['balance_tip'])
        gist = _DOSHA_FRIEND.get(dosha["primary"], "")
        if dosha["secondary"] and dosha["secondary"] != dosha["primary"]:
            gist += tr('. Your mind adds {0}', _DOSHA_FRIEND_TOUCH.get(dosha['secondary'], 'its own flavour'))
        text_bits.append(dosha_line + friend(tr('your body type is mostly {0}, which means {1}.', dosha['primary'], gist)))
    asc_text = (tr('Ascendant lord (overall vitality): {0}', ascendant_lord_text) if ascendant_lord_text else
                tr('Ascendant lord {0} (overall vitality) is {1} in {2}.', first['lord'], first_dignity, first['lord_sign']))
    text_bits.append(asc_text + friend(tx("this is your overall energy, and ") + _friend_asc_lord(first_dignity)))
    text_bits.append(moon_text + friend(tx("the Moon is your mind and mood - ") +
                                        _friend_moon(moon_dignity, moon_afflicted, moon_supported)))
    if saturn_text:
        text_bits.append(tr('Saturn, the classical significator of endurance and chronic conditions: {0}', saturn_text)
                         + friend(_friend_saturn(saturn_dignity)))
    elif saturn_dignity:
        text_bits.append(tr('Saturn, the classical significator of endurance and chronic conditions, is {0} in {1}.', saturn_dignity, saturn_detail['sign']) + friend(_friend_saturn(saturn_dignity)))
    def health_gloss(house_num, area):
        placed = house_lords[house_num]["placed_in_house"]
        where = _PLAIN_HOUSE.get(placed, "another part of life")
        if placed in _STRONG_HOUSES:
            senti = tx("that is usually a helpful placement, so this area tends to be looked after.")
        elif placed in _WEAK_HOUSES:
            senti = tx("that tends to ask for extra care here, with some ups and downs before things settle.")
        else:
            senti = tx("that is a mixed, workable placement.")
        return (tr('In simple terms: the planet that looks after your {0} sits in the part of your life about {1} - '
                   '{2}', area, where, senti))

    sixth_gloss = health_gloss(6, tx("everyday health and immunity"))
    eighth_gloss = health_gloss(8, tx("long-running or hidden health matters"))
    text_bits.append((tr('6th house (disease, daily health): {0}', sixth_text) if sixth_text else
                      tr('The 6th house is ruled by {0}, {1} in {2}.', sixth['lord'], sixth_dignity, sixth['lord_sign']))
                     + (tr(' [{0}]', sixth_gloss) if sixth_gloss else ""))
    text_bits.append((tr('8th house (chronic or hidden conditions): {0}', eighth_text) if eighth_text else
                      tr('The 8th house is ruled by {0}, {1} in {2}.', eighth['lord'], eighth_dignity, eighth['lord_sign']))
                     + (tr(' [{0}]', eighth_gloss) if eighth_gloss else ""))

    body_bits, strain_parts, support_parts = [], [], []
    for area in body_areas:
        if not area["occupant_notes"]:
            continue
        clause_bits = []
        for note in area["occupant_notes"]:
            tag = "supportive" if note["planet"] in _BENEFICS else tx("worth extra attention")
            clause_bits.append(
                tr('{0} ({1}, classically {2}) points to {3}', note['planet'], note['dignity'], tag, note['theme'])
            )
        body_bits.append(tr('Your {0} house ({1}): ', ordinal(area['house']), area['body_part']) + "; ".join(clause_bits) + ".")
        if area["malefic_occupants"]:
            strain_parts.append(area["short"].lower())
        elif area["benefic_occupants"]:
            support_parts.append(area["short"].lower())
    if body_bits:
        friend_bits = []
        if strain_parts:
            friend_bits.append(tx("the spots on your body map that carry a planet worth a little extra care are ")
                               + ", ".join(strain_parts))
        if support_parts:
            friend_bits.append((tx("and") + " " if strain_parts else "") + tx("these have a friendly, supportive planet on them: ")
                               + ", ".join(support_parts))
        friend_bits.append(tx("every other area has nothing sitting on it, which is simply neutral"))
        text_bits.append(tx("Body areas where your own planets sit: ") + " ".join(body_bits)
                         + friend("; ".join(friend_bits) + tx(". Think of shaded spots as 'keep an eye on this', "
                                  "not 'something is wrong'.")))

    if age_windows:
        text_bits.append(
            tx("Classically-flagged age windows worth being mindful during (a Mahadasha is a multi-year "
            "planetary period; these are the ones ruled by a planet tied to health themes above - "
            "not certainties, just windows classically worth a bit more attention): ") +
            "; ".join(
                tr('age {0}-{1} ({2} Mahadasha - {3}; themes: {4})', w['start_age'], w['end_age'], w['lord'], w['role'], w['theme']) for w in age_windows
            ) + "." + friend(
                tx("these are just stretches of life when it is smart to be a bit more mindful of your health - "
                "book the check-up and keep your routine going. Think of it as a friendly nudge, not a warning "
                "that something will happen.")))
    text_bits.append(tx(_MEDICAL_CAVEAT))

    return {
        "title": tx("Medical Astrology"),
        "overview": tx(_MEDICAL_OVERVIEW),
        "dosha": dosha,
        "ascendant_lord": first["lord"], "ascendant_lord_sign": first["lord_sign"],
        "ascendant_lord_dignity": first_dignity,
        "moon_sign": moon_detail["sign"], "moon_house": moon_detail["house"], "moon_dignity": moon_dignity,
        "moon_afflicted_by": moon_afflicted, "moon_supported_by": moon_supported,
        "saturn_sign": saturn_detail["sign"] if saturn_detail else None, "saturn_dignity": saturn_dignity,
        "sixth_house_lord": sixth["lord"], "sixth_house_lord_sign": sixth["lord_sign"],
        "sixth_house_lord_dignity": sixth_dignity,
        "eighth_house_lord": eighth["lord"], "eighth_house_lord_sign": eighth["lord_sign"],
        "eighth_house_lord_dignity": eighth_dignity,
        "body_areas": body_areas,
        "age_windows": age_windows,
        "text": "\n\n".join(text_bits),
        "caveat": tx(_MEDICAL_CAVEAT),
    }


def _build_life_predictions(chart, planets_reading, house_lords, yogas, dasha, karakas):
    running = dasha["running_at_birth"]
    dasha_note = ""
    if running.get("mahadasha_lord"):
        dasha_note = (
            tr(' The Mahadasha running at birth is {0}', running['mahadasha_lord'])
            + (tr(' / {0} Antardasha', running['antardasha_lord']) if running.get("antardasha_lord") else "")
            + tx(", which colors the timing and flavor of this area for the corresponding period of life.")
        )

    def area(title, house_nums, planet_names, extra_yoga_ids=(), closing="", area_word=""):
        bits = []
        for h in house_nums:
            t = _hl_text(house_lords, h)
            if t:
                bits.append(tr('Through {0}', t))
        for p in planet_names:
            t = _planet_text(planets_reading, p)
            if t:
                bits.append(t)
        present_yogas = [y for y in yogas if y["present"] and y["id"] in extra_yoga_ids]
        for y in present_yogas:
            bits.append(tr('{0} is present in this chart: {1}', y['name'], y['details']))
        text = " ".join(bits)
        if closing:
            text = text + " " + closing
        # A genuinely simplified reading of the key placement for this area
        # (see _plain_life_gloss) - a plain-language explanation of what the
        # dense classical text above actually means, not a topic
        # description. Appended in [brackets] at the END of the professional
        # text, never replacing it (explicit user feedback: keep the dense
        # writing intact, add the gist in brackets after it, not before it
        # or instead of it). Also exposed separately as `plain_gloss` (the
        # unbracketed sentence) in case a UI wants it on its own.
        gloss = _plain_life_gloss(house_lords, house_nums[0], area_word) if area_word and house_nums else ""
        if gloss:
            text = text + tr('\n\n[{0}]', gloss)
        return {
            "title": title, "houses_considered": list(house_nums), "planets_considered": list(planet_names),
            "text": text.strip(), "plain_gloss": gloss or None,
        }

    predictions = {
        "career_and_profession": area(
            tx("Career & Profession"),
            [10, 6, 2, 11], ["Sun", "Saturn"],
            closing=(
                tr("The Amatyakaraka (Jaimini's career significator) here is {0}, in {1} — classically read as the "
                   'planet whose qualities most shape vocational direction.', chara_karaka.get_karaka(karakas, 'AmK')['planet'], planets_reading[chara_karaka.get_karaka(karakas, 'AmK')['planet']]['sign'])
                + dasha_note
            ),
            area_word="career",
        ),
        "wealth_and_finances": area(tx("Wealth & Finances"), [2, 11, 9], ["Jupiter", "Venus"],
            area_word=tx("money and finances")),
        "marriage_and_relationships": area(
            tx("Marriage & Relationships"),
            [7], ["Venus"],
            closing=(
                tr("The Darakaraka (Jaimini's spouse significator) is {0}, in {1} — see the Karmic & Past Life tab "
                   "for this soul's own relational disposition, and Family Compatibility for an actual two-chart "
                   'comparison if a partner profile has been generated.', chara_karaka.get_karaka(karakas, 'DK')['planet'], planets_reading[chara_karaka.get_karaka(karakas, 'DK')['planet']]['sign'])
            ),
            area_word=tx("marriage and partnerships"),
        ),
        "health_and_vitality": area(tx("Health & Vitality"), [1, 6, 8], [],
            area_word=tx("health and vitality")),
        "education_and_learning": area(tx("Education & Learning"), [4, 5], ["Mercury", "Jupiter"],
            area_word=tx("education and learning")),
        "family_and_home": area(tx("Family & Home"), [2, 4], ["Moon"],
            area_word=tx("home and family")),
        "spirituality_and_inner_growth": area(tx("Spirituality & Inner Growth"), [9, 12], ["Jupiter", "Ketu"],
            area_word=tx("spiritual life")),
        "travel_and_foreign_connections": area(tx("Travel & Foreign Connections"), [3, 9, 12], [],
            area_word=tx("travel and foreign ties")),
    }
    predictions["caveat"] = tx(_LIFE_PREDICTIONS_CAVEAT)
    return predictions


# ---------------------------------------------------------------------------
# Plain-language "in short" digests for the sections that deliberately report
# raw indicators with NO combined verdict (Doshas, Relationship Themes,
# Yogas) - manglik.py's own design philosophy, followed by doshas.py and
# relationship_themes.py too (see their module docstrings). A reader
# unfamiliar with the classical framing still deserves an easy answer to
# "so what am I actually looking at here", so these name what's PRESENT in
# plain words without ever grading it good/bad or combining it into a
# verdict - strictly descriptive, matching how a doctor's after-visit
# summary lists findings without diagnosing a single "score" for the visit.
# ---------------------------------------------------------------------------
def _plain_list_summary(present_count, total_count, present_names, topic, absent_note):
    if present_count == 0:
        return tr('In short: none of these {0} {1} are present in this chart. {2}', total_count, topic, absent_note)
    names = ", ".join(present_names)
    return (
        tr('In short: {0} of {1} {2} {3} present in this chart — {4}. See below for what each one means; '
           "they're reported separately on purpose, not combined into a single verdict.", present_count, total_count, topic, 'is' if present_count == 1 else 'are', names)
    )


def _doshas_plain_summary(doshas_reading):
    indicators = [
        doshas_reading["pitra"]["rahu_ketu_in_9th"],
        doshas_reading["pitra"]["sun_conjunct_rahu_ketu"],
        doshas_reading["pitra"]["ninth_lord_afflicted"],
        doshas_reading["guru_chandal"],
        doshas_reading["grahan"]["surya_grahan"],
        doshas_reading["grahan"]["chandra_grahan"],
        doshas_reading["shrapit"],
    ]
    present = [i["kb"]["title"] for i in indicators if i["present"] and i.get("kb")]
    return _plain_list_summary(
        len(present), len(indicators), present, tx("affliction checks"),
        tx("That's a common, unremarkable result, not a gap in the chart."),
    )


def _relationship_deep_discussion(rel_reading, karmic_and_past_life):
    """A single, detailed narrative combining every relationship_themes
    indicator's own KB text with the marriage-count tendency and a karmic
    read on WHY relationships take the shape they do for this person. Still
    describes only the NATIVE's own chart - never a partner, and never
    naming or implying infidelity (relationship_themes.py's own docstring
    explains why that word is deliberately avoided throughout this app)."""
    s = rel_reading["seventh_house_lord"]
    present_texts = []
    for indicator in (
        s["in_dusthana"], s["malefic_conjunction"], s["malefic_aspect"],
        rel_reading["venus_mars"]["conjunction"], rel_reading["venus_mars"]["mutual_aspect"],
        rel_reading["rahu"]["conjunct_venus"], rel_reading["rahu"]["in_seventh_house"],
        rel_reading["crowded_seventh_house"], rel_reading["venus_afflicted"],
    ):
        if indicator.get("present") and indicator.get("kb"):
            text = indicator["kb"].get("effects") or indicator["kb"].get("summary")
            if text:
                present_texts.append(text)

    bits = []
    mct = rel_reading.get("marriage_count_tendency")
    if mct:
        bits.append(
            tr('On how many significant relationships or marriages this chart tends toward: this reading leans '
               'toward {0}.', mct['tendency'])
            + (" Specifically: " + " ".join(mct["indicators"]) if mct["indicators"] else
               tx(" No strong classical multiplicity indicators (a dual-sign 7th lord, a crowded 7th "
               "house, Rahu/Ketu sharing a house with the 7th lord, or Venus in a dual sign) are "
               "present here."))
        )

    if present_texts:
        bits.append(
            tx("On commitment and exclusivity themes specifically - read only as tendencies in this "
            "person's OWN chart, never as evidence about a partner (see the caveat above): ")
            + " ".join(present_texts)
        )
    else:
        bits.append(
            tx("None of this chart's checked commitment/exclusivity indicators (7th-lord affliction, "
            "Venus-Mars combinations, Rahu on Venus or the 7th house, a crowded 7th house, or an "
            "afflicted Venus) are present here - a common, unremarkable result, not a gap.")
        )

    dk = (karmic_and_past_life or {}).get("darakaraka")
    if dk and (dk.get("in_house_effects") or dk.get("in_sign_effects")):
        bits.append(
            tr("Why relationships may take the shape they do (a karmic lens): the Darakaraka - Jaimini's "
               'significator of the spouse or life partner - is {0} in {1}, house {2}. Classically, the '
               'Darakaraka describes the KIND of partner and partnership this soul is karmically drawn toward, '
               'prior to comparing charts with anyone specific. ', dk['planet'], dk['sign'], dk['house']) + (dk.get("in_sign_effects") or "")
        )

    bits.append(
        tx("None of the above says anything about what a real partner has done, will do, or is like - "
        "it describes tendencies in this person's OWN chart only, and free will always matters more "
        "than any single placement.")
    )
    return " ".join(bits)


def _relationship_themes_plain_summary(rel_reading):
    s = rel_reading["seventh_house_lord"]
    indicators = [
        s["in_dusthana"], s["malefic_conjunction"], s["malefic_aspect"],
        rel_reading["venus_mars"]["conjunction"], rel_reading["venus_mars"]["mutual_aspect"],
        rel_reading["rahu"]["conjunct_venus"], rel_reading["rahu"]["in_seventh_house"],
        rel_reading["crowded_seventh_house"], rel_reading["venus_afflicted"],
    ]
    present = [i["kb"]["title"] for i in indicators if i["present"] and i.get("kb")]
    return _plain_list_summary(
        len(present), len(indicators), present, "indicators",
        tx("That's a common, unremarkable result, not a gap in the chart."),
    )


def _first_sentence(text, max_chars=140):
    """A short, one-sentence teaser from a longer KB `effects` paragraph -
    used where space is tight (e.g. one line per yoga in a summary list)
    and the full text is shown in full elsewhere anyway."""
    if not text:
        return ""
    end = text.find(". ")
    sentence = text[: end + 1] if end != -1 else text
    if not is_english():
        return t_text(sentence)      # the whole sentence, so it matches the translation table (never cut mid-sentence)
    if len(sentence) > max_chars:
        sentence = sentence[:max_chars].rsplit(" ", 1)[0] + "..."
    return sentence


def _yogas_plain_summary(yogas_present):
    if not yogas_present:
        return (
            tx("In short: none of the 24 classical yogas this app checks are formed in this chart. "
            "That's common — most charts trigger only a few, if any; it isn't a deficiency.")
        )
    lines = [
        tr('In short: {0} classical yoga{1} {2} present in this chart:', len(yogas_present), 's' if len(yogas_present) != 1 else '', 'are' if len(yogas_present) != 1 else 'is')
    ]
    for y in yogas_present:
        kb = y.get("kb_entry") or {}
        gist = _first_sentence(kb.get("effects"))
        lines.append(f"  • {tx(y['name'])}" + (f" — {gist}" if gist else ""))
    return "\n".join(lines)


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
          "divisional_chart_overviews": {"D2": {...KB DIV-D2...}, ...},  # generic "what this varga is for"
          "chart_descriptions": {"D1": {"name", "ascendant_sign", "text", "plain_explanation"}, "D2": {...}, ...},
                                # THIS person's own placements in each chart (text = dense classical,
                                # plain_explanation = same facts in everyday language)
          "medical_astrology": {"title", "sixth_house_lord", "eighth_house_lord", "body_areas": [...],
                                 "age_windows": [...], "text", "caveat"},
          "chara_karakas": [ {rank, karaka, abbr, domain, planet, ...}, ... ],  # 7, see chara_karaka.py
          "karmic_and_past_life": {"atmakaraka": {...}, "darakaraka": {...}, "putrakaraka": {...},
                                    "ketu": {...}, "rahu": {...}, "saturn": {...},
                                    "purva_punya_house_5": {...}, "dharma_house_9": {...},
                                    "moksha_house_12": {...},
                                    "past_life_identity": {"house", "sign", "summary", "detail", "profession"},
                                    "karmic_actions": "... (past actions that led here)",
                                    "main_karmic_goal": "... (this life's central karmic goal)",
                                    "soul_narrative": "... (long-form, includes the three above)",
                                    "synthesis": "... (short)", "caveat": "..."},
          "life_predictions": {"career_and_profession": {...}, "wealth_and_finances": {...},
                                "marriage_and_relationships": {...}, "health_and_vitality": {...},
                                "education_and_learning": {...}, "family_and_home": {...},
                                "spirituality_and_inner_growth": {...},
                                "travel_and_foreign_connections": {...},
                                "caveat": "..."},   # (no children or lifespan/longevity sections)
          "year_by_year": {"years": [{age, calendar_year, mahadasha_lord, antardasha_lord,
                                       pratyantardasha_lord, houses_activated, muntha_sign,
                                       muntha_theme, note}, ...], "caveat": "..."},
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
    chart_descriptions = _build_chart_descriptions(chart, planets_reading, divisional_overviews)
    karakas = _compute_chara_karakas(chart)
    karmic_and_past_life = _build_karmic_and_past_life(chart, planets_reading, house_lords, karakas)
    life_predictions = _build_life_predictions(chart, planets_reading, house_lords, yogas, dasha, karakas)
    medical_astrology = _build_medical_astrology(chart, planets_reading, house_lords, dasha)

    remedies = {
        "caveat": upaya.CAVEAT,
        "gemstone_candidates": upaya.suggest_gemstone_candidates(planets_reading),
        "gemstones": {p: upaya.gemstone_for(p) for p in planets_reading},
        "mantras": {p: upaya.mantra_for(p) for p in planets_reading},
        "yantras": {p: upaya.yantra_for(p) for p in planets_reading},
        "daan": {p: upaya.daan_for(p) for p in planets_reading},
        "vrat": {p: upaya.vrat_for(p) for p in planets_reading},
        "rudraksha": {p: upaya.rudraksha_for(p) for p in planets_reading},
        "colors": {p: upaya.colors_for(p) for p in planets_reading},
        "combinations_to_avoid": upaya.combinations_to_avoid(),
        # Full 21-pair data, kept (not rendered as a table - see
        # combinations_to_avoid above for what the UI actually displays)
        # so the interactive combination checker can look up ANY pair the
        # user picks, not just the ones graded "avoid".
        "combination_matrix": upaya.full_combination_matrix(),
    }

    relationship_themes_reading = _relationship_themes_reading(chart, warnings)
    relationship_themes_reading["plain_summary"] = _relationship_themes_plain_summary(relationship_themes_reading)
    relationship_themes_reading["deep_discussion"] = _relationship_deep_discussion(
        relationship_themes_reading, karmic_and_past_life
    )
    doshas_reading = _doshas_reading(chart, warnings)
    doshas_reading["plain_summary"] = _doshas_plain_summary(doshas_reading)
    yogas_present = [y for y in yogas if y["present"]]

    # Year-by-year life outlook (Dasha + Muntha) - see life_timeline.py's
    # module docstring for exactly what technique this is/isn't. Reuses the
    # "dasha" readings dict just built above so every year's note quotes the
    # same already-verified antardasha text the Dasha tab itself shows.
    year_by_year = life_timeline.compute_life_timeline(chart, dasha)

    return {
        "name": chart.get("name"),
        "ascendant": {
            "sign": chart["ascendant"]["sign"],
            "degree_in_sign": chart["ascendant"]["degree_in_sign"],
        },
        "planets": planets_reading,
        "house_lords": house_lords,
        "yogas": yogas,
        "yogas_present": yogas_present,
        "yogas_plain_summary": _yogas_plain_summary(yogas_present),
        "dasha": dasha,
        "divisional_chart_overviews": divisional_overviews,
        "chart_descriptions": chart_descriptions,
        "chara_karakas": karakas,
        "karmic_and_past_life": karmic_and_past_life,
        "life_predictions": life_predictions,
        "medical_astrology": medical_astrology,
        "remedies": remedies,
        "relationship_themes": relationship_themes_reading,
        "doshas": doshas_reading,
        "year_by_year": year_by_year,
        "warnings": warnings,
    }


def reading_to_json_string(reading):
    import datetime

    def default(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError(tr('Not JSON serializable: {0}', type(obj)))

    return json.dumps(reading, indent=2, ensure_ascii=False, default=default)
