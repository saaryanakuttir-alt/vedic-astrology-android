"""upaya.py — Upaya (remedial measures): gemstones (Ratna) and mantras,
loaded from kb/gemstones.json and kb/mantras.json, plus the logic for
checking whether a SET of gemstones is safe to wear together and for
suggesting which planets a chart's own weaknesses might call for support on.

GEMSTONE COMBINATION LOGIC directly reuses maitri.py's already-verified
Naisargika (natural) friendship table - this is not a separate, newly-
invented rule: the classical "never combine Blue Sapphire with Ruby/Pearl/
Red Coral" caution IS the Sun/Moon/Mars-are-Saturn's-natural-enemies fact
already encoded there, and "never combine Diamond with Ruby or Pearl" IS
Venus regarding Sun and Moon as natural enemies. Reusing that table means
this logic can't silently disagree with the sign_lord_relationship feature
already using the same data elsewhere in this project.

GEMSTONE RECOMMENDATION is deliberately conservative and clearly caveated:
it flags planets that are weak by dignity/combustion/Panchadha-Maitri as
CANDIDATES worth discussing with a qualified astrologer, not a prescription.
Full classical gemstone selection also weighs functional benefic/malefic
status by ascendant and dasha timing - real complexity this module does not
attempt to resolve on its own; see CAVEAT below.
"""
import json
import os

import maitri

KB_DIR = os.path.join(os.path.dirname(__file__), "kb")

CAVEAT = (
    "Gemstone and mantra recommendations here are traditional guidance, not a "
    "medical, financial, or psychological prescription, and not a guarantee of "
    "any outcome. Full classical gemstone selection also weighs a planet's "
    "FUNCTIONAL status for this specific ascendant (which houses it rules here, "
    "not just its natural tendencies) and current dasha timing - real factors "
    "this module does not fully resolve on its own. Treat this as a starting "
    "point for a conversation with a qualified astrologer and, for anything "
    "worn on the body, a jeweler you trust - not a final answer."
)

_gemstones_cache = None
_mantras_cache = None


def _load_gemstones():
    global _gemstones_cache
    if _gemstones_cache is None:
        with open(os.path.join(KB_DIR, "gemstones.json"), encoding="utf-8") as f:
            data = json.load(f)
        _gemstones_cache = {item["planet"]: item for item in data["items"]}
    return _gemstones_cache


def _load_mantras():
    global _mantras_cache
    if _mantras_cache is None:
        with open(os.path.join(KB_DIR, "mantras.json"), encoding="utf-8") as f:
            data = json.load(f)
        _mantras_cache = {item["planet"]: item for item in data["items"]}
    return _mantras_cache


def gemstone_for(planet):
    return _load_gemstones().get(planet)


def mantra_for(planet):
    return _load_mantras().get(planet)


def check_gemstone_combination(planets):
    """planets: a list of 2+ planet names the user is considering wearing
    together. Returns {"pairs": [...], "verdict": "safe"|"caution"|"avoid",
    "notes": [...]} - checked via maitri's natural-friendship table, which
    is directional, so BOTH directions of each pair are checked (e.g. Moon
    regards Mercury as a friend, but Mercury regards Moon as an enemy - the
    pair is flagged if EITHER direction is an enemy)."""
    gemstones = _load_gemstones()
    known = [p for p in planets if p in maitri.CLASSICAL_SEVEN]
    unknown = [p for p in planets if p not in maitri.CLASSICAL_SEVEN]
    pairs = []
    worst = "safe"
    for i in range(len(known)):
        for j in range(i + 1, len(known)):
            a, b = known[i], known[j]
            a_view = maitri.natural_friendship(a, b)
            b_view = maitri.natural_friendship(b, a)
            if a_view == "enemy" or b_view == "enemy":
                grade = "avoid"
            elif a_view == "neutral" or b_view == "neutral":
                grade = "caution"
            else:
                grade = "safe"
            pairs.append({
                "a": a, "b": b,
                "a_stone": gemstones[a]["stone"], "b_stone": gemstones[b]["stone"],
                "a_regards_b": a_view, "b_regards_a": b_view, "grade": grade,
            })
            if grade == "avoid":
                worst = "avoid"
            elif grade == "caution" and worst != "avoid":
                worst = "caution"

    notes = []
    if unknown:
        notes.append(
            f"{', '.join(unknown)} not included in the pairwise check - Rahu/Ketu "
            f"aren't covered by the natural-friendship table this check uses "
            f"(see maitri.py)."
        )
    # The two most commonly-cited classical cautions, called out explicitly
    # even though the pairwise check above already catches them via the
    # underlying friendship data - worth naming directly since they're the
    # ones most traditional sources lead with.
    stone_set = set(known)
    if "Saturn" in stone_set and stone_set & {"Sun", "Moon", "Mars"}:
        notes.append(
            "Blue Sapphire (Saturn) with Ruby (Sun), Pearl (Moon), or Red Coral "
            "(Mars) is one of the most consistently warned-against combinations "
            "across classical sources - Saturn regards all three as natural "
            "enemies."
        )
    if "Venus" in stone_set and stone_set & {"Sun", "Moon"}:
        notes.append(
            "Diamond (Venus) with Ruby (Sun) or Pearl (Moon) is another widely "
            "cited caution - Venus regards both as natural enemies."
        )
    return {"pairs": pairs, "verdict": worst, "notes": notes}


def full_combination_matrix():
    """Every pairwise combination among the 7 classical grahas' gemstones
    (21 pairs), pre-computed - lets a UI show which combinations are safe
    to wear together at a glance, not just check one pair on request. Same
    grading as check_gemstone_combination's per-pair logic."""
    gemstones = _load_gemstones()
    pairs = []
    for i in range(len(maitri.CLASSICAL_SEVEN)):
        for j in range(i + 1, len(maitri.CLASSICAL_SEVEN)):
            a, b = maitri.CLASSICAL_SEVEN[i], maitri.CLASSICAL_SEVEN[j]
            result = check_gemstone_combination([a, b])
            pairs.append(result["pairs"][0])
    return pairs


def suggest_gemstone_candidates(planets_reading):
    """planets_reading: the "planets" sub-dict of rule_engine.generate_reading()'s
    return value (each planet's sign/house/in_sign/combustion/
    sign_lord_relationship, etc.). Returns a list of {"planet", "stone",
    "sanskrit", "reasons": [...]} for planets whose OWN chart signals
    (dignity, combustion, sign-lord relationship) suggest they might be
    worth discussing with an astrologer - conservative by design, see this
    module's own CAVEAT. Does NOT weigh functional benefic/malefic status
    by ascendant or dasha timing (see CAVEAT)."""
    gemstones = _load_gemstones()
    candidates = []
    for planet, detail in planets_reading.items():
        if planet not in gemstones:
            continue
        reasons = []
        in_sign = detail.get("in_sign") or {}
        if in_sign.get("dignity") == "debilitated":
            reasons.append("debilitated by sign")
        combustion = detail.get("combustion") or {}
        if combustion.get("combust"):
            reasons.append("combust (too close to the Sun)")
        rel = detail.get("sign_lord_relationship")
        if rel and rel.get("grade") == "Adhi Shatru":
            reasons.append("Great Enemy relationship with its own sign's lord")
        if reasons:
            g = gemstones[planet]
            candidates.append({
                "planet": planet, "stone": g["stone"], "sanskrit": g["sanskrit"],
                "reasons": reasons,
            })
    return candidates
