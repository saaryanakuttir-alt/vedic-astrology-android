"""
chalit.py — the "Chalit" (Bhava/house-cusp) chart, built with the classical
Sripati Bhava method: the most commonly used cuspal-house system in
mainstream Parashari software (AstroSage included) alongside whole-sign.

Whole-sign houses (houses.py, used for all main interpretation in this
project) treat an entire sign as one house. Chalit instead computes each
house's exact MADHYA (mid-point) and SANDHI (boundary/start) in degrees,
which can occasionally place a planet that's very early or very late in
its whole-sign house into the ADJACENT chalit house instead — classically
used as a secondary refinement ("chalit" = "moving/shifted"), not a
replacement for the main whole-sign chart.

METHOD (Sripati): the four ANGLES — Ascendant (=Bhava 1 madhya), IC
(=Bhava 4 madhya, i.e. MC+180), Descendant (=Bhava 7 madhya, i.e. Asc+180),
and MC (=Bhava 10 madhya) — divide the ecliptic into 4 quadrants. Each
quadrant is trisected into 3 EQUAL arcs to give the 3 bhava madhyas within
it (e.g. bhava 2 and 3 madhyas trisect the Asc-to-IC quadrant). Each
bhava's SANDHI (start/cusp) is simply the midpoint between its own madhya
and the previous bhava's madhya.

This was verified against a real reference chart (AstroSage kundli,
native "Sammya") and matched all 12 rows of its printed Chalit table
(Bhava Begin sign+degree and Mid Bhava sign+degree) to within about a
tenth of a degree — see tests/test_kundli_details.py.
"""
import ephemeris
from panchanga import get_sign


def _trisect(start, end):
    """3 equal sub-arcs from `start` to `end`, going in the direction of
    INCREASING longitude (wrapping past 360 if needed). Returns the 3
    madhya points AFTER start (i.e. start + arc/3, start + 2*arc/3, and
    end itself), which become bhava madhyas 2/3/4 (etc.) of this quadrant."""
    arc = (end - start) % 360.0
    third = arc / 3.0
    return [(start + third) % 360.0, (start + 2 * third) % 360.0, end % 360.0]


def compute_bhava_madhyas(ascendant_longitude, mc_longitude):
    """Returns a list of 12 madhya longitudes (index 0 = Bhava 1 madhya =
    the Ascendant itself), using the Sripati quadrant-trisection method."""
    asc = ascendant_longitude % 360.0
    mc = mc_longitude % 360.0
    ic = (mc + 180.0) % 360.0
    desc = (asc + 180.0) % 360.0

    madhyas = [asc]
    madhyas += _trisect(asc, ic)      # bhavas 2, 3, 4
    madhyas += _trisect(ic, desc)     # bhavas 5, 6, 7
    madhyas += _trisect(desc, mc)     # bhavas 8, 9, 10
    madhyas += _trisect(mc, asc)      # bhavas 11, 12, (back to 1)
    return madhyas[:12]


def _midpoint_going_forward(a, b):
    """Midpoint of the SHORT forward arc from a to b (b assumed to be
    "ahead" of a by less than 360; handles the 360-degree wrap)."""
    arc = (b - a) % 360.0
    return (a + arc / 2.0) % 360.0


def compute_chalit(ascendant_longitude, mc_longitude):
    """
    Returns a list of 12 dicts (index 0 = Bhava/house 1), each:
        {"bhava": 1, "madhya_longitude": deg, "madhya_sign": ..., "madhya_degree_in_sign": ...,
         "begin_longitude": deg, "begin_sign": ..., "begin_degree_in_sign": ...,
         "end_longitude": deg}
    "begin" is this bhava's sandhi (start boundary) — the midpoint between
    the PREVIOUS bhava's madhya and this one's; "end" is the next bhava's
    begin (so consecutive bhavas tile the zodiac with no gaps/overlaps).
    """
    madhyas = compute_bhava_madhyas(ascendant_longitude, mc_longitude)
    begins = [_midpoint_going_forward(madhyas[i - 1], madhyas[i]) for i in range(12)]

    chalit = []
    for i in range(12):
        madhya_sign, madhya_deg = get_sign(madhyas[i])
        begin_sign, begin_deg = get_sign(begins[i])
        end_longitude = begins[(i + 1) % 12]
        chalit.append({
            "bhava": i + 1,
            "madhya_longitude": round(madhyas[i], 4),
            "madhya_sign": madhya_sign,
            "madhya_degree_in_sign": round(madhya_deg, 4),
            "begin_longitude": round(begins[i], 4),
            "begin_sign": begin_sign,
            "begin_degree_in_sign": round(begin_deg, 4),
            "end_longitude": round(end_longitude, 4),
        })
    return chalit


def find_chalit_bhava(chalit, longitude):
    """Given a computed chalit list and any longitude (e.g. a planet's),
    returns which bhava (1-12) it falls in by cusp (sandhi) boundaries —
    this is the "chalit house" that can differ from the whole-sign house
    for a planet near a house boundary."""
    longitude = longitude % 360.0
    for entry in chalit:
        start = entry["begin_longitude"]
        end = entry["end_longitude"]
        span = (end - start) % 360.0
        offset = (longitude - start) % 360.0
        if offset < span or (span == 0 and offset == 0):
            return entry["bhava"]
    return chalit[-1]["bhava"]  # pragma: no cover - unreachable given full coverage above


def compute_chalit_for_chart(ascendant_longitude, mc_longitude, planet_longitudes):
    """Convenience wrapper: returns (chalit_table, {planet: chalit_bhava})."""
    chalit = compute_chalit(ascendant_longitude, mc_longitude)
    planet_bhavas = {p: find_chalit_bhava(chalit, lon) for p, lon in planet_longitudes.items()}
    return chalit, planet_bhavas
