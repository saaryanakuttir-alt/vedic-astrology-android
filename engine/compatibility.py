"""
compatibility.py — Ashtakoot Guna Milan: the classical 36-point Vedic
marriage-compatibility system, comparing the Moon sign/nakshatra of two
people across 8 "kootas" (Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri
5, Gana 6, Bhakoot 7, Nadi 8 — maximum points sum to 36).

RESEARCH / VERIFICATION NOTE — please read before treating this as
gospel: unlike this project's core planet/house/dasha calculations,
Ashtakoot has no single universally-published exact ruleset once you go
past the broad structure. Multiple published sources (including
Jagannatha Hora's own site) were checked while building this module, and
several openly state that finer details vary between traditions/software.
What's implemented, and how confident each part is:

  - Varna, Gana, Nadi, and the Tara counting method: consistently
    described identically across every source checked. High confidence.
  - Bhakoot's 3 dosha-causing sign-distance pairs (2-12, 5-9, 6-8) and its
    "cancelled if the two Moon-sign lords are the same planet or are
    natural friends" exception: cited consistently across sources
    checked, though not verified against a primary classical text
    directly. Moderate-high confidence.
  - Yoni's "same animal" (4 pts) and its 7 classical enemy pairs (0 pts)
    are consistent everywhere. The finer 3-way split of every OTHER pair
    into "friendly" (3) / "neutral" (2) / "mildly unfriendly" (1) is
    NOT consistently published anywhere found (even Jagannatha Hora's own
    article says to "verify against the matching tool you use, as
    variations exist") — so this module scores every non-same,
    non-enemy pair as a flat "neutral" (2), a documented simplification.
  - Graha Maitri uses the classical Naisargika (natural, non-directional-
    exception) planetary friendship table, which IS well-established and
    internally cross-checked here against its well-known asymmetric
    quirks (e.g. Mercury calls the Sun a friend, but the Sun calls
    Mercury neutral). The exact point value for the 2 middle combinations
    (one-friend-one-neutral=4, one-neutral-one-enemy=2) follows the
    standard "descending order" pattern every source describes
    qualitatively; a single source spelling out all 6 combinations
    numerically wasn't found, so treat those two specific numbers as
    the best-supported convention rather than a directly-cited fact.
  - Nadi's classical cancellation exceptions (e.g. same nakshatra but
    different pada) are mentioned inconsistently across sources and are
    NOT auto-applied here — the raw same/different-Nadi result is
    reported plainly, with a note that traditional exceptions exist and
    should be checked by an astrologer rather than assumed.

Bottom line: treat the total score and the well-established kootas
(Varna/Gana/Nadi/Tara/Bhakoot's core rule) with confidence, and treat
Yoni's middle tier and Graha Maitri's exact middle numbers as reasonable,
clearly-flagged approximations — consistent with how this whole project
handles genuinely disputed classical points (see divisional.py's D60 note
for the precedent).
"""
from avkahada import (
    YONI_ANIMAL_BY_NAKSHATRA,
    VARNA_RANK,
    _GANA_BY_NAKSHATRA,
    _NADI_BY_NAKSHATRA,
    _VARNA_BY_SIGN,
    _VASHYA_BY_SIGN,
)
from astrology_tables import SIGN_LORD
from panchanga import NAKSHATRAS, SIGNS

# ---------------------------------------------------------------------------
# Naisargika Maitri — classical NATURAL planetary friendship (asymmetric by
# design; e.g. Mercury treats the Sun as a friend, but the Sun treats
# Mercury as neutral — this is a well-known, deliberate classical quirk,
# not an error). {planet: {"friend": {...}, "enemy": {...}}}; anything not
# listed for a planet is neutral to it.
# ---------------------------------------------------------------------------
_NATURAL_FRIENDS = {
    "Sun": {"friend": {"Moon", "Mars", "Jupiter"}, "enemy": {"Saturn", "Venus"}},
    "Moon": {"friend": {"Sun", "Mercury"}, "enemy": set()},
    "Mars": {"friend": {"Sun", "Moon", "Jupiter"}, "enemy": {"Mercury"}},
    "Mercury": {"friend": {"Sun", "Venus"}, "enemy": {"Moon"}},
    "Jupiter": {"friend": {"Sun", "Moon", "Mars"}, "enemy": {"Mercury", "Venus"}},
    "Venus": {"friend": {"Mercury", "Saturn"}, "enemy": {"Sun", "Moon"}},
    "Saturn": {"friend": {"Mercury", "Venus"}, "enemy": {"Sun", "Moon", "Mars"}},
}

_YONI_ENEMY_PAIRS = {
    frozenset({"Cow", "Tiger"}), frozenset({"Horse", "Buffalo"}),
    frozenset({"Elephant", "Lion"}), frozenset({"Dog", "Deer"}),
    frozenset({"Serpent", "Mongoose"}), frozenset({"Cat", "Rat"}),
    frozenset({"Goat", "Monkey"}),
}

_BHAKOOT_DOSHA_DISTANCES = {2, 12, 5, 9, 6, 8}

_TARA_UNFAVORABLE_REMAINDERS = {3, 5, 7}

KOOTA_MAX_POINTS = {
    "varna": 1, "vashya": 2, "tara": 3, "yoni": 4,
    "graha_maitri": 5, "gana": 6, "bhakoot": 7, "nadi": 8,
}
MAX_TOTAL = sum(KOOTA_MAX_POINTS.values())  # 36
assert MAX_TOTAL == 36


def _natural_relation(from_planet, to_planet):
    if from_planet == to_planet:
        return "friend"  # a planet is always its own friend (relevant for same-sign-lord case)
    rules = _NATURAL_FRIENDS[from_planet]
    if to_planet in rules["friend"]:
        return "friend"
    if to_planet in rules["enemy"]:
        return "enemy"
    return "neutral"


def _sign_distance(from_sign, to_sign):
    """Classical inclusive counting: same sign = 1, next sign = 2, ... (1-12)."""
    return ((SIGNS.index(to_sign) - SIGNS.index(from_sign)) % 12) + 1


def _nakshatra_distance(from_nak, to_nak):
    return ((NAKSHATRAS.index(to_nak) - NAKSHATRAS.index(from_nak)) % 27) + 1


def _score_varna(person_a, person_b):
    varna_a = _VARNA_BY_SIGN[person_a["moon_sign"]]
    varna_b = _VARNA_BY_SIGN[person_b["moon_sign"]]
    # Classical rule is directional (groom's Varna >= bride's). Use `sex`
    # when both are known and differ; otherwise fall back to person_a as
    # the reference side and say so plainly rather than guessing gender.
    sex_a, sex_b = person_a.get("sex"), person_b.get("sex")
    assumption = None
    if sex_a == "Female" and sex_b == "Male":
        higher, lower = varna_b, varna_a
    elif sex_a == "Male" and sex_b == "Female":
        higher, lower = varna_a, varna_b
    else:
        higher, lower = varna_a, varna_b
        assumption = "Sex not given for both people — compared person_a's Varna against person_b's (classical rule is normally groom-vs-bride directional)."
    points = KOOTA_MAX_POINTS["varna"] if VARNA_RANK[higher] >= VARNA_RANK[lower] else 0
    return {
        "koota": "Varna", "max_points": KOOTA_MAX_POINTS["varna"], "points": points,
        "person_a_varna": varna_a, "person_b_varna": varna_b, "assumption": assumption,
    }


def _score_vashya(person_a, person_b):
    vashya_a = _VASHYA_BY_SIGN[person_a["moon_sign"]]
    vashya_b = _VASHYA_BY_SIGN[person_b["moon_sign"]]
    points = KOOTA_MAX_POINTS["vashya"] if vashya_a == vashya_b else 0
    return {
        "koota": "Vashya", "max_points": KOOTA_MAX_POINTS["vashya"], "points": points,
        "person_a_vashya": vashya_a, "person_b_vashya": vashya_b,
        "note": "Same-category only (2 or 0) — the classical middle tier "
                "('one is Vashya of the other', 1 point) is not implemented; see module docstring.",
    }


def _score_tara(person_a, person_b):
    nak_a, nak_b = person_a["nakshatra"], person_b["nakshatra"]
    d_ab = _nakshatra_distance(nak_a, nak_b) % 9 or 9
    d_ba = _nakshatra_distance(nak_b, nak_a) % 9 or 9
    fav_ab = d_ab not in _TARA_UNFAVORABLE_REMAINDERS
    fav_ba = d_ba not in _TARA_UNFAVORABLE_REMAINDERS
    if fav_ab and fav_ba:
        points = 3.0
    elif fav_ab or fav_ba:
        points = 1.5
    else:
        points = 0.0
    return {
        "koota": "Tara", "max_points": KOOTA_MAX_POINTS["tara"], "points": points,
        "person_a_to_b_remainder": d_ab, "person_b_to_a_remainder": d_ba,
    }


def _score_yoni(person_a, person_b):
    animal_a = YONI_ANIMAL_BY_NAKSHATRA[person_a["nakshatra"]]
    animal_b = YONI_ANIMAL_BY_NAKSHATRA[person_b["nakshatra"]]
    if animal_a == animal_b:
        points, relation = 4, "same"
    elif frozenset({animal_a, animal_b}) in _YONI_ENEMY_PAIRS:
        points, relation = 0, "enemy"
    else:
        points, relation = 2, "neutral (simplified — see module docstring)"
    return {
        "koota": "Yoni", "max_points": KOOTA_MAX_POINTS["yoni"], "points": points,
        "person_a_yoni": animal_a, "person_b_yoni": animal_b, "relation": relation,
    }


def _score_graha_maitri(person_a, person_b):
    lord_a = SIGN_LORD[person_a["moon_sign"]]
    lord_b = SIGN_LORD[person_b["moon_sign"]]
    rel_ab = _natural_relation(lord_a, lord_b)
    rel_ba = _natural_relation(lord_b, lord_a)
    pair = frozenset({rel_ab, rel_ba}) if rel_ab != rel_ba else {rel_ab}
    if pair == {"friend"}:
        points = 5
    elif pair == {"friend", "neutral"}:
        points = 4
    elif pair == {"neutral"}:
        points = 3
    elif pair == {"neutral", "enemy"}:
        points = 2
    elif pair == {"friend", "enemy"}:
        points = 1
    else:  # {"enemy"}
        points = 0
    return {
        "koota": "Graha Maitri", "max_points": KOOTA_MAX_POINTS["graha_maitri"], "points": points,
        "person_a_moon_lord": lord_a, "person_b_moon_lord": lord_b,
        "a_sees_b_as": rel_ab, "b_sees_a_as": rel_ba,
    }


def _score_gana(person_a, person_b):
    gana_a = _GANA_BY_NAKSHATRA[person_a["nakshatra"]]
    gana_b = _GANA_BY_NAKSHATRA[person_b["nakshatra"]]
    pair = {gana_a, gana_b}
    if gana_a == gana_b:
        points = 6
    elif pair == {"Deva", "Manushya"}:
        points = 5
    elif pair == {"Manushya", "Rakshasa"}:
        points = 1
    else:  # Deva-Rakshasa
        points = 0
    return {
        "koota": "Gana", "max_points": KOOTA_MAX_POINTS["gana"], "points": points,
        "person_a_gana": gana_a, "person_b_gana": gana_b,
    }


def _score_bhakoot(person_a, person_b):
    sign_a, sign_b = person_a["moon_sign"], person_b["moon_sign"]
    # Forward distance A->B already captures the pair symmetrically: e.g. a
    # forward distance of 2 (the "2/12" pair) means the reverse B->A
    # distance is 12, and both values are already in the dosha set below.
    distance = _sign_distance(sign_a, sign_b)
    dosha = distance in _BHAKOOT_DOSHA_DISTANCES
    cancelled = False
    if dosha:
        lord_a, lord_b = SIGN_LORD[sign_a], SIGN_LORD[sign_b]
        if lord_a == lord_b or _natural_relation(lord_a, lord_b) == "friend" or _natural_relation(lord_b, lord_a) == "friend":
            cancelled = True
    points = KOOTA_MAX_POINTS["bhakoot"] if (not dosha or cancelled) else 0
    return {
        "koota": "Bhakoot", "max_points": KOOTA_MAX_POINTS["bhakoot"], "points": points,
        "sign_distance": distance, "dosha_by_distance": dosha, "cancelled_by_lord_friendship": cancelled,
    }


def _score_nadi(person_a, person_b):
    nadi_a = _NADI_BY_NAKSHATRA[person_a["nakshatra"]]
    nadi_b = _NADI_BY_NAKSHATRA[person_b["nakshatra"]]
    same = nadi_a == nadi_b
    points = 0 if same else KOOTA_MAX_POINTS["nadi"]
    return {
        "koota": "Nadi", "max_points": KOOTA_MAX_POINTS["nadi"], "points": points,
        "person_a_nadi": nadi_a, "person_b_nadi": nadi_b, "same_nadi": same,
        "note": (
            "Nadi Dosha (0 points) shown as-is with no automatic cancellation applied. "
            "Classical texts describe exception cases (e.g. identical nakshatra but "
            "different pada) inconsistently across sources — have an astrologer confirm "
            "whether an exception applies rather than assuming either way."
        ) if same else None,
    }


def compute_ashtakoot(person_a, person_b):
    """
    person_a / person_b: {"moon_sign": ..., "nakshatra": ..., "sex": "Male"|"Female"|None}
    (pull these straight from a computed chart's chart["planets"]["Moon"]
    and chart["birth_input"]["sex"]).

    Returns {"kootas": [8 koota dicts], "total_points": float (0-36),
             "max_points": 36, "verdict": str}.
    """
    kootas = [
        _score_varna(person_a, person_b),
        _score_vashya(person_a, person_b),
        _score_tara(person_a, person_b),
        _score_yoni(person_a, person_b),
        _score_graha_maitri(person_a, person_b),
        _score_gana(person_a, person_b),
        _score_bhakoot(person_a, person_b),
        _score_nadi(person_a, person_b),
    ]
    total = sum(k["points"] for k in kootas)

    if total >= 33:
        verdict = "Excellent match (traditional threshold: 33-36)"
    elif total >= 25:
        verdict = "Very good match (traditional threshold: 25-32)"
    elif total >= 18:
        verdict = "Acceptable — commonly cited as the minimum workable score (18-24); consider other factors too"
    else:
        verdict = "Below the commonly-cited minimum (18) — traditionally considered a weak match on this method alone"

    nadi_dosha = any(k["koota"] == "Nadi" and k["points"] == 0 for k in kootas)
    bhakoot_dosha = any(k["koota"] == "Bhakoot" and k["points"] == 0 for k in kootas)

    return {
        "kootas": kootas,
        "total_points": total,
        "max_points": MAX_TOTAL,
        "verdict": verdict,
        "nadi_dosha_present": nadi_dosha,
        "bhakoot_dosha_present": bhakoot_dosha,
    }
