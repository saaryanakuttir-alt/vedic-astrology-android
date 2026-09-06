"""
houses.py — whole-sign house assignment (Rashi = Bhava), the standard
Parashari house system. This project deliberately does NOT use Placidus
or other quadrant house systems, matching the "Parashari only" scope of
the whole knowledge base.

Whole-sign houses: whichever sign the Ascendant falls in IS the 1st house
in its entirety (regardless of the exact Ascendant degree within it); the
next sign is the 2nd house; and so on around the zodiac.
"""
from panchanga import SIGNS


def get_house_of_sign(ascendant_sign, target_sign):
    """
    Returns the house number (1-12) that `target_sign` occupies, counting
    from `ascendant_sign` as house 1. This is exactly the
    "relation_of_placed_house_from_lord_house" logic already used in
    house_lord_placement.json — kept consistent with that file's counting
    convention (inclusive counting: house 1 is the ascendant sign itself).
    """
    asc_index = SIGNS.index(ascendant_sign)
    target_index = SIGNS.index(target_sign)
    return ((target_index - asc_index) % 12) + 1


def get_sign_of_house(ascendant_sign, house_number):
    """Inverse of get_house_of_sign: which sign occupies a given house number (1-12)."""
    if not 1 <= house_number <= 12:
        raise ValueError("house_number must be 1-12")
    asc_index = SIGNS.index(ascendant_sign)
    return SIGNS[(asc_index + house_number - 1) % 12]


def build_house_map(ascendant_sign):
    """Returns {house_number: sign_name} for all 12 houses given the Ascendant sign."""
    return {h: get_sign_of_house(ascendant_sign, h) for h in range(1, 13)}
