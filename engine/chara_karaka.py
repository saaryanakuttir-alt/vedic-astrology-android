"""
chara_karaka.py — the classical Jaimini "Chara Karaka" (movable significator)
scheme: ranking the 7 physical grahas (Sun through Saturn — Rahu/Ketu
excluded, see below) by their exact degree WITHIN their own sign, highest
to lowest. The planet at each rank becomes the significator ("karaka") for
a specific life domain, regardless of which planet it actually is:

    Rank  Karaka name         Sanskrit      Domain
    1     Atmakaraka   (AK)   Atma-karaka   The soul itself — its core drive,
                                             temperament, and evolutionary focus
    2     Amatyakaraka (AmK)  Amatya-karaka Career, vocation, counsel
    3     Bhratrukaraka(BK)   Bhratru-karaka Siblings, courage, effort
    4     Matrikaraka  (MK)   Matru-karaka  Mother, home, emotional foundation
    5     Putrakaraka  (PK)   Putra-karaka  Children, intelligence, creativity
    6     Gnatikaraka  (GK)   Gnati-karaka  Obstacles, extended relatives, disputes
    7     Darakaraka   (DK)   Dara-karaka   Spouse/life partner, partnerships

This is a well-established, widely-taught Jaimini technique — the ranking
RULE itself (sort by degree-in-sign, descending) is not seriously disputed.
Two scoping choices are worth being explicit about:

  - **7 karakas (this module) vs. 8 karakas.** Some traditions add Rahu as
    an 8th contender (ranked by its degree measured RETROGRADE, since Rahu
    always moves backward), which shifts every rank below Atmakaraka down
    by one and drops Gnatikaraka. Both the 7- and 8-karaka schemes are in
    active use; this module implements the 7-karaka version (Sun..Saturn
    only) as it's the simpler and more commonly taught starting point, and
    does not include Rahu here.
  - **Tie-breaking.** Classical texts describe tie-break rules (by
    nakshatra, then navamsa) for when two planets land on the exact same
    degree. With real ephemeris data (continuous floating-point degrees)
    an exact tie is astronomically negligible, so this module does not
    implement those tie-break rules — if a tie somehow occurs it falls back
    to a fixed planet-priority order, which is flagged in the result via
    `tie_broken`.

Atmakaraka in particular is the classical basis for "what is this soul
here to do" style analysis: whichever planet is Atmakaraka, its sign/house/
nakshatra placement is read as the soul's dominant quality and direction —
this module supplies the ranking; rule_engine.py supplies the interpretive
text (reusing the same verified planet_in_sign/planet_in_house KB entries
used everywhere else in this project, not a new invented layer).
"""

KARAKA_NAMES = [
    ("Atmakaraka", "AK", "The soul's core drive, temperament, and evolutionary focus"),
    ("Amatyakaraka", "AmK", "Career, vocation, and counsel"),
    ("Bhratrukaraka", "BK", "Siblings, courage, and effort"),
    ("Matrikaraka", "MK", "Mother, home, and emotional foundation"),
    ("Putrakaraka", "PK", "Children, intelligence, and creativity"),
    ("Gnatikaraka", "GK", "Obstacles, extended relatives, and disputes"),
    ("Darakaraka", "DK", "Spouse, life partner, and close partnerships"),
]

# Fixed planet-priority order used ONLY as a tie-break fallback (see
# module docstring) — classical dignity/precedence ordering.
_TIE_BREAK_PRIORITY = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

_KARAKA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def compute_chara_karakas(planet_degrees):
    """
    planet_degrees: {"Sun": degree_in_sign (0-30), "Moon": ..., ...} for the
        7 classical planets (extra keys, e.g. Rahu/Ketu, are ignored).

    Returns a list of 7 dicts, ranked highest-degree-first (index 0 =
    Atmakaraka .. index 6 = Darakaraka):
        {"rank": 1, "karaka": "Atmakaraka", "abbr": "AK", "domain": "...",
         "planet": "Sun", "degree_in_sign": 23.4567, "tie_broken": False}
    """
    entries = [(planet_degrees[p], p) for p in _KARAKA_PLANETS if p in planet_degrees]
    if len(entries) != 7:
        missing = set(_KARAKA_PLANETS) - set(planet_degrees)
        raise ValueError(f"compute_chara_karakas needs all 7 classical planets; missing: {sorted(missing)}")

    # Sort by degree descending; break exact ties by the fixed priority
    # order (see module docstring) rather than leaving Python's sort to
    # decide arbitrarily.
    def sort_key(entry):
        degree, planet = entry
        return (-degree, _TIE_BREAK_PRIORITY.index(planet))

    ranked = sorted(entries, key=sort_key)
    degrees_seen = [d for d, _ in ranked]
    has_tie = len(set(round(d, 6) for d in degrees_seen)) != len(degrees_seen)

    result = []
    for rank, (degree, planet) in enumerate(ranked, start=1):
        name, abbr, domain = KARAKA_NAMES[rank - 1]
        result.append({
            "rank": rank, "karaka": name, "abbr": abbr, "domain": domain,
            "planet": planet, "degree_in_sign": round(degree, 4),
            "tie_broken": has_tie,
        })
    return result


def get_karaka(chara_karakas, abbr):
    """Convenience lookup: get_karaka(result, 'AK') -> that karaka's dict."""
    for entry in chara_karakas:
        if entry["abbr"] == abbr:
            return entry
    raise KeyError(f"No karaka with abbr '{abbr}'")
