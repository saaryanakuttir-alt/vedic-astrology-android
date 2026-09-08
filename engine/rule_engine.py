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
from astrology_tables import PLANET_ABBR, SIGN_ABBR, SIGN_LORD, get_dignity
from yogas import detect_all_yogas

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
        warnings.append(f"No 'nakshatra' entry found for '{nakshatra_name}'.")
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
        warnings.append(f"No 'nakshatra_pada' entry found for '{nakshatra_name}' pada {pada}.")
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
    entry = _lookup("combustion", f"CMB-{planet[:2]}", warnings) if combust else None
    return {"combust": combust, "orb": orb, "separation": round(sep, 2), "reading": entry}


def _planet_reading(chart, planet, warnings):
    detail = chart["planets"][planet]
    sign, house = detail["sign"], detail["house"]
    is_vargottama = detail["vargas"].get("D9") == sign

    reading = {
        "sign": sign,
        "house": house,
        "nakshatra": detail["nakshatra"],
        "nakshatra_pada": detail["nakshatra_pada"],
        "in_sign": _lookup("planet_in_sign", planet_in_sign_id(planet, sign), warnings),
        "in_house": _lookup("planet_in_house", planet_in_house_id(planet, house), warnings),
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


# Ketu is the classical significator of the past-life imprint — the domain
# whose skills/tendencies were already heavily developed before this birth.
# Reading Ketu's HOUSE as "the arena the past life centered on" is a
# standard traditional interpretation; the phrasings below describe the
# symbolic ROLE/arena each house points to, never a literal identity claim.
_KETU_HOUSE_PAST_ARENA = {
    1: "a life turned intensely inward on the self, the body, or a strongly individual identity — self-reliance developed to the point of over-identification with 'I' and 'my own way'",
    2: "a life organized around family, lineage, accumulated wealth, and the spoken word — resources and belonging mastered, perhaps clung to",
    3: "a hands-on life of courage, skill, and effort — a craftsperson, communicator, sibling-among-many, or someone who lived by their own initiative and daring",
    4: "a life rooted in home, land, mother, and emotional belonging — deeply domestic, tied to a place, property, or the inner emotional world",
    5: "a creative, devotional, or scholarly life — children, teaching, artistry, mantra, or speculative intelligence were the center of gravity",
    6: "a life of service, discipline, conflict, or healing — a soldier, healer, servant, or someone defined by daily toil and the overcoming of obstacles",
    7: "a life centered on others — partnership, trade, diplomacy, or public dealings — identity built through relationship and the marketplace",
    8: "a life marked by the hidden, the transformative, and the sudden — occult knowledge, research, crises, inheritance, or a preoccupation with what lies beneath the surface",
    9: "a philosophical, religious, or wandering life — a teacher, priest, pilgrim, or seeker of higher meaning, law, and distant horizons",
    10: "a life of authority, duty, and public standing — governance, command, career, or a strong preoccupation with status and worldly achievement",
    11: "a life of gains, networks, and community — commerce, alliances, elder siblings, and the pursuit of ambitions through the collective",
    12: "a secluded, foreign, or otherworldly life — monastery, exile, distant lands, imagination, or a withdrawal from the visible world toward the inner or the beyond",
}

# Broad temperament flavor of the past-life imprint, by the ELEMENT of the
# sign Ketu occupies — a coarse classical Tattva grouping, not a precise claim.
_ELEMENT_PAST_NATURE = {
    "Fire": "with a zealous, assertive, leadership-driven temperament (fire signs)",
    "Earth": "with a practical, material, endurance-driven temperament (earth signs)",
    "Air": "with an intellectual, social, communicative temperament (air signs)",
    "Water": "with an emotional, intuitive, devotional temperament (water signs)",
}

_SIGN_ELEMENT = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

# Plain-English, jargon-free meaning of each of the 12 houses - used to
# turn "the 10th lord sits in the 9th" into "your career is tied to luck,
# higher learning and mentors". Deliberately everyday wording.
_PLAIN_HOUSE = {
    1: "yourself - your body, health and personality",
    2: "money, family and what you say",
    3: "courage, siblings and your own effort",
    4: "home, your mother and inner peace",
    5: "children, creativity and romance",
    6: "work, health and overcoming obstacles",
    7: "marriage and close partnerships",
    8: "big changes, shared money and hidden things",
    9: "luck, higher learning, teachers and father",
    10: "career, status and public life",
    11: "income, friendships and big goals",
    12: "letting go, foreign lands and spiritual life",
}
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
    where = _PLAIN_HOUSE.get(placed, "another part of life")
    if placed in _STRONG_HOUSES:
        senti = "That is usually a supportive, helpful placement for this part of life."
    elif placed in _WEAK_HOUSES:
        senti = ("That placement tends to ask for extra effort here, or brings some ups and "
                 "downs before things settle.")
    else:
        senti = "That is a mixed, workable placement for this part of life."
    return (f"In simple terms: the planet in charge of your {area_word} sits in the part of "
            f"your life about {where}, so your {area_word} is closely tied to {where}. {senti}")


def _past_life_identity(ketu):
    """From Ketu's house (the arena the past life centered on) and the
    element of Ketu's sign (its temperament), sketch WHAT the native may
    have been — a symbolic arena + temperament, never a literal identity."""
    arena = _KETU_HOUSE_PAST_ARENA.get(ketu["house"], "an arena not cleanly captured by a single house theme")
    element = _SIGN_ELEMENT.get(ketu["sign"], None)
    nature = _ELEMENT_PAST_NATURE.get(element, "") if element else ""
    summary = (
        f"With Ketu in {ketu['sign']} (house {ketu['house']}, {ketu['nakshatra']} nakshatra), the "
        f"strongest past-life imprint points to {arena}"
        + (f", {nature}" if nature else "")
        + "."
    )
    detail = (
        "Classically, Ketu marks what the soul had already 'finished' — a mastery so complete it "
        "was carried in as instinct rather than learned again. Wherever Ketu sits is therefore "
        "read as the life-arena that was over-developed to the point of diminishing returns: "
        "familiar, even effortless, but no longer where growth lies. That is precisely why this "
        "life pulls in the opposite direction (see the main karmic goal below), toward the house "
        "and sign Rahu occupies."
    )
    return {"house": ketu["house"], "sign": ketu["sign"], "summary": summary, "detail": detail}


def _karmic_actions(ketu, saturn, purva_punya):
    """What past actions plausibly led here: Ketu's over-developed arena (the
    comfort/attachment that must now be released), Saturn as the karma-karaka
    (debts and consequences being worked off), and the 5th house / Purva
    Punya (the store of past merit carried forward)."""
    bits = [
        f"The over-reliance shown by Ketu in house {ketu['house']} ({ketu['sign']}) is read as the "
        f"past-life pattern most in need of release now — the very competence that once served the "
        f"soul became a groove too deep, a comfort clung to past its usefulness."
    ]
    if saturn.get("in_house_effects") or saturn.get("in_sign_effects"):
        bits.append(
            f"Saturn — the karaka of karma itself — sits in {saturn['sign']} (house {saturn['house']}), "
            f"marking where accumulated debts and consequences of past conduct are being steadily "
            f"worked off through responsibility and delay in this life: "
            f"{saturn.get('in_house_effects') or saturn.get('in_sign_effects')}"
        )
    if purva_punya.get("summary"):
        bits.append(
            f"The 5th house — Purva Punya, the storehouse of merit EARNED by good past-life action — "
            f"is ruled by {purva_punya['lord']} (in {purva_punya['lord_sign']}, placed in house "
            f"{purva_punya['placed_in_house']}), describing the credit balance carried forward: "
            f"{purva_punya.get('effects') or purva_punya['summary']}"
        )
    return " ".join(bits)


# Rahu's house is read as the unfamiliar territory this life's karmic
# growth reaches toward — the mirror image of _KETU_HOUSE_PAST_ARENA above
# (same 12 houses, opposite pole: what is being BUILT, not what was already
# mastered). Phrased as a goal/direction rather than a past-tense identity.
_RAHU_HOUSE_GROWTH_GOAL = {
    1: "building a confident, self-directed identity — learning to stand on one's own initiative rather than leaning on old, over-familiar support",
    2: "developing a stable relationship with resources, family, and one's own voice — learning to value and articulate what one has rather than taking it for granted",
    3: "growing into courage, self-effort, and communication — reaching for skills and initiative that must be earned firsthand, not inherited",
    4: "cultivating genuine inner and domestic security — building a home, emotional foundation, or sense of belonging that had to be consciously created rather than assumed",
    5: "developing creative, intellectual, or devotional expression — reaching toward legacy, children, or original ideas rather than simply repeating what already came easily",
    6: "mastering discipline, service, and the resolution of conflict — learning to face obstacles directly and build competence through daily effort",
    7: "learning genuine partnership and reciprocity — reaching outward into relationship and negotiation rather than staying self-contained",
    8: "engaging transformation, shared resources, and the hidden directly — learning to sit with crisis, depth, and change instead of avoiding it",
    9: "reaching for higher meaning, belief, and far horizons — building a personal philosophy or sense of purpose rather than inheriting one unexamined",
    10: "stepping into public responsibility, career, and authority — building a reputation and standing earned through visible effort, not granted by birthright",
    11: "growing through community, ambition, and long-term gain — learning to work toward goals through networks and collective effort rather than solitary comfort",
    12: "developing surrender, imagination, and release — reaching toward the unseen, the spiritual, or the foreign, rather than clinging to the visible and familiar",
}


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
        f"This life's main karmic goal centers on {goal_arena} — the territory Rahu occupies in "
        f"{rahu['sign']} (house {rahu['house']}, {rahu['nakshatra']} nakshatra), read as the "
        f"direction the soul is here to stretch toward, however unfamiliar or effortful it may "
        f"feel at first."
    ]
    if rahu.get("in_house_effects") or rahu.get("in_sign_effects"):
        sentences.append(
            "Concretely, that stretch plays out as: "
            + (rahu.get("in_house_effects") or rahu.get("in_sign_effects"))
        )
    sentences.append(
        f"This growth is carried out through the lens of the Atmakaraka, {atmakaraka['planet']} "
        f"in {atmakaraka['sign']} (house {atmakaraka['house']}) — the soul's central "
        f"quality — meaning the goal is not simply to arrive in Rahu's territory, but to bring "
        f"{atmakaraka['planet']}'s own nature into it: "
        + (atmakaraka.get("in_sign_effects") or f"the qualities {atmakaraka['sign']} classically signifies")
        + "."
    )
    if dharma.get("summary"):
        sentences.append(
            f"The 9th house (Dharma) frames why this matters beyond the individual: ruled by "
            f"{dharma['lord']} in {dharma['lord_sign']}, placed in house {dharma['placed_in_house']}, "
            f"it points to {dharma.get('effects') or dharma['summary']} — the larger sense of "
            f"purpose this life's karmic stretch is ultimately in service of."
        )
    return " ".join(sentences)


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
            f"Your Janma Nakshatra — the lunar mansion the Moon occupied at birth, and "
            f"traditionally read as foundational to personal identity in its own right — is "
            f"{moon_nakshatra['name']}, ruled by {moon_nakshatra['ruling_planet']} and "
            f"presided over by {moon_nakshatra['deity']}, symbolized by {moon_nakshatra['symbol'].lower()}. "
            f"{moon_nakshatra['effects']}"
        )
        if moon_pada:
            # Not splicing moon_pada['summary'] into a lowercase mid-sentence
            # fragment: it starts with the nakshatra's own NAME (a proper
            # noun, e.g. "Revati's core theme...") - lowercasing its first
            # letter mangled that into "revati's" on the first pass. A colon
            # break avoids needing to touch the KB text's own capitalization.
            janma_text += (
                f" More specifically, the Moon sits in pada {moon_nakshatra_pada} of "
                f"{moon_nakshatra_name} (Navamsa: {moon_pada['navamsa_sign']}): "
                f"{moon_pada['summary']}"
            )
        paragraphs.append(janma_text)

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

    # --- Past-life identity, the actions that led here, and this life's
    #     main karmic goal (the three things the user specifically asked to
    #     see spelled out) ---
    past_life = _past_life_identity(ketu)
    karmic_actions = _karmic_actions(ketu, saturn, purva_punya)
    main_karmic_goal = _karmic_goal_statement(rahu, atmakaraka, dharma)

    ketu_where = _PLAIN_HOUSE.get(ketu["house"], "a familiar part of life")
    rahu_where = _PLAIN_HOUSE.get(rahu["house"], "a new part of life")
    paragraphs.append(
        "--- What you may have been (past-life imprint) ---\n"
        + past_life["summary"] + " " + past_life["detail"]
        + f"\n\nIn simple terms: you seem to have come into this life already comfortable with "
        f"{ketu_where}. It feels natural, even over-familiar - so it's a strength you can lean "
        f"on, but not where your growth is meant to happen this time."
    )
    paragraphs.append(
        "--- What led here (the actions carried forward) ---\n" + karmic_actions
        + "\n\nIn simple terms: these are the old habits and duties your chart suggests you're "
        "still carrying - leaning too hard on what already came easily, which now has to be "
        "balanced out."
    )
    if main_karmic_goal:
        paragraphs.append(
            "--- Your main karmic goal this life ---\n" + main_karmic_goal
            + f"\n\nIn simple terms: your growth this life is mostly about {rahu_where}. Leaning "
            f"into that - even when it feels new or uncomfortable - is where the real meaning and "
            f"progress tend to come from."
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


# ---------------------------------------------------------------------------
# Longevity / lifespan (Ayurdaya + Maraka) — the most sensitive section in
# the whole app. Classical Vedic astrology DOES have longevity techniques,
# but every serious text is emphatic that (a) they yield a BAND (Alpayu /
# Madhyayu / Purnayu), not a precise date, (b) the three main calculation
# schemes (Pindayu, Nisargayu, Amsayu) routinely disagree, and (c) longevity
# is the single hardest thing to judge and should never be stated as a
# certainty. What follows is therefore a deliberately TRANSPARENT, simplified
# indication built from factors this project already computes — it is NOT a
# medical opinion, NOT a certainty, and NOT a substitute for a doctor or a
# qualified astrologer. The single "most likely age" figure is a midpoint
# estimate the user explicitly asked to see, wrapped in that framing.
_LONGEVITY_CAVEAT = (
    "IMPORTANT: This is a traditional, symbolic longevity indication, not a medical assessment "
    "and not a certainty. Classical astrology deliberately gives a lifespan BAND rather than an "
    "exact date, its three main longevity methods routinely disagree, and every serious text "
    "warns that longevity is the hardest judgment in the entire subject. The single 'most likely "
    "age' below is only the midpoint of the indicated band, shown because it was asked for — it "
    "is NOT a prediction of when anyone will actually die. If this raises real worry, or for any "
    "health concern, please speak with a doctor. Read everything here as reflection, nothing more."
)

# Ayurdaya bands and the age RANGE this app shows for each. (Balarishta /
# infant-mortality bands are deliberately omitted — they do not apply to
# anyone old enough to be reading their own chart.)
_LONGEVITY_BANDS = {
    "Alpayu": (32, 55, "short span"),
    "Madhyayu": (55, 78, "middle span"),
    "Purnayu": (78, 100, "full span"),
}

# Classical body/ailment karaka themes per planet — used ONLY to describe the
# symbolic "area" a maraka planet points at, never as a diagnosis.
_PLANET_HEALTH_THEME = {
    "Sun": "heart, bones, general vitality, and the eyes",
    "Moon": "the mind and emotions, blood, bodily fluids, and the chest/lungs",
    "Mars": "blood, muscles, inflammation, accidents, wounds, and surgical events",
    "Mercury": "the nervous system, skin, and speech",
    "Jupiter": "the liver, weight/metabolism, and sugar regulation",
    "Venus": "the reproductive and urinary systems and the kidneys",
    "Saturn": "chronic and degenerative conditions, the joints, bones, and slow-developing ailments",
    "Rahu": "hard-to-diagnose, toxic, or unusual conditions",
    "Ketu": "sudden, undiagnosed, or accident-related conditions",
}

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


def _build_longevity(chart, planets_reading, house_lords, dasha):
    birth_utc = _dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"])
    planets = chart["planets"]

    # --- Longevity strength score (transparent, simplified) ---
    # Strong 1st lord (vitality) and 8th lord (the house OF longevity), a
    # dignified Saturn (ayushkaraka), and benefic vs malefic occupation of
    # the 1st/8th are the factors that most consistently push the band up or
    # down across sources. This is a heuristic, not a full Pindayu calc.
    def dignity_points(lord, sign):
        d = get_dignity(lord, sign)
        if d in ("exalted", "moolatrikona", "own"):
            return 2
        if d in ("debilitated", "great enemy", "enemy"):
            return -1
        return 1  # friend / neutral

    first = house_lords[1]
    eighth = house_lords[8]
    score = 0
    score += dignity_points(first["lord"], first["lord_sign"])
    score += dignity_points(eighth["lord"], eighth["lord_sign"])
    if "Saturn" in planets:
        score += 1 if get_dignity("Saturn", planets["Saturn"]["sign"]) in ("exalted", "moolatrikona", "own", "friend", "neutral") else -1
    # 1st lord tucked away in a dusthana (6/8/12) weakens vitality.
    if first["placed_in_house"] in (6, 8, 12):
        score -= 1
    # Benefic / malefic occupation of the 1st and 8th houses.
    for planet, detail in planets.items():
        if detail["house"] in (1, 8):
            if planet in _BENEFICS:
                score += 1
            elif planet in _MALEFICS:
                score -= 1

    if score >= 3:
        band = "Purnayu"
    elif score >= 0:
        band = "Madhyayu"
    else:
        band = "Alpayu"
    low, high, band_desc = _LONGEVITY_BANDS[band]
    # Most-likely age: midpoint of the band, nudged within the band by how
    # strongly the score sits above/below that band's own entry threshold.
    midpoint = (low + high) / 2
    most_likely_age = int(round(max(low, min(high, midpoint))))
    # Approximate calendar years, for readers who want a year rather than
    # an age (birth year + age). Same heavy caveat applies - these are
    # midpoint/band estimates, never a prediction of an actual date.
    birth_year = birth_utc.year
    most_likely_year = birth_year + most_likely_age
    year_low = birth_year + low
    year_high = birth_year + high

    # --- Maraka (killer) significators: lords of the 2nd and 7th houses,
    #     plus Saturn as a natural maraka/ayushkaraka. ---
    maraka_lords = []
    for h in (2, 7):
        hl = house_lords[h]
        ordinal = {2: "2nd", 7: "7th"}[h]
        maraka_lords.append((hl["lord"], f"{ordinal}-house lord"))
    maraka_planet_names = {p for p, _ in maraka_lords} | {"Saturn"}

    # --- Maraka dasha periods: Mahadashas ruled by a maraka planet whose
    #     age-span overlaps or follows the indicated band. These are the
    #     classically-flagged 'vulnerable' windows. ---
    vulnerable_periods = []
    for maha in dasha["timeline"]:
        if maha["lord"] in maraka_planet_names:
            start_age = _age_at(maha["start"], birth_utc)
            end_age = _age_at(maha["end"], birth_utc)
            # Only windows that reach into or past the band's lower edge.
            if end_age >= low - 5:
                role = "natural maraka (Saturn)" if maha["lord"] == "Saturn" else \
                    next((r for p, r in maraka_lords if p == maha["lord"]), "maraka")
                sa = max(0, int(round(start_age)))
                ea = int(round(end_age))
                vulnerable_periods.append({
                    "lord": maha["lord"], "role": role,
                    "start_age": sa,
                    "end_age": ea,
                    "start_year": birth_year + sa,
                    "end_year": birth_year + ea,
                })

    # --- Possible causes: the health themes of the maraka planets, plus the
    #     6th (disease) and 8th (manner/chronic) house significations. ---
    cause_themes = []
    for planet in sorted(maraka_planet_names):
        theme = _PLANET_HEALTH_THEME.get(planet)
        if theme:
            cause_themes.append(f"{planet} (a maraka here) classically signifies {theme}")
    sixth = house_lords[6]
    cause_themes.append(
        f"the 6th house of illness is ruled by {sixth['lord']} (in {sixth['lord_sign']}), "
        f"pointing broadly to {_PLANET_HEALTH_THEME.get(sixth['lord'], 'its own significations')}"
    )

    # --- Assemble the readable text ---
    parts = []
    parts.append(
        f"Indicated longevity band: {band} — the classical '{band_desc}' — which this app maps to "
        f"roughly age {low}-{high} (around the years {year_low}-{year_high}). Most likely age "
        f"(midpoint estimate only): about {most_likely_age}, i.e. around the year {most_likely_year}."
    )
    parts.append(
        f"This band comes from a simplified strength reading of the 1st house/lord (vitality: "
        f"{first['lord']} in {first['lord_sign']}), the 8th house/lord (the house of longevity "
        f"itself: {eighth['lord']} in {eighth['lord_sign']}), Saturn as the ayushkaraka "
        f"(longevity significator), and the benefic vs. malefic planets occupying the 1st and 8th."
    )
    if vulnerable_periods:
        period_bits = [
            f"the {vp['lord']} Mahadasha ({vp['role']}), spanning roughly age {vp['start_age']}-{vp['end_age']} "
            f"(years {vp['start_year']}-{vp['end_year']})"
            for vp in vulnerable_periods
        ]
        parts.append(
            "Classically-flagged vulnerable periods (Maraka Mahadashas — the 2nd- and 7th-house "
            "lords and Saturn are the traditional 'markers of transition'): " + "; ".join(period_bits) + "."
        )
    parts.append(
        "Possible symbolic health themes (NOT a diagnosis): " + "; ".join(cause_themes) + "."
    )
    parts.append(_LONGEVITY_CAVEAT)

    return {
        "title": "Longevity & Lifespan (Ayurdaya)",
        "band": band,
        "age_low": low,
        "age_high": high,
        "most_likely_age": most_likely_age,
        "most_likely_year": most_likely_year,
        "year_low": year_low,
        "year_high": year_high,
        "cause_themes": cause_themes,
        "strength_score": score,
        "maraka_planets": sorted(maraka_planet_names),
        "vulnerable_periods": vulnerable_periods,
        "text": "\n\n".join(parts),
    }


def _build_life_predictions(chart, planets_reading, house_lords, yogas, dasha, karakas):
    running = dasha["running_at_birth"]
    dasha_note = ""
    if running.get("mahadasha_lord"):
        dasha_note = (
            f" The Mahadasha running at birth is {running['mahadasha_lord']}"
            + (f" / {running['antardasha_lord']} Antardasha" if running.get("antardasha_lord") else "")
            + ", which colors the timing and flavor of this area for the corresponding period of life."
        )

    def area(title, house_nums, planet_names, extra_yoga_ids=(), closing="", area_word=""):
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
        # A genuinely simplified reading of the key placement for this area
        # (see _plain_life_gloss) - a plain-language explanation of what the
        # dense classical text above actually means, not a topic description.
        if area_word and house_nums:
            gloss = _plain_life_gloss(house_lords, house_nums[0], area_word)
            if gloss:
                text = text + "\n\n" + gloss
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
            area_word="career",
        ),
        "wealth_and_finances": area("Wealth & Finances", [2, 11, 9], ["Jupiter", "Venus"],
            area_word="money and finances"),
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
            area_word="marriage and partnerships",
        ),
        "health_and_vitality": area("Health & Vitality", [1, 6, 8], [],
            area_word="health and vitality"),
        "education_and_learning": area("Education & Learning", [4, 5], ["Mercury", "Jupiter"],
            area_word="education and learning"),
        "family_and_home": area("Family & Home", [2, 4], ["Moon"],
            area_word="home and family"),
        "children": area(
            "Children",
            [5], ["Jupiter"],
            closing=(
                f"The Putrakaraka (Jaimini's children significator) is "
                f"{chara_karaka.get_karaka(karakas, 'PK')['planet']}, in "
                f"{planets_reading[chara_karaka.get_karaka(karakas, 'PK')['planet']]['sign']}."
            ),
            area_word="children",
        ),
        "spirituality_and_inner_growth": area("Spirituality & Inner Growth", [9, 12], ["Jupiter", "Ketu"],
            area_word="spiritual life"),
        "travel_and_foreign_connections": area("Travel & Foreign Connections", [3, 9, 12], [],
            area_word="travel and foreign ties"),
        # Longevity is intentionally placed LAST so it reads after the
        # life-area predictions above, and carries its own strong caveat.
        "longevity_and_lifespan": _build_longevity(chart, planets_reading, house_lords, dasha),
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
                                    "moksha_house_12": {...},
                                    "past_life_identity": {"house", "sign", "summary", "detail"},
                                    "karmic_actions": "... (past actions that led here)",
                                    "main_karmic_goal": "... (this life's central karmic goal)",
                                    "soul_narrative": "... (long-form, includes the three above)",
                                    "synthesis": "... (short)", "caveat": "..."},
          "life_predictions": {"career_and_profession": {...}, "wealth_and_finances": {...},
                                "marriage_and_relationships": {...}, "health_and_vitality": {...},
                                "education_and_learning": {...}, "family_and_home": {...},
                                "children": {...}, "spirituality_and_inner_growth": {...},
                                "travel_and_foreign_connections": {...},
                                "longevity_and_lifespan": {"title", "band", "age_low", "age_high",
                                                            "most_likely_age", "maraka_planets",
                                                            "vulnerable_periods", "text"},
                                "caveat": "..."},
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

    remedies = {
        "caveat": upaya.CAVEAT,
        "gemstone_candidates": upaya.suggest_gemstone_candidates(planets_reading),
        "gemstones": {p: upaya.gemstone_for(p) for p in planets_reading},
        "mantras": {p: upaya.mantra_for(p) for p in planets_reading},
    }

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
        "remedies": remedies,
        "warnings": warnings,
    }


def reading_to_json_string(reading):
    import datetime

    def default(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError(f"Not JSON serializable: {type(obj)}")

    return json.dumps(reading, indent=2, ensure_ascii=False, default=default)
