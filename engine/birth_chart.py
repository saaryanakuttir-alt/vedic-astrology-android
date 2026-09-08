"""
birth_chart.py — the main orchestrator. Takes the three pieces of
information a user actually provides (name, place of birth, date+time of
birth) and produces one complete, structured birth chart: Ascendant, all 9
grahas placed by sign/house/nakshatra in D1, their resulting sign in all
12 divisional charts, and the full Vimshottari dasha timeline.

This module does NOT interpret the chart (say what "Jupiter in the 10th"
MEANS) — that's what the knowledge base JSON files (planet_in_house.json,
etc.) are for. This module's job ends at producing the structured FACTS a
later rule engine will look up against that knowledge base.

USAGE:
    from birth_chart import compute_birth_chart
    chart = compute_birth_chart(
        name="Jane Doe",
        birth_date=(1990, 6, 15),      # (year, month, day)
        birth_time=(14, 30, 0),        # (hour, minute, second) — 24h, LOCAL time
        place_name="Mumbai",
        country_hint="IN",             # optional, disambiguates same-named cities
    )
    # or, bypassing the bundled gazetteer entirely:
    chart = compute_birth_chart(
        name="Jane Doe", birth_date=(1990, 6, 15), birth_time=(14, 30, 0),
        place_name="Mumbai",           # kept for the record/display only
        latitude=19.0760, longitude=72.8777, tz_name="Asia/Kolkata",
    )
"""
import datetime
import json
from zoneinfo import ZoneInfo

import avkahada
import ashtakvarga
import chalit as chalit_module
import dasha
import divisional
import ephemeris
import geocode
import houses
import manglik
import panchang_daily
import panchanga
import timezone_resolver

SCHEMA_VERSION = "1.0"


def _resolve_location(place_name, country_hint, latitude, longitude, tz_name):
    """Figures out (latitude, longitude, tz_name, location_meta) from
    whatever combination of place_name / explicit overrides was given."""
    location_meta = {"place_name_as_entered": place_name}

    if latitude is not None and longitude is not None:
        location_meta["source"] = "explicit_lat_lon"
    else:
        match = geocode.lookup_place(place_name, country_hint=country_hint)
        latitude, longitude = match["lat"], match["lng"]
        location_meta.update({
            "source": "gazetteer_lookup",
            "matched_name": match["matched_name"],
            "country_code": match["country"],
            "match_type": match["match_type"],
        })
        if match["match_type"] == "ambiguous":
            location_meta["alternatives"] = match["alternatives"]
        if tz_name is None:
            tz_result = timezone_resolver.resolve_timezone(match["country"], latitude, longitude)
            tz_name = tz_result["tz_name"]
            location_meta["timezone_resolution"] = tz_result

    if tz_name is None:
        raise ValueError(
            "Could not determine a timezone. Either pass tz_name explicitly, or "
            "pass a place_name that resolves via the gazetteer to a country whose "
            "timezone can be looked up."
        )

    location_meta["latitude"] = latitude
    location_meta["longitude"] = longitude
    location_meta["tz_name"] = tz_name
    return latitude, longitude, tz_name, location_meta


def _local_datetime_to_utc(birth_date, birth_time, tz_name):
    """Builds an aware local datetime, then converts to UTC using zoneinfo
    — this correctly accounts for the HISTORICAL UTC offset and DST rules
    in effect on that specific date (not just today's offset), which
    matters a great deal for older birth dates."""
    year, month, day = birth_date
    hour, minute, second = (list(birth_time) + [0, 0, 0])[:3]
    local_dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo(tz_name))
    utc_dt = local_dt.astimezone(datetime.timezone.utc)
    utc_offset_hours = local_dt.utcoffset().total_seconds() / 3600.0
    return local_dt, utc_dt, utc_offset_hours


def _planet_detail(longitude, ascendant_sign, is_retrograde, chalit_bhava=None):
    sign, deg_in_sign = panchanga.get_sign(longitude)
    nak, pada, nak_lord, deg_in_nak = panchanga.get_nakshatra(longitude)
    house = houses.get_house_of_sign(ascendant_sign, sign)
    return {
        "longitude": round(longitude, 4),
        "sign": sign,
        "degree_in_sign": round(deg_in_sign, 4),
        "house": house,
        "chalit_house": chalit_bhava,
        "nakshatra": nak,
        "nakshatra_pada": pada,
        "nakshatra_lord": nak_lord,
        "retrograde": is_retrograde,
        "vargas": divisional.compute_all_vargas(longitude),
    }


def compute_birth_chart(name, birth_date, birth_time, place_name,
                         country_hint=None, latitude=None, longitude=None, tz_name=None,
                         dasha_years_forward=120, sex=None):
    """See module docstring for parameters. Returns a plain dict (JSON-serializable
    after passing datetimes through str() — see save_chart_json below).

    Wrapped in ephemeris.EPHEMERIS_LOCK: pyswisseph is not thread-safe (see
    that module's own note) - this ensures no two calls into it ever
    interleave, regardless of how many threads call compute_birth_chart
    concurrently (the local web app's ThreadingHTTPServer is the one
    caller in this project that actually can)."""
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        return _compute_birth_chart_locked(
            name, birth_date, birth_time, place_name, country_hint,
            latitude, longitude, tz_name, dasha_years_forward, sex,
        )


def _compute_birth_chart_locked(name, birth_date, birth_time, place_name,
                                 country_hint, latitude, longitude, tz_name,
                                 dasha_years_forward, sex):
    """The actual implementation - see compute_birth_chart above, which is
    just this function wrapped in the ephemeris thread-safety lock."""

    lat, lon, tz_name, location_meta = _resolve_location(
        place_name, country_hint, latitude, longitude, tz_name)
    local_dt, utc_dt, utc_offset_hours = _local_datetime_to_utc(birth_date, birth_time, tz_name)

    jd_ut = ephemeris.julian_day_ut(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour, utc_dt.minute, utc_dt.second,
        utc_offset_hours=0.0,  # utc_dt is already UTC, so offset is 0 here
    )

    ascendant_longitude, mc_longitude = ephemeris.get_ascendant_and_mc(jd_ut, lat, lon)
    ascendant_sign, ascendant_deg = panchanga.get_sign(ascendant_longitude)

    positions = ephemeris.get_all_positions(jd_ut)
    retro_flags = ephemeris.get_all_retrograde_flags(jd_ut)

    chalit_table, chalit_planet_bhavas = chalit_module.compute_chalit_for_chart(
        ascendant_longitude, mc_longitude, positions)

    planets = {
        p: _planet_detail(lon_p, ascendant_sign, retro_flags[p], chalit_planet_bhavas[p])
        for p, lon_p in positions.items()
    }

    ascendant_vargas = divisional.compute_all_vargas(ascendant_longitude)

    timeline = dasha.compute_vimshottari_timeline(
        utc_dt.replace(tzinfo=None), positions["Moon"], years_forward=dasha_years_forward)
    running_at_birth = dasha.find_running_dasha(timeline, utc_dt.replace(tzinfo=None))
    dasha_balance_at_birth = dasha.format_balance_at_birth(timeline, utc_dt.replace(tzinfo=None))

    moon_sign = planets["Moon"]["sign"]
    moon_nakshatra = planets["Moon"]["nakshatra"]
    avkahada_chakra = avkahada.compute_avkahada(moon_sign, moon_nakshatra)

    tropical_sun_longitude = ephemeris.get_tropical_sun_longitude(jd_ut)
    western_sun_sign, _ = panchanga.get_sign(tropical_sun_longitude)

    panchang = panchang_daily.compute_panchang(positions["Moon"], positions["Sun"])
    local_midnight_jd_ut = ephemeris.julian_day_ut(
        birth_date[0], birth_date[1], birth_date[2], 0, 0, 0, utc_offset_hours)
    day_details = panchang_daily.compute_day_details(local_midnight_jd_ut, lat, lon, jd_ut)

    mangal_dosha = manglik.compute_manglik_dosha(
        mars_sign=planets["Mars"]["sign"],
        ascendant_sign=ascendant_sign,
        moon_sign=moon_sign,
        venus_sign=planets["Venus"]["sign"],
    )

    planet_signs_for_avk = {p: planets[p]["sign"] for p in ashtakvarga.PLANET_ORDER}
    ashtakavarga_result = ashtakvarga.compute_ashtakavarga(planet_signs_for_avk, ascendant_sign)

    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "tradition": "Parashari",
        "ayanamsa": "Lahiri",
        "house_system": "whole_sign",
        "birth_input": {
            "birth_date": f"{birth_date[0]:04d}-{birth_date[1]:02d}-{birth_date[2]:02d}",
            "birth_time_local": f"{birth_time[0]:02d}:{birth_time[1]:02d}:{(birth_time[2] if len(birth_time) > 2 else 0):02d}",
            "place_name": place_name,
            "sex": sex,
        },
        "resolved_location": location_meta,
        "resolved_datetime": {
            "local": local_dt.isoformat(),
            "utc": utc_dt.isoformat(),
            "utc_offset_hours": utc_offset_hours,
            "julian_day_ut": jd_ut,
            "ayanamsa_value_deg": round(ephemeris.get_ayanamsa(jd_ut), 6),
        },
        "ascendant": {
            "longitude": round(ascendant_longitude, 4),
            "sign": ascendant_sign,
            "degree_in_sign": round(ascendant_deg, 4),
            "vargas": ascendant_vargas,
            "mc_longitude": round(mc_longitude, 4),
            "mc_sign": panchanga.get_sign(mc_longitude)[0],
        },
        "houses": houses.build_house_map(ascendant_sign),
        "planets": planets,
        "dasha": {
            "running_at_birth": running_at_birth,
            "balance_at_birth": dasha_balance_at_birth,
            "timeline": timeline,
        },
        "day_of_week": local_dt.strftime("%A"),
        "western_sun_sign": western_sun_sign,
        "avkahada_chakra": avkahada_chakra,
        "panchang": panchang,
        "day_details": day_details,
        "mangal_dosha": mangal_dosha,
        "ashtakavarga": ashtakavarga_result,
        "chalit": chalit_table,
        "caveats": {
            "geocoding": (
                "Place resolved via a bundled ~34,000-city gazetteer (see geocode.py). "
                "Verify resolved_location matches the intended place, especially for "
                "small towns or ambiguous names."
            ),
            "timezone": (
                "Exact for single-timezone countries. For multi-timezone countries "
                "(see timezone_resolver.MULTI_ZONE_COUNTRIES) this uses a "
                "nearest-principal-location approximation, not a real boundary lookup "
                "— check resolved_location.timezone_resolution.confidence."
            ),
            "rahu_ketu": "Mean lunar node convention (not True Node) — see ephemeris.py.",
            "divisional_charts_needing_check": sorted(divisional.NEEDS_CHECK_VARGAS),
            "ashtakavarga": (
                "Bhinnashtakavarga/Sarvashtakavarga only (raw bindu counts) — "
                "Sodhya Pinda / trikona-ekadhipatya reductions used for some "
                "advanced Ashtakavarga transit techniques are not computed. "
                "See ashtakvarga.py."
            ),
            "chalit": (
                "Sripati (quadrant-trisection) house-cusp system — a secondary "
                "refinement alongside the whole-sign chart used for all main "
                "interpretation, not a replacement for it. See chalit.py."
            ),
        },
    }


def _json_default(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def save_chart_json(chart, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2, ensure_ascii=False, default=_json_default)


def chart_to_json_string(chart):
    return json.dumps(chart, indent=2, ensure_ascii=False, default=_json_default)
