"""
manglik.py — Mangal Dosha ("Kuja Dosha" / "Manglik") assessment: the
classical check for whether Mars sits in one of the traditionally
inauspicious-for-marriage houses (1st, 2nd, 4th, 7th, 8th, or 12th),
counted from three different reference points.

This is a genuinely tradition-dependent area of classical astrology:
  - EVERY source agrees on checking Mars from the LAGNA (Ascendant).
  - MOST sources also check Mars from the MOON.
  - SOME (fewer) sources additionally check Mars from VENUS.
  - Sources also disagree on which of the 6 houses matter for which
    reference point, and on a long list of classical CANCELLATION
    (Mangal Dosha Nivarana) conditions (Mars in its own/exalted sign,
    aspects from benefics, etc.) that this module does NOT attempt to
    apply — those require judgment calls this project isn't scoping in.

Rather than assert one verdict, this module reports the raw fact (which
houses Mars occupies from each reference point) and a per-reference-point
flag, and leaves the combined "is this person Manglik" judgment to the
reader — consistent with how yogas.py's own YOGA-22 (Kuja Dosha, Lagna
only) already handles this. No cancellation conditions are checked; that
is called out explicitly in the returned dict.
"""
from houses import get_house_of_sign

DOSHA_HOUSES = {1, 2, 4, 7, 8, 12}

CANCELLATION_NOTE = (
    "This checks raw house placement only. Classical cancellation "
    "conditions (Mangal Dosha Nivarana) — e.g. Mars in its own sign "
    "(Aries/Scorpio) or exaltation (Capricorn), or a benefic aspect on "
    "Mars — are NOT evaluated here and can nullify a dosha shown as "
    "present below."
)


def _mars_house_from(mars_sign, reference_sign):
    return get_house_of_sign(reference_sign, mars_sign)


def compute_manglik_dosha(mars_sign, ascendant_sign, moon_sign, venus_sign=None):
    """Returns a dict with Mars's house-distance from Lagna, Moon, and
    (if given) Venus, plus a boolean dosha flag for each and an overall
    `any_present` flag. See module docstring for the important caveats."""
    from_lagna = _mars_house_from(mars_sign, ascendant_sign)
    from_moon = _mars_house_from(mars_sign, moon_sign)
    result = {
        "mars_sign": mars_sign,
        "from_lagna": {"house": from_lagna, "dosha_present": from_lagna in DOSHA_HOUSES},
        "from_moon": {"house": from_moon, "dosha_present": from_moon in DOSHA_HOUSES},
        "from_venus": None,
        "cancellation_conditions_checked": False,
        "note": CANCELLATION_NOTE,
    }
    if venus_sign is not None:
        from_venus = _mars_house_from(mars_sign, venus_sign)
        result["from_venus"] = {"house": from_venus, "dosha_present": from_venus in DOSHA_HOUSES}
    result["any_present"] = (
        result["from_lagna"]["dosha_present"]
        or result["from_moon"]["dosha_present"]
        or (result["from_venus"]["dosha_present"] if result["from_venus"] else False)
    )
    return result
