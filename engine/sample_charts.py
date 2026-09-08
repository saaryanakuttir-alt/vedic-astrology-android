"""sample_charts.py — the "sample chart" browsing feature: a curated list
of real, publicly-documented people (see sample_profiles.json) that a user
can pick to generate a chart for, without typing in birth details.

Every profile here passed one bar the research process behind it enforced
strictly: a genuinely SOURCED birth time, not just date/place. See
sample_profiles.json's own "note" field for what that process looked like
and why 20 originally-confirmed names were left out entirely.
"""
import json
import os

_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "sample_profiles.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(_PROFILES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _cache = data
    return _cache


def list_profiles():
    """Returns the full profile list (id, name, category, notable_for,
    time_confidence, etc.) - everything EXCEPT actually generating a
    chart, which is comparatively expensive and only done on request via
    generate_chart_for_profile below."""
    return _load()["profiles"]


def get_profile(profile_id):
    for p in list_profiles():
        if p["id"] == profile_id:
            return p
    return None


def generate_chart_for_profile(profile_id):
    """Computes and returns a full birth chart for one sample profile, in
    the exact same shape birth_chart.compute_birth_chart returns for any
    user-entered chart - so every existing rule_engine/UI code path works
    on a sample profile with zero special-casing."""
    import birth_chart  # local import - avoids a hard dependency for callers that only need list_profiles()

    profile = get_profile(profile_id)
    if profile is None:
        raise ValueError(f"No sample profile with id '{profile_id}'")

    bd = profile["birth_date"]
    bt = profile["birth_time"]
    return birth_chart.compute_birth_chart(
        name=profile["name"],
        birth_date=(bd["year"], bd["month"], bd["day"]),
        birth_time=(bt["hour"], bt["minute"], 0),
        place_name=profile["geocode_place"],
        country_hint=profile["country_hint"],
        sex=profile["sex"],
    )
