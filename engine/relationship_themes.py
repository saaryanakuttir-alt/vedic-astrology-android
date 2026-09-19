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
            f"{seventh_lord} (7th lord) sits in {seventh_lord_sign}, a dual sign - classically "
            "associated with more than one significant relationship theme."
        )
        score += 1
    if len(seventh_house_occupants) >= 2:
        indicators.append(
            f"{len(seventh_house_occupants)} planets share the 7th house "
            f"({', '.join(seventh_house_occupants)}) - classically read as more activity or "
            "complexity around partnership."
        )
        score += 1
    rahu_house = planets["Rahu"]["house"]
    ketu_house = planets["Ketu"]["house"]
    if seventh_lord_house in (rahu_house, ketu_house):
        axis_planet = "Rahu" if seventh_lord_house == rahu_house else "Ketu"
        indicators.append(
            f"{seventh_lord} (7th lord) shares a house with {axis_planet} - a classical marker of "
            "an unconventional or non-linear relationship path."
        )
        score += 1
    venus_sign = planets["Venus"]["sign"]
    if venus_sign in _DUAL_SIGNS:
        indicators.append(f"Venus sits in {venus_sign}, a dual sign - another classical multiplicity marker.")
        score += 1

    if score >= 3:
        tendency = "real complexity here - more than one significant relationship across life is a plausible reading"
    elif score >= 1:
        tendency = "some complexity, but nothing overwhelming - a mix of steadiness and change is more likely than either extreme"
    else:
        tendency = "a single, steady partnership rather than multiplicity"

    return {
        "seventh_lord": seventh_lord, "seventh_lord_sign": seventh_lord_sign,
        "indicators": indicators, "score": score, "tendency": tendency,
        "caveat": (
            "This is a TENDENCY, not a count - no classical method fixes an exact number of "
            "marriages or relationships from a natal chart alone. It also says nothing about a "
            "partner's behavior or fidelity - only about complexity/multiplicity themes in the "
            "native's own chart."
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


# ---------------------------------------------------------------------------
# Year-by-year relationship outlook (age 6 onward)
#
# For every year of life this scores how strongly the chart EMPHASISES
# relationships in that year, from four classical timing factors:
#   1. the Mahadasha / Antardasha / Pratyantardasha lords running at that
#      birthday - how closely each is tied to relationships (Venus, the 7th
#      lord = partnership, the 5th lord = romance and attraction, the 11th
#      lord = friendships and fulfilment of wishes, the Moon = emotional
#      needs), and whether it sits in the 5th or 7th house;
#   2. the Muntha (progressed Ascendant) falling in the 5th, 7th or 11th house;
#   3. Jupiter's transit that year occupying or aspecting the natal 7th / 5th
#      house.
# The result is a LEVEL (Low / Moderate / High / Very high) that compares the
# years of THIS chart with each other. It is NOT a real probability and not a
# prediction that anything happens. Before age 18 it is described only as
# friendships and close emotional bonds; romance/intimacy wording starts at 18.
# ---------------------------------------------------------------------------
import datetime as _dt

import ephemeris
from panchanga import SIGNS

YEARLY_FROM_AGE = 6
YEARLY_TO_AGE = 80
ADULT_AGE = 18

# (minimum score, level) - calibrated so that across many charts about a third
# of years read Low, a third Moderate, and the rest High / Very high.
_LEVELS = [(4.8, "Very high"), (3.4, "High"), (2.0, "Moderate"), (0.0, "Low")]

YEARLY_CAVEAT = (
    "This is a traditional-astrology indicator of when relationship themes are emphasised in THIS chart "
    "(from the Dasha periods, the progressed Ascendant and Jupiter's transit). It is not a real "
    "probability and not a prediction that anything will happen: the levels only compare the years of "
    "this one chart with each other. Before age 18 it describes friendships and close emotional bonds "
    "only. Free will and circumstances matter far more than any placement."
)

# Short plain descriptors, one set for adults and one for under-18s (no romance
# or partnership wording for children and teenagers).
_ROLE_TEXT = {
    "Venus": ("love and attraction", "affection and friendship"),
    "7th": ("rules your partnership house", "rules your close one-to-one bonds"),
    "5th": ("rules your romance house", "rules your affection-and-fun house"),
    "11th": ("rules your friendships-and-wishes house", "rules your friendships house"),
    "Moon": ("emotional needs", "feelings"),
}
_HOUSE_WORD = {
    5: ("romance", "affection and fun"),
    7: ("partnership", "close one-to-one bonds"),
    11: ("friendships and wishes", "friendships"),
}
_ROLE_POINTS = {"Venus": 2.0, "7th": 2.0, "5th": 1.5, "11th": 1.0, "Moon": 1.0}


def _kind_for_age(age):
    if age < 13:
        return "friendships and close attachments"
    if age < ADULT_AGE:
        return "friendships, crushes and close emotional bonds"
    return "romance or partnership (emotional or physical)"


def _level_for(score):
    for floor, name in _LEVELS:
        if score >= floor:
            return name
    return "Low"


def _roles(chart):
    """{planet: [role, ...]} for the planets whose dashas matter to relationships."""
    houses = chart["houses"]
    roles = {}
    for key, house in (("7th", 7), ("5th", 5), ("11th", 11)):
        roles.setdefault(SIGN_LORD[houses[house]], []).append(key)
    roles.setdefault("Venus", []).insert(0, "Venus")
    roles.setdefault("Moon", []).append("Moon")
    return roles


def _lord_score(planet, roles, chart):
    """(points, best role or None) for one running dasha lord."""
    mine = roles.get(planet, [])
    if not mine:
        return 0.0, None
    base = max(_ROLE_POINTS[r] for r in mine) + 0.5 * (len(mine) - 1)
    house = chart["planets"][planet]["house"]
    if house in (5, 7):
        base += 0.5
    return min(base, 3.0), max(mine, key=lambda r: _ROLE_POINTS[r])


def _jupiter_influence(jup_house):
    """Houses Jupiter occupies or aspects (5th, 7th, 9th from itself)."""
    return {jup_house} | {((jup_house - 1 + off) % 12) + 1 for off in (4, 6, 8)}


def yearly_relationship_outlook(chart, years, from_age=YEARLY_FROM_AGE, to_age=YEARLY_TO_AGE):
    """years: life_timeline.compute_life_timeline(...)["years"]. Returns
    {"from_age", "to_age", "years": [{age, calendar_year, score, level, kind,
    reasons, plain}], "standouts": [ages 18+ at High or above], "caveat"}."""
    roles = _roles(chart)
    asc_index = SIGNS.index(chart["ascendant"]["sign"])
    utc = _dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"])
    month, day = utc.month, utc.day

    jupiter_house = {}
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        for entry in years:
            if not from_age <= entry["age"] <= to_age:
                continue
            d = min(day, 28) if month == 2 else day
            jd = ephemeris.julian_day_ut(entry["calendar_year"], month, d, 12, 0, 0, utc_offset_hours=0.0)
            sign_idx = int(ephemeris.get_all_positions(jd)["Jupiter"] // 30)
            jupiter_house[entry["age"]] = (sign_idx - asc_index) % 12 + 1

    out = []
    for entry in years:
        age = entry["age"]
        if not from_age <= age <= to_age:
            continue
        minor = 1 if age < ADULT_AGE else 0        # index into the (adult, under-18) wording pairs
        points, why = 0.0, []
        for planet, weight, label in ((entry["mahadasha_lord"], 0.5, "main life period"),
                                      (entry["antardasha_lord"], 1.0, "sub-period"),
                                      (entry.get("pratyantardasha_lord"), 0.5, "current phase")):
            if not planet:
                continue
            pts, role = _lord_score(planet, roles, chart)
            if pts:
                points += weight * pts
                why.append((weight * pts, f"your {label} is ruled by {planet} ({_ROLE_TEXT[role][minor]})"))
        muntha_house = (age % 12) + 1
        if muntha_house in (5, 7, 11):
            points += 1.0
            why.append((1.0, f"the year's focus point falls on your {_HOUSE_WORD[muntha_house][minor]} house"))
        infl = _jupiter_influence(jupiter_house[age])
        if 7 in infl:
            points += 1.0
            why.append((1.0, f"Jupiter, the planet of good fortune, is looking at your {_HOUSE_WORD[7][minor]} house"))
        elif 5 in infl:
            points += 0.5
            why.append((0.5, f"Jupiter, the planet of good fortune, is looking at your {_HOUSE_WORD[5][minor]} house"))
        why.sort(key=lambda w: -w[0])
        level = _level_for(points)
        kind = _kind_for_age(age)
        top = [t for _, t in why[:2]]
        if top:
            plain = f"Mainly because {' and '.join(top)}."
        else:
            plain = "Nothing in the chart points to relationships this year."
        out.append({"age": age, "calendar_year": entry["calendar_year"], "score": round(points, 2),
                    "level": level, "kind": kind, "reasons": [t for _, t in why], "plain": plain})
    standouts = [y["age"] for y in out if y["age"] >= ADULT_AGE and y["level"] in ("High", "Very high")]
    return {"from_age": from_age, "to_age": to_age, "years": out, "standouts": standouts,
            "caveat": YEARLY_CAVEAT}
