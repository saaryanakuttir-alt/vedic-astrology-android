"""
transits.py — a weekly & monthly outlook built from CURRENT planetary
transits (Gochara) over the natal chart, plus the running Vimshottari
sub-period. Unlike rule_engine.py (which reads the fixed birth chart),
this is time-dependent: it asks "where are the planets right now, and
what do they mean relative to this person's birth Moon?"

Method (all classical, all offline):
  * Gochara from the Moon: each transiting planet's house counted from the
    native's natal Moon sign (Chandra Lagna). Classical texts list, per
    planet, which of those 12 houses give favourable vs. difficult results
    - see _GOCHARA_GOOD below.
  * Sade Sati: Saturn transiting the 12th, 1st or 2nd house from the natal
    Moon (its ~7.5-year passage), with the phase named.
  * The running Mahadasha / Antardasha at the forecast moment, for timing
    flavour.

This is a traditional, symbolic outlook - general tendencies for the
period, not a guarantee of specific events. Weekly vs. monthly differ in
which planets dominate: the fast Moon (and the running sub-period) colour
the week; the slower planets (Jupiter, Saturn, Rahu/Ketu) frame the month.
"""
import datetime as _dt

import ephemeris
from panchanga import SIGNS

# Gochara: houses (counted from the natal Moon) in which each transiting
# planet is classically said to give FAVOURABLE results. Anything else is
# read as more mixed/effortful. These are the standard textbook sets.
_GOCHARA_GOOD = {
    "Sun": {3, 6, 10, 11},
    "Moon": {1, 3, 6, 7, 10, 11},
    "Mars": {3, 6, 11},
    "Mercury": {2, 4, 6, 8, 10, 11},
    "Jupiter": {2, 5, 7, 9, 11},
    "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12},
    "Saturn": {3, 6, 11},
    "Rahu": {3, 6, 10, 11},
    "Ketu": {3, 6, 11},
}

# Plain, everyday description of what each planet's transit tends to touch.
_PLANET_THEME = {
    "Sun": "confidence, health, status and dealings with authority",
    "Moon": "mood, comfort, and day-to-day emotional weather",
    "Mars": "energy, drive, conflict and physical effort",
    "Mercury": "communication, paperwork, travel and decisions",
    "Jupiter": "growth, luck, learning, finances and optimism",
    "Venus": "relationships, comfort, money and pleasures",
    "Saturn": "responsibility, discipline, delays and hard lessons",
    "Rahu": "ambition, restlessness and unconventional pushes",
    "Ketu": "detachment, letting go and inward focus",
}

_MONTH_PLANETS = ["Jupiter", "Saturn", "Rahu", "Ketu"]   # slow movers frame the month
_WEEK_PLANETS = ["Moon", "Mercury", "Venus", "Sun", "Mars"]  # faster movers colour the week

_CAVEAT = (
    "This is a traditional Gochara (transit) outlook - general tendencies for the period read "
    "from where the planets are now relative to your birth Moon, plus your running dasha. It is "
    "for reflection, not a guarantee of specific events. Transit timing is approximate: the Moon "
    "changes sign every ~2-3 days, so the weekly notes shift within the week."
)


def _house_from(sign, moon_sign):
    """1-based house of `sign` counted from `moon_sign` (both sign names)."""
    return ((SIGNS.index(sign) - SIGNS.index(moon_sign)) % 12) + 1


def _ord(n):
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4..12 -> 'Nth'."""
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _naive_utc(dt):
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt


def _running_dasha(chart, at_dt):
    """Find the Mahadasha/Antardasha covering at_dt in the natal timeline."""
    at = _naive_utc(at_dt)
    for maha in chart["dasha"]["timeline"]:
        ms, me = _naive_utc(_asdt(maha["start"])), _naive_utc(_asdt(maha["end"]))
        if ms <= at < me:
            lord = maha["lord"]
            for an in maha["antardashas"]:
                as_, ae = _naive_utc(_asdt(an["start"])), _naive_utc(_asdt(an["end"]))
                if as_ <= at < ae:
                    return {"mahadasha": lord, "antardasha": an["lord"]}
            return {"mahadasha": lord, "antardasha": maha["antardashas"][-1]["lord"] if maha["antardashas"] else lord}
    return None


def _asdt(v):
    return _dt.datetime.fromisoformat(v) if isinstance(v, str) else v


def compute_transit_forecast(chart, at_dt=None):
    """chart: a dict from birth_chart.compute_birth_chart().
    at_dt: UTC datetime of the forecast moment (default: now).
    Returns a dict with structured transit data + readable weekly/monthly text.

    Wrapped in ephemeris.EPHEMERIS_LOCK - see that module's own note on why
    (pyswisseph is not thread-safe; this is the other top-level entry point
    in this project, besides compute_birth_chart, that touches it directly)."""
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        return _compute_transit_forecast_locked(chart, at_dt)


def _compute_transit_forecast_locked(chart, at_dt):
    if at_dt is None:
        at_dt = _dt.datetime.utcnow()
    jd = ephemeris.julian_day_ut(at_dt.year, at_dt.month, at_dt.day,
                                 at_dt.hour, at_dt.minute, at_dt.second, utc_offset_hours=0.0)
    positions = ephemeris.get_all_positions(jd)
    moon_sign = chart["planets"]["Moon"]["sign"]

    planet_transits = {}
    for planet, lon in positions.items():
        sign = SIGNS[int(lon // 30)]
        house = _house_from(sign, moon_sign)
        good = house in _GOCHARA_GOOD.get(planet, set())
        planet_transits[planet] = {
            "sign": sign, "house_from_moon": house,
            "favourable": good, "theme": _PLANET_THEME.get(planet, ""),
        }

    # Sade Sati: Saturn in 12th / 1st / 2nd from natal Moon.
    sat_house = planet_transits["Saturn"]["house_from_moon"]
    phase = {12: "first (rising) phase", 1: "peak phase", 2: "final (setting) phase"}.get(sat_house)
    sade_sati = {"active": phase is not None, "phase": phase, "saturn_house_from_moon": sat_house}

    running = _running_dasha(chart, at_dt)

    def line(planet):
        t = planet_transits[planet]
        verdict = "a generally favourable transit" if t["favourable"] else "a more mixed / effortful transit"
        return (f"{planet} is transiting {t['sign']} ({_ord(t['house_from_moon'])} from your Moon) - "
                f"{verdict} for {t['theme']}.")

    # --- Monthly outlook (slow planets + dasha) ---
    m = ["=== This Month ==="]
    if running:
        m.append(f"Running period: {running['mahadasha']} Mahadasha / {running['antardasha']} Antardasha - "
                 f"this sets the underlying tone for the whole stretch.")
    for p in _MONTH_PLANETS:
        m.append(line(p))
    if sade_sati["active"]:
        m.append(f"Sade Sati is currently active ({sade_sati['phase']}): Saturn is in the {_ord(sat_house)} from "
                 f"your Moon. Traditionally a demanding, maturing ~7.5-year passage - steady effort and "
                 f"patience are the classic advice, not alarm.")
    good_m = [p for p in _MONTH_PLANETS if planet_transits[p]["favourable"]]
    m.append("In simple terms: this month leans " + (
        "generally supportive" if len(good_m) >= 2 else "toward effort and patience") +
        ". Focus on the areas the favourable planets above touch, and go steadily where the mixed ones do.")

    # --- Weekly outlook (fast planets) ---
    w = ["=== This Week ==="]
    for p in _WEEK_PLANETS:
        w.append(line(p))
    if running:
        w.append(f"The {running['antardasha']} sub-period continues to flavour these days.")
    good_w = [p for p in _WEEK_PLANETS if planet_transits[p]["favourable"]]
    w.append("In simple terms: " + (
        "a broadly positive few days - good for moving things forward." if len(good_w) >= 3 else
        "a mixed few days - pick your moments and avoid forcing things.") +
        " Remember the Moon shifts sign every 2-3 days, so the mood changes through the week.")

    return {
        "as_of": at_dt.replace(microsecond=0).isoformat() + "Z",
        "moon_sign": moon_sign,
        "planet_transits": planet_transits,
        "sade_sati": sade_sati,
        "running_dasha": running,
        "weekly_text": "\n".join(w),
        "monthly_text": "\n".join(m),
        "caveat": _CAVEAT,
    }
