"""varshaphal.py - the yearly (Tajika) chart: the Varsha Pravesh moment when the Sun returns to its birth
position, the chart cast for it, the Muntha, the Mudda Vimshottari periods of the year and a plain
good / mixed / needs-care outlook for that year. Wording is a tendency, never a fixed event.
"""
import datetime as _dt
import zoneinfo

import swisseph as swe

import ephemeris
from extras import BODIES, _HOUSE_AREA, _TONE_GIST, _TONE_PHRASE, ordinal, house_verdicts, planet_considerations
from panchanga import SIGNS

_DAYS_PER_YEAR = 365.2422
_MUDDA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
_MUDDA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
_NAKSHATRA_LORD = [_MUDDA_ORDER[i % 9] for i in range(27)]            # Ashwini -> Ketu, Bharani -> Venus, ...

_MUNTHA_KIND = {h: "good" for h in (1, 2, 3, 5, 9, 10, 11)}
_MUNTHA_KIND.update({4: "mixed", 7: "mixed", 6: "care", 8: "care", 12: "care"})
_MUNTHA_TEXT = {
    "good": "The Muntha falls in a supportive house, so the year's main focus tends to go well and give you backing in %s.",
    "mixed": "The Muntha falls in a house that brings a mix of easy and effortful stretches, so %s may ask for some give-and-take this year.",
    "care": "The Muntha falls in a house that asks for care, so %s may need extra patience and looking after this year.",
}


def _sun_return_jd(natal_sun_lon, near_jd):
    """The Julian day (UT) at which the sidereal Sun is at `natal_sun_lon`, found from a starting guess."""
    jd = near_jd
    for _ in range(12):
        lon = ephemeris.get_planet_longitude(jd, "Sun")
        diff = (natal_sun_lon - lon + 180) % 360 - 180
        jd += diff / 0.9856
        if abs(diff) < 1e-8:
            break
    return jd


def _jd_to_utc(jd):
    y, m, d, h = swe.revjul(jd)
    return _dt.datetime(y, m, d) + _dt.timedelta(hours=h)


def return_moment(chart, year):
    """UTC datetime of the Sun's return to its birth degree in calendar `year`."""
    bi = chart["birth_input"]
    by, bm, bd = (int(x) for x in bi["birth_date"].split("-"))
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        guess = swe.julday(year, bm, bd, 12.0)
        jd = _sun_return_jd(chart["planets"]["Sun"]["longitude"], guess)
    return _jd_to_utc(jd)


def varsha_chart(chart, year):
    """The chart cast for the Varsha Pravesh moment of `year`, at the birth place."""
    from birth_chart import compute_birth_chart
    loc, bi = chart["resolved_location"], chart["birth_input"]
    utc = return_moment(chart, year).replace(tzinfo=_dt.timezone.utc)
    local = utc.astimezone(zoneinfo.ZoneInfo(loc["tz_name"]))
    v = compute_birth_chart(name=f"{chart.get('name') or 'Chart'} - Varsha {year}", birth_date=(local.year, local.month, local.day),
                            birth_time=(local.hour, local.minute, local.second), place_name=bi.get("place_name") or "",
                            latitude=loc["latitude"], longitude=loc["longitude"], tz_name=loc["tz_name"],
                            dasha_years_forward=2, sex=bi.get("sex"))
    v["varsha"] = {"year": year, "local": local.replace(tzinfo=None), "utc": utc.replace(tzinfo=None)}
    return v


def muntha(chart, varsha, age):
    """Muntha: the birth Lagna sign moved forward one sign for each completed year of age."""
    idx = (SIGNS.index(chart["ascendant"]["sign"]) + age) % 12
    sign = SIGNS[idx]
    house = (idx - SIGNS.index(varsha["ascendant"]["sign"])) % 12 + 1
    return {"sign": sign, "house": house}


def mudda_dasha(chart, varsha, age):
    """The nine Mudda Vimshottari periods of the year (the 120-year cycle squeezed into one solar year).
    The first period belongs to the lord of the nakshatra reached by moving the birth Moon nakshatra on by
    one nakshatra per completed year."""
    span = 360.0 / 27
    nak_no = int(chart["planets"]["Moon"]["longitude"] // span)          # 0-based
    idx = _MUDDA_ORDER.index(_NAKSHATRA_LORD[(nak_no + age) % 27])
    start = varsha["varsha"]["local"]          # shown in the birth place's own time
    year_days = _DAYS_PER_YEAR
    out, t = [], start
    for k in range(9):
        lord = _MUDDA_ORDER[(idx + k) % 9]
        end = t + _dt.timedelta(days=_MUDDA_YEARS[lord] * 3 * year_days / 360.0)
        out.append({"lord": lord, "start": t, "end": end, "days": round((end - t).total_seconds() / 86400)})
        t = end
    return out


def _house_text(kind, house):
    return _MUNTHA_TEXT[kind] % _HOUSE_AREA[house]


def varshaphal(chart, year):
    """Everything for one year: {year, age, varsha (chart), local, muntha, mudda, outlook}. `year` is the
    calendar year in which the birthday falls; age = completed years at that birthday."""
    birth_year = int(chart["birth_input"]["birth_date"][:4])
    age = year - birth_year
    v = varsha_chart(chart, year)
    m = muntha(chart, v, age)
    mudda = mudda_dasha(chart, v, age)
    cons = planet_considerations(v)
    hv = {h["house"]: h for h in house_verdicts(v)}
    lagna_lord = hv[1]["lord"]
    for period in mudda:
        c = cons[period["lord"]]
        period.update(house=c["house"], tone=c["tone"], area=_HOUSE_AREA[c["house"]])
    kind = _MUNTHA_KIND[m["house"]]
    summary = (f"The year starting {v['varsha']['local']:%d %b %Y} has the {v['ascendant']['sign']} sign rising. Its ruler {lagna_lord} "
               f"{_TONE_PHRASE[cons[lagna_lord]['tone']]} in the yearly chart. The Muntha is in {m['sign']}, the {ordinal(m['house'])} house "
               f"({_HOUSE_AREA[m['house']]}). " + _house_text(kind, m["house"]))
    return {"year": year, "age": age, "varsha": v, "local": v["varsha"]["local"], "muntha": {**m, "kind": kind},
            "mudda": mudda, "lagna_lord": lagna_lord, "lagna_lord_tone": cons[lagna_lord]["tone"], "summary": summary,
            "houses": [hv[h] for h in range(1, 13)], "considerations": cons}


def varshaphal_text(vp, compact=False):
    """Reader-friendly text in the '--- Heading ---' convention."""
    parts = [f"--- Your year from {vp['local']:%d %b %Y} (age {vp['age']}) ---\n{vp['summary']}\n\n"
             f"[In simple terms: the yearly chart is a fresh map for the year that begins on your birthday. The Muntha shows the "
             f"life area that gets the spotlight, and the periods below show how the mood changes through the year. These are "
             f"tendencies, not fixed events.]"]
    tone_idx = {"Good": 0, "Mostly good": 0, "Mixed": 1, "Needs some care": 2, "Challenging": 2}
    from extras import _EFFECTS
    parts.append("--- The year's periods (Mudda Dasha) ---\nThe year is split into nine periods, each coloured by one planet as placed in "
                 "the yearly chart.")
    for p in vp["mudda"]:
        line = (f"{p['lord']} period, {p['start']:%d %b %Y} to {p['end']:%d %b %Y} ({p['days']} days): {p['lord']} "
                f"{_TONE_PHRASE[p['tone']]} in the yearly chart and sits in the {ordinal(p['house'])} house, so this stretch is felt "
                f"through {p['area']}.")
        if not compact:
            line += " What may happen: " + _EFFECTS[p["lord"]][tone_idx[p["tone"]]]
        parts.append(line)
    if not compact:
        parts.append("--- The yearly chart's 12 houses at a glance ---\n" + "\n\n".join(
            f"{ordinal(h['house'])} house ({h['area']}): {h['tone']}. {h['may_happen']}" for h in vp["houses"]))
    return "\n\n".join(parts)
