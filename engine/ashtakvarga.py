"""
ashtakvarga.py — the classical Ashtakavarga bindu (benefic-point) system:
for each of the 7 classical planets, a Bhinnashtakavarga ("individual
ashtakavarga") table showing how many of 8 contributors (the 7 planets
plus the Ascendant) place a bindu into each of the 12 signs, and the
Sarvashtakavarga ("total ashtakavarga") — the sign-wise sum across all 7
planets' tables.

METHOD (unchanged across virtually every classical source and every piece
of mainstream software): each of the 8 contributors (Sun, Moon, Mars,
Mercury, Jupiter, Venus, Saturn, Lagna) has a FIXED list of "benefic
house positions counted from that contributor's own sign" for each of
the 7 planets' Bhinnashtakavarga tables. To build planet P's table: for
each of the 8 contributors, find the contributor's own sign, then place
a bindu in every sign that is one of P's benefic positions counted
forward from the contributor's sign (position 1 = the contributor's own
sign). Summing the 8 contributors' bindus, sign by sign, gives planet
P's 12-sign Bhinnashtakavarga row (each cell 0-8). Summing all 7
planets' rows, sign by sign, gives the Sarvashtakavarga.

The contribution tables below were verified against a reliable published
source (vedastro.org's Ashtakavarga reference) and cross-checked two ways:
  1. Each planet's per-contributor position-COUNT sums to that planet's
     well-known classical Bhinnashtakavarga total (Sun=48, Moon=49,
     Mars=39, Mercury=54, Jupiter=56, Venus=52, Saturn=39 — these 7
     totals sum to the invariant grand total of 337).
  2. The FULL COMPUTED TABLE (all 7 rows x 12 signs, 84 cells) was run
     against a real reference chart (AstroSage kundli, native "Sammya":
     Howrah, 29 May 1992, 07:06 IST) and matched EXACTLY, cell for cell,
     including the printed Total row — see
     tests/test_kundli_details.py's Ashtakavarga test.

Rahu and Ketu are NOT part of the classical 7-planet Ashtakavarga system
(this is standard — Ashtakavarga is defined only for the 7 physical
grahas) and are not included here.
"""
from panchanga import SIGNS

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
CONTRIBUTOR_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]

# {target_planet: {contributor: [benefic positions counted from contributor's sign, 1-12]}}
_CONTRIBUTIONS = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11], "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11], "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [3, 4, 6, 10, 11, 12],
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11], "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11], "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12], "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11], "Lagna": [3, 6, 10, 11],
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11], "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12], "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11], "Lagna": [1, 3, 6, 10, 11],
    },
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12], "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11], "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12], "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11], "Lagna": [1, 2, 4, 6, 8, 10, 11],
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11], "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11], "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12], "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "Venus": {
        "Sun": [8, 11, 12], "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12], "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11], "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11], "Lagna": [1, 2, 3, 4, 5, 8, 9, 11],
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11], "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12], "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12], "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11], "Lagna": [1, 3, 4, 6, 10, 11],
    },
}

# Each planet's classical total bindu count (sum across all 12 signs of its
# Bhinnashtakavarga row) — used as an internal self-check, not just docs.
_EXPECTED_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
                    "Jupiter": 56, "Venus": 52, "Saturn": 39}
assert sum(_EXPECTED_TOTALS.values()) == 337


def _positions_to_signs(contributor_sign_index, positions):
    """Position 1 = the contributor's own sign; position N = (N-1) signs
    forward from it. Returns the set of 0-based sign indices that get a bindu."""
    return {(contributor_sign_index + p - 1) % 12 for p in positions}


def compute_bhinnashtakavarga(target_planet, contributor_signs):
    """
    contributor_signs: {"Sun": sign_name, "Moon": sign_name, ..., "Lagna": sign_name}
    — the sign each of the 8 contributors occupies in this chart.

    Returns {sign_name: bindu_count (0-8)} for target_planet's Bhinnashtakavarga.
    """
    rules = _CONTRIBUTIONS[target_planet]
    bindus = [0] * 12
    for contributor, positions in rules.items():
        contributor_sign = contributor_signs[contributor]
        contributor_index = SIGNS.index(contributor_sign)
        for sign_index in _positions_to_signs(contributor_index, positions):
            bindus[sign_index] += 1
    total = sum(bindus)
    expected = _EXPECTED_TOTALS[target_planet]
    if total != expected:
        raise AssertionError(
            f"Bhinnashtakavarga total for {target_planet} was {total}, expected {expected} "
            "— this should never happen given a fixed, internally-consistent contribution "
            "table; check contributor_signs for a bad/missing entry."
        )
    return {SIGNS[i]: bindus[i] for i in range(12)}


def compute_ashtakavarga(planet_signs, ascendant_sign):
    """
    planet_signs: {"Sun": sign, "Moon": sign, ..., "Saturn": sign} (the 7
        classical planets only — Rahu/Ketu excluded, see module docstring).
    ascendant_sign: the Lagna's sign.

    Returns:
        {
          "bhinnashtakavarga": {planet: {sign: bindus}},
          "sarvashtakavarga": {sign: total_bindus},   # sums to 337
        }
    """
    contributor_signs = dict(planet_signs)
    contributor_signs["Lagna"] = ascendant_sign

    bhinna = {planet: compute_bhinnashtakavarga(planet, contributor_signs)
              for planet in PLANET_ORDER}

    sarva = {sign: sum(bhinna[planet][sign] for planet in PLANET_ORDER) for sign in SIGNS}
    grand_total = sum(sarva.values())
    if grand_total != 337:
        raise AssertionError(f"Sarvashtakavarga grand total was {grand_total}, expected 337.")

    return {"bhinnashtakavarga": bhinna, "sarvashtakavarga": sarva}
