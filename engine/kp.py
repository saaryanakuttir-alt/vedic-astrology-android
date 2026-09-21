"""kp.py - Krishnamurti Paddhati (KP) tables: Placidus cusps, the star / sub / sub-sub lord of every cusp and
planet, ruling planets and house significators. Uses the KP (new) ayanamsa, which is the Lahiri ayanamsa
less 5'24" (0.09 degree); planets are the same as the main chart shifted by that amount.
"""
import swisseph as swe

import ephemeris
from astrology_tables import SIGN_LORD
from extras import BODIES
from panchanga import SIGNS

KP_OFFSET = 0.09                                         # degrees: Lahiri ayanamsa minus KP-new ayanamsa
ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
NAK = 360.0 / 27
_DAYLORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]        # Monday-first is handled below


def _split(start, span, first_lord):
    """The nine Vimshottari divisions of a stretch beginning at `start`: [(lord, from, to)]."""
    out, pos, i0 = [], start, ORDER.index(first_lord)
    for k in range(9):
        lord = ORDER[(i0 + k) % 9]
        width = span * YEARS[lord] / 120.0
        out.append((lord, pos, pos + width))
        pos += width
    return out


def lords(longitude):
    """(sign lord, star lord, sub lord, sub-sub lord) for a sidereal (KP) longitude in degrees."""
    lon = longitude % 360
    sign_lord = SIGN_LORD[SIGNS[int(lon // 30)]]
    n = min(int(lon // NAK), 26)
    star = ORDER[n % 9]
    sub = subsub = None
    for s_lord, a, b in _split(n * NAK, NAK, star):
        if a <= lon < b or s_lord == ORDER[(ORDER.index(star) + 8) % 9]:
            sub = s_lord
            for ss_lord, a2, b2 in _split(a, b - a, s_lord):
                if a2 <= lon < b2:
                    subsub = ss_lord
                    break
            subsub = subsub or ORDER[(ORDER.index(s_lord) + 8) % 9]
            break
    return sign_lord, star, sub, subsub


def _dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round(((deg - d) * 60 - m) * 60)
    if s == 60:
        s, m = 0, m + 1
    if m == 60:
        m, d = 0, d + 1
    return f"{d:03d}-{m:02d}-{s:02d}"


def kp_tables(chart):
    """{ayanamsa, cusps: [...], planets: [...], ruling: {...}, significators: {...}}."""
    jd = chart["resolved_datetime"]["julian_day_ut"]
    loc = chart["resolved_location"]
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        ayan = ephemeris.get_ayanamsa(jd) - KP_OFFSET
        cusps_trop, _ascmc = swe.houses(jd, loc["latitude"], loc["longitude"], b"P")
    cusp_lon = [(c - ayan) % 360 for c in cusps_trop]
    cusps = []
    for i, lon in enumerate(cusp_lon, start=1):
        sl, st, sb, ss = lords(lon)
        cusps.append({"cusp": i, "longitude": lon, "dms": _dms(lon), "sign": SIGNS[int(lon // 30)], "sign_lord": sl,
                      "star_lord": st, "sub_lord": sb, "subsub_lord": ss})

    def house_of(lon):
        for i in range(12):
            a, b = cusp_lon[i], cusp_lon[(i + 1) % 12]
            if (a <= lon < b) if a < b else (lon >= a or lon < b):
                return i + 1
        return 1

    planets = []
    for p in BODIES:
        lon = (chart["planets"][p]["longitude"] + KP_OFFSET) % 360
        sl, st, sb, ss = lords(lon)
        planets.append({"planet": p, "longitude": lon, "dms": _dms(lon), "sign": SIGNS[int(lon // 30)], "house": house_of(lon),
                        "sign_lord": sl, "star_lord": st, "sub_lord": sb, "subsub_lord": ss,
                        "retrograde": bool(chart["planets"][p].get("retrograde"))})
    by = {x["planet"]: x for x in planets}

    # ruling planets: lagna and Moon (sign / star / sub lords) and the weekday lord
    weekday = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]                      # Monday = 0
    import datetime
    y, m, d = (int(v) for v in chart["birth_input"]["birth_date"].split("-"))
    ruling = {"Lagna": (cusps[0]["sign_lord"], cusps[0]["star_lord"], cusps[0]["sub_lord"]),
              "Moon": (by["Moon"]["sign_lord"], by["Moon"]["star_lord"], by["Moon"]["sub_lord"]),
              "Day lord": weekday[datetime.date(y, m, d).weekday()]}

    # significators of each house, strongest first: planets in the star of an occupant, occupants,
    # planets in the star of the house's owner (cusp sign lord), and the owner itself
    sig = {}
    for h in range(1, 13):
        occupants = [p["planet"] for p in planets if p["house"] == h]
        owner = cusps[h - 1]["sign_lord"]
        levels = [[p["planet"] for p in planets if p["star_lord"] in occupants], occupants,
                  [p["planet"] for p in planets if p["star_lord"] == owner], [owner]]
        seen, ordered = set(), []
        for lvl in levels:
            for pl in lvl:
                if pl not in seen:
                    seen.add(pl)
                    ordered.append(pl)
        sig[h] = ordered
    return {"ayanamsa": ayan, "ayanamsa_dms": _dms(ayan), "cusps": cusps, "planets": planets, "ruling": ruling, "significators": sig}


# ---------------------------------------------------------------- KP Vimshottari: maha / antar / pratyantar
def kp_dasha(chart, years=100):
    """[{lord, start, end, antardashas: [{lord, start, end, pratyantars: [{lord, start, end}]}]}] using the KP Moon.
    Only periods that end after birth are kept; the first period starts at birth."""
    import datetime as dt
    day = dt.timedelta(days=1)
    birth = dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"]).replace(tzinfo=None)
    # the KP Moon is 0.09 degree ahead of the Lahiri Moon; local clock time is used for the dates shown
    offset = dt.datetime.fromisoformat(chart["resolved_datetime"]["local"]).replace(tzinfo=None) - birth
    moon = (chart["planets"]["Moon"]["longitude"] + KP_OFFSET) % 360
    n = int(moon // NAK)
    first = ORDER[n % 9]
    left = 1 - (moon % NAK) / NAK
    t = birth - day * (YEARS[first] * (1 - left) * 365.25)
    limit = birth + day * (years * 365.25)
    out, i = [], ORDER.index(first)
    while t < limit:
        lord = ORDER[i % 9]
        end = t + day * (YEARS[lord] * 365.25)
        antars, s = [], t
        for k in range(9):
            a = ORDER[(ORDER.index(lord) + k) % 9]
            ae = s + day * (YEARS[lord] * YEARS[a] / 120.0 * 365.25)
            if ae > birth:
                pr, ps = [], s
                for m in range(9):
                    pl = ORDER[(ORDER.index(a) + m) % 9]
                    pe = ps + day * (YEARS[lord] * YEARS[a] * YEARS[pl] / 14400.0 * 365.25)
                    if pe > birth:
                        pr.append({"lord": pl, "start": max(ps, birth) + offset, "end": pe + offset})
                    ps = pe
                antars.append({"lord": a, "start": max(s, birth) + offset, "end": ae + offset, "pratyantars": pr})
            s = ae
        out.append({"lord": lord, "start": max(t, birth) + offset, "end": end + offset, "antardashas": antars})
        t, i = end, i + 1
    return out
