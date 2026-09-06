"""
chart_geometry.py — pure layout logic for drawing a traditional Vedic
birth-chart diagram in either of the two standard styles:

  NORTH INDIAN  — a fixed diamond-in-a-square shape. House 1 (the Lagna) is
                  always the top "kite" cell; houses proceed CLOCKWISE in
                  DECREASING order from there (1, 12, 11, 10, ... 2), i.e.
                  counter-clockwise increasing — the standard convention
                  (cross-checked against a real AstroSage-rendered chart:
                  ground-truthed planet-to-sign-to-house against the chart
                  image's actual pixel layout). Which SIGN occupies which
                  house cell rotates with the Ascendant.
  SOUTH INDIAN  — a fixed 4x4 grid. Each SIGN has a permanently fixed cell
                  (Aries is always top row, 2nd column, etc.); which house
                  number a cell represents rotates with the Ascendant
                  instead (marked by highlighting the Lagna cell).

This module contains NO drawing code (no tkinter import) — it only computes
polygon/grid coordinates and sign/planet assignments, so it can be tested
without a display and reused by any UI layer.

All coordinates are in a normalized 0.0-1.0 unit square; the caller scales
them to whatever canvas size it's drawing on.
"""
from astrology_tables import PLANET_ABBR
from houses import get_house_of_sign
from panchanga import SIGNS

# ---------------------------------------------------------------------------
# NORTH INDIAN layout
# ---------------------------------------------------------------------------
_TM, _RM, _BM, _LM = (0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5)
_C = (0.5, 0.5)
_P1, _P2, _P3, _P4 = (0.25, 0.25), (0.75, 0.75), (0.75, 0.25), (0.25, 0.75)
_TL, _TR, _BR, _BL = (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)

# house_number -> {"polygon": [(x,y), ...], "outer_vertex": (x,y)}
# "outer_vertex" is where the small sign-number label is anchored (nudged
# inward slightly by the caller); the polygon's own centroid is where the
# (larger) planet-abbreviation text is anchored.
NORTH_INDIAN_HOUSES = {
    1: {"polygon": [_TM, _P3, _C, _P1], "outer_vertex": _TM},
    2: {"polygon": [_TL, _P1, _TM], "outer_vertex": _TL},
    3: {"polygon": [_TL, _LM, _P1], "outer_vertex": _TL},
    4: {"polygon": [_LM, _P1, _C, _P4], "outer_vertex": _LM},
    5: {"polygon": [_BL, _P4, _LM], "outer_vertex": _BL},
    6: {"polygon": [_BL, _BM, _P4], "outer_vertex": _BL},
    7: {"polygon": [_BM, _P4, _C, _P2], "outer_vertex": _BM},
    8: {"polygon": [_BR, _P2, _BM], "outer_vertex": _BR},
    9: {"polygon": [_BR, _RM, _P2], "outer_vertex": _BR},
    10: {"polygon": [_RM, _P2, _C, _P3], "outer_vertex": _RM},
    11: {"polygon": [_TR, _P3, _RM], "outer_vertex": _TR},
    12: {"polygon": [_TR, _TM, _P3], "outer_vertex": _TR},
}
# The square's own outline and the two full corner-to-corner diagonals —
# drawn once as "frame" lines; the house polygons above already cover every
# internal line needed, but re-drawing the outer square + diagonals as
# simple line segments is the cleanest way to render the traditional look.
NORTH_INDIAN_FRAME_LINES = [
    (_TL, _TR), (_TR, _BR), (_BR, _BL), (_BL, _TL),  # outer square
    (_TL, _BR), (_TR, _BL),                          # diagonals
    (_TM, _RM), (_RM, _BM), (_BM, _LM), (_LM, _TM),  # inner diamond
]


def polygon_centroid(polygon):
    """Simple vertex-average centroid — exact for the symmetric
    triangles/kites used here, which is all this module needs."""
    n = len(polygon)
    x = sum(p[0] for p in polygon) / n
    y = sum(p[1] for p in polygon) / n
    return x, y


def north_indian_sign_map(ascendant_sign):
    """{house_number: sign_name} for a North Indian chart with this Ascendant."""
    asc_index = SIGNS.index(ascendant_sign)
    return {house: SIGNS[(asc_index + house - 1) % 12] for house in range(1, 13)}


# ---------------------------------------------------------------------------
# SOUTH INDIAN layout — signs have permanently fixed grid cells.
# ---------------------------------------------------------------------------
SOUTH_INDIAN_GRID = {
    "Pisces": (0, 0), "Aries": (0, 1), "Taurus": (0, 2), "Gemini": (0, 3),
    "Aquarius": (1, 0), "Cancer": (1, 3),
    "Capricorn": (2, 0), "Leo": (2, 3),
    "Sagittarius": (3, 0), "Scorpio": (3, 1), "Libra": (3, 2), "Virgo": (3, 3),
}
SOUTH_INDIAN_EMPTY_CELLS = [(1, 1), (1, 2), (2, 1), (2, 2)]


# ---------------------------------------------------------------------------
# Planet/sign/house placement helpers — shared by both styles.
# ---------------------------------------------------------------------------
def planet_positions_for_varga(chart, varga_key):
    """Returns {planet: sign_name} for every planet in the given varga
    ('D1' means the main Rasi chart; any other key looks inside
    chart['planets'][p]['vargas'])."""
    positions = {}
    for planet, detail in chart["planets"].items():
        if varga_key == "D1":
            positions[planet] = detail["sign"]
        else:
            positions[planet] = detail["vargas"][varga_key]
    return positions


def ascendant_sign_for_varga(chart, varga_key):
    if varga_key == "D1":
        return chart["ascendant"]["sign"]
    return chart["ascendant"]["vargas"][varga_key]


def build_house_planet_map(chart, varga_key):
    """{house_number (1-12): [planet abbreviations]} — for North Indian
    rendering, where each planet's HOUSE (counted from that varga's own
    Ascendant sign) determines its cell."""
    asc_sign = ascendant_sign_for_varga(chart, varga_key)
    positions = planet_positions_for_varga(chart, varga_key)
    house_map = {h: [] for h in range(1, 13)}
    for planet, sign in positions.items():
        house = get_house_of_sign(asc_sign, sign)
        house_map[house].append(PLANET_ABBR[planet])
    return house_map


def build_sign_planet_map(chart, varga_key):
    """{sign_name: [planet abbreviations]} — for South Indian rendering,
    where each planet's SIGN directly determines its (fixed) cell."""
    positions = planet_positions_for_varga(chart, varga_key)
    sign_map = {s: [] for s in SIGNS}
    for planet, sign in positions.items():
        sign_map[sign].append(PLANET_ABBR[planet])
    return sign_map
