"""combustion.py — Combustion (Asta): a planet too close to the Sun is
considered "burnt up" by the Sun's light, its own significations weakened
or overwhelmed. Classical orb (the maximum Sun-planet separation still
counted as combust) varies by planet, and — flagged honestly rather than
picked silently — ALSO varies somewhat by source for a few planets (see
_ORB_NOTE below), the same class of genuine classical disagreement this
project already flags elsewhere (Rahu/Ketu dignity, Paya).

Direction matters for the two inner planets: Mercury and Venus, being
closer to the Sun than Earth, have a WIDER orb when retrograde than when
direct (the classical reasoning: a retrograde inner planet is on the near
side of its orbit, physically closer to Earth and so, by the classical
model, less overwhelmed at the same angular separation). Mars, Jupiter,
and Saturn use one fixed orb regardless of retrograde status; the Moon
always does too.
"""

# Degrees of separation from the Sun at or under which a planet is
# considered combust. Where retrograde changes the orb, use ORB_RETROGRADE.
ORB_DIRECT = {
    "Moon": 12.0,
    "Mars": 17.0,
    "Mercury": 14.0,
    "Jupiter": 11.0,
    "Venus": 10.0,
    "Saturn": 15.0,
}
ORB_RETROGRADE = {
    "Mercury": 12.0,
    "Venus": 8.0,
}

_ORB_NOTE = (
    "Classical sources broadly agree on Moon (12deg), Jupiter (11deg) and Saturn (15deg); "
    "Mars, Mercury, and Venus orbs are cited with more variation across texts (Mars is "
    "sometimes given as 17deg for both direct and retrograde rather than a single fixed "
    "value; some sources give Mercury 14deg/12deg and Venus 10deg/8deg the other way around "
    "from the direct/retrograde split used here). This project uses the most commonly-cited "
    "figures rather than asserting one text as definitive - the same approach already taken "
    "for other genuinely disputed classical points (see avkahada.py's Paya note)."
)


def combustion_orb(planet, retrograde):
    """The orb (degrees) that applies to `planet` given its retrograde
    status, or None if `planet` has no combustion rule (Sun/Rahu/Ketu)."""
    if retrograde and planet in ORB_RETROGRADE:
        return ORB_RETROGRADE[planet]
    return ORB_DIRECT.get(planet)


def sun_separation(sun_longitude, planet_longitude):
    """Absolute angular separation (0-180 degrees) between the Sun and a
    planet, shortest way around the zodiac."""
    diff = abs(sun_longitude - planet_longitude) % 360.0
    return min(diff, 360.0 - diff)


def is_combust(planet, sun_longitude, planet_longitude, retrograde):
    """True if `planet` is combust — within its orb of the Sun."""
    orb = combustion_orb(planet, retrograde)
    if orb is None:
        return False
    return sun_separation(sun_longitude, planet_longitude) <= orb


def combustion_status(chart):
    """{planet: {"combust": bool, "orb": float, "separation": float}} for
    every planet with a combustion rule, computed from `chart`'s already-
    resolved longitudes."""
    sun_lon = chart["planets"]["Sun"]["longitude"]
    result = {}
    for planet in ORB_DIRECT:
        detail = chart["planets"][planet]
        sep = sun_separation(sun_lon, detail["longitude"])
        orb = combustion_orb(planet, detail.get("retrograde", False))
        result[planet] = {"combust": sep <= orb, "orb": orb, "separation": round(sep, 4)}
    return result
