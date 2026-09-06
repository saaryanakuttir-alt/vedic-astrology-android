"""
panchanga.py — converts a raw sidereal longitude (degrees, 0-360) into the
sign/nakshatra/pada breakdown used throughout this project's knowledge base.

Sign names and order match exactly what's used in planet_in_sign.json and
every other file in this project — this is the single source of truth for
that mapping so nothing drifts out of sync.
"""

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# 27 nakshatras, each spanning exactly 13°20' (360/27 degrees), starting at 0° Aries.
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# The 9 Vimshottari dasha lords, in the fixed cyclic order, repeated 3x to
# cover all 27 nakshatras — each nakshatra's ruling planet, per classical
# assignment (this is what determines the dasha balance at birth). Matches
# dasha_sequence_order in vimshottari_mahadasha.json.
_DASHA_CYCLE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
NAKSHATRA_LORD = {NAKSHATRAS[i]: _DASHA_CYCLE[i % 9] for i in range(27)}

SIGN_SPAN = 30.0
NAKSHATRA_SPAN = 360.0 / 27.0  # 13.333... degrees
PADA_SPAN = NAKSHATRA_SPAN / 4.0  # 3.333... degrees


def get_sign(longitude):
    """Returns (sign_name, degree_within_sign) for a sidereal longitude."""
    longitude = longitude % 360.0
    index = int(longitude // SIGN_SPAN)
    degree_in_sign = longitude - index * SIGN_SPAN
    return SIGNS[index], degree_in_sign


def get_nakshatra(longitude):
    """Returns (nakshatra_name, pada[1-4], lord_planet, degree_within_nakshatra)."""
    longitude = longitude % 360.0
    index = int(longitude // NAKSHATRA_SPAN)
    index = min(index, 26)  # guard against float rounding pushing index to 27
    degree_in_nakshatra = longitude - index * NAKSHATRA_SPAN
    pada = int(degree_in_nakshatra // PADA_SPAN) + 1
    pada = min(pada, 4)
    name = NAKSHATRAS[index]
    return name, pada, NAKSHATRA_LORD[name], degree_in_nakshatra


def describe_longitude(longitude):
    """Convenience: everything panchanga.py knows about one longitude, bundled."""
    sign, deg_in_sign = get_sign(longitude)
    nak, pada, lord, deg_in_nak = get_nakshatra(longitude)
    return {
        "longitude": longitude % 360.0,
        "sign": sign,
        "degree_in_sign": round(deg_in_sign, 4),
        "nakshatra": nak,
        "nakshatra_pada": pada,
        "nakshatra_lord": lord,
        "degree_in_nakshatra": round(deg_in_nak, 4),
    }
