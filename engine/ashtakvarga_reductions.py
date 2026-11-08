"""
ashtakvarga_reductions.py - the classical reductions (Shodhana) of each planet's Bhinnashtakavarga, the Shodhya
Pinda that follows from them, and Kakshya (the eight 3 deg 45 min sub-divisions of a sign used to time transits).

Rules (BPHS ch.67-69; Phaladeepika ch.24 "Horasara" slokas 18-23; B.V. Raman, Hindu Predictive Astrology ch.26;
M.S. Mehta, Ashtakvarga - Concept & Application ch.III - all four agree):

TRIKONA SHODHANA, for each trine group (Aries-Leo-Sagittarius, Taurus-Virgo-Capricorn, Gemini-Libra-Aquarius,
Cancer-Scorpio-Pisces) of one planet's row:
  * if any of the three signs has 0, no reduction;
  * if all three are equal, all become 0;
  * otherwise the smallest is subtracted from all three.

EKADHIPATYA SHODHANA, after Trikona, for each pair of signs with one lord (Mars: Aries/Scorpio, Venus: Taurus/
Libra, Mercury: Gemini/Virgo, Jupiter: Sagittarius/Pisces, Saturn: Capricorn/Aquarius; Cancer and Leo are never
reduced). "Occupied" means a planet of the seven (Rahu, Ketu and the Lagna do not count) is in the sign:
  * either sign has 0 -> no reduction;           * both signs occupied -> no reduction;
  * one occupied: if the empty sign has MORE, it is lowered to the occupied sign's figure; if it has the same or
    fewer, the empty sign becomes 0;
  * both empty: equal -> both 0; unequal -> the larger is lowered to the smaller.

SHODHYA PINDA = Rasi Pinda + Graha Pinda. Rasi Pinda: each sign's reduced figure x the sign's multiplier (Aries 7,
Taurus 10, Gemini 8, Cancer 4, Leo 10, Virgo 5, Libra 7, Scorpio 8, Sagittarius 9, Capricorn 5, Aquarius 11,
Pisces 12). Graha Pinda: for each of the seven planets, the reduced figure of the sign it occupies x the planet's
multiplier (Sun 5, Moon 5, Mars 8, Mercury 5, Jupiter 10, Venus 7, Saturn 5). Classical texts use the Pinda for
timing and for life-span arithmetic; this app shows it only as a figure and makes no life-span use of it.

KAKSHYA: each sign is split into eight equal parts of 3 deg 45 min, ruled in order by Saturn, Jupiter, Mars, the
Sun, Venus, Mercury, the Moon and the Lagna. A planet transiting a Kakshya whose lord gave a point to that sign in
the planet's own Prastharashtakvarga is traditionally favourable for that stretch; if the lord gave no point, less so.
"""
from ashtakvarga import PLANET_ORDER
from astrology_tables import SIGN_LORD
from panchanga import SIGNS

TRINES = [("Aries", "Leo", "Sagittarius"), ("Taurus", "Virgo", "Capricorn"),
          ("Gemini", "Libra", "Aquarius"), ("Cancer", "Scorpio", "Pisces")]
SAME_LORD = [("Aries", "Scorpio"), ("Taurus", "Libra"), ("Gemini", "Virgo"),
             ("Sagittarius", "Pisces"), ("Capricorn", "Aquarius")]
RASI_MULTIPLIER = {"Aries": 7, "Taurus": 10, "Gemini": 8, "Cancer": 4, "Leo": 10, "Virgo": 5, "Libra": 7,
                   "Scorpio": 8, "Sagittarius": 9, "Capricorn": 5, "Aquarius": 11, "Pisces": 12}
GRAHA_MULTIPLIER = {"Sun": 5, "Moon": 5, "Mars": 8, "Mercury": 5, "Jupiter": 10, "Venus": 7, "Saturn": 5}
KAKSHYA_LORDS = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Lagna"]
KAKSHYA_SPAN = 30.0 / 8                     # 3 deg 45 min

assert all(SIGN_LORD[a] == SIGN_LORD[b] for a, b in SAME_LORD)


def trikona_shodhana(row):
    """row: {sign: points} -> a new reduced row (Trikona rules above)."""
    out = dict(row)
    for group in TRINES:
        vals = [out[s] for s in group]
        if min(vals) == 0:
            continue
        if len(set(vals)) == 1:
            for s in group:
                out[s] = 0
        else:
            low = min(vals)
            for s in group:
                out[s] -= low
    return out


def ekadhipatya_shodhana(row, occupied):
    """row: {sign: points} after Trikona; occupied: set of signs holding one of the seven planets."""
    out = dict(row)
    for a, b in SAME_LORD:
        va, vb = out[a], out[b]
        if va == 0 or vb == 0:
            continue
        occ_a, occ_b = a in occupied, b in occupied
        if occ_a and occ_b:
            continue
        if occ_a != occ_b:
            full, empty = (a, b) if occ_a else (b, a)
            if out[empty] > out[full]:
                out[empty] = out[full]
            else:
                out[empty] = 0
        elif va == vb:
            out[a] = out[b] = 0
        else:
            out[a] = out[b] = min(va, vb)
    return out


def occupied_signs(chart):
    return {chart["planets"][p]["sign"] for p in PLANET_ORDER}


def reductions(chart):
    """{planet: {"raw": row, "trikona": row, "ekadhipatya": row, "rasi_pinda", "graha_pinda", "shodhya_pinda"}}
    plus "sarva_reduced": the reduced rows summed per sign."""
    bav = chart["ashtakavarga"]["bhinnashtakavarga"]
    occ = occupied_signs(chart)
    out = {}
    for p in PLANET_ORDER:
        raw = {s: bav[p][s] for s in SIGNS}
        tri = trikona_shodhana(raw)
        eka = ekadhipatya_shodhana(tri, occ)
        rasi = sum(eka[s] * RASI_MULTIPLIER[s] for s in SIGNS)
        graha = sum(eka[chart["planets"][q]["sign"]] * GRAHA_MULTIPLIER[q] for q in PLANET_ORDER)
        out[p] = {"raw": raw, "trikona": tri, "ekadhipatya": eka, "rasi_pinda": rasi, "graha_pinda": graha,
                  "shodhya_pinda": rasi + graha}
    out["sarva_reduced"] = {s: sum(out[p]["ekadhipatya"][s] for p in PLANET_ORDER) for s in SIGNS}
    return out


def kakshya_of(longitude):
    """(index 0-7, lord, start degree within the sign) of a sidereal longitude."""
    deg = longitude % 30.0
    i = min(int(deg // KAKSHYA_SPAN), 7)
    return i, KAKSHYA_LORDS[i], i * KAKSHYA_SPAN


def kakshya_transits(chart, positions):
    """positions: {planet: sidereal longitude} of the seven planets at some moment (e.g. ephemeris.get_all_positions).
    For each planet: the sign it transits, its Kakshya and lord, whether that lord gave a point to the sign in the
    planet's Prastharashtakvarga, and the planet's Bhinnashtakavarga points in that sign."""
    import prastara
    out = {}
    for p in PLANET_ORDER:
        lon = positions[p]
        sign = SIGNS[int(lon // 30) % 12]
        i, lord, start = kakshya_of(lon)
        grid = prastara.prastara(chart, p)
        gives = bool(grid["rows"][lord][SIGNS.index(sign)])
        out[p] = {"sign": sign, "degree": lon % 30.0, "kakshya": i + 1, "lord": lord, "start": start,
                  "end": start + KAKSHYA_SPAN, "lord_gives_point": gives,
                  "bindus": chart["ashtakavarga"]["bhinnashtakavarga"][p][sign]}
    return out


def kakshya_now(chart, at_dt):
    """kakshya_transits for the moment `at_dt` (naive UTC)."""
    import ephemeris
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        jd = ephemeris.julian_day_ut(at_dt.year, at_dt.month, at_dt.day, at_dt.hour, at_dt.minute, at_dt.second,
                                     utc_offset_hours=0.0)
        positions = ephemeris.get_all_positions(jd)
    return kakshya_transits(chart, positions)
