"""
geocode.py — resolves a free-text "place of birth" into coordinates,
entirely offline, using a bundled city gazetteer (data/world_cities.csv).

DATA SOURCE: data/world_cities.csv is the "15000+ population" cut of
joelacus/world-cities (https://github.com/joelacus/world-cities), itself
derived from the GeoNames Gazetteer. Licensed CC BY 4.0 — keep attribution
if this ships in the app. ~34,000 cities/towns worldwide with country,
name, latitude, longitude.

KNOWN LIMITATION — fix before shipping: this only covers places with
15,000+ population and does exact/near-exact name matching (see
_normalize below) — it will miss small towns and won't gracefully handle
typos or alternate spellings/transliterations. For production, either
swap in the finer-grained "5000" or "1000" population-threshold file from
the same source (bigger file, more coverage) and/or add a proper fuzzy
string-matching library, and/or let the user fall back to entering
latitude/longitude directly (birth_chart.py already supports that path).
"""
import csv
import os
import re

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "world_cities.csv")


def _normalize(name):
    """Lowercase, strip accents-ish punctuation, collapse whitespace, so
    'São Paulo' loosely matches 'sao paulo' and 'New York' matches 'new york'."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _load_cities():
    cities = []
    with open(_DATA_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cities.append({
                "country": row["country"],
                "name": row["name"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "_norm": _normalize(row["name"]),
            })
    return cities


_CITIES = _load_cities()
_BY_NORM_NAME = {}
for _c in _CITIES:
    _BY_NORM_NAME.setdefault(_c["_norm"], []).append(_c)


def lookup_place(place_name, country_hint=None):
    """
    place_name: free text, e.g. "Mumbai", "Springfield, IL", "Paris".
    country_hint: optional ISO 3166-1 alpha-2 code (e.g. "IN", "US") to
        disambiguate common city names that exist in multiple countries.

    Returns a dict:
        {"matched_name", "country", "lat", "lng", "match_type", "alternatives"}
    match_type is "exact" (unique match) or "ambiguous" (multiple candidates
    were found; the first/most-likely is returned but `alternatives` lists
    the rest so the caller can prompt the user to pick).

    Raises LookupError if nothing matches at all.
    """
    # Allow "City, ST" or "City, Country" style input by taking the part
    # before the first comma as the primary search term.
    primary = place_name.split(",")[0]
    norm = _normalize(primary)

    candidates = _BY_NORM_NAME.get(norm, [])

    if country_hint:
        country_hint = country_hint.upper()
        filtered = [c for c in candidates if c["country"] == country_hint]
        if filtered:
            candidates = filtered

    if not candidates:
        raise LookupError(
            f"No match for '{place_name}' in the bundled gazetteer "
            f"({len(_CITIES)} places, population 15,000+ threshold). "
            f"Try a nearby larger town, or supply latitude/longitude directly."
        )

    best = candidates[0]
    result = {
        "matched_name": best["name"],
        "country": best["country"],
        "lat": best["lat"],
        "lng": best["lng"],
        "match_type": "exact" if len(candidates) == 1 else "ambiguous",
    }
    if len(candidates) > 1:
        result["alternatives"] = [
            {"matched_name": c["name"], "country": c["country"], "lat": c["lat"], "lng": c["lng"]}
            for c in candidates[1:]
        ]
    return result
