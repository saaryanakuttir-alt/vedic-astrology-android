"""graha_yuddha.py — Graha Yuddha (planetary war): when two of the 5
"war-eligible" planets (Mercury, Venus, Mars, Jupiter, Saturn — Sun, Moon,
Rahu, and Ketu never participate by classical rule) sit within about 1
degree of each other in longitude.

WINNER RULE HAS CROSS-SOURCE VARIATION, same honesty-first treatment as
manglik.py's Manglik / doshas.py's Pitra Dosha. The most commonly cited
rule (Brihat Parashara Hora Shastra) is: the planet with the GREATER
ecliptic latitude (further from the ecliptic plane, regardless of
north/south sign) wins; the other is considered "defeated" and reads as
weakened for the significations it governs, even though it keeps its own
sign/house placement on the chart. Some modern sources instead break ties
by which planet is more advanced in degrees, or treat the war as a wash
when latitudes are very close. This module reports the raw fact (which
planets are within orb, and each one's latitude) and applies the BPHS
latitude rule as its primary read, but says so explicitly rather than
presenting it as uncontested.
"""
from ephemeris import WAR_ELIGIBLE_PLANETS

WAR_ORB_DEG = 1.0


def _angular_separation(lon_a, lon_b):
    diff = abs(lon_a - lon_b) % 360.0
    return min(diff, 360.0 - diff)


def find_wars(longitudes, latitudes):
    """longitudes/latitudes: {planet_name: degrees}, both keyed by the 5
    war-eligible planets (a subset of a full chart's positions is fine -
    extra keys are ignored). Returns a list of war dicts, one per pair
    within WAR_ORB_DEG of each other; empty list if no war is happening."""
    wars = []
    planets = [p for p in WAR_ELIGIBLE_PLANETS if p in longitudes and p in latitudes]
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            a, b = planets[i], planets[j]
            sep = _angular_separation(longitudes[a], longitudes[b])
            if sep > WAR_ORB_DEG:
                continue
            lat_a, lat_b = latitudes[a], latitudes[b]
            if abs(lat_a) > abs(lat_b):
                winner, loser = a, b
            elif abs(lat_b) > abs(lat_a):
                winner, loser = b, a
            else:
                winner, loser = None, None  # exact tie - genuinely undetermined
            wars.append({
                "planets": [a, b],
                "separation_deg": round(sep, 4),
                "latitudes": {a: round(lat_a, 4), b: round(lat_b, 4)},
                "winner": winner,
                "loser": loser,
                "detail": (
                    f"{a} and {b} are in Graha Yuddha ({sep:.2f}° apart)."
                    + (f" By the greater-latitude rule, {winner} wins and {loser} is considered defeated."
                       if winner else " Latitudes are effectively tied - no clear winner by this rule.")
                ),
            })
    return wars
