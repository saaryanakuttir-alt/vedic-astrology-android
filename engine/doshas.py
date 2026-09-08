"""doshas.py — classical afflictions beyond Mangal Dosha (which stays in
manglik.py, unchanged): Pitra Dosha, Guru Chandal Dosha, Grahan Dosha, and
Shrapit Dosha.

Same discipline as manglik.py: report the RAW conjunction/placement fact
and a per-indicator `present` flag, no combined verdict, no classical
cancellation (Nivarana) conditions applied. Pitra Dosha in particular has
real cross-source disagreement on exactly which combination counts (see
PITRA_NOTE below) - this module picks one commonly-cited formulation and
says so plainly rather than presenting it as the single correct rule.
"""
from astrology_tables import SIGN_LORD, NATURAL_MALEFICS

RAHU_KETU = {"Rahu", "Ketu"}

PITRA_NOTE = (
    "Pitra Dosha (ancestral affliction) has real disagreement across "
    "classical sources on exactly which combination qualifies - some "
    "texts look only at the 9th house, others at the Sun specifically, "
    "others at both. This checks three commonly-cited indicators "
    "independently rather than asserting one is THE rule."
)


def _house_planets(chart):
    by_house = {h: [] for h in range(1, 13)}
    for planet, detail in chart["planets"].items():
        by_house[detail["house"]].append(planet)
    return by_house


def assess_pitra_dosha(chart):
    """Three independent, commonly-cited Pitra Dosha indicators - see
    PITRA_NOTE. No combined verdict."""
    planets = chart["planets"]
    houses = chart["houses"]
    by_house = _house_planets(chart)

    ninth_sign = houses[9]
    ninth_lord = SIGN_LORD[ninth_sign]
    ninth_lord_house = planets[ninth_lord]["house"]

    rahu_ketu_in_9th = [p for p in by_house[9] if p in RAHU_KETU]
    sun_house = planets["Sun"]["house"]
    sun_conjunct_shadow = [p for p in by_house[sun_house] if p in RAHU_KETU]
    lord_conjunct_malefic = [
        p for p in by_house[ninth_lord_house] if p in NATURAL_MALEFICS and p != ninth_lord
    ]

    return {
        "note": PITRA_NOTE,
        "rahu_ketu_in_9th": {
            "present": bool(rahu_ketu_in_9th), "planets": rahu_ketu_in_9th,
            "detail": (f"{', '.join(rahu_ketu_in_9th)} in the 9th house." if rahu_ketu_in_9th
                       else "Neither Rahu nor Ketu is in the 9th house."),
        },
        "sun_conjunct_rahu_ketu": {
            "present": bool(sun_conjunct_shadow), "planets": sun_conjunct_shadow,
            "detail": (f"Sun is conjunct {', '.join(sun_conjunct_shadow)}." if sun_conjunct_shadow
                       else "Sun is not conjunct Rahu or Ketu."),
        },
        "ninth_lord_afflicted": {
            "present": bool(lord_conjunct_malefic), "lord": ninth_lord, "planets": lord_conjunct_malefic,
            "detail": (f"{ninth_lord} (9th lord) is conjunct {', '.join(lord_conjunct_malefic)}."
                       if lord_conjunct_malefic else f"{ninth_lord} (9th lord) has no natural-malefic conjunction."),
        },
    }


def assess_guru_chandal_dosha(chart):
    """Jupiter conjunct Rahu - classically read as Jupiter's wisdom/guru
    significations being colored by Rahu's amplifying, boundary-pushing
    nature, sometimes toward unconventional or misguided teachers."""
    planets = chart["planets"]
    jup_house = planets["Jupiter"]["house"]
    rahu_house = planets["Rahu"]["house"]
    present = jup_house == rahu_house
    return {
        "present": present,
        "jupiter_house": jup_house, "rahu_house": rahu_house,
        "detail": ("Jupiter is conjunct Rahu." if present
                   else f"Jupiter (house {jup_house}) and Rahu (house {rahu_house}) are not conjunct."),
    }


def assess_grahan_dosha(chart):
    """Sun or Moon conjunct Rahu or Ketu (the 'eclipse axis') - two
    independent checks, Surya (Sun) and Chandra (Moon) Grahan Dosha."""
    planets = chart["planets"]
    by_house = _house_planets(chart)

    def check(luminary):
        house = planets[luminary]["house"]
        shadow = [p for p in by_house[house] if p in RAHU_KETU]
        return {
            "present": bool(shadow), "planets": shadow,
            "detail": (f"{luminary} is conjunct {', '.join(shadow)}." if shadow
                       else f"{luminary} is not conjunct Rahu or Ketu."),
        }

    return {"surya_grahan": check("Sun"), "chandra_grahan": check("Moon")}


def assess_shrapit_dosha(chart):
    """Saturn conjunct Rahu ('Shrapit Yog') - classically read as a
    curse-like affliction: sudden reversals, delays compounding on
    delays, family-pattern themes."""
    planets = chart["planets"]
    sat_house = planets["Saturn"]["house"]
    rahu_house = planets["Rahu"]["house"]
    present = sat_house == rahu_house
    return {
        "present": present,
        "saturn_house": sat_house, "rahu_house": rahu_house,
        "detail": ("Saturn is conjunct Rahu." if present
                   else f"Saturn (house {sat_house}) and Rahu (house {rahu_house}) are not conjunct."),
    }
