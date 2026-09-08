"""
ephemeris.py — thin wrapper around Swiss Ephemeris (pyswisseph) for the
9 classical Parashari grahas plus the Ascendant.

Everything here is SIDEREAL (Lahiri/Chitrapaksha ayanamsa), which is the
standard ayanamsa for mainstream Parashari astrology. If you ever need to
compare against a chart built with a different ayanamsa (Raman, KP, etc.),
change LAHIRI below to the matching swe.SIDM_* constant — but note the
whole knowledge base (dignity tables, etc.) assumes standard sidereal
positions, not tied to one ayanamsa in particular (dignity is sign-based).

RAHU/KETU NOTE: this uses the MEAN lunar node (not the "True Node"), which
is the classical convention used by most traditional Parashari software.
The mean node moves smoothly; the true node oscillates slightly. Both are
used in modern practice — mean node is the more traditional default and is
what this module uses. To switch to the true node, change MEAN_NODE to
swe.TRUE_NODE below.

THREAD SAFETY: pyswisseph's sidereal mode (set_sid_mode) is THREAD-LOCAL in
the underlying C library - confirmed by direct testing (2026-09-08).
set_sid_mode(SIDM_LAHIRI) below runs once at import time, on whichever
thread happens to import this module first (the main thread, in every
caller this project has). Any OTHER thread that later calls swisseph
directly - with NO error, warning, or exception of any kind - silently
computes against THAT thread's own never-initialized sidereal mode
instead, giving a wrong but perfectly deterministic ayanamsa (off by
~0.88 degrees in the case tested), enough to shift a planet into the
wrong divisional-chart sign or house boundary. This only bit the local
web app (webapp/server.py's ThreadingHTTPServer genuinely runs each
request's Python code on its own thread); the single-threaded desktop
and Android UIs never call this module from more than one thread, so
they were never at risk. The fix is ensure_sidereal_mode() below -
call it at the very start of any function that will call into swisseph,
on the CURRENT thread, every time (it's a cheap C call - safe and cheap
to call unconditionally rather than trying to track "has this thread
already set it"). EPHEMERIS_LOCK is kept as well, as ordinary good
hygiene around a C extension with any shared mutable state, but it is
NOT what fixes this specific bug (a lock only prevents two threads
running at the SAME instant - this bug reproduces on a single, lone,
non-main thread with no other thread running at all).
"""
import threading

import swisseph as swe

EPHEMERIS_LOCK = threading.Lock()


def ensure_sidereal_mode():
    """Call at the start of every function that calls into swisseph,
    before any other swe.* call, on whatever thread is actually running -
    see the THREAD SAFETY note above for why this can't just be the
    module-level call below."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)


# ---------------------------------------------------------------------------
# Ayanamsa
# ---------------------------------------------------------------------------
# Kept for the main thread's own first import (and any single-threaded
# caller that never touches ensure_sidereal_mode itself) - NOT sufficient
# on its own for multi-threaded callers, see THREAD SAFETY above.
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------------------------------------------------------------------------
# Planet constants used throughout this project (Parashari 9 grahas)
# ---------------------------------------------------------------------------
MEAN_NODE = swe.MEAN_NODE  # Rahu; classical convention (see module docstring)

PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": MEAN_NODE,
    # Ketu is not a real body swisseph knows about — it's always exactly
    # 180 degrees from Rahu. Computed manually in get_all_positions() below.
}

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

SIDEREAL_FLAG = swe.FLG_SWIEPH | swe.FLG_SIDEREAL


def julian_day_ut(year, month, day, hour, minute, second, utc_offset_hours):
    """
    Convert a LOCAL civil date/time (with its UTC offset in hours, e.g. +5.5
    for India) into a Julian Day in Universal Time, which is what every
    swisseph call below expects.

    utc_offset_hours: local_time - UTC, e.g. India = +5.5, New York (EST) = -5.
    Get this from timezone_resolver.py — don't hardcode it per call site.
    """
    decimal_hour_local = hour + minute / 60.0 + second / 3600.0
    decimal_hour_ut = decimal_hour_local - utc_offset_hours
    # swe.julday handles hour values outside [0, 24) by rolling the date,
    # so we don't need to manually adjust the calendar day here.
    return swe.julday(year, month, day, decimal_hour_ut)


def get_ascendant(jd_ut, latitude, longitude):
    """
    Returns the sidereal Ascendant (Lagna) longitude in degrees [0, 360).

    We ask swisseph for houses using the Placidus system (hsys=b'P') purely
    as a mechanism to obtain ascmc[0], the Ascendant point — Parashari
    astrology uses WHOLE-SIGN houses (see houses.py), not Placidus cusps,
    so the house cusps themselves (cusps[1..12]) are discarded. The
    Ascendant point itself is identical regardless of which house system
    you ask swisseph to compute cusps for.
    """
    cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b'P', flags=swe.FLG_SIDEREAL)
    asc_longitude = ascmc[0]
    return asc_longitude % 360.0


def get_ascendant_and_mc(jd_ut, latitude, longitude):
    """
    Returns (ascendant_longitude, mc_longitude), both sidereal degrees
    [0, 360). The MC (Medium Coeli — where the ecliptic crosses the local
    meridian) is used by chalit.py to build the Sripati Bhava (house-cusp)
    chart; it's house-system-independent (same value regardless of which
    hsys byte is passed to swe.houses_ex), so reusing Placidus here is
    just a mechanism to retrieve ascmc, same as get_ascendant() above.
    """
    cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b'P', flags=swe.FLG_SIDEREAL)
    return ascmc[0] % 360.0, ascmc[1] % 360.0


def get_planet_longitude(jd_ut, planet_name):
    """Sidereal longitude in degrees [0, 360) for one of the 7 classical
    planets or Rahu. Use get_all_positions() for the full set including Ketu."""
    if planet_name == "Ketu":
        raise ValueError("Ketu has no direct swisseph body — use get_all_positions()")
    planet_id = PLANET_IDS[planet_name]
    result, _ = swe.calc_ut(jd_ut, planet_id, SIDEREAL_FLAG)
    return result[0] % 360.0


def get_all_positions(jd_ut):
    """
    Returns {planet_name: sidereal_longitude_degrees} for all 9 grahas.
    Ketu is always Rahu + 180 (shadow points are always exactly opposite).
    """
    positions = {}
    for name in PLANET_ORDER:
        if name == "Ketu":
            continue
        positions[name] = get_planet_longitude(jd_ut, name)
    positions["Ketu"] = (positions["Rahu"] + 180.0) % 360.0
    return positions


WAR_ELIGIBLE_PLANETS = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]  # Sun/Moon/Rahu/Ketu never fight a Graha Yuddha


def get_all_latitudes(jd_ut):
    """Returns {planet_name: ecliptic_latitude_degrees} for the 5 planets
    that classically participate in Graha Yuddha (planetary war) - Sun,
    Moon, Rahu, and Ketu are excluded by classical rule, not by an
    oversight here. Latitude (index 1 of swe.calc_ut's result tuple,
    degrees north/south of the ecliptic) is what BPHS uses to decide a
    war's winner - see graha_yuddha.py for that logic."""
    lats = {}
    for name in WAR_ELIGIBLE_PLANETS:
        result, _ = swe.calc_ut(jd_ut, PLANET_IDS[name], SIDEREAL_FLAG)
        lats[name] = result[1]
    return lats


def get_ayanamsa(jd_ut):
    """The Lahiri ayanamsa value (degrees) applied for this date — useful
    for debugging / cross-checking against other software's displayed value."""
    return swe.get_ayanamsa_ut(jd_ut)


# ---------------------------------------------------------------------------
# Retrograde motion
# ---------------------------------------------------------------------------
# A planet is classically "retrograde" (vakri) when its apparent daily motion
# through the zodiac is backwards — i.e. its ecliptic longitude speed is
# negative. Sun and Moon never retrograde (they have no real backward loop
# from Earth's vantage point) and are always reported as False. The lunar
# nodes (Rahu/Ketu) move backwards (westward) by default under the MEAN node
# convention used here — some traditions still call this "retrograde" in
# software displays, so it's reported as True to match, but note it isn't a
# real reversal of motion (mean nodes never turn direct).
_NEVER_RETROGRADE = {"Sun", "Moon"}
_ALWAYS_RETROGRADE = {"Rahu", "Ketu"}  # mean node: always moving backwards


def get_all_speeds(jd_ut):
    """Returns {planet_name: longitude_speed_degrees_per_day} for the 7
    classical planets that swisseph tracks directly (Sun through Saturn).
    Rahu/Ketu are omitted (their "speed" is handled separately below since
    the mean node's motion doesn't need a live speed lookup)."""
    speeds = {}
    for name, planet_id in PLANET_IDS.items():
        if name == "Rahu":
            continue
        result, _ = swe.calc_ut(jd_ut, planet_id, SIDEREAL_FLAG | swe.FLG_SPEED)
        speeds[name] = result[3]  # index 3 = speed in longitude, deg/day
    return speeds


def get_all_retrograde_flags(jd_ut):
    """Returns {planet_name: bool} for all 9 grahas — True if retrograde
    (vakri) at this moment. Sun/Moon are always False; Rahu/Ketu are always
    True under the mean-node convention (see module note above)."""
    speeds = get_all_speeds(jd_ut)
    flags = {}
    for name in PLANET_ORDER:
        if name in _NEVER_RETROGRADE:
            flags[name] = False
        elif name in _ALWAYS_RETROGRADE:
            flags[name] = True
        else:
            flags[name] = speeds[name] < 0
    return flags


# ---------------------------------------------------------------------------
# Tropical (Western) positions — used only for the single "Western Sun sign"
# display field. Everything else in this project is sidereal; this is the
# one deliberate exception, since Western tropical sun-sign is a commonly
# expected reference field (distinct from the sidereal "SunSign (Indian)").
# ---------------------------------------------------------------------------
TROPICAL_FLAG = swe.FLG_SWIEPH  # no FLG_SIDEREAL => tropical longitude


def get_tropical_sun_longitude(jd_ut):
    result, _ = swe.calc_ut(jd_ut, swe.SUN, TROPICAL_FLAG)
    return result[0] % 360.0


# ---------------------------------------------------------------------------
# Sunrise / sunset and local sidereal time — used for Panchang details.
# ---------------------------------------------------------------------------
def get_sunrise_sunset(local_midnight_jd_ut, latitude, longitude):
    """
    Returns (sunrise_jd_ut, sunset_jd_ut) — the Julian Days (UT) of true
    sunrise and sunset for the LOCAL CALENDAR DAY that begins at
    `local_midnight_jd_ut` (the JD, in UT, of 00:00:00 local civil time on
    the day in question — the caller computes this using the correct local
    UTC offset, since this module has no timezone awareness of its own).
    Searching forward from local midnight guarantees both events found are
    that same calendar day's sunrise/sunset, not the previous day's.

    Uses swe.rise_trans with the standard solar disc-edge convention (upper
    limb, with atmospheric refraction) — the usual almanac/Panchang
    convention. Returns (None, None) for the rare high-latitude case where
    the sun does not rise or set that day, rather than raising an error.
    """
    geopos = (longitude, latitude, 0.0)
    try:
        _, rise_data = swe.rise_trans(local_midnight_jd_ut, swe.SUN, swe.CALC_RISE, geopos)
        sunrise_jd = rise_data[0]
    except swe.Error:
        sunrise_jd = None
    try:
        _, set_data = swe.rise_trans(local_midnight_jd_ut, swe.SUN, swe.CALC_SET, geopos)
        sunset_jd = set_data[0]
    except swe.Error:
        sunset_jd = None
    return sunrise_jd, sunset_jd


def get_local_sidereal_time(jd_ut, longitude):
    """Local Mean Sidereal Time, in decimal hours [0, 24) — Greenwich
    Sidereal Time (swe.sidtime) adjusted for geographic longitude."""
    gst_hours = swe.sidtime(jd_ut)
    lst_hours = (gst_hours + longitude / 15.0) % 24.0
    return lst_hours
