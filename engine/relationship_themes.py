"""relationship_themes.py — classical indicators sometimes discussed under
"marital discord" or "fidelity" in Parashari texts: affliction to the 7th
house/lord, Venus-Mars-Rahu combinations, and a crowded 7th house.

FRAMING MATTERS HERE MORE THAN ANYWHERE ELSE IN THIS PROJECT. Every
indicator below is reported as a RAW FACT with NO combined verdict,
exactly like manglik.py's own Mangal Dosha check - this module goes
further and deliberately avoids the word "infidelity" in any indicator's
own text, using "commitment/monogamy themes" or "relationship complexity"
instead. Reasons:

  1. These are classical correlations with RELATIONSHIP TENDENCIES in the
     NATIVE's own chart - restlessness, difficulty with exclusivity,
     attraction to multiple people, turbulence in partnership. They are
     NOT a prediction of behavior, NOT a character judgment, and NOT
     evidence about any specific real event.
  2. A chart belongs to ONE person. It cannot show what a PARTNER did or
     will do. This module must never be read as evidence about someone
     else - only as a reflective lens on the native's own tendencies.
  3. Free will matters more than any placement here. Classical texts
     themselves treat these as tendencies to be conscious of, not a
     fate to submit to.

Only D1 (Rasi) indicators are checked - matching manglik.py's own scope
(no D9/Navamsa marriage-house analysis, no cancellation conditions, no
combined "verdict"). See RELATIONSHIP_CAVEAT below, which should be
surfaced in the UI every time this data is shown, not just noted here.
"""
from astrology_tables import (
    NATURAL_MALEFICS, DUSTHANA_HOUSES, SIGN_LORD, get_dignity, planet_aspects_house,
)
import combustion
from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

RELATIONSHIP_CAVEAT = (
    "These are classical correlations with relationship TENDENCIES in the native's "
    "OWN chart - restlessness, difficulty with exclusivity, turbulence in "
    "partnership - not a prediction of behavior, not a character judgment, and not "
    "evidence about any specific event. A chart belongs to one person: it cannot "
    "show what a partner did or will do, and should never be used as evidence "
    "against someone else. Classical texts themselves treat these as tendencies to "
    "be conscious of, not a fate to submit to - free will matters more than any "
    "single placement. No combined verdict is given below, deliberately: read each "
    "indicator on its own, the same way this project's Mangal Dosha check works."
)


# Dual (mutable) signs - classically the multiplicity/duality signs.
# Duplicated here rather than imported from divisional.py (which defines
# the same set for a different purpose) since this is the only place in
# this module that needs it - not worth a cross-module import for one set.
_DUAL_SIGNS = {"Gemini", "Virgo", "Sagittarius", "Pisces"}


def marriage_count_tendency(chart):
    """A descriptive TENDENCY (never an exact count - no classical method
    fixes one from a natal chart alone, the same honesty-over-false-
    precision approach this project uses for Longevity and Children) for
    whether this chart's classical multiple-relationship indicators lean
    toward a single steady partnership or toward more complexity/
    multiplicity. Uses: the 7th lord's sign (dual vs. fixed/movable), how
    many planets share the 7th house, whether the 7th lord sits with
    Rahu/Ketu, and Venus's sign - all standard classical multiplicity
    markers, combined into ONE band rather than a fabricated digit."""
    planets = chart["planets"]
    houses = chart["houses"]
    seventh_sign = houses[7]
    seventh_lord = SIGN_LORD[seventh_sign]
    seventh_lord_sign = planets[seventh_lord]["sign"]
    seventh_lord_house = planets[seventh_lord]["house"]
    seventh_house_occupants = [p for p, d in planets.items() if d["house"] == 7]

    indicators = []
    score = 0
    if seventh_lord_sign in _DUAL_SIGNS:
        indicators.append(
            tr('{0} (7th lord) sits in {1}, a dual sign - classically associated with more than one significant '
               'relationship theme.', seventh_lord, seventh_lord_sign)
        )
        score += 1
    if len(seventh_house_occupants) >= 2:
        indicators.append(
            tr('{0} planets share the 7th house ({1}) - classically read as more activity or complexity around '
               'partnership.', len(seventh_house_occupants), ', '.join(seventh_house_occupants))
        )
        score += 1
    rahu_house = planets["Rahu"]["house"]
    ketu_house = planets["Ketu"]["house"]
    if seventh_lord_house in (rahu_house, ketu_house):
        axis_planet = "Rahu" if seventh_lord_house == rahu_house else "Ketu"
        indicators.append(
            tr('{0} (7th lord) shares a house with {1} - a classical marker of an unconventional or non-linear '
               'relationship path.', seventh_lord, axis_planet)
        )
        score += 1
    venus_sign = planets["Venus"]["sign"]
    if venus_sign in _DUAL_SIGNS:
        indicators.append(tr('Venus sits in {0}, a dual sign - another classical multiplicity marker.', venus_sign))
        score += 1

    if score >= 3:
        tendency = tx("real complexity here - more than one significant relationship across life is a plausible reading")
    elif score >= 1:
        tendency = tx("some complexity, but nothing overwhelming - a mix of steadiness and change is more likely than either extreme")
    else:
        tendency = tx("a single, steady partnership rather than multiplicity")

    return {
        "seventh_lord": seventh_lord, "seventh_lord_sign": seventh_lord_sign,
        "indicators": indicators, "score": score, "tendency": tendency,
        "caveat": (
            tx("This is a TENDENCY, not a count - no classical method fixes an exact number of "
            "marriages or relationships from a natal chart alone. It also says nothing about a "
            "partner's behavior or fidelity - only about complexity/multiplicity themes in the "
            "native's own chart.")
        ),
    }


def _house_planets(chart):
    by_house = {h: [] for h in range(1, 13)}
    for planet, detail in chart["planets"].items():
        by_house[detail["house"]].append(planet)
    return by_house


def assess_relationship_themes(chart):
    """Returns a dict of independent indicators, each with its own raw
    fact and a `present` flag - no combined score or verdict. See module
    docstring for why."""
    planets = chart["planets"]
    houses = chart["houses"]
    by_house = _house_planets(chart)

    seventh_sign = houses[7]
    seventh_lord = SIGN_LORD[seventh_sign]
    seventh_lord_house = planets[seventh_lord]["house"]

    # Which malefics are conjunct (same house as) or aspecting the 7th lord.
    malefics_conjunct_7th_lord = [
        p for p in by_house[seventh_lord_house] if p in NATURAL_MALEFICS and p != seventh_lord
    ]
    malefics_aspecting_7th_lord = [
        p for p, d in planets.items()
        if p in NATURAL_MALEFICS and p != seventh_lord
        and planet_aspects_house(p, d["house"], seventh_lord_house)
    ]

    venus_house = planets["Venus"]["house"]
    mars_house = planets["Mars"]["house"]
    venus_mars_conjunction = venus_house == mars_house
    venus_mars_mutual_aspect = (
        planet_aspects_house("Venus", venus_house, mars_house)
        or planet_aspects_house("Mars", mars_house, venus_house)
    )

    rahu_house = planets["Rahu"]["house"]
    rahu_venus_conjunction = rahu_house == venus_house
    rahu_in_7th = rahu_house == 7

    seventh_house_occupants = by_house[7]

    venus_sign = planets["Venus"]["sign"]
    venus_dignity = get_dignity("Venus", venus_sign)
    venus_combust = combustion.is_combust(
        "Venus", planets["Sun"]["longitude"], planets["Venus"]["longitude"],
        planets["Venus"].get("retrograde", False),
    )

    return {
        "caveat": tx(RELATIONSHIP_CAVEAT),
        "seventh_house_lord": {
            "lord": seventh_lord, "sign": seventh_sign, "placed_in_house": seventh_lord_house,
            "in_dusthana": {
                "present": seventh_lord_house in DUSTHANA_HOUSES,
                "detail": tr('{0} (7th lord) is placed in house {1}.', seventh_lord, seventh_lord_house),
            },
            "malefic_conjunction": {
                "present": bool(malefics_conjunct_7th_lord),
                "planets": malefics_conjunct_7th_lord,
                "detail": (tr('{0} (7th lord) is conjunct {1}.', seventh_lord, ', '.join(malefics_conjunct_7th_lord))
                           if malefics_conjunct_7th_lord else tr('{0} (7th lord) has no natural malefic conjunction.', seventh_lord)),
            },
            "malefic_aspect": {
                "present": bool(malefics_aspecting_7th_lord),
                "planets": malefics_aspecting_7th_lord,
                "detail": (tr('{0} (7th lord) is aspected by {1}.', seventh_lord, ', '.join(malefics_aspecting_7th_lord))
                           if malefics_aspecting_7th_lord else tr('{0} (7th lord) has no natural malefic aspect.', seventh_lord)),
            },
        },
        "venus_mars": {
            "conjunction": {
                "present": venus_mars_conjunction,
                "detail": tr('Venus (house {0}) and Mars (house {1})', venus_house, mars_house)
                          + (tx(" are conjunct.") if venus_mars_conjunction else tx(" are not conjunct.")),
            },
            "mutual_aspect": {
                "present": venus_mars_mutual_aspect,
                "detail": tx("Venus and Mars aspect each other.") if venus_mars_mutual_aspect
                          else tx("Venus and Mars do not aspect each other."),
            },
        },
        "rahu": {
            "conjunct_venus": {
                "present": rahu_venus_conjunction,
                "detail": tx("Rahu is conjunct Venus.") if rahu_venus_conjunction else tx("Rahu is not conjunct Venus."),
            },
            "in_seventh_house": {
                "present": rahu_in_7th,
                "detail": tx("Rahu occupies the 7th house.") if rahu_in_7th else tr('Rahu occupies house {0}, not the 7th.', rahu_house),
            },
        },
        "crowded_seventh_house": {
            "present": len(seventh_house_occupants) >= 3,
            "occupants": seventh_house_occupants,
            "detail": (tr('{0} planet{1} in the 7th house ({2}).', len(seventh_house_occupants), 's' if len(seventh_house_occupants) != 1 else '', ', '.join(seventh_house_occupants))
                       if seventh_house_occupants else tx("No planets in the 7th house.")),
        },
        "venus_afflicted": {
            "present": venus_dignity == "debilitated" or venus_combust,
            "dignity": venus_dignity, "combust": venus_combust,
            "detail": tr('Venus is {0}', venus_dignity) + (tx(", and combust") if venus_combust else "") + tx(" in this chart."),
        },
    }
