"""
yogas.py — detects all 24 classical yogas covered by classical_yogas.json
against a computed birth chart (the dict returned by
birth_chart.compute_birth_chart).

Each detect_* function returns a dict:
    {"id": "YOGA-01", "present": bool, "details": "<what was found>"}
"present" answers "is this yoga formed in this chart", using the PRIMARY
classical definition given in classical_yogas.json's own `formation` field
(this module's docstring on each function quotes the relevant part). Several
yogas (Neecha Bhanga, Dhana, Adhi, Kuja Dosha, Vipareeta) have real,
documented classical variation in how strictly they're defined — where that
matters, the function docstring says which variant is checked, matching
what classical_yogas.json itself flags as the "pinned"/default reading.

detect_all_yogas(chart) runs all 24 and returns them as a list, in
YOGA-01..YOGA-24 order, ready to be joined against classical_yogas.json by
`rule_engine.py`.
"""
from astrology_tables import (
    DUSTHANA_HOUSES,
    EXALTATION_SIGN,
    KENDRA_HOUSES,
    NATURAL_BENEFICS_UNCONDITIONAL,
    OWN_SIGNS,
    SIGN_LORD,
    TRIKONA_HOUSES,
    house_distance,
    is_kendra_from,
    is_moon_waxing,
    planet_aspects_house,
)
from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


# ---------------------------------------------------------------------------
# Small chart-reading helpers (all operate on the dict compute_birth_chart
# returns; `chart["houses"]` may have int or str keys depending on whether
# the chart was round-tripped through JSON, so every house lookup here
# tolerates both).
# ---------------------------------------------------------------------------
def _house_sign(chart, house_num):
    houses = chart["houses"]
    return houses.get(house_num, houses.get(str(house_num)))


def _planet_house(chart, planet):
    return chart["planets"][planet]["house"]


def _planet_sign(chart, planet):
    return chart["planets"][planet]["sign"]


def _planet_longitude(chart, planet):
    return chart["planets"][planet]["longitude"]


def _planets_in_house(chart, house_num):
    return [p for p in chart["planets"] if _planet_house(chart, p) == house_num]


def lord_of_house(chart, house_num):
    """Which planet rules the sign occupying `house_num`."""
    return SIGN_LORD[_house_sign(chart, house_num)]


def house_of_lord(chart, house_num):
    """Where the lord of `house_num` is itself placed (a house number)."""
    return _planet_house(chart, lord_of_house(chart, house_num))


def are_conjunct(chart, planet_a, planet_b):
    return _planet_house(chart, planet_a) == _planet_house(chart, planet_b)


def planet_aspects_planet(chart, aspecting, aspected):
    """Does `aspecting` cast its classical drishti onto the house `aspected` sits in?"""
    return planet_aspects_house(aspecting, _planet_house(chart, aspecting), _planet_house(chart, aspected))


def have_mutual_connection(chart, planet_a, planet_b):
    """Conjunction, either-direction aspect, or a mutual sign-exchange
    (parivartana) between two individual planets — the general-purpose
    'connection' classical Raja/Dhana Yoga rules ask for between two lords."""
    if planet_a == planet_b:
        return True
    if are_conjunct(chart, planet_a, planet_b):
        return True
    if planet_aspects_planet(chart, planet_a, planet_b) or planet_aspects_planet(chart, planet_b, planet_a):
        return True
    return is_parivartana_pair(chart, planet_a, planet_b)


def is_parivartana_pair(chart, planet_a, planet_b):
    """True if planet_a sits in a sign owned by planet_b AND planet_b sits
    in a sign owned by planet_a (mutual sign exchange)."""
    sign_a, sign_b = _planet_sign(chart, planet_a), _planet_sign(chart, planet_b)
    return SIGN_LORD.get(sign_a) == planet_b and SIGN_LORD.get(sign_b) == planet_a


def houses_connected(chart, house_a, house_b):
    """Do the LORDS of house_a and house_b have a connection (conjunction,
    mutual aspect, or parivartana)? Returns (bool, lord_a, lord_b)."""
    lord_a, lord_b = lord_of_house(chart, house_a), lord_of_house(chart, house_b)
    return have_mutual_connection(chart, lord_a, lord_b), lord_a, lord_b


def _yoga(yoga_id, present, details):
    return {"id": yoga_id, "present": present, "details": details}


# ---------------------------------------------------------------------------
# YOGA-01 — Gajakesari: Jupiter in a kendra counted FROM THE MOON.
# ---------------------------------------------------------------------------
def detect_gajakesari(chart):
    moon_h, jup_h = _planet_house(chart, "Moon"), _planet_house(chart, "Jupiter")
    dist = house_distance(moon_h, jup_h)
    present = dist in KENDRA_HOUSES
    return _yoga("YOGA-01", present,
                 tr("Jupiter is {0} houses from the Moon (house {1} vs Moon's house {2}).", dist, jup_h, moon_h)
                 if present else tr('Jupiter is not in a kendra from the Moon (distance {0}).', dist))


# ---------------------------------------------------------------------------
# YOGA-02..06 — Pancha Mahapurusha: planet in own/exaltation sign AND in a
# kendra (1/4/7/10) FROM THE LAGNA.
# ---------------------------------------------------------------------------
_MAHAPURUSHA = {
    "YOGA-02": ("Mars", "Ruchaka"), "YOGA-03": ("Mercury", "Bhadra"),
    "YOGA-04": ("Jupiter", "Hamsa"), "YOGA-05": ("Venus", "Malavya"),
    "YOGA-06": ("Saturn", "Sasa"),
}


def _detect_mahapurusha(chart, yoga_id, planet, label):
    house = _planet_house(chart, planet)
    sign = _planet_sign(chart, planet)
    well_dignified = sign in OWN_SIGNS.get(planet, []) or sign == EXALTATION_SIGN.get(planet)
    in_kendra = house in KENDRA_HOUSES
    present = well_dignified and in_kendra
    return _yoga(yoga_id, present,
                 tr('{0} is in {1} (own/exaltation) and in house {2} (a kendra) — {3} Yoga formed.', planet, sign, house, label)
                 if present else tr('{0} in {1}, house {2}: {3}.', planet, sign, house, 'own/exalted sign but not a kendra house' if well_dignified else 'not in own/exaltation sign'))


# ---------------------------------------------------------------------------
# YOGA-07 — Kendra-Trikona Raja Yoga: a kendra lord connects with a trikona
# lord (conjunction, mutual aspect, or parivartana).
# ---------------------------------------------------------------------------
def detect_kendra_trikona_raja_yoga(chart):
    pairs_found = []
    for k in KENDRA_HOUSES:
        for t in TRIKONA_HOUSES:
            lord_k, lord_t = lord_of_house(chart, k), lord_of_house(chart, t)
            if lord_k == lord_t:
                continue  # same planet ruling both — not a "connection" between two lords
            connected, _, _ = houses_connected(chart, k, t)
            if connected:
                pairs_found.append(tr('{0}th-lord {1} <-> {2}th-lord {3}', k, lord_k, t, lord_t))
    present = len(pairs_found) > 0
    details = (tx("Kendra-trikona lord connection(s): ") + "; ".join(sorted(set(pairs_found)))) if present \
        else tx("No kendra lord forms a conjunction/aspect/parivartana with a trikona lord.")
    return _yoga("YOGA-07", present, details)


# ---------------------------------------------------------------------------
# YOGA-08 — Dhana Yoga (pinned core definition): 2nd lord and 11th lord connect.
# ---------------------------------------------------------------------------
def detect_dhana_yoga(chart):
    lord2, lord11 = lord_of_house(chart, 2), lord_of_house(chart, 11)
    if lord2 == lord11:
        return _yoga("YOGA-08", True,
                      tr('The same planet ({0}) rules both the 2nd (wealth) and 11th (gains) houses — a direct '
                         'wealth-combination in its own right.', lord2))
    connected, _, _ = houses_connected(chart, 2, 11)
    return _yoga("YOGA-08", connected,
                 tr('2nd lord {0} and 11th lord {1} {2}', lord2, lord11, 'are connected (conjunction/aspect/parivartana).' if connected else 'have no direct connection.'))


# ---------------------------------------------------------------------------
# YOGA-09 — Kemadruma: Moon isolated — no planet (Rahu/Ketu excluded) in the
# 2nd/12th from Moon, and no conjunction/aspect onto the Moon from any other
# planet (nodes excluded from this count too).
# ---------------------------------------------------------------------------
def detect_kemadruma(chart):
    moon_h = _planet_house(chart, "Moon")
    second_from_moon = ((moon_h) % 12) + 1
    twelfth_from_moon = ((moon_h - 2) % 12) + 1
    others = [p for p in CLASSICAL_PLANETS if p != "Moon"]
    occupants = [p for p in others if _planet_house(chart, p) in (second_from_moon, twelfth_from_moon)]
    aspecting_or_conjunct = [
        p for p in others
        if _planet_house(chart, p) == moon_h or planet_aspects_planet(chart, p, "Moon")
    ]
    present = not occupants and not aspecting_or_conjunct
    if present:
        details = tx("No classical planet occupies the 2nd/12th from the Moon, and none conjoins or aspects it — the Moon is isolated.")
    else:
        supporting = sorted(set(occupants) | set(aspecting_or_conjunct))
        details = tr('The Moon is supported by: {0} — not isolated, so Kemadruma is not formed.', ', '.join(supporting))
    return _yoga("YOGA-09", present, details)


# ---------------------------------------------------------------------------
# YOGA-10 — Neecha Bhanga Raja Yoga (checks the two most commonly cited
# kendra-based cancellation variants, plus the D9 variant):
#   (a) the lord of the debilitation sign is in a kendra from lagna or Moon;
#   (b) the planet exalted in the debilitated planet's sign is in a kendra
#       from lagna or Moon;
#   (c) the debilitated planet occupies its own or exaltation sign in the D9.
# Only applies to the 7 classical grahas (Rahu/Ketu have no fixed
# debilitation sign in this project's KB — see astrology_tables.py).
# ---------------------------------------------------------------------------
def detect_neecha_bhanga(chart):
    from astrology_tables import DEBILITATION_SIGN, SIGN_EXALTS

    lagna_house = 1
    moon_house = _planet_house(chart, "Moon")
    findings = []
    for planet in CLASSICAL_PLANETS:
        if _planet_sign(chart, planet) != DEBILITATION_SIGN.get(planet):
            continue
        debil_sign = DEBILITATION_SIGN[planet]
        dispositor = SIGN_LORD[debil_sign]
        dispositor_house = _planet_house(chart, dispositor)
        cond_a = is_kendra_from(lagna_house, dispositor_house) or is_kendra_from(moon_house, dispositor_house)

        exalted_here = SIGN_EXALTS.get(debil_sign)
        cond_b = False
        if exalted_here and exalted_here in chart["planets"]:
            exalt_planet_house = _planet_house(chart, exalted_here)
            cond_b = is_kendra_from(lagna_house, exalt_planet_house) or is_kendra_from(moon_house, exalt_planet_house)

        d9_sign = chart["planets"][planet]["vargas"].get("D9")
        cond_c = d9_sign in OWN_SIGNS.get(planet, []) or d9_sign == EXALTATION_SIGN.get(planet)

        if cond_a or cond_b or cond_c:
            reasons = []
            if cond_a:
                reasons.append(tr('debilitation-dispositor {0} is in a kendra from lagna/Moon', dispositor))
            if cond_b:
                reasons.append(tr('{0} (exalted in {1}) is in a kendra from lagna/Moon', exalted_here, debil_sign))
            if cond_c:
                reasons.append(tr('{0} is in its own/exaltation sign ({1}) in the D9 despite D1 debilitation', planet, d9_sign))
            findings.append(tr('{0} debilitated in {1}, cancelled because: {2}.', planet, debil_sign, '; '.join(reasons)))
    present = len(findings) > 0
    details = " | ".join(findings) if present else tx("No debilitated classical planet meets the checked cancellation conditions.")
    return _yoga("YOGA-10", present, details)


# ---------------------------------------------------------------------------
# YOGA-11/12/13 — Vipareeta Raja Yoga (Harsha/Sarala/Vimala): lord of the
# 6th/8th/12th house respectively sits in the 6th, 8th, or 12th. Also notes
# whether it's the weaker "self-placement" or the stronger "different
# dusthana" form, per classical_yogas.json's own strength note.
# ---------------------------------------------------------------------------
def _detect_vipareeta(chart, yoga_id, house, label):
    lord_house = house_of_lord(chart, house)
    present = lord_house in DUSTHANA_HOUSES
    if not present:
        return _yoga(yoga_id, False, tr('Lord of house {0} is in house {1} (not a dusthana).', house, lord_house))
    form = tx("self-placement (weaker classical form)") if lord_house == house else tx("different dusthana (stronger classical form)")
    return _yoga(yoga_id, True, tr('{0}: lord of house {1} is in house {2} — {3}.', label, house, lord_house, form))


# ---------------------------------------------------------------------------
# YOGA-14 — Chandra-Mangal: Moon and Mars conjunct.
# ---------------------------------------------------------------------------
def detect_chandra_mangal(chart):
    present = are_conjunct(chart, "Moon", "Mars")
    return _yoga("YOGA-14", present,
                 tr('Moon and Mars are both in house {0}.', _planet_house(chart, 'Moon')) if present
                 else tx("Moon and Mars are not conjunct."))


# ---------------------------------------------------------------------------
# YOGA-15 — Guru-Mangal: Jupiter and Mars conjunct, or mutual kendra aspect.
# ---------------------------------------------------------------------------
def detect_guru_mangal(chart):
    conjunct = are_conjunct(chart, "Jupiter", "Mars")
    mutual_aspect = (planet_aspects_planet(chart, "Jupiter", "Mars")
                      and planet_aspects_planet(chart, "Mars", "Jupiter"))
    present = conjunct or mutual_aspect
    if conjunct:
        details = tr('Jupiter and Mars are conjunct in house {0}.', _planet_house(chart, 'Jupiter'))
    elif mutual_aspect:
        details = tx("Jupiter and Mars are in mutual kendra aspect.")
    else:
        details = tx("Jupiter and Mars are neither conjunct nor in mutual aspect.")
    return _yoga("YOGA-15", present, details)


# ---------------------------------------------------------------------------
# YOGA-16 — Amala: a natural benefic (Jupiter/Venus/Mercury, or a waxing
# Moon) occupies the 10th from lagna or from Moon, unafflicted (no natural
# malefic conjunct there too).
# ---------------------------------------------------------------------------
def detect_amala(chart):
    from astrology_tables import NATURAL_MALEFICS

    moon_house = _planet_house(chart, "Moon")
    tenth_from_lagna = 10
    tenth_from_moon = ((moon_house + 8) % 12) + 1  # 10th house counted from the Moon
    waxing = is_moon_waxing(_planet_longitude(chart, "Sun"), _planet_longitude(chart, "Moon"))
    benefics_now = set(NATURAL_BENEFICS_UNCONDITIONAL) | ({"Moon"} if waxing else set())

    findings = []
    for house_label, house_num in (("lagna", tenth_from_lagna), ("Moon", tenth_from_moon)):
        occupants = _planets_in_house(chart, house_num)
        benefics_here = [p for p in occupants if p in benefics_now]
        malefics_here = [p for p in occupants if p in NATURAL_MALEFICS]
        if benefics_here and not malefics_here:
            findings.append(tr('10th from {0} (house {1}) holds unafflicted benefic(s): {2}', house_label, house_num, ', '.join(benefics_here)))
    present = len(findings) > 0
    return _yoga("YOGA-16", present, "; ".join(findings) if present else tx("No unafflicted benefic occupies the 10th from lagna or Moon."))


# ---------------------------------------------------------------------------
# YOGA-17 — Adhi Yoga (Chandra-Adhi, the classical default): benefics
# (Jupiter/Venus/Mercury) occupy the 6th, 7th, AND 8th houses counted from
# the Moon (at least one benefic in each of the three).
# ---------------------------------------------------------------------------
def detect_adhi_yoga(chart):
    moon_house = _planet_house(chart, "Moon")
    houses_6_7_8 = [((moon_house + off - 1) % 12) + 1 for off in (6, 7, 8)]
    per_house = {h: [p for p in _planets_in_house(chart, h) if p in NATURAL_BENEFICS_UNCONDITIONAL] for h in houses_6_7_8}
    present = all(per_house[h] for h in houses_6_7_8)
    details = "; ".join(tr('house {0} (from Moon): {1}', h, per_house[h] or 'none') for h in houses_6_7_8)
    return _yoga("YOGA-17", present, details)


# ---------------------------------------------------------------------------
# YOGA-18 — Shakat: Moon in the 6th, 8th, or 12th from Jupiter.
# ---------------------------------------------------------------------------
def detect_shakat(chart):
    jup_house = _planet_house(chart, "Jupiter")
    moon_house = _planet_house(chart, "Moon")
    dist = house_distance(jup_house, moon_house)
    present = dist in DUSTHANA_HOUSES
    return _yoga("YOGA-18", present,
                 tr('Moon is {0} houses from Jupiter.', dist) if present else tr('Moon is {0} houses from Jupiter (not a dusthana relationship).', dist))


# ---------------------------------------------------------------------------
# YOGA-19 — Kalasarpa: all 7 classical planets fall within the 180-degree
# arc from Rahu to Ketu (or, equivalently, entirely within the other arc).
# ---------------------------------------------------------------------------
def _in_forward_arc(start, end, point):
    """True if `point` lies in the arc going forward from start to end
    (mod 360), start exclusive-ish handled via >= / < to avoid double-counting
    a planet sitting exactly on a node's degree."""
    span = (end - start) % 360.0
    offset = (point - start) % 360.0
    return offset <= span


def detect_kalasarpa(chart):
    rahu_lon, ketu_lon = _planet_longitude(chart, "Rahu"), _planet_longitude(chart, "Ketu")
    lons = {p: _planet_longitude(chart, p) for p in CLASSICAL_PLANETS}
    all_rahu_to_ketu = all(_in_forward_arc(rahu_lon, ketu_lon, lon) for lon in lons.values())
    all_ketu_to_rahu = all(_in_forward_arc(ketu_lon, rahu_lon, lon) for lon in lons.values())
    present = all_rahu_to_ketu or all_ketu_to_rahu
    side = "Rahu-to-Ketu" if all_rahu_to_ketu else ("Ketu-to-Rahu" if all_ketu_to_rahu else None)
    details = tr('All 7 classical planets fall within the {0} arc.', side) if present \
        else tx("The 7 classical planets are not all confined to one node-to-node arc.")
    return _yoga("YOGA-19", present, details)


# ---------------------------------------------------------------------------
# YOGA-20 — Grahan: Sun or Moon conjunct Rahu or Ketu.
# ---------------------------------------------------------------------------
def detect_grahan(chart):
    combos = [("Sun", "Rahu"), ("Sun", "Ketu"), ("Moon", "Rahu"), ("Moon", "Ketu")]
    hits = [tr('{0}-{1}', a, b) for a, b in combos if are_conjunct(chart, a, b)]
    present = len(hits) > 0
    return _yoga("YOGA-20", present, (tx("Conjunctions found: ") + ", ".join(hits)) if present else tx("No Sun/Moon-node conjunction."))


# ---------------------------------------------------------------------------
# YOGA-21 — Angarak: Mars conjunct Rahu.
# ---------------------------------------------------------------------------
def detect_angarak(chart):
    present = are_conjunct(chart, "Mars", "Rahu")
    return _yoga("YOGA-21", present, tx("Mars and Rahu are conjunct.") if present else tx("Mars and Rahu are not conjunct."))


# ---------------------------------------------------------------------------
# YOGA-22 — Kuja Dosha: Mars in 1st/2nd/4th/7th/8th/12th from the lagna.
# ---------------------------------------------------------------------------
def detect_kuja_dosha(chart):
    mars_house = _planet_house(chart, "Mars")
    present = mars_house in {1, 2, 4, 7, 8, 12}
    return _yoga("YOGA-22", present, tr('Mars is in house {0} from the lagna.', mars_house))


# ---------------------------------------------------------------------------
# YOGA-23 — Guru Chandal: Jupiter conjunct Rahu (also flags Ketu, per some
# traditions, as a secondary note).
# ---------------------------------------------------------------------------
def detect_guru_chandal(chart):
    with_rahu = are_conjunct(chart, "Jupiter", "Rahu")
    with_ketu = are_conjunct(chart, "Jupiter", "Ketu")
    present = with_rahu or with_ketu
    if with_rahu:
        details = tx("Jupiter and Rahu are conjunct (the primary classical form).")
    elif with_ketu:
        details = tx("Jupiter and Ketu are conjunct (a secondary form recognized by some traditions).")
    else:
        details = tx("Jupiter is not conjunct either node.")
    return _yoga("YOGA-23", present, details)


# ---------------------------------------------------------------------------
# YOGA-24 — Vish Yoga: Saturn conjunct Rahu.
# ---------------------------------------------------------------------------
def detect_vish_yoga(chart):
    present = are_conjunct(chart, "Saturn", "Rahu")
    return _yoga("YOGA-24", present, tx("Saturn and Rahu are conjunct.") if present else tx("Saturn and Rahu are not conjunct."))


def detect_all_yogas(chart):
    """Runs all 24 detectors, returns a list in YOGA-01..YOGA-24 order."""
    results = [detect_gajakesari(chart)]
    for yoga_id, (planet, label) in _MAHAPURUSHA.items():
        results.append(_detect_mahapurusha(chart, yoga_id, planet, label))
    results.append(detect_kendra_trikona_raja_yoga(chart))
    results.append(detect_dhana_yoga(chart))
    results.append(detect_kemadruma(chart))
    results.append(detect_neecha_bhanga(chart))
    results.append(_detect_vipareeta(chart, "YOGA-11", 6, "Harsha"))
    results.append(_detect_vipareeta(chart, "YOGA-12", 8, "Sarala"))
    results.append(_detect_vipareeta(chart, "YOGA-13", 12, "Vimala"))
    results.append(detect_chandra_mangal(chart))
    results.append(detect_guru_mangal(chart))
    results.append(detect_amala(chart))
    results.append(detect_adhi_yoga(chart))
    results.append(detect_shakat(chart))
    results.append(detect_kalasarpa(chart))
    results.append(detect_grahan(chart))
    results.append(detect_angarak(chart))
    results.append(detect_kuja_dosha(chart))
    results.append(detect_guru_chandal(chart))
    results.append(detect_vish_yoga(chart))
    results.sort(key=lambda r: int(r["id"].split("-")[1]))
    return results
