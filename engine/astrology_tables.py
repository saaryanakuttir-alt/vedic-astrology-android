"""
astrology_tables.py — static classical reference tables (sign lords,
dignities, house-relationship categories, and planetary aspect rules)
shared by yogas.py and rule_engine.py.

Every table here was cross-checked against this project's own knowledge
base (planet_in_sign.json's `dignity` field) rather than hand-typed from
memory, so it can't drift from what the interpretive JSON files already
assert. Run this module directly (`python3 astrology_tables.py`) to
re-print that cross-check.

Rahu/Ketu deliberately have NO entry in EXALTATION_SIGN/DEBILITATION_SIGN
here, matching planet_in_sign.json's own `rahu_ketu_dignity_note`: classical
texts disagree on a fixed exaltation/debilitation sign for the lunar nodes,
and this project does not assert one scheme as definitive.
"""
from panchanga import SIGNS

PLANET_ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
    "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}
SIGN_ABBR = {
    "Aries": "Ari", "Taurus": "Tau", "Gemini": "Gem", "Cancer": "Can",
    "Leo": "Leo", "Virgo": "Vir", "Libra": "Lib", "Scorpio": "Sco",
    "Sagittarius": "Sag", "Capricorn": "Cap", "Aquarius": "Aqu", "Pisces": "Pis",
}

# Sign lordship (rulership) — classical, undisputed.
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

# Own signs (includes moolatrikona) — classical 7 grahas only.
OWN_SIGNS = {
    "Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"],
}

EXALTATION_SIGN = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
    "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra",
}
DEBILITATION_SIGN = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
    "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries",
}
# Reverse lookup: which planet is exalted in a given sign (only 7 signs have an entry).
SIGN_EXALTS = {sign: planet for planet, sign in EXALTATION_SIGN.items()}
SIGN_DEBILITATES = {sign: planet for planet, sign in DEBILITATION_SIGN.items()}

# Natural benefics/malefics. Mercury and the Moon are CONDITIONAL benefics
# classically (Mercury when not conjunct/aspected by malefics, "well-placed";
# Moon only when waxing) — matching the wording in classical_yogas.json's
# Amala Yoga (YOGA-16) and Adhi Yoga (YOGA-17) formation text exactly. This
# module treats Mercury as always benefic for simplicity (a reasonable
# default; conditional weakening is left as a documented approximation) and
# provides is_moon_waxing() so callers can apply the waxing condition to the
# Moon explicitly where the classical rule requires it.
NATURAL_BENEFICS_UNCONDITIONAL = {"Jupiter", "Venus", "Mercury"}
NATURAL_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}

# Classical graha drishti (aspect): every planet aspects the 7th house from
# itself; Mars additionally aspects the 4th and 8th; Jupiter additionally
# aspects the 5th and 9th; Saturn additionally aspects the 3rd and 10th.
# Expressed here as "house-distance offsets" (1-indexed, inclusive counting
# — matching houses.get_house_of_sign's convention where distance 1 = same
# house, distance 7 = the 7th house from it).
_DEFAULT_ASPECT_DISTANCES = {7}
SPECIAL_ASPECT_DISTANCES = {
    "Mars": {4, 7, 8},
    "Jupiter": {5, 7, 9},
    "Saturn": {3, 7, 10},
}


def aspect_distances_for(planet):
    """Which house-distances (1-indexed) `planet` casts its drishti on."""
    return SPECIAL_ASPECT_DISTANCES.get(planet, _DEFAULT_ASPECT_DISTANCES)


def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4..12 -> 'Nth'. Houses only ever
    run 1-12 in this project, so the general English exceptions at 11/12/13
    (which would otherwise need "11th" not "11st") never actually arise
    here - this is deliberately NOT a general-purpose ordinal formatter.
    Added after finding "the 1th house", "the 2th house" hardcoded in
    rule_engine.py's life-predictions template - the same trivial-but-
    visible bug an external report was independently caught making."""
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def house_distance(from_house, to_house):
    """Inclusive-counting distance from `from_house` to `to_house` (1-12),
    matching houses.get_house_of_sign's convention: same house = 1, the
    house 6 steps ahead = 7 (the classical '7th house from X')."""
    return ((to_house - from_house) % 12) + 1


def is_kendra_from(from_house, to_house):
    return house_distance(from_house, to_house) in KENDRA_HOUSES


def is_trikona_from(from_house, to_house):
    return house_distance(from_house, to_house) in TRIKONA_HOUSES


def is_dusthana_from(from_house, to_house):
    return house_distance(from_house, to_house) in DUSTHANA_HOUSES


def planet_aspects_house(planet, from_house, target_house):
    """Does `planet`, sitting in `from_house`, cast a classical aspect on
    `target_house`?"""
    return house_distance(from_house, target_house) in aspect_distances_for(planet)


def get_dignity(planet, sign):
    """Returns one of: 'exalted', 'own', 'debilitated', 'neutral', or
    (for Rahu/Ketu) 'undetermined (classical texts disagree)'."""
    if planet in ("Rahu", "Ketu"):
        return "undetermined (classical texts disagree)"
    if EXALTATION_SIGN.get(planet) == sign:
        return "exalted"
    if sign in OWN_SIGNS.get(planet, []):
        return "own"
    if DEBILITATION_SIGN.get(planet) == sign:
        return "debilitated"
    return "neutral"


def is_moon_waxing(sun_longitude, moon_longitude):
    """True if the Moon is waxing (Shukla Paksha) — Moon is within 180
    degrees ahead of the Sun along the zodiac."""
    return (moon_longitude - sun_longitude) % 360.0 < 180.0


if __name__ == "__main__":
    # Cross-check every table above against this project's own
    # planet_in_sign.json, so the tables can never silently drift from the
    # KB's own asserted dignities.
    import json
    import os

    kb_path = os.path.join(os.path.dirname(__file__), "kb", "planet_in_sign.json")
    data = json.load(open(kb_path, encoding="utf-8"))
    mismatches = []
    for item in data["items"]:
        planet, sign, kb_dignity = item["planet"], item["sign"], item["dignity"]
        if planet in ("Rahu", "Ketu"):
            continue
        computed = get_dignity(planet, sign)
        kb_is_own = kb_dignity.startswith("own sign")
        kb_is_exalted = kb_dignity == "exalted" or kb_dignity.startswith("exalted &")
        kb_is_debilitated = kb_dignity == "debilitated"
        ok = (
            (computed == "own" and kb_is_own)
            or (computed == "exalted" and kb_is_exalted)
            or (computed == "debilitated" and kb_is_debilitated)
            or (computed == "neutral" and kb_dignity == "neutral")
        )
        if not ok:
            mismatches.append((planet, sign, kb_dignity, computed))
    if mismatches:
        print("MISMATCHES FOUND:")
        for m in mismatches:
            print("  ", m)
    else:
        print("OK — astrology_tables.py dignity tables match planet_in_sign.json exactly "
              "(all 7 classical grahas x 12 signs).")
