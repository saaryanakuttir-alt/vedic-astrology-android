"""
dasha.py — computes the full Vimshottari Mahadasha + Antardasha timeline
for a birth chart, from the Moon's exact sidereal longitude at birth.

Matches the durations, fixed running order, and antardasha duration
formula already verified and documented in vimshottari_mahadasha.json and
vimshottari_antardasha.json — this module is the "calculator" counterpart
to those two static reference/interpretation files, not a replacement for
them: use this to find WHICH dasha/antardasha is running at a given time,
then look up that planet pair in vimshottari_antardasha.json for the
interpretation.

METHOD:
1. The Moon's nakshatra at birth determines which planet's Mahadasha is
   running at the moment of birth (see panchanga.NAKSHATRA_LORD).
2. How far through that nakshatra the Moon already was (degree_in_nakshatra
   / 13°20') tells us what FRACTION of that Mahadasha had already elapsed
   before birth — so the first Mahadasha in the timeline is a PARTIAL
   period, and everything after it runs full-length in the fixed cyclic
   order (Ketu -> Venus -> Sun -> Moon -> Mars -> Rahu -> Jupiter ->
   Saturn -> Mercury -> Ketu -> ...).
3. Within each Mahadasha, the 9 Antardashas always start with the
   Mahadasha's OWN lord first, then continue around the same fixed cyclic
   order. Each Antardasha's length = mahadasha_years * antardasha_years / 120
   years (equivalent to the mahadasha_years * antardasha_years / 10 MONTHS
   formula used in vimshottari_antardasha.json).

1 Vimshottari "year" is treated as 365.25 days (the standard convention
used by virtually all Vedic astrology software for this calculation).
"""
import datetime

from panchanga import NAKSHATRA_SPAN, get_nakshatra

DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
MAHADASHA_YEARS = {"Sun": 6, "Moon": 10, "Mars": 7, "Mercury": 17, "Jupiter": 16,
                    "Venus": 20, "Saturn": 19, "Rahu": 18, "Ketu": 7}
TOTAL_CYCLE_YEARS = 120
DAYS_PER_YEAR = 365.25


def _years_to_timedelta(years):
    return datetime.timedelta(days=years * DAYS_PER_YEAR)


def _next_lord(lord):
    i = DASHA_SEQUENCE.index(lord)
    return DASHA_SEQUENCE[(i + 1) % 9]


def _build_sub_periods(parent_lord, parent_start, parent_years, parent_end):
    """Generic ONE-LEVEL Vimshottari sub-division: 9 sub-periods within a
    parent period, starting from the parent period's own lord and cycling
    through DASHA_SEQUENCE, each sub-period's length = parent_years *
    THAT_LORD's_mahadasha_years / 120. The formula is identical at every
    level of the Vimshottari hierarchy (Mahadasha -> Antardasha ->
    Pratyantardasha -> ...), so this one function backs both
    _build_antardashas (Antardasha-within-Mahadasha) and
    compute_pratyantardashas (Pratyantardasha-within-Antardasha) below,
    rather than duplicating the loop at each level.

    parent_end is the CALLER's independently-computed end of the parent
    period (a single direct addition). We force the final sub-period's
    `end` to be exactly this value rather than trusting the cumulative sum
    of 9 separately-rounded timedeltas, which can drift from it by a
    sub-microsecond amount due to floating-point rounding at each step.
    Without this, exact-equality chaining checks (sub-period chain end ==
    parent end == next parent start) could spuriously fail."""
    periods = []
    cursor = parent_start
    lord = parent_lord
    for i in range(9):
        if i == 8:
            end = parent_end  # anchor the last sub-period to the exact parent end
        else:
            sub_years = parent_years * MAHADASHA_YEARS[lord] / TOTAL_CYCLE_YEARS
            end = cursor + _years_to_timedelta(sub_years)
        periods.append({"lord": lord, "start": cursor, "end": end})
        cursor = end
        lord = _next_lord(lord)
    return periods


def _build_antardashas(maha_lord, maha_start, maha_years, maha_end):
    """9 antardashas for one mahadasha, starting from the mahadasha's own
    lord. See _build_sub_periods above - this is just that generic
    one-level division applied at the Mahadasha level."""
    return _build_sub_periods(maha_lord, maha_start, maha_years, maha_end)


def compute_pratyantardashas(antardasha):
    """9 pratyantardashas (the 3rd Vimshottari level) within ONE
    antardasha dict ({"lord", "start", "end"} - e.g. from a mahadasha's
    "antardashas" list, or from find_running_dasha's antardasha lookup).

    Computed ON DEMAND for a single antardasha rather than eagerly for the
    whole 120-year timeline: eagerly expanding all 9 mahadashas x 9
    antardashas x 9 pratyantardashas would be 729 stored periods per
    chart for a level of detail most readings never need - this way a
    caller (UI or rule_engine) asks for pratyantardashas only for
    whichever antardasha it's actually displaying (usually just the one
    currently running)."""
    antar_years = (antardasha["end"] - antardasha["start"]).total_seconds() / (86400.0 * DAYS_PER_YEAR)
    return _build_sub_periods(antardasha["lord"], antardasha["start"], antar_years, antardasha["end"])


def find_running_pratyantardasha(antardasha, at_datetime):
    """Given one antardasha dict and a datetime known to fall within it
    (e.g. from find_running_dasha), returns the lord of the
    pratyantardasha running at that moment, or the last one if float
    rounding puts at_datetime a hair past the final boundary."""
    pratyantardashas = compute_pratyantardashas(antardasha)
    for p in pratyantardashas:
        if p["start"] <= at_datetime < p["end"]:
            return p["lord"]
    return pratyantardashas[-1]["lord"]


def compute_vimshottari_timeline(birth_datetime_utc, moon_longitude, years_forward=120):
    """
    birth_datetime_utc: a datetime.datetime (UTC, naive is fine — this
        module only does relative arithmetic, it doesn't care about timezone
        as long as it's consistent).
    moon_longitude: Moon's SIDEREAL longitude at birth (degrees, 0-360) —
        from ephemeris.get_all_positions()["Moon"].
    years_forward: how far past the birth date to generate the timeline.
        120 (default) covers one full Vimshottari cycle from birth, which
        exceeds any human lifespan.

    Returns a list of mahadasha dicts, each shaped:
        {"lord": "Venus", "start": datetime, "end": datetime,
         "is_partial_at_birth": bool,
         "antardashas": [{"lord": "Venus", "start": ..., "end": ...}, ...]}
    The FIRST mahadasha in the list is the one running at birth (with
    is_partial_at_birth=True, since only part of it falls after the birth
    moment) — start/end here still describe the FULL period, so you can see
    how much had already elapsed before birth; antardashas within it are
    also computed for the full period, so look up which one contains the
    birth datetime to find the running antardasha at birth.
    """
    _, _, birth_lord, degree_in_nakshatra = get_nakshatra(moon_longitude)
    fraction_elapsed = degree_in_nakshatra / NAKSHATRA_SPAN

    birth_maha_years = MAHADASHA_YEARS[birth_lord]
    elapsed_time = _years_to_timedelta(fraction_elapsed * birth_maha_years)
    # The full mahadasha "started" this long before the birth moment.
    first_maha_start = birth_datetime_utc - elapsed_time

    timeline = []
    cursor = first_maha_start
    lord = birth_lord
    cutoff = birth_datetime_utc + datetime.timedelta(days=years_forward * DAYS_PER_YEAR)

    while cursor < cutoff:
        maha_years = MAHADASHA_YEARS[lord]
        maha_end = cursor + _years_to_timedelta(maha_years)
        antardashas = _build_antardashas(lord, cursor, maha_years, maha_end)
        timeline.append({
            "lord": lord,
            "start": cursor,
            "end": maha_end,
            "is_partial_at_birth": cursor < birth_datetime_utc < maha_end and cursor == first_maha_start,
            "antardashas": antardashas,
        })
        cursor = maha_end
        lord = _next_lord(lord)

    return timeline


def format_balance_at_birth(timeline, birth_datetime_utc):
    """Returns {"lord": ..., "years": int, "months": int, "days": int} for
    how much of the FIRST (birth) mahadasha remained at the moment of
    birth — the "Dasa Balance" figure shown on a traditional chart
    printout (e.g. "Ketu 4Y 5M 28D"). Uses the same 365.25-day year
    convention as the rest of this module, with a 30.4375-day (365.25/12)
    average month — cross-checked against a real reference chart and
    matched to within a day (ordinary rounding noise from the tiny
    Moon-position differences documented in this project's verification
    notes)."""
    first = timeline[0]
    remaining_days = (first["end"] - birth_datetime_utc).total_seconds() / 86400.0
    years = int(remaining_days // DAYS_PER_YEAR)
    remaining_days -= years * DAYS_PER_YEAR
    avg_month_days = DAYS_PER_YEAR / 12.0
    months = int(remaining_days // avg_month_days)
    remaining_days -= months * avg_month_days
    days = round(remaining_days)
    return {"lord": first["lord"], "years": years, "months": months, "days": days}


def find_running_dasha(timeline, at_datetime):
    """Given a timeline from compute_vimshottari_timeline(), find which
    mahadasha, antardasha, AND pratyantardasha are running at a given
    datetime (e.g. 'now', or the birth moment itself). Returns
        {"mahadasha_lord": ..., "antardasha_lord": ..., "pratyantardasha_lord": ...}
    or None if at_datetime falls outside the computed timeline range. The
    pratyantardasha is computed lazily (see compute_pratyantardashas) only
    for the one antardasha that matched - no eager 729-period expansion."""
    for maha in timeline:
        if maha["start"] <= at_datetime < maha["end"]:
            for antar in maha["antardashas"]:
                if antar["start"] <= at_datetime < antar["end"]:
                    return {
                        "mahadasha_lord": maha["lord"], "antardasha_lord": antar["lord"],
                        "pratyantardasha_lord": find_running_pratyantardasha(antar, at_datetime),
                    }
            # Fell in the mahadasha but not any antardasha window (float
            # rounding at the very last instant) — treat as the last one.
            last_antar = maha["antardashas"][-1]
            return {
                "mahadasha_lord": maha["lord"], "antardasha_lord": last_antar["lord"],
                "pratyantardasha_lord": find_running_pratyantardasha(last_antar, at_datetime),
            }
    return None
