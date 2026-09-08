"""maitri.py — Panchadha Maitri (five-fold planetary friendship): Naisargika
(natural, permanent) friendship combined with Tatkalika (temporal, chart-
specific) friendship, per classical Parashari rules. Covers only the 7
classical grahas — Rahu/Ketu are traditionally not assigned a natural-
friendship row of their own (their whole dignity/relationship scheme is
already flagged as disputed elsewhere in this project — see
astrology_tables.py's module docstring).

Naisargika Maitri (natural friendship) is directional and NOT necessarily
symmetric — e.g. the Moon considers Mercury a friend, but Mercury considers
the Moon an enemy. This is a real, well-documented classical feature (every
planet's natural disposition toward every other is fixed by its own
temperament), not an error to "fix" into symmetry.

Tatkalika Maitri (temporal friendship) is symmetric and purely positional:
two planets sitting 2, 3, 4, 10, 11, or 12 houses apart from each other (by
the same inclusive-counting convention as astrology_tables.house_distance)
are temporal friends for THIS chart; any other separation (conjunct, or 5,
6, 7, 8, or 9 houses apart) makes them temporal enemies.

Combining the two gives one of five grades (Panchadha Maitri):
    natural friend + temporal friend  -> Adhi Mitra   (Great Friend)
    natural friend + temporal enemy   -> Sama         (Neutral)
    natural neutral + temporal friend -> Mitra        (Friend)
    natural neutral + temporal enemy  -> Shatru       (Enemy)
    natural enemy + temporal friend   -> Sama         (Neutral)
    natural enemy + temporal enemy    -> Adhi Shatru  (Great Enemy)
"""
from astrology_tables import house_distance

CLASSICAL_SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

# Directional: NATURAL_FRIENDSHIP[A][B] is how A regards B.
NATURAL_FRIENDSHIP = {
    "Sun":     {"friends": ["Moon", "Mars", "Jupiter"], "neutral": ["Mercury"],
                "enemies": ["Venus", "Saturn"]},
    "Moon":    {"friends": ["Sun", "Mercury"], "neutral": ["Mars", "Jupiter", "Venus", "Saturn"],
                "enemies": []},
    "Mars":    {"friends": ["Sun", "Moon", "Jupiter"], "neutral": ["Venus", "Saturn"],
                "enemies": ["Mercury"]},
    "Mercury": {"friends": ["Sun", "Venus"], "neutral": ["Mars", "Jupiter", "Saturn"],
                "enemies": ["Moon"]},
    "Jupiter": {"friends": ["Sun", "Moon", "Mars"], "neutral": ["Saturn"],
                "enemies": ["Mercury", "Venus"]},
    "Venus":   {"friends": ["Mercury", "Saturn"], "neutral": ["Mars", "Jupiter"],
                "enemies": ["Sun", "Moon"]},
    "Saturn":  {"friends": ["Mercury", "Venus"], "neutral": ["Jupiter"],
                "enemies": ["Sun", "Moon", "Mars"]},
}

assert set(NATURAL_FRIENDSHIP) == set(CLASSICAL_SEVEN)
for _p, _row in NATURAL_FRIENDSHIP.items():
    _others = _row["friends"] + _row["neutral"] + _row["enemies"]
    assert sorted(_others) == sorted(o for o in CLASSICAL_SEVEN if o != _p), \
        f"{_p}'s natural-friendship row doesn't cover the other 6 grahas exactly once"

_TEMPORAL_FRIEND_DISTANCES = {2, 3, 4, 10, 11, 12}

_COMBINED_GRADE = {
    ("friend", "friend"): "Adhi Mitra",
    ("friend", "enemy"): "Sama",
    ("neutral", "friend"): "Mitra",
    ("neutral", "enemy"): "Shatru",
    ("enemy", "friend"): "Sama",
    ("enemy", "enemy"): "Adhi Shatru",
}


def natural_friendship(planet_a, planet_b):
    """How `planet_a` regards `planet_b`: 'friend', 'neutral', or 'enemy'."""
    row = NATURAL_FRIENDSHIP[planet_a]
    if planet_b in row["friends"]:
        return "friend"
    if planet_b in row["neutral"]:
        return "neutral"
    return "enemy"


def temporal_friendship(house_a, house_b):
    """Symmetric: 'friend' if the two houses are 2/3/4/10/11/12 apart in
    EITHER direction, else 'enemy'."""
    return "friend" if (
        house_distance(house_a, house_b) in _TEMPORAL_FRIEND_DISTANCES
        or house_distance(house_b, house_a) in _TEMPORAL_FRIEND_DISTANCES
    ) else "enemy"


def combined_grade(natural, temporal):
    """The five-fold Panchadha Maitri grade for one (natural, temporal) pair."""
    return _COMBINED_GRADE[(natural, temporal)]


def panchadha_maitri(planet_a, planet_b, house_a, house_b):
    """Full result for how `planet_a` regards `planet_b` in this chart:
    {"natural": ..., "temporal": ..., "grade": ...}. Call twice (swap a/b)
    for planet_b's own (possibly different) view of planet_a, since natural
    friendship is directional."""
    natural = natural_friendship(planet_a, planet_b)
    temporal = temporal_friendship(house_a, house_b)
    return {"natural": natural, "temporal": temporal, "grade": combined_grade(natural, temporal)}


def compute_all_maitri(chart):
    """{planet: {other_planet: panchadha_maitri result}} for all directed
    pairs among the 7 classical grahas, using each planet's house in
    `chart` (Rasi/D1 — the classical basis for Tatkalika Maitri)."""
    houses = {p: chart["planets"][p]["house"] for p in CLASSICAL_SEVEN}
    result = {}
    for a in CLASSICAL_SEVEN:
        result[a] = {}
        for b in CLASSICAL_SEVEN:
            if a == b:
                continue
            result[a][b] = panchadha_maitri(a, b, houses[a], houses[b])
    return result


if __name__ == "__main__":
    # Sanity print: every planet's relationship to every other, natural
    # friendship only (chart-independent part), to eyeball against a
    # classical reference table.
    for p in CLASSICAL_SEVEN:
        row = NATURAL_FRIENDSHIP[p]
        print(f"{p:8s} friends={row['friends']} neutral={row['neutral']} enemies={row['enemies']}")
