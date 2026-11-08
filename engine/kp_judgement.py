"""kp_judgement.py - what each KP cusp sub lord says, and KP horary (prashna) by the 1-249 number.

KP is a separate system from the Parashari knowledge base; its rules live in kb/kp_house_groups.json.

The KP rule used here (K. S. Krishnamurti, KP Readers):
  * every matter has a group of houses (marriage 2-7-11, job 2-6-10-11, ...);
  * the sub lord of the matter's main cusp decides whether it is promised. It is judged by the houses its
    STAR LORD occupies and owns (the main level) and by the houses it occupies and owns itself (a weaker level);
  * the houses 12th from the group's houses work against the matter;
  * Rahu and Ketu also give the houses of their sign lord (they act as its agents);
  * a sub lord that is retrograde, or in the star of a retrograde planet, delays the matter.

Horary: the querent names a number from 1 to 249. Each number is one KP sub (27 stars x 9 subs = 243; the
six subs that cross a sign boundary are counted once on each side, giving 249). The horary ascendant is set at
the START of that sub (Krishnamurti's own rule), and the other cusps are Placidus cusps for the moment and place
of judgement.
"""
import datetime as _dt
import json
import os
import zoneinfo

import swisseph as swe

import ephemeris
import kp
from astrology_tables import SIGN_LORD
from extras import BODIES
from panchanga import SIGNS

_KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb", "kp_house_groups.json")
_DATA = None
_NODES = ("Rahu", "Ketu")
_WEEKDAY_LORD = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]        # Monday = 0


def _data():
    global _DATA
    if _DATA is None:
        with open(_KB, encoding="utf-8") as fh:
            _DATA = json.load(fh)
    return _DATA


def matters():
    return _data()["matters"]


def matter(matter_id):
    return next(m for m in matters() if m["id"] == matter_id)


def cusp_theme(cusp):
    return _data()["cusps"][str(cusp)]


# ---------------------------------------------------------------- significations
def owned_houses(cusps, planet):
    """Houses whose cusp falls in a sign of `planet` (KP ownership)."""
    return sorted(c["cusp"] for c in cusps if c["sign_lord"] == planet)


def houses_of(tables, planet):
    """The houses a planet gives as itself: the house it occupies plus the houses it owns. Rahu and Ketu also give
    the houses of their sign lord."""
    by = {p["planet"]: p for p in tables["planets"]}
    out = {by[planet]["house"], *owned_houses(tables["cusps"], planet)}
    if planet in _NODES:
        lord = by[planet]["sign_lord"]
        out |= {by[lord]["house"], *owned_houses(tables["cusps"], lord)}
    return out


def significations(tables, planet):
    """{"star": houses through its star lord (main level), "own": its own houses, "star_lord": name}."""
    by = {p["planet"]: p for p in tables["planets"]}
    star_lord = by[planet]["star_lord"]
    return {"star_lord": star_lord, "star": sorted(houses_of(tables, star_lord)), "own": sorted(houses_of(tables, planet))}


def _retro_note(tables, sub_lord):
    by = {p["planet"]: p for p in tables["planets"]}
    sl = by[sub_lord]
    real = lambda p: p not in _NODES and by[p]["retrograde"]           # mean nodes always move backwards: not counted
    if real(sub_lord):
        return "retro_self"
    if real(sl["star_lord"]):
        return "retro_star"
    return None


def judge(tables, matter_id, cusp=None):
    """The KP verdict for one matter: {matter, cusp, sub_lord, star_lord, star, own, for, against, verdict, retro}.
    verdict is one of "promised", "mixed", "weak", "not_shown"."""
    m = matter(matter_id)
    cusp = cusp or m["cusp"]
    sub_lord = tables["cusps"][cusp - 1]["sub_lord"]
    sig = significations(tables, sub_lord)
    star, own = set(sig["star"]), set(sig["own"])
    fav, bad = set(m["houses"]), set(m["against"])
    f_star, b_star = sorted(fav & star), sorted(bad & star)
    f_own = sorted(fav & own)
    if f_star and not b_star:
        verdict = "promised"
    elif f_star:
        verdict = "mixed"
    elif f_own:
        verdict = "weak"
    else:
        verdict = "not_shown"
    return {"matter": m, "cusp": cusp, "sub_lord": sub_lord, "star_lord": sig["star_lord"], "star": sig["star"],
            "own": sig["own"], "for": sorted(fav & (star | own)), "against": sorted(bad & (star | own)),
            "verdict": verdict, "retro": _retro_note(tables, sub_lord)}


def timing_planets(tables, matter_id):
    """Planets that signify at least two of the matter's houses (through star or self) - the ones whose periods
    can bring the matter."""
    fav = set(matter(matter_id)["houses"])
    out = []
    for p in BODIES:
        s = significations(tables, p)
        hit = fav & (set(s["star"]) | set(s["own"]))
        if len(hit) >= min(2, len(fav)):
            out.append(p)
    return out


def cusp_readings(tables):
    """For each cusp 1-12: {cusp, theme, sub_lord, star_lord, star, own, judgements: [judge(...) per matter]}."""
    out = []
    for c in tables["cusps"]:
        sig = significations(tables, c["sub_lord"])
        out.append({"cusp": c["cusp"], "theme": cusp_theme(c["cusp"]), "sub_lord": c["sub_lord"], "star_lord": sig["star_lord"],
                    "star": sig["star"], "own": sig["own"],
                    "judgements": [judge(tables, m["id"]) for m in matters() if m["cusp"] == c["cusp"]]})
    return out


# ---------------------------------------------------------------- the 1-249 horary table
def _build_horary_table():
    rows = []
    for n in range(27):
        start = n * kp.NAK
        for lord, a, b in kp._split(start, kp.NAK, kp.ORDER[n % 9]):
            pieces = [(a, b)]
            boundary = (int(a // 30) + 1) * 30
            if a < boundary < b - 1e-9:
                pieces = [(a, boundary), (boundary, b)]
            for x, y in pieces:
                mid = (x + y) / 2
                rows.append({"number": len(rows) + 1, "start": x, "end": y, "sign": SIGNS[int(mid // 30) % 12],
                             "sign_lord": SIGN_LORD[SIGNS[int(mid // 30) % 12]], "star_lord": kp.ORDER[n % 9], "sub_lord": lord})
    return rows


HORARY = _build_horary_table()


def horary_row(number):
    if not 1 <= int(number) <= len(HORARY):
        raise ValueError("The KP horary number must be between 1 and 249.")
    return HORARY[int(number) - 1]


def _dms_in_sign(lon):
    d = lon % 30
    deg, rem = int(d), (d - int(d)) * 60
    mins = int(rem)
    secs = round((rem - mins) * 60)
    if secs == 60:
        secs, mins = 0, mins + 1
    if mins == 60:
        mins, deg = 0, deg + 1
    return f"{deg:02d}°{mins:02d}'{secs:02d}\""


def horary_row_parts(row):
    """(sign, from, to) of the stretch a horary number stands for, e.g. ("Aries", '00°46\'40"', '03°00\'00"')."""
    end = row["end"] - row["start"] + (row["start"] % 30)
    return row["sign"], _dms_in_sign(row["start"]), (_dms_in_sign(end) if end < 30 - 1e-9 else "30°00'00\"")


def horary_row_text(row):
    """'Aries 00°46'40" - 03°00'00"' - the stretch of the zodiac a horary number stands for."""
    sign, a, b = horary_row_parts(row)
    return f"{sign} {a} - {b}"


def _asc_for_armc(armc, lat, eps, ayan, hsys):
    cusps, ascmc = swe.houses_armc(armc, lat, eps, hsys)
    return (ascmc[0] - ayan) % 360, cusps


def horary_tables(number, at_utc, latitude, longitude, tz_name=None):
    """The KP horary chart for a number 1-249 judged at `at_utc` (naive UTC) at the given place.
    Returns the same shape as kp.kp_tables() plus {"number", "row", "ruling", "house_system"}."""
    row = horary_row(number)
    target = row["start"] + 1e-7
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        jd = ephemeris.julian_day_ut(at_utc.year, at_utc.month, at_utc.day, at_utc.hour, at_utc.minute,
                                     at_utc.second, utc_offset_hours=0.0)
        ayan = ephemeris.get_ayanamsa(jd) - kp.KP_OFFSET
        eps = swe.calc_ut(jd, swe.ECL_NUT)[0][0]
        hsys = b"P" if abs(latitude) < 66.0 else b"O"                     # Placidus fails in polar latitudes
        # the ascendant grows steadily with the ARMC: scan in 1 degree steps, then bisect the step that crosses
        diff = lambda armc: ((_asc_for_armc(armc, latitude, eps, ayan, hsys)[0] - target + 180) % 360) - 180
        prev_a, prev_d = 0.0, diff(0.0)
        lo = hi = None
        for k in range(1, 361):
            a = float(k)
            d = diff(a % 360)
            if prev_d <= 0 < d or prev_d == 0:
                lo, hi = prev_a, a
                break
            prev_a, prev_d = a, d
        if lo is None:
            raise ValueError("Could not place this ascendant at this latitude.")
        for _ in range(60):
            mid = (lo + hi) / 2
            if diff(mid % 360) <= 0:
                lo = mid
            else:
                hi = mid
        armc = hi % 360
        _asc, cusps_trop = _asc_for_armc(armc, latitude, eps, ayan, hsys)
        positions = {p: (lon + kp.KP_OFFSET) % 360 for p, lon in ephemeris.get_all_positions(jd).items()}
        retro = ephemeris.get_all_retrograde_flags(jd)
        real_asc = (swe.houses_ex(jd, latitude, longitude, hsys, flags=swe.FLG_SIDEREAL)[1][0] + kp.KP_OFFSET) % 360
    cusp_lon = [(c - ayan) % 360 for c in cusps_trop[:12]]
    cusp_lon[0] = target
    cusps, planets, sig = kp.build_tables(cusp_lon, positions, retro)
    by = {p["planet"]: p for p in planets}
    local = at_utc
    if tz_name:
        try:
            local = at_utc.replace(tzinfo=_dt.timezone.utc).astimezone(zoneinfo.ZoneInfo(tz_name)).replace(tzinfo=None)
        except Exception:  # noqa: BLE001 - an unknown zone just means UTC is used for the weekday
            local = at_utc
    ra = kp.lords(real_asc)
    ruling = {"Lagna": (ra[0], ra[1], ra[2]),
              "Moon": (by["Moon"]["sign_lord"], by["Moon"]["star_lord"], by["Moon"]["sub_lord"]),
              "Day lord": _WEEKDAY_LORD[local.weekday()]}
    return {"number": int(number), "row": row, "ayanamsa": ayan, "ayanamsa_dms": kp._dms(ayan), "cusps": cusps,
            "planets": planets, "significators": sig, "ruling": ruling, "house_system": hsys.decode(), "local": local}


def ruling_set(tables):
    r = tables["ruling"]
    return set(r["Lagna"]) | set(r["Moon"]) | {r["Day lord"]}


def horary_judgement(number, matter_id, at_utc, latitude, longitude, tz_name=None):
    """{"tables", "judgement", "in_ruling": bool, "timing": [...]} for one horary question."""
    t = horary_tables(number, at_utc, latitude, longitude, tz_name)
    j = judge(t, matter_id)
    rp = ruling_set(t)
    return {"tables": t, "judgement": j, "in_ruling": j["sub_lord"] in rp or j["star_lord"] in rp,
            "timing": [p for p in timing_planets(t, matter_id) if p in rp] or timing_planets(t, matter_id)}
