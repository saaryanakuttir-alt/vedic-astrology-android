"""
panchang_daily.py — the classical "Panchang" (five limbs of the almanac)
for a specific moment: Tithi, (Panchang) Yoga, Karana, and Paksha, computed
from the Sun's and Moon's sidereal longitudes; plus sunrise/sunset/day
duration and local sidereal time, which round out the "Basic Details"
section of a traditional chart printout.

NOTE ON NAMING: the 27 "Panchang Yogas" computed here (Vishkumbha,
Priti, ...) are a completely different classical system from the 24
*chart* yogas in classical_yogas.json / yogas.py (Gajakesari, Raja Yoga,
etc.) — same word, unrelated meaning. Don't confuse the two.

All four Panchang values and the sunrise/sunset/day-duration/sidereal-time
figures were cross-checked against a real reference chart (native
"Sammya", Howrah, 29 May 1992, 07:06 IST) and matched to within a few
tens of seconds (ordinary cross-software ephemeris/rounding noise):
    Tithi=Dvadasi, Paksha=Krishna, Yoga=Saubhagya, Karan=Taitila (~"Tetil"),
    Sunrise 04:52, Sunset 18:16, Day Duration 13:24, Sidereal Time 23:56.
"""
import ephemeris

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi",
]  # 15th name depends on paksha (Purnima / Amavasya) — handled below

PANCHANG_YOGA_NAMES = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
    "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti",
]
assert len(PANCHANG_YOGA_NAMES) == 27

_MOVABLE_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti (Bhadra)"]


def _tithi_number(moon_longitude, sun_longitude):
    diff = (moon_longitude - sun_longitude) % 360.0
    return int(diff // 12.0) + 1  # 1-30


def get_tithi(moon_longitude, sun_longitude):
    """Returns {"number": 1-30, "name": str, "paksha": "Shukla"|"Krishna",
    "day_of_paksha": 1-15}."""
    number = _tithi_number(moon_longitude, sun_longitude)
    number = min(number, 30)
    paksha = "Shukla" if number <= 15 else "Krishna"
    day_of_paksha = number if number <= 15 else number - 15
    if day_of_paksha == 15:
        name = "Purnima" if paksha == "Shukla" else "Amavasya"
    else:
        name = TITHI_NAMES[day_of_paksha - 1]
    return {"number": number, "name": name, "paksha": paksha, "day_of_paksha": day_of_paksha}


def get_panchang_yoga(moon_longitude, sun_longitude):
    """Returns {"number": 1-27, "name": str} for the classical Panchang
    Yoga (Sun + Moon longitude, divided into 27 equal spans) — NOT to be
    confused with the 24 chart yogas in yogas.py (see module docstring)."""
    total = (moon_longitude + sun_longitude) % 360.0
    index = int(total // (360.0 / 27.0))
    index = min(index, 26)
    return {"number": index + 1, "name": PANCHANG_YOGA_NAMES[index]}


def get_karana(moon_longitude, sun_longitude):
    """Returns {"number": 1-60, "name": str} for the half-tithi Karana.
    Karana 1 is always the fixed "Kimstughna"; 2-57 cycle through the 7
    movable karanas 8 times; 58-60 are the fixed Shakuni/Chatushpada/Naga."""
    diff = (moon_longitude - sun_longitude) % 360.0
    number = int(diff // 6.0) + 1
    number = min(number, 60)
    if number == 1:
        name = "Kimstughna"
    elif 2 <= number <= 57:
        name = _MOVABLE_KARANAS[(number - 2) % 7]
    elif number == 58:
        name = "Shakuni"
    elif number == 59:
        name = "Chatushpada"
    else:
        name = "Naga"
    return {"number": number, "name": name}


def compute_panchang(moon_longitude, sun_longitude):
    """Bundles Tithi, Panchang Yoga, and Karana (Paksha is included inside
    the Tithi dict, matching how a reference chart printout groups it)."""
    return {
        "tithi": get_tithi(moon_longitude, sun_longitude),
        "yoga": get_panchang_yoga(moon_longitude, sun_longitude),
        "karana": get_karana(moon_longitude, sun_longitude),
    }


def _format_hms(decimal_hours):
    """Formats decimal hours as H:MM:SS, wrapping into [0, 24)."""
    decimal_hours = decimal_hours % 24.0
    total_seconds = round(decimal_hours * 3600.0)
    h, remainder = divmod(total_seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def compute_day_details(local_midnight_jd_ut, latitude, longitude, birth_jd_ut):
    """Sunrise, sunset, day duration, and local sidereal time at birth —
    the remaining "Basic Details" fields not already covered elsewhere.
    `local_midnight_jd_ut` must be the JD (UT) of 00:00:00 local civil time
    on the birth date (see ephemeris.get_sunrise_sunset for why)."""
    sunrise_jd, sunset_jd = ephemeris.get_sunrise_sunset(local_midnight_jd_ut, latitude, longitude)
    result = {
        "sunrise_jd_ut": sunrise_jd,
        "sunset_jd_ut": sunset_jd,
        "sunrise_local": None,
        "sunset_local": None,
        "day_duration": None,
    }
    if sunrise_jd is not None and sunset_jd is not None:
        # Derive sunrise/sunset LOCAL clock time directly from their offset
        # (in days) from local midnight — timezone-agnostic and avoids any
        # fragility around the Julian Day's noon-based convention.
        sunrise_local_hours = (sunrise_jd - local_midnight_jd_ut) * 24.0
        sunset_local_hours = (sunset_jd - local_midnight_jd_ut) * 24.0
        result["sunrise_local"] = _format_hms(sunrise_local_hours)
        result["sunset_local"] = _format_hms(sunset_local_hours)
        result["day_duration"] = _format_hms(sunset_local_hours - sunrise_local_hours)
    result["local_sidereal_time_at_birth"] = _format_hms(
        ephemeris.get_local_sidereal_time(birth_jd_ut, longitude))
    return result
