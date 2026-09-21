"""shadbala.py - planetary strength from the parts of the classical six-fold strength (Shadbala) that can be
worked out from the chart alone, each in virupas (60 virupas = 1 rupa) for the seven planets:

    Sthana  : Uchcha (nearness to exaltation), Saptavargaja (dignity across seven divisional charts),
              Ojayugma (odd/even sign), Kendra (angular house), Drekkana
    Dig     : the direction of the house the planet sits in
    Kala    : Nathonnatha (day/night), Paksha (Moon phase), Tribhaga (part of day), Vara (weekday lord),
              Hora (hour lord), Ayana (declination)
    Naisargika : each planet's fixed natural strength

NOT included (they need year/month lord tables, planetary speeds against mean positions, or graded aspect
values): Abda, Masa, Cheshta, Drik and Yuddha bala. So the totals here are called "strength points" and
should be read as a comparison between the planets of one chart, not as the traditional Shadbala rupas.
"""
import datetime as _dt
import math

from astrology_tables import SIGN_LORD
from divisional import d7_saptamsha
from maitri import CLASSICAL_SEVEN, panchadha_maitri
from panchanga import SIGNS
from i18n import tbl, tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

SEVEN = CLASSICAL_SEVEN
_DEBIL_POINT = {"Sun": 190.0, "Moon": 213.0, "Mars": 118.0, "Mercury": 345.0, "Jupiter": 275.0, "Venus": 177.0, "Saturn": 20.0}
_MOOLATRIKONA = {"Sun": ("Leo", 0, 20), "Moon": ("Taurus", 3, 30), "Mars": ("Aries", 0, 12), "Mercury": ("Virgo", 16, 20),
                 "Jupiter": ("Sagittarius", 0, 10), "Venus": ("Libra", 0, 15), "Saturn": ("Aquarius", 0, 20)}
_GRADE_POINTS = {"Adhi Mitra": 22.5, "Mitra": 15.0, "Sama": 7.5, "Shatru": 3.75, "Adhi Shatru": 1.875}
_NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.86, "Jupiter": 34.29, "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57}
_WEEKDAY = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]           # Monday first
_DIG_STRONG = {"Jupiter": "asc", "Mercury": "asc", "Sun": "mc", "Mars": "mc", "Saturn": "desc", "Moon": "ic", "Venus": "ic"}
_ODD_SIGNS = set(SIGNS[0::2])

COMPONENTS = [("uchcha", "Uchcha (exaltation)"), ("saptavargaja", "Saptavargaja (7 charts)"), ("ojayugma", "Ojayugma (odd/even)"),
              ("kendra", "Kendra (angular)"), ("drekkana", "Drekkana"), ("dig", "Dig (direction)"),
              ("nathonnatha", "Nathonnatha (day/night)"), ("paksha", "Paksha (Moon phase)"), ("tribhaga", "Tribhaga"),
              ("vara", "Vara (weekday)"), ("hora", "Hora (hour)"), ("ayana", "Ayana (declination)"),
              ("naisargika", "Naisargika (natural)")]


def _angle(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _sign_in(chart, planet, varga):
    if varga == "D1":
        return chart["planets"][planet]["sign"]
    if varga == "D7":
        return d7_saptamsha(chart["planets"][planet]["longitude"])
    return chart["planets"][planet]["vargas"][varga]


def _saptavargaja(chart, p):
    total = 0.0
    house = chart["planets"][p]["house"]
    for varga in ("D1", "D2", "D3", "D7", "D9", "D12", "D30"):
        sign = _sign_in(chart, p, varga)
        lord = SIGN_LORD[sign]
        if varga == "D1":
            sname, a, b = _MOOLATRIKONA[p]
            deg = chart["planets"][p]["degree_in_sign"]
            if sign == sname and a <= deg < b:
                total += 45.0
                continue
        if lord == p:
            total += 30.0
        else:
            grade = panchadha_maitri(p, lord, house, chart["planets"][lord]["house"])["grade"]
            total += _GRADE_POINTS[grade]
    return total


def _declination(chart, planet):
    """Declination in degrees from the planet's tropical longitude (the classical 'kranti'; latitude is ignored)."""
    tropical = chart["planets"][planet]["longitude"] + chart["resolved_datetime"]["ayanamsa_value_deg"]
    return math.degrees(math.asin(math.sin(math.radians(23.45)) * math.sin(math.radians(tropical))))


def _hour_lord(chart):
    """The lord of the planetary hour at birth (counted from local sunrise, one hour each)."""
    bi = chart["birth_input"]
    y, m, d = (int(v) for v in bi["birth_date"].split("-"))
    day_lord = _WEEKDAY[_dt.date(y, m, d).weekday()]
    rise = chart["day_details"]["sunrise_local"]
    h, mi, s = (int(v) for v in rise.split(":"))
    bh, bmi, bs = (int(v) for v in bi["birth_time_local"].split(":")[:3])
    hours = ((bh * 3600 + bmi * 60 + bs) - (h * 3600 + mi * 60 + s)) / 3600.0
    if hours < 0:
        hours += 24
    order = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]          # the order the hours follow each other
    return order[(order.index(day_lord) + int(hours)) % 7], day_lord


def _day_parts(chart):
    """(seconds since sunrise, day length, sunset length ...) needed for the day/night parts, in hours."""
    bi = chart["birth_input"]
    dd = chart["day_details"]
    to_h = lambda t: sum(int(v) * f for v, f in zip(t.split(":")[:3], (1, 1 / 60, 1 / 3600)))
    rise, sset = to_h(dd["sunrise_local"]), to_h(dd["sunset_local"])
    birth = to_h(bi["birth_time_local"])
    return birth, rise, sset


def compute_shadbala(chart):
    """{planet: {component: virupas, ..., 'total': x, 'rupas': x/60, 'rank': n, 'tone': ...}} for the seven planets."""
    pl = chart["planets"]
    asc, mc = chart["ascendant"]["longitude"], chart["ascendant"]["mc_longitude"]
    strong_point = {"asc": asc, "mc": mc, "desc": (asc + 180) % 360, "ic": (mc + 180) % 360}
    birth, rise, sset = _day_parts(chart)
    noon = (rise + sset) / 2
    day_fraction = max(0.0, 60.0 * (12 - min(abs(birth - noon), 12)) / 12)                   # 60 at midday, 0 at midnight
    elong = _angle(pl["Moon"]["longitude"], pl["Sun"]["longitude"])
    benefic_paksha = elong / 3.0
    hour_lord, day_lord = _hour_lord(chart)
    if rise <= birth < sset:                                                                   # day birth: three parts of the day
        part = min(int((birth - rise) / ((sset - rise) / 3.0)), 2)
        tri = ["Mercury", "Sun", "Saturn"][part]
    else:
        night_len = 24 - (sset - rise)
        since = (birth - sset) % 24
        part = min(int(since / (night_len / 3.0)), 2)
        tri = ["Moon", "Venus", "Mars"][part]
    out = {}
    decl = {p: _declination(chart, p) for p in SEVEN}
    for p in SEVEN:
        d = pl[p]
        lon = d["longitude"]
        c = {}
        c["uchcha"] = _angle(lon, _DEBIL_POINT[p]) / 3.0
        c["saptavargaja"] = _saptavargaja(chart, p)
        signs = (d["sign"], d["vargas"]["D9"])
        wants_even = p in ("Moon", "Venus")
        c["ojayugma"] = 15.0 * sum(1 for s in signs if (s not in _ODD_SIGNS) == wants_even)
        c["kendra"] = {1: 60, 4: 60, 7: 60, 10: 60, 2: 30, 5: 30, 8: 30, 11: 30}.get(d["house"], 15.0)
        c["drekkana"] = 0.0
        third = int(d["degree_in_sign"] // 10)
        if (p in ("Sun", "Mars", "Jupiter") and third == 0) or (p in ("Mercury", "Saturn") and third == 1) or (p in ("Moon", "Venus") and third == 2):
            c["drekkana"] = 15.0
        c["dig"] = (180 - _angle(lon, strong_point[_DIG_STRONG[p]])) / 3.0
        c["nathonnatha"] = 60.0 if p == "Mercury" else day_fraction if p in ("Sun", "Jupiter", "Venus") else 60.0 - day_fraction
        c["paksha"] = (benefic_paksha * (2 if p == "Moon" else 1)) if p in ("Moon", "Mercury", "Jupiter", "Venus") else 60.0 - benefic_paksha
        c["tribhaga"] = 60.0 if p == "Jupiter" or p == tri else 0.0
        c["vara"] = 45.0 if p == day_lord else 0.0
        c["hora"] = 60.0 if p == hour_lord else 0.0
        north = (23.45 + decl[p]) / 46.9 * 60 if p not in ("Moon", "Saturn") else (23.45 - decl[p]) / 46.9 * 60
        c["ayana"] = min(max((23.45 + abs(decl[p])) / 46.9 * 60, 0), 60) if p == "Mercury" else min(max(north, 0), 60)
        if p == "Sun":
            c["ayana"] *= 2
        c["naisargika"] = _NAISARGIKA[p]
        c["total"] = sum(c[k] for k, _ in COMPONENTS)
        c["sthana"] = c["uchcha"] + c["saptavargaja"] + c["ojayugma"] + c["kendra"] + c["drekkana"]
        c["kala"] = c["nathonnatha"] + c["paksha"] + c["tribhaga"] + c["vara"] + c["hora"] + c["ayana"]
        out[p] = c
    ranked = sorted(SEVEN, key=lambda x: -out[x]["total"])
    for rank, p in enumerate(ranked, start=1):
        out[p]["rank"] = rank
        out[p]["tone"] = "Strong" if rank <= 2 else "Average" if rank <= 5 else "Weaker"
    return out


_TONE_TEXT = tbl({
    "Strong": "one of the strongest planets in your chart, so its themes tend to come through clearly and reliably",
    "Average": "of middling strength, so its themes come through steadily but need some effort",
    "Weaker": "among the weaker planets in your chart, so its themes may need extra effort and support",
})
_STRENGTH_THEME = tbl({"Sun": "confidence and vitality", "Moon": "mind and emotional steadiness", "Mars": "energy and courage",
                   "Mercury": "thinking and communication", "Jupiter": "wisdom and good fortune", "Venus": "love and comfort",
                   "Saturn": "discipline and endurance"})


def shadbala_text(chart):
    sb = compute_shadbala(chart)
    parts = [tx("--- Planet strength ---\nEach planet is scored on several classical sources of strength: how close it is to its exalted sign, how "
             "it fares across seven divisional charts, whether it sits in a strong house or direction, the time of day and Moon phase at "
             "your birth, and its own natural strength. The scores are compared between the planets of your own chart. "
             "[In simple terms: a stronger planet delivers its good qualities more easily; a weaker one needs more effort and support. "
             "It is a comparison, not a verdict on your life.]")]
    for p in sorted(SEVEN, key=lambda x: sb[x]["rank"]):
        c = sb[p]
        best = max(COMPONENTS, key=lambda kv: c[kv[0]] / 60.0)
        parts.append(tr('{0} - rank {1} of 7 ({2}): {3:.0f} points. Its {4} are {5}. Its strongest support comes from '
                        '{6}.', p, c['rank'], c['tone'], c['total'], _STRENGTH_THEME[p], _TONE_TEXT[c['tone']], best[1].split(' (')[0]))
    return "\n\n".join(parts)
