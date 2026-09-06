"""
avkahada.py — the "Avkahada Chakra" classification tables: five classical
nakshatra/rashi-based categorizations used to describe a native's basic
temperament and (traditionally) for marriage-compatibility (Ashtakoot)
scoring. This module computes facts only — no interpretation.

All five values were cross-checked against a real reference chart (native
"Sammya", Moon in Ashwini/Aries) and matched exactly:
    Varna=Kshatriya, Vasya=Chatushpada (Chatu), Yoni=Ashva (Horse),
    Gana=Devta (Deva), Nadi=Adi.

Two values are deliberately NOT computed here, consistent with this
project's practice of flagging genuinely disputed classical points rather
than guessing (see divisional.py's D60 note for the precedent):

  - "Paya" (metal associated with the nakshatra quarter/pada — Gold,
    Silver, Copper, or Iron) uses a formula that varies across sources
    depending on whether the nakshatra's RULING PLANET or its RASHI LORD
    is used as the entry point, and the two disagree for a meaningful
    minority of padas. Not implemented; flagged in the returned dict.
  - Vashya (Vasya) below uses the simple WHOLE-SIGN table. Fuller
    classical treatments split Leo, Sagittarius, Capricorn and Scorpio at
    their midpoint into two different Vashya categories — that half-sign
    split is not implemented here (documented limitation, see
    VASHYA_SIMPLIFICATION_NOTE below).
"""
from panchanga import SIGNS, NAKSHATRAS

VASHYA_SIMPLIFICATION_NOTE = (
    "Vashya is computed from the Moon's whole sign only. Fuller classical "
    "treatments split Sagittarius and Capricorn at their midpoint into a "
    "different Vashya category for each half (front-Sagittarius is Manava, "
    "back-Sagittarius is Chatushpada; front-Capricorn is Chatushpada, "
    "back-Capricorn is Jalachara) — not implemented here, so those two "
    "signs use their more commonly-cited whole-sign default instead."
)
PAYA_NOTE = (
    "Paya (the lucky metal — Gold/Silver/Copper/Iron — associated with the "
    "Moon's nakshatra pada) is not computed: sources disagree on whether it "
    "keys off the nakshatra's ruling planet or its rashi lord, and the two "
    "give different answers for a meaningful minority of padas."
)

# ---------------------------------------------------------------------------
# Varna — by the Moon's sign ELEMENT. Water=Brahmin, Fire=Kshatriya,
# Earth=Vaishya, Air=Shudra.
# ---------------------------------------------------------------------------
_VARNA_BY_SIGN = {
    "Cancer": "Brahmin", "Scorpio": "Brahmin", "Pisces": "Brahmin",
    "Aries": "Kshatriya", "Leo": "Kshatriya", "Sagittarius": "Kshatriya",
    "Taurus": "Vaishya", "Virgo": "Vaishya", "Capricorn": "Vaishya",
    "Gemini": "Shudra", "Libra": "Shudra", "Aquarius": "Shudra",
}

# Classical hierarchy (highest first) — used by compatibility.py's Varna
# Koota, which compares rank rather than just equality.
VARNA_RANK = {"Brahmin": 4, "Kshatriya": 3, "Vaishya": 2, "Shudra": 1}

# ---------------------------------------------------------------------------
# Vashya (Vasya) — by the Moon's whole sign (see simplification note above).
# ---------------------------------------------------------------------------
_VASHYA_BY_SIGN = {
    "Aries": "Chatushpada (quadruped)", "Taurus": "Chatushpada (quadruped)",
    "Sagittarius": "Chatushpada (quadruped)", "Capricorn": "Chatushpada (quadruped)",
    "Gemini": "Manava (human)", "Virgo": "Manava (human)",
    "Libra": "Manava (human)", "Aquarius": "Manava (human)",
    "Cancer": "Jalachara (aquatic)", "Pisces": "Jalachara (aquatic)",
    "Leo": "Vanachara (wild)",
    "Scorpio": "Keeta (insect)",
}

# ---------------------------------------------------------------------------
# Yoni — one of 14 animal symbols (each shared by 2 nakshatras, one male one
# female), by nakshatra.
# ---------------------------------------------------------------------------
_YONI_BY_NAKSHATRA = {
    "Ashwini": "Ashva (Horse) - M", "Bharani": "Gaja (Elephant) - F",
    "Krittika": "Mesha (Goat) - F", "Rohini": "Sarpa (Serpent) - M",
    "Mrigashira": "Sarpa (Serpent) - F", "Ardra": "Shwan (Dog) - F",
    "Punarvasu": "Marjar (Cat) - M", "Pushya": "Mesha (Goat) - M",
    "Ashlesha": "Marjar (Cat) - F", "Magha": "Mushak (Rat) - M",
    "Purva Phalguni": "Mushak (Rat) - F", "Uttara Phalguni": "Gau (Cow) - M",
    "Hasta": "Mahish (Buffalo) - F", "Chitra": "Vyaghra (Tiger) - F",
    "Swati": "Mahish (Buffalo) - M", "Vishakha": "Vyaghra (Tiger) - M",
    "Anuradha": "Mriga (Deer) - F", "Jyeshtha": "Mriga (Deer) - M",
    "Mula": "Shwan (Dog) - M", "Purva Ashadha": "Vanar (Monkey) - F",
    "Uttara Ashadha": "Nakul (Mongoose) - M", "Shravana": "Vanar (Monkey) - M",
    "Dhanishta": "Simha (Lion) - F", "Shatabhisha": "Ashva (Horse) - F",
    "Purva Bhadrapada": "Simha (Lion) - M", "Uttara Bhadrapada": "Gau (Cow) - F",
    "Revati": "Gaja (Elephant) - M",
}

# ---------------------------------------------------------------------------
# Gana — Deva (divine), Manushya (human), or Rakshasa (demon), by nakshatra.
# ---------------------------------------------------------------------------
_GANA_BY_NAKSHATRA = {
    "Ashwini": "Deva", "Mrigashira": "Deva", "Punarvasu": "Deva", "Pushya": "Deva",
    "Hasta": "Deva", "Swati": "Deva", "Anuradha": "Deva", "Shravana": "Deva",
    "Revati": "Deva",
    "Bharani": "Manushya", "Rohini": "Manushya", "Ardra": "Manushya",
    "Purva Phalguni": "Manushya", "Uttara Phalguni": "Manushya",
    "Purva Ashadha": "Manushya", "Uttara Ashadha": "Manushya",
    "Purva Bhadrapada": "Manushya", "Uttara Bhadrapada": "Manushya",
    "Krittika": "Rakshasa", "Ashlesha": "Rakshasa", "Magha": "Rakshasa",
    "Chitra": "Rakshasa", "Vishakha": "Rakshasa", "Jyeshtha": "Rakshasa",
    "Mula": "Rakshasa", "Dhanishta": "Rakshasa", "Shatabhisha": "Rakshasa",
}

# ---------------------------------------------------------------------------
# Nadi — Adi (Vata), Madhya (Pitta), or Antya (Kapha), by nakshatra.
# ---------------------------------------------------------------------------
_NADI_BY_NAKSHATRA = {
    "Ashwini": "Adi (Vata)", "Ardra": "Adi (Vata)", "Punarvasu": "Adi (Vata)",
    "Uttara Phalguni": "Adi (Vata)", "Hasta": "Adi (Vata)", "Jyeshtha": "Adi (Vata)",
    "Mula": "Adi (Vata)", "Shatabhisha": "Adi (Vata)", "Purva Bhadrapada": "Adi (Vata)",
    "Bharani": "Madhya (Pitta)", "Mrigashira": "Madhya (Pitta)", "Pushya": "Madhya (Pitta)",
    "Purva Phalguni": "Madhya (Pitta)", "Chitra": "Madhya (Pitta)", "Anuradha": "Madhya (Pitta)",
    "Purva Ashadha": "Madhya (Pitta)", "Dhanishta": "Madhya (Pitta)",
    "Uttara Bhadrapada": "Madhya (Pitta)",
    "Krittika": "Antya (Kapha)", "Rohini": "Antya (Kapha)", "Ashlesha": "Antya (Kapha)",
    "Magha": "Antya (Kapha)", "Swati": "Antya (Kapha)", "Vishakha": "Antya (Kapha)",
    "Uttara Ashadha": "Antya (Kapha)", "Shravana": "Antya (Kapha)", "Revati": "Antya (Kapha)",
}

# Bare English animal name only (Sanskrit name and gender both dropped,
# e.g. "Marjar (Cat) - F" -> "Cat") — used by compatibility.py's Yoni Koota,
# which compares animal identity (via the classical English names the 7
# enemy pairs are conventionally listed under), not the male/female variant.
YONI_ANIMAL_BY_NAKSHATRA = {
    nak: label.split(" - ")[0].split("(")[1].rstrip(")")
    for nak, label in _YONI_BY_NAKSHATRA.items()
}

assert set(_VARNA_BY_SIGN) == set(SIGNS)
assert set(_VASHYA_BY_SIGN) == set(SIGNS)
assert set(_YONI_BY_NAKSHATRA) == set(NAKSHATRAS)
assert set(_GANA_BY_NAKSHATRA) == set(NAKSHATRAS)
assert set(_NADI_BY_NAKSHATRA) == set(NAKSHATRAS)


def compute_avkahada(moon_sign, moon_nakshatra):
    """Given the Moon's rashi (sign) and nakshatra, returns the Avkahada
    Chakra dict (Varna, Vasya, Yoni, Gana, Nadi — Paya deliberately
    omitted, see module docstring)."""
    return {
        "varna": _VARNA_BY_SIGN[moon_sign],
        "vasya": _VASHYA_BY_SIGN[moon_sign],
        "yoni": _YONI_BY_NAKSHATRA[moon_nakshatra],
        "gana": _GANA_BY_NAKSHATRA[moon_nakshatra],
        "nadi": _NADI_BY_NAKSHATRA[moon_nakshatra],
        "paya": None,
        "notes": [VASHYA_SIMPLIFICATION_NOTE, PAYA_NOTE],
    }
