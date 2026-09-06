"""
timezone_resolver.py — resolves a birth country (+ coordinates) to an IANA
timezone name, entirely offline, using the standard tzdata zone1970.tab
file (bundled in data/zone1970.tab — this exact file also ships with every
Linux/Android system's tzdata, so it's a natural fit to bundle in the
Android app too, not just this prototype).

WHY THIS APPROACH: most countries have exactly one civil timezone, so
country code alone resolves them exactly (confidence="exact"). A handful
of large countries (US, Russia, Canada, Brazil, Australia, ...) span
several timezones. For those, zone1970.tab conveniently also lists each
timezone's "principal location" coordinates, so we pick whichever zone's
principal location is geographically nearest to the birth coordinates
(confidence="nearest_zone_approximation"). This is NOT the same as a real
timezone-boundary polygon lookup (like the `timezonefinder` package does)
— it can be wrong for a birthplace near an internal timezone boundary.

KNOWN LIMITATION — fix before shipping: for production, replace the
"nearest principal location" heuristic below with a real polygon-based
lookup (e.g. the `timezonefinder` Python package, or an Android port of
the same boundary data) for the ~15 multi-zone countries. This wasn't
built into this prototype because timezonefinder's boundary data is
distributed as a separate large download that this sandbox's network
couldn't reach — it should install normally with plain `pip install
timezonefinder` on a machine with normal internet access.
"""
import math
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "zone1970.tab")


def _parse_coord(coord_str):
    """Parses zone1970.tab's ISO-6709 coordinate column, e.g. '+2232+08822'
    or '-3453-058823', into (lat, lon) decimal degrees."""
    # Format is +/-DDMM(SS)+/-DDDMM(SS), split by finding the second sign.
    for split_at in range(1, len(coord_str)):
        if coord_str[split_at] in "+-":
            lat_part, lon_part = coord_str[:split_at], coord_str[split_at:]
            break
    else:
        raise ValueError(f"Unparseable coordinate: {coord_str}")

    def to_decimal(part):
        sign = 1 if part[0] == "+" else -1
        digits = part[1:]
        if len(digits) in (4, 5):  # DDMM or DDDMM
            deg_len = len(digits) - 2
            deg = int(digits[:deg_len])
            minute = int(digits[deg_len:])
            return sign * (deg + minute / 60.0)
        elif len(digits) in (6, 7):  # DDMMSS or DDDMMSS
            deg_len = len(digits) - 4
            deg = int(digits[:deg_len])
            minute = int(digits[deg_len:deg_len + 2])
            second = int(digits[deg_len + 2:])
            return sign * (deg + minute / 60.0 + second / 3600.0)
        raise ValueError(f"Unparseable coordinate part: {part}")

    return to_decimal(lat_part), to_decimal(lon_part)


def _load_zones():
    """Returns {country_code: [(tz_name, lat, lon), ...]}."""
    zones = {}
    with open(_DATA_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            countries, coord, tz_name = parts[0], parts[1], parts[2]
            lat, lon = _parse_coord(coord)
            for country in countries.split(","):
                zones.setdefault(country, []).append((tz_name, lat, lon))
    return zones


_ZONES_BY_COUNTRY = _load_zones()

# Countries where more than one civil timezone applies — resolved by the
# nearest-principal-location heuristic rather than a direct 1:1 lookup.
MULTI_ZONE_COUNTRIES = {cc for cc, zs in _ZONES_BY_COUNTRY.items() if len(zs) > 1}


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def resolve_timezone(country_code, latitude=None, longitude=None):
    """
    country_code: ISO 3166-1 alpha-2 (e.g. "IN", "US") — get this from
        geocode.py's lookup result.
    latitude, longitude: birth coordinates, REQUIRED if country_code is in
        MULTI_ZONE_COUNTRIES (raises ValueError otherwise).

    Returns {"tz_name": "Asia/Kolkata", "confidence": "exact"} or
            {"tz_name": "America/New_York", "confidence": "nearest_zone_approximation",
             "candidates": [...other zone names in this country...]}
    """
    country_code = country_code.upper()
    zones = _ZONES_BY_COUNTRY.get(country_code)
    if not zones:
        raise ValueError(f"No timezone data for country code '{country_code}'")

    if len(zones) == 1:
        return {"tz_name": zones[0][0], "confidence": "exact"}

    if latitude is None or longitude is None:
        raise ValueError(
            f"'{country_code}' has {len(zones)} timezones — latitude and longitude "
            f"are required to pick the nearest one. Candidates: "
            f"{[z[0] for z in zones]}"
        )

    best = min(zones, key=lambda z: _haversine_km(latitude, longitude, z[1], z[2]))
    return {
        "tz_name": best[0],
        "confidence": "nearest_zone_approximation",
        "candidates": [z[0] for z in zones if z[0] != best[0]],
        "note": (
            "Picked by nearest timezone 'principal location', not a real boundary "
            "lookup. Double-check this against a map for birthplaces near an "
            "internal timezone border."
        ),
    }
