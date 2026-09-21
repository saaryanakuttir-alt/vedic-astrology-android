"""
life_timeline.py — a year-by-year life outlook: for every age from birth to
a chosen horizon, which Vimshottari Mahadasha/Antardasha was (or will be)
running, and what that combination classically points to.

METHOD — worth being explicit about, since "yearly predictions" can mean
several different classical techniques:
  * This module uses DASHA (which planet's multi-year, then sub-year,
    period governs a given age) as the primary timing layer, plus MUNTHA
    (the natal Ascendant progressed forward by one sign per year of age —
    a simple, well-established supplementary technique) for a second,
    independent per-year data point.
  * It does NOT compute a true Varshphal (solar-return) chart — casting a
    fresh chart for the exact moment the transiting Sun returns to its
    natal degree each year, with its own Varshesh (year-lord) derived from
    that chart. That is a real, more elaborate classical system; this
    project's Dasha+Muntha approach is the more commonly practiced
    "which years are governed by which planet" technique, reuses this
    project's own already-verified Dasha timeline (dasha.py) and Ascendant
    computation directly, and needs no new ephemeris work to compute for
    every age from 0-100 at once. If a true annual solar-return chart is
    wanted later, it is a natural follow-on, not a rewrite of this.

Both Dasha and Muntha are read from data ALREADY on the chart - no new
astronomical computation happens here, just arithmetic over what
birth_chart.compute_birth_chart() and dasha.compute_vimshottari_timeline()
already produced. This keeps the whole 0-100-year table effectively free to
compute (no per-year ephemeris calls) and, just as important, keeps every
age's dasha lord in exact agreement with the Dasha tab elsewhere in this
app, since it is the literal same timeline data, not a re-derivation.
"""
import datetime as _dt

from dasha import find_running_dasha
from panchanga import SIGNS
from i18n import tbl, tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

CAVEAT = (
    "This year-by-year outlook is built from two classical, well-established techniques: which "
    "Vimshottari Dasha period (Mahadasha/Antardasha) governs each age, and Muntha (the natal "
    "Ascendant progressed one sign per year of age). It is NOT a true Varshphal (solar-return) "
    "chart - a more elaborate classical system this app does not yet compute. Read every year's "
    "note as a general TENDENCY for that stretch of life, not a guarantee that a specific event "
    "happens in that specific year - classical timing techniques indicate THEMES and windows of "
    "likelihood, not a fixed calendar of events."
)


def _naive(dt_value):
    if isinstance(dt_value, str):
        dt_value = _dt.datetime.fromisoformat(dt_value)
    return dt_value.replace(tzinfo=None) if getattr(dt_value, "tzinfo", None) else dt_value


def _birthday_at_age(birth_utc, age):
    """birth_utc advanced by exactly `age` years, same calendar month/day -
    handled the ordinary way a birthday works (a Feb-29 native's birthday
    in a non-leap year falls back to Feb 28, matching how everyone actually
    treats that date, rather than raising or drifting to March 1)."""
    year = birth_utc.year + age
    try:
        return birth_utc.replace(year=year)
    except ValueError:
        return birth_utc.replace(year=year, month=2, day=28)


def _houses_ruled_by(planet, sign_of_house):
    """Which of the 12 houses (1-12) this planet rules, given `sign_of_house`
    = {house_num: sign} (chart["houses"]) - i.e. the reverse of the usual
    SIGN_LORD lookup, built fresh here rather than imported: this is the
    only place in the project that needs "which houses does X planet own"
    rather than "who owns house N", so it isn't worth a shared module for
    one caller."""
    from astrology_tables import SIGN_LORD
    return [h for h, sign in sign_of_house.items() if SIGN_LORD[sign] == planet]


# Muntha's sign each year is read through the SAME plain-house-meaning
# lens the rest of this app already uses for house themes (see
# rule_engine.py's _PLAIN_HOUSE) - duplicated here in short form rather
# than importing rule_engine (which imports the KB loader and a great deal
# else this module has no use for) for one small dict.
_MUNTHA_HOUSE_THEME = tbl({
    1: "the self, health, and how you come across",
    2: "money, family, and speech",
    3: "effort, courage, and siblings",
    4: "home, comfort, and inner peace",
    5: "creativity, romance, and learning",
    6: "work, routine, and obstacles to push through",
    7: "partnerships and one-to-one dealings",
    8: "change, shared resources, and the unexpected",
    9: "fortune, learning, and long journeys",
    10: "career and public standing",
    11: "income, goals, and your wider circle",
    12: "rest, release, and things winding down",
})


def age_for_date(chart, target_dt):
    """Whole-number age this person is (or will be) on target_dt - used by
    the combined Predictions UI to look up the matching entry in an
    already-computed years[] list (compute_life_timeline's output) for
    whatever specific date the user picks, without recomputing anything."""
    birth_utc = _naive(_dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"]))
    target = _naive(target_dt)
    age = target.year - birth_utc.year
    if (target.month, target.day) < (birth_utc.month, birth_utc.day):
        age -= 1
    return max(0, age)


def compute_life_timeline(chart, dasha_readings, start_age=0, end_age=100):
    """chart: from birth_chart.compute_birth_chart(). dasha_readings: the
    "dasha" dict rule_engine.generate_reading() already built (its
    "timeline" list, with each mahadasha/antardasha KB reading attached -
    reused here so every year's note can quote the SAME already-verified
    antardasha summary text the Dasha tab shows, not a fresh lookup).

    Returns {"years": [ {age, calendar_year, mahadasha_lord,
    antardasha_lord, pratyantardasha_lord, houses_activated, leaning,
    muntha_sign, muntha_theme, note}, ... ], "caveat": CAVEAT}.
    """
    # module-level import would be circular (rule_engine imports this module)
    from rule_engine import _PLAIN_HOUSE, _STRONG_HOUSES, _WEAK_HOUSES

    # dasha.py's own timeline stores naive UTC datetimes (see dasha.py) while
    # chart["resolved_datetime"]["utc"] is an ISO string WITH a +00:00
    # offset - strip it here (via the same _naive() helper this module
    # already defines) so birthday comparisons against the timeline below
    # don't raise "can't compare offset-naive and offset-aware datetimes".
    birth_utc = _naive(_dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"]))
    natal_asc_sign = chart["ascendant"]["sign"]
    natal_asc_index = SIGNS.index(natal_asc_sign)
    houses = chart["houses"]
    timeline = chart["dasha"]["timeline"]

    # A quick lookup from (mahadasha_lord, antardasha_lord) -> that
    # antardasha's already-computed KB reading, built once rather than
    # re-searching timeline_readings per age.
    antar_reading_by_pair = {}
    for maha in dasha_readings["timeline"]:
        for antar in maha["antardashas"]:
            antar_reading_by_pair[(maha["lord"], antar["lord"])] = antar["reading"]

    years = []
    for age in range(start_age, end_age + 1):
        birthday = _birthday_at_age(birth_utc, age)
        running = find_running_dasha(timeline, birthday)
        if running is None:
            continue  # past the computed timeline's horizon (dasha.py's own years_forward)

        maha_lord, antar_lord = running["mahadasha_lord"], running["antardasha_lord"]
        pratyantar_lord = running.get("pratyantardasha_lord")
        houses_activated = sorted(set(_houses_ruled_by(maha_lord, houses)) | set(_houses_ruled_by(antar_lord, houses)))
        house_themes = [_PLAIN_HOUSE[h] for h in houses_activated if h in _PLAIN_HOUSE]
        # Whether the houses this year's rulers govern lean classically
        # supportive (kendra/trikona) or effortful (dusthana) - the same
        # _STRONG_HOUSES/_WEAK_HOUSES classification _plain_life_gloss
        # already uses elsewhere, reused here for a genuine "is this an
        # easier or harder year" signal rather than just naming the houses.
        strong_hit = [h for h in houses_activated if h in _STRONG_HOUSES]
        weak_hit = [h for h in houses_activated if h in _WEAK_HOUSES]
        if strong_hit and not weak_hit:
            leaning = tx("a classically supportive, easier-going stretch overall")
        elif weak_hit and not strong_hit:
            leaning = tx("a classically more effortful stretch - progress is still possible, just with more friction")
        elif strong_hit and weak_hit:
            leaning = tx("a mixed stretch - real support in some areas, real friction in others")
        else:
            leaning = tx("a fairly neutral, workable stretch")

        muntha_sign = SIGNS[(natal_asc_index + (age % 12)) % 12]
        muntha_theme = _MUNTHA_HOUSE_THEME.get((age % 12) + 1, "")

        antar_reading = antar_reading_by_pair.get((maha_lord, antar_lord))
        antar_gist = (antar_reading.get("summary") if antar_reading else None) or ""
        antar_detail = (antar_reading.get("effects") if antar_reading else None) or ""

        note_bits = [
            tr('Age {0} (around {1}) runs under your {2} Mahadasha / {3} Antardasha', age, birthday.year, maha_lord, antar_lord)
            + (tr(' / {0} Pratyantardasha', pratyantar_lord) if pratyantar_lord else "") + "."
        ]
        if house_themes:
            note_bits.append(
                tr('{0} and {1} between them rule house', antar_lord, maha_lord)
                + ("s " if len(houses_activated) != 1 else " ")
                + ", ".join(str(h) for h in houses_activated)
                + tr(' - so this year leans toward themes of {0}, overall {1}.', ', and '.join(house_themes), leaning)
            )
        if antar_detail:
            note_bits.append(antar_detail)
        elif antar_gist:
            note_bits.append(antar_gist)
        note_bits.append(
            tr('Muntha (the progressed Ascendant) falls in {0} this year, adding a secondary emphasis on {1}.', muntha_sign, muntha_theme)
        )

        years.append({
            "age": age,
            "calendar_year": birthday.year,
            "mahadasha_lord": maha_lord,
            "antardasha_lord": antar_lord,
            "pratyantardasha_lord": pratyantar_lord,
            "houses_activated": houses_activated,
            "leaning": leaning,
            "muntha_sign": muntha_sign,
            "muntha_theme": muntha_theme,
            "note": " ".join(note_bits),
        })

    return {"years": years, "caveat": tx(CAVEAT)}
