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
        "caveat": RELATIONSHIP_CAVEAT,
        "seventh_house_lord": {
            "lord": seventh_lord, "sign": seventh_sign, "placed_in_house": seventh_lord_house,
            "in_dusthana": {
                "present": seventh_lord_house in DUSTHANA_HOUSES,
                "detail": f"{seventh_lord} (7th lord) is placed in house {seventh_lord_house}.",
            },
            "malefic_conjunction": {
                "present": bool(malefics_conjunct_7th_lord),
                "planets": malefics_conjunct_7th_lord,
                "detail": (f"{seventh_lord} (7th lord) is conjunct {', '.join(malefics_conjunct_7th_lord)}."
                           if malefics_conjunct_7th_lord else f"{seventh_lord} (7th lord) has no natural malefic conjunction."),
            },
            "malefic_aspect": {
                "present": bool(malefics_aspecting_7th_lord),
                "planets": malefics_aspecting_7th_lord,
                "detail": (f"{seventh_lord} (7th lord) is aspected by {', '.join(malefics_aspecting_7th_lord)}."
                           if malefics_aspecting_7th_lord else f"{seventh_lord} (7th lord) has no natural malefic aspect."),
            },
        },
        "venus_mars": {
            "conjunction": {
                "present": venus_mars_conjunction,
                "detail": f"Venus (house {venus_house}) and Mars (house {mars_house})"
                          + (" are conjunct." if venus_mars_conjunction else " are not conjunct."),
            },
            "mutual_aspect": {
                "present": venus_mars_mutual_aspect,
                "detail": "Venus and Mars aspect each other." if venus_mars_mutual_aspect
                          else "Venus and Mars do not aspect each other.",
            },
        },
        "rahu": {
            "conjunct_venus": {
                "present": rahu_venus_conjunction,
                "detail": "Rahu is conjunct Venus." if rahu_venus_conjunction else "Rahu is not conjunct Venus.",
            },
            "in_seventh_house": {
                "present": rahu_in_7th,
                "detail": "Rahu occupies the 7th house." if rahu_in_7th else f"Rahu occupies house {rahu_house}, not the 7th.",
            },
        },
        "crowded_seventh_house": {
            "present": len(seventh_house_occupants) >= 3,
            "occupants": seventh_house_occupants,
            "detail": (f"{len(seventh_house_occupants)} planet{'s' if len(seventh_house_occupants) != 1 else ''} "
                       f"in the 7th house ({', '.join(seventh_house_occupants)})."
                       if seventh_house_occupants else "No planets in the 7th house."),
        },
        "venus_afflicted": {
            "present": venus_dignity == "debilitated" or venus_combust,
            "dignity": venus_dignity, "combust": venus_combust,
            "detail": f"Venus is {venus_dignity}" + (", and combust" if venus_combust else "") + " in this chart.",
        },
    }
