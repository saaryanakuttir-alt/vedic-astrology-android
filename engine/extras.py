"""extras.py - the "at a glance" layer on top of a computed chart: doshas, Sade Sati / Dhaiya periods
for a whole lifetime, planet-by-planet considerations with a plain verdict, planetary friendships,
Western-style aspects and the Shodashvarga (16 divisional charts) table.

Everything here is derived from the chart dict (plus one Saturn scan for the Sade Sati table) and
is written for a general reader: each verdict is a *tendency* ("Good", "Mostly good", "Mixed",
"Needs some care", "Challenging") followed by what may happen and what the effects usually look
like - never a fixed prediction. Nothing here touches longevity or children: the Android app
leaves those out on purpose (see tests/test_engine_content.py).
"""
import datetime as _dt

import ephemeris
from astrology_tables import (
    DEBILITATION_SIGN, EXALTATION_SIGN, OWN_SIGNS, SIGN_LORD, aspect_distances_for,
)
from maitri import CLASSICAL_SEVEN, natural_friendship, panchadha_maitri
from panchanga import SIGNS
from i18n import join_list, tbl, tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

# ---------------------------------------------------------------- shared vocabulary
TONES = ["Good", "Mostly good", "Mixed", "Needs some care", "Challenging"]

# (key, name, what this chart is used to look at). D7 is deliberately absent (see module docstring).
SHODASHVARGA = tbl([
    ("D1", "Lagna (Rasi)", "you, your body and life as a whole"),
    ("D2", "Hora", "wealth and savings"),
    ("D3", "Drekkana", "brothers, sisters and courage"),
    ("D4", "Chaturthamsha", "luck, property and home"),
    ("D9", "Navamsha", "marriage, partners and inner strength"),
    ("D10", "Dashamsha", "profession and status"),
    ("D12", "Dwadashamsha", "parents and family roots"),
    ("D16", "Shodashamsha", "vehicles and comforts"),
    ("D20", "Vimshamsha", "spiritual inclination"),
    ("D24", "Chaturvimshamsha", "education and learning"),
    ("D27", "Saptavimshamsha", "inner strength and stamina"),
    ("D30", "Trimshamsha", "troubles and misfortunes to watch"),
    ("D40", "Khavedamsha", "auspicious results from family lines"),
    ("D45", "Akshavedamsha", "general well-being and character"),
    ("D60", "Shashtiamsha", "deeper karmic patterns"),
])
BODIES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

_HOUSE_AREA = tbl({
    1: "your body, looks and personality", 2: "money, family and speech", 3: "courage, effort and siblings",
    4: "home, mother and inner peace", 5: "studies, creativity and fun", 6: "work, debts and health habits",
    7: "marriage and partnerships", 8: "sudden changes and hidden matters", 9: "luck, teachers and travel",
    10: "career and reputation", 11: "gains and friends", 12: "expenses, sleep and foreign places",
})
_ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(n):
    return _ORD.get(n, f"{n}th")


def houses_phrase(nums):
    """'6th house' / '1st, 4th and 5th houses' in the current language."""
    names = [ordinal(h) for h in nums]
    return tr("{0} house", names[0]) if len(names) == 1 else tr("{0} houses", join_list(names))


def _list(items):
    """'A, B and C' (translated pieces and joining word in the current language)."""
    return join_list(list(items))


# ---------------------------------------------------------------- shodashvarga table
def shodashvarga_table(chart):
    """One row per divisional chart: {key, name, purpose, signs: {'Lagna': sign, 'Sun': sign, ...}}."""
    rows = []
    for key, name, purpose in SHODASHVARGA:
        if key == "D1":
            signs = {"Lagna": chart["ascendant"]["sign"]}
            signs.update({p: chart["planets"][p]["sign"] for p in BODIES})
        else:
            signs = {"Lagna": chart["ascendant"]["vargas"].get(key)}
            signs.update({p: chart["planets"][p]["vargas"].get(key) for p in BODIES})
        if all(signs.values()):
            rows.append({"key": key, "name": name, "purpose": purpose, "signs": signs})
    return rows


# ---------------------------------------------------------------- planet considerations
_SIGNIFIES = tbl({
    "Sun": "confidence, health, father figures and standing in society",
    "Moon": "mind, mood, mother and everyday comfort",
    "Mars": "energy, courage, drive and how you handle conflict",
    "Mercury": "thinking, speech, learning, business and skills",
    "Jupiter": "wisdom, growth, teachers, money and good fortune",
    "Venus": "love, comfort, art, pleasures and vehicles",
    "Saturn": "hard work, discipline, patience and responsibility",
    "Rahu": "big ambitions, sudden pushes, foreign things and restlessness",
    "Ketu": "detachment, intuition, letting go and spiritual interest",
})

# What may happen when the planet is doing well / mixed / needs care. Always tendencies.
_EFFECTS = tbl({
    "Sun": ("Your confidence can be steady and people may naturally look up to you. Health and vitality tend to be decent and dealings with bosses or authorities can go smoothly.",
            "Confidence may come and go. Some periods bring recognition, others make you feel overlooked, so results tend to depend on how consistently you put yourself forward.",
            "You may sometimes doubt yourself or clash with authority figures, and energy can dip. Building routines, morning sunlight and small confidence wins usually help."),
    "Moon": ("Your mind tends to be calm and caring, emotions are easier to handle and home life may feel comforting.",
             "Moods may swing between peaceful and restless. Sleep, food habits and the people around you can noticeably change how you feel.",
             "You may worry or overthink more than most and feel emotionally drained at times. Rest, routine and talking things out usually help a lot."),
    "Mars": ("You may have good stamina, courage and the drive to finish what you start. Competition can bring out your best.",
             "Energy can be strong but temper or impatience may show up now and then. Channelling it into sport or work usually pays off.",
             "You may face impatience, arguments, minor injuries or too much heat in the body. Slowing down before reacting is the classic advice."),
    "Mercury": ("A sharp, quick mind, good speech and a talent for learning, trading or communication is likely.",
                "Your thinking is good but can be scattered. Results improve when you finish one thing at a time and double-check details.",
                "You may find it harder to focus or express yourself, or be prone to nervous worry. Reading, writing and steady study habits help."),
    "Jupiter": ("Wisdom, optimism and helpful teachers or elders often turn up when you need them. Money and opportunities may grow steadily.",
                "Good luck is present but not automatic - growth tends to come when you learn, teach or share rather than wait.",
                "Luck may feel slow and advice from elders or teachers can be hard to follow. Patience, learning and generosity usually turn this around."),
    "Venus": ("Love, comfort, creativity and enjoyment of life may come easily, and relationships tend to be warm.",
              "Relationships and comforts are present but may need more effort, or come with some give-and-take.",
              "Love life, money for comforts or artistic confidence may feel harder to keep steady. Being clear and kind with partners helps most."),
    "Saturn": ("Hard work usually pays back well, and you may be seen as reliable and mature. Success tends to be slow but lasting.",
               "Effort is needed and results are often delayed, though they usually do arrive with patience.",
               "You may feel delays, extra responsibility or tiredness. Discipline, routine and patience are what turn this planet from a strict teacher into a helper."),
    "Rahu": ("Ambitions, foreign links or modern fields can give sudden progress. You may stand out from the crowd.",
             "You may feel a strong pull toward something new, with some restlessness. Staying grounded keeps the gains.",
             "Confusion, over-ambition or sudden changes may happen. Avoid shortcuts and check facts before big steps."),
    "Ketu": ("Good intuition and a natural ability to let go of what you do not need. Interest in deeper or spiritual subjects may run strong.",
             "You may sometimes feel detached or restless about things others chase. This usually mellows with age and inner work.",
             "You may feel lost, distracted or cut off from people in this area at times. Meditation and a steady routine help."),
})

_COMBUST_LIMIT = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}
_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}


def _lordships(chart):
    lord_of = {p: [] for p in BODIES}
    for house, sign in chart["houses"].items():
        lord_of[SIGN_LORD[sign]].append(int(house))
    return {p: sorted(h) for p, h in lord_of.items()}


def _sign_relation(planet, chart):
    """'Own sign' / 'Exalted' / 'Debilitated' / 'Friendly sign' / 'Neutral sign' / 'Enemy sign' (or None for Rahu/Ketu)."""
    sign = chart["planets"][planet]["sign"]
    if planet in ("Rahu", "Ketu"):
        return None
    if sign in OWN_SIGNS.get(planet, ()):
        return "Own sign"
    if EXALTATION_SIGN.get(planet) == sign:
        return "Exalted"
    if DEBILITATION_SIGN.get(planet) == sign:
        return "Debilitated"
    # friendly / neutral / enemy sign: how the planet naturally regards the sign's lord (the usual textbook rule)
    return {"friend": tx("Friendly sign"), "neutral": tx("Neutral sign"), "enemy": tx("Enemy sign")}[
        natural_friendship(planet, SIGN_LORD[sign])]


def _aspects_on(chart):
    """{planet: [planets whose Vedic aspect lands on its house]} and {planet: [houses it aspects]}."""
    pl = chart["planets"]
    aspecting, aspected_by = {}, {p: [] for p in BODIES}
    for p in BODIES:
        houses = sorted({((pl[p]["house"] - 1 + d - 1) % 12) + 1 for d in aspect_distances_for(p)})
        aspecting[p] = houses
        for q in BODIES:
            if q != p and pl[q]["house"] in houses:
                aspected_by[q].append(p)
    return aspecting, aspected_by


def _tone_from_score(score):
    if score >= 3:
        return "Good"
    if score == 2:
        return "Good"
    if score == 1:
        return "Mostly good"
    if score == 0:
        return "Mixed"
    if score == -1:
        return "Needs some care"
    return "Challenging"


def planet_considerations(chart):
    """{planet: {...}} facts + reasons + a plain verdict for every planet."""
    pl = chart["planets"]
    lords = _lordships(chart)
    aspecting, aspected_by = _aspects_on(chart)
    sun_lon = pl["Sun"]["longitude"]
    out = {}
    for p in BODIES:
        d = pl[p]
        rel = _sign_relation(p, chart)
        reasons, score = [], 0
        if rel in ("Own sign", "Exalted"):
            score += 2
            reasons.append(tr('it sits in a strong place ({0})', rel.lower()))
        elif rel == "Friendly sign":
            score += 1
            reasons.append(tx("it sits in a friendly sign"))
        elif rel == "Enemy sign":
            score -= 1
            reasons.append(tx("it sits in an unfriendly sign"))
        elif rel == "Debilitated":
            score -= 2
            reasons.append(tx("it sits in a weak sign (debilitated)"))
        house = d["house"]
        if p in _BENEFICS:
            if house in (6, 8, 12):
                score -= 1
                reasons.append(tr('the {0} house is a tougher house for a helpful planet', ordinal(house)))
            elif house != 3:
                score += 1
                reasons.append(tr('the {0} house suits a helpful planet', ordinal(house)))
        else:
            if house in (3, 6, 10, 11):
                score += 1
                reasons.append(tr('the {0} house is a house where strong planets tend to do well', ordinal(house)))
            elif house in (8, 12):
                score -= 1
                reasons.append(tr('the {0} house is a tougher house for this planet', ordinal(house)))
        combust = False
        limit = _COMBUST_LIMIT.get(p)
        if limit:
            gap = abs((d["longitude"] - sun_lon + 180) % 360 - 180)
            if gap <= limit:
                combust = True
                score -= 1
                reasons.append(tx("it is very close to the Sun (combust), which can dim its results"))
        helpers = [q for q in aspected_by[p] if q in ("Jupiter", "Venus")]
        strainers = [q for q in aspected_by[p] if q in ("Saturn", "Mars", "Rahu", "Ketu")]
        if helpers:
            score += 1
            reasons.append(tr('it gets a supportive look from {0}', _list(helpers)))
        if strainers:
            score -= 1
            reasons.append(tr('it gets a pressuring look from {0}', _list(strainers)))
        tone = _tone_from_score(score)
        idx = {"Good": 0, "Mostly good": 0, "Mixed": 1, "Needs some care": 2, "Challenging": 2}[tone]
        lord_txt = ""
        if lords[p]:
            lord_txt = tr(' It rules your {0} house{1}.', _list(ordinal(h) for h in lords[p]), 's' if len(lords[p]) > 1 else '')
        area = _HOUSE_AREA[house]
        simple = (tr('{0} stands for {1}. In your chart it sits in the {2} house, so its effects show up mostly in '
                     '{3}.{4}', p, _SIGNIFIES[p], ordinal(house), area, lord_txt))
        out[p] = {
            "planet": p, "sign": d["sign"], "house": house, "relation": rel, "lord_of": lords[p],
            "aspects_houses": aspecting[p], "aspected_by": aspected_by[p], "combust": combust,
            "retrograde": bool(d.get("retrograde")), "score": score, "tone": tone,
            "reasons": reasons, "summary": simple, "effects": _EFFECTS[p][idx],
        }
    return out


_TONE_GIST = tbl({
    "Good": "it is more of a helper than a hurdle for the areas it touches",
    "Mostly good": "it mostly helps, with the odd bump along the way",
    "Mixed": "expect a blend of easy and effortful stretches in the areas it touches",
    "Needs some care": "the areas it touches may need extra patience and looking after",
    "Challenging": "the areas it touches may ask a lot of you, so steady habits and patience matter most",
})


_TONE_PHRASE = tbl({"Good": "looks good", "Mostly good": "looks mostly good", "Mixed": "looks mixed",
                "Needs some care": "needs some care", "Challenging": "looks challenging"})


def planet_considerations_text(chart):
    """Reader-friendly paragraphs: one block per planet, in the '--- Heading ---' convention."""
    parts = []
    for p, c in planet_considerations(chart).items():
        rel = tr(' ({0})', c['relation'].lower()) if c["relation"] else ""
        facts = tr('{0} is in {1}{2}, in your {3} house.', p, c['sign'], rel, ordinal(c['house']))
        if c["lord_of"]:
            facts += tr(' It is the lord of the {0}.', houses_phrase(c['lord_of']))
        facts += tr(" It looks at the {0}.", houses_phrase(c["aspects_houses"]))
        if c["aspected_by"]:
            facts += tr(" It is looked at by {0}.", _list(c["aspected_by"]))
        why = tr("Why this verdict: {0}.", "; ".join(c["reasons"])) if c["reasons"] else tx("Why this verdict: nothing special helps or hurts it.")
        if c["retrograde"] and p not in ("Rahu", "Ketu"):
            why += tx(" It is moving backwards (retrograde), which classical texts read as a more inward, delayed or intense version of its themes.")
        parts.append(tr('--- {0}: {1} ---\n{2}\n\n{3}\n\n{4}\n\nWhat may happen: {5}\n\n[In simple terms: {6} {7} in your chart - '
                        '{8}.]', p, c['tone'], c['summary'], facts, why, c['effects'], p, _TONE_PHRASE[c['tone']], _TONE_GIST[c['tone']]))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- the 12 houses and the running period
_HOUSE_TEMPLATE = tbl({
    "Good": "{area} tend to go smoothly and give you support.",
    "Mostly good": "{area} mostly go well, with a few bumps along the way.",
    "Mixed": "{area} bring a mix of easy and effortful stretches.",
    "Needs some care": "{area} may need extra care and patience; steady effort usually helps.",
    "Challenging": "{area} may ask a lot of you, so steady habits and patience matter most.",
})


def house_verdicts(chart):
    """A good / mixed / needs-care verdict for each of the 12 houses (life areas), with the reasons."""
    pl = chart["planets"]
    cons = planet_considerations(chart)
    sav = chart["ashtakavarga"]["sarvashtakavarga"]
    _aspecting, aspected_by = _aspects_on(chart)
    out = []
    for h in range(1, 13):
        sign = chart["houses"][h]
        lord = SIGN_LORD[sign]
        score, reasons = 0, []
        c = cons[lord]
        if c["relation"] in ("Own sign", "Exalted"):
            score += 2
            reasons.append(tr('its ruler {0} is strong ({1})', lord, c['relation'].lower()))
        elif c["relation"] == "Friendly sign":
            score += 1
            reasons.append(tr('its ruler {0} sits in a friendly sign', lord))
        elif c["relation"] == "Enemy sign":
            score -= 1
            reasons.append(tr('its ruler {0} sits in an unfriendly sign', lord))
        elif c["relation"] == "Debilitated":
            score -= 2
            reasons.append(tr('its ruler {0} is weak (debilitated)', lord))
        lh = pl[lord]["house"]
        if h not in (6, 8, 12):
            if lh in (1, 4, 5, 7, 9, 10, 11):
                score += 1
                reasons.append(tr('{0} is placed in the {1} house, a helpful spot', lord, ordinal(lh)))
            elif lh in (6, 8, 12):
                score -= 1
                reasons.append(tr('{0} is placed in the {1} house, a tougher spot', lord, ordinal(lh)))
        occupants = [p for p in BODIES if pl[p]["house"] == h]
        good_occ = [p for p in occupants if p in ("Jupiter", "Venus", "Mercury", "Moon")]
        bad_occ = [p for p in occupants if p in ("Saturn", "Mars", "Rahu", "Ketu", "Sun")]
        if good_occ and h not in (6, 8, 12):
            score += 1
            reasons.append(tr('{0} brings support from inside the house', _list(good_occ)) if len(good_occ) == 1
                           else tr('{0} bring support from inside the house', _list(good_occ)))
        if bad_occ and h not in (3, 6, 10, 11):
            score -= 1
            reasons.append(tr('{0} adds pressure from inside the house', _list(bad_occ)) if len(bad_occ) == 1
                           else tr('{0} add pressure from inside the house', _list(bad_occ)))
        elif bad_occ:
            score += 1
            reasons.append(tr('{0} can do well here', _list(bad_occ)))
        helpers = [q for q in aspected_by_house(chart, h) if q in ("Jupiter", "Venus")]
        if helpers:
            score += 1
            reasons.append(tr('{0} looks at it kindly', _list(helpers)) if len(helpers) == 1
                           else tr('{0} look at it kindly', _list(helpers)))
        pts = sav[sign]
        if pts >= 30:
            score += 1
            reasons.append(tr('the sign has a high support score ({0} points)', pts))
        elif pts <= 22:
            score -= 1
            reasons.append(tr('the sign has a low support score ({0} points)', pts))
        tone = _tone_from_score(score)
        area = _HOUSE_AREA[h]
        out.append({"house": h, "sign": sign, "lord": lord, "area": area, "tone": tone, "score": score, "reasons": reasons,
                    "may_happen": _HOUSE_TEMPLATE[tone].format(area=area[0].upper() + area[1:])})
    return out


def aspected_by_house(chart, house):
    """Planets whose Vedic aspect falls on the given house."""
    pl = chart["planets"]
    return [p for p in BODIES if pl[p]["house"] != house and
            house in {((pl[p]["house"] - 1 + d - 1) % 12) + 1 for d in aspect_distances_for(p)}]


def houses_text(chart):
    parts = [tx("--- Your 12 houses at a glance ---\nEach house is one area of life. For each: is it looking good, mixed or in need of "
             "care, and what may happen. [In simple terms: this is the quick overview - the sections below explain each area "
             "in more depth.]")]
    for v in house_verdicts(chart):
        why = tr("Because {0}.", "; ".join(v["reasons"])) if v["reasons"] else tx("Nothing special helps or hurts it.")
        parts.append(tr('{0} house ({1}): {2}. {3} {4}', ordinal(v['house']), v['area'], v['tone'], v['may_happen'], why))
    return "\n\n".join(parts)


def period_outlook(chart, at=None):
    """What the running Mahadasha / Antardasha is likely to feel like, from the planet verdicts."""
    from transits import _running_dasha
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    running = _running_dasha(chart, at)
    if not running:
        return None
    cons = planet_considerations(chart)
    maha, antar = running["mahadasha"], running["antardasha"]
    return {"mahadasha": maha, "antardasha": antar, "maha_tone": cons[maha]["tone"], "antar_tone": cons[antar]["tone"],
            "maha_effects": cons[maha]["effects"], "antar_effects": cons[antar]["effects"]}


def period_text(chart, at=None):
    o = period_outlook(chart, at)
    if not o:
        return ""
    return (tr('--- Where you are right now ---\nYour main life period (Mahadasha) is {0}, which looks {1} in '
               'your chart. What may happen: {2}\n\nInside it you are in the {3} sub-period (Antardasha), which '
               'looks {4}. What may happen: {5}\n\n[In simple terms: the {6} season sets the general mood of '
               'these years and the {7} sub-period is the weather within it. These are tendencies, not fixed '
               'events.]', o['mahadasha'], o['maha_tone'].lower(), o['maha_effects'], o['antardasha'], o['antar_tone'].lower(), o['antar_effects'], o['mahadasha'], o['antardasha']))


# ---------------------------------------------------------------- friendships and aspects
def friendship_tables(chart):
    """Natural, temporary and compound (five-fold) friendship among the seven classical planets."""
    pl = chart["planets"]
    natural, temporary, compound = {}, {}, {}
    for a in CLASSICAL_SEVEN:
        natural[a], temporary[a], compound[a] = {}, {}, {}
        for b in CLASSICAL_SEVEN:
            if a == b:
                continue
            m = panchadha_maitri(a, b, pl[a]["house"], pl[b]["house"])
            natural[a][b], temporary[a][b], compound[a][b] = m["natural"], m["temporal"], m["grade"]
    return {"natural": natural, "temporary": temporary, "compound": compound}


_ASPECTS = [("Conjunction", 0, 9, "blend"), ("Sextile", 60, 5, "easy"), ("Square", 90, 7, "tense"),
            ("Trine", 120, 8, "easy"), ("Opposition", 180, 9, "tense")]
_ASPECT_PLAIN = tbl({
    "blend": "these two energies mix together and act as one, for better or worse depending on the planets",
    "easy": "these two energies support each other, so this area tends to run smoothly",
    "tense": "these two energies pull against each other, which can feel like friction but also drives action",
})


def western_aspects(chart):
    """Angles between the nine bodies (Western style: conjunction/sextile/square/trine/opposition
    within an orb), each with a plain reading. The Rahu-Ketu axis itself is left out."""
    pl = chart["planets"]
    out = []
    for i, a in enumerate(BODIES):
        for b in BODIES[i + 1:]:
            if {a, b} == {"Rahu", "Ketu"}:
                continue
            gap = abs(pl[a]["longitude"] - pl[b]["longitude"]) % 360
            gap = min(gap, 360 - gap)
            for name, angle, orb_limit, flow in _ASPECTS:
                orb = abs(gap - angle)
                if orb <= orb_limit:
                    out.append({"a": a, "b": b, "aspect": name, "orb": round(orb, 2), "flow": flow,
                                "meaning": _ASPECT_PLAIN[flow]})
                    break
    out.sort(key=lambda r: r["orb"])
    return out


# ---------------------------------------------------------------- doshas
def _dosha(name, present, status, what, may_happen, easing, tone, plain):
    return {"name": name, "present": present, "status": status, "tone": tone, "what": what,
            "may_happen": may_happen, "easing": easing, "plain": plain}


_KALSARPA_TYPES = {1: "Anant", 2: "Kulik", 3: "Vasuki", 4: "Shankhpal", 5: "Padma", 6: "Mahapadma", 7: "Takshak",
                   8: "Karkotak", 9: "Shankhchur", 10: "Ghatak", 11: "Vishdhar", 12: "Sheshnag"}


def kalsarpa(chart):
    """All seven classical planets on one side of the Rahu-Ketu axis."""
    pl = chart["planets"]
    rahu = pl["Rahu"]["longitude"]
    inside = [p for p in CLASSICAL_SEVEN if (pl[p]["longitude"] - rahu) % 360 < 180]
    outside = [p for p in CLASSICAL_SEVEN if p not in inside]
    full = len(inside) in (0, 7)
    partial = len(inside) in (1, 6) and not full
    return {"full": full, "partial": partial, "type": _KALSARPA_TYPES[pl["Rahu"]["house"]] if full else None,
            "odd_ones": (inside if len(inside) == 1 else outside) if partial else []}


def sade_sati_now(chart, at=None):
    """Where Saturn is today relative to the natal Moon: Sade Sati phase, Dhaiya, or none."""
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
        jd = ephemeris.julian_day_ut(at.year, at.month, at.day, at.hour, at.minute, at.second, 0.0)
        lon = ephemeris.get_planet_longitude(jd, "Saturn")
    house = ((int(lon // 30) - SIGNS.index(chart["planets"]["Moon"]["sign"])) % 12) + 1
    return {"house_from_moon": house, "saturn_sign": SIGNS[int(lon // 30)], "kind": _saturn_phase(house)}


def _saturn_phase(house_from_moon):
    return {12: tx("Sade Sati - rising phase"), 1: tx("Sade Sati - peak phase"), 2: tx("Sade Sati - setting phase"),
            4: tx("Dhaiya (Saturn in the 4th from Moon)"), 8: tx("Dhaiya (Saturn in the 8th from Moon)")}.get(house_from_moon)


def assess_doshas(chart, at=None):
    """The list of dosha entries shown in the app and the PDF."""
    from doshas import (assess_grahan_dosha, assess_guru_chandal_dosha, assess_pitra_dosha,
                        assess_shrapit_dosha)
    pl = chart["planets"]
    out = []

    # Mangal (Kuja) dosha
    md = chart["mangal_dosha"]
    marks = [("Lagna", md["from_lagna"]["dosha_present"]), ("Moon", md["from_moon"]["dosha_present"]),
             ("Venus", md["from_venus"]["dosha_present"])]
    hit = [n for n, v in marks if v]
    mars_sign, mars = pl["Mars"]["sign"], pl["Mars"]
    eased_by = []
    if mars_sign in OWN_SIGNS["Mars"] or EXALTATION_SIGN["Mars"] == mars_sign:
        eased_by.append(tx("Mars is in a strong sign of its own or exaltation"))
    _asp, _by = _aspects_on(chart)
    if "Jupiter" in _by["Mars"]:
        eased_by.append(tx("Jupiter looks at Mars and softens it"))
    if not hit:
        out.append(_dosha("Manglik (Mangal) Dosha", False, "Not present",
                          tx("Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house from the Lagna, Moon or Venus."),
                          tx("Nothing to worry about here - Mars does not sit in a tense marriage house."),
                          "", "Good", tx("Mars is not in a sensitive place, so this worry does not apply to you.")))
    else:
        strength = "stronger" if len(hit) >= 2 else "mild"
        tone = "Needs some care" if len(hit) >= 2 else "Mixed"
        out.append(_dosha("Manglik (Mangal) Dosha", True, tr('Present ({0}) - counted from {1}', strength, _list(hit)),
                          tx("Mars sits in the 1st, 2nd, 4th, 7th, 8th or 12th house counted from ") + _list(hit) + ".",
                          tx("It may bring a hot temper, quick reactions or delays and friction in marriage or close partnerships. "
                          "Many people with it have happy marriages, and it is traditionally seen as balanced when the partner also has it."),
                          (tx("It may be eased because ") + _list(eased_by) + ". ") if eased_by else
                          tx("Patience, calm talk and choosing a partner who understands your fire usually help."),
                          tone, tx("Mars is in a sensitive spot, so relationships may need extra patience - it is a tendency, not a fixed fate.")))

    # Kalsarpa
    ks = kalsarpa(chart)
    if ks["full"]:
        out.append(_dosha("Kalsarpa Dosha", True, tr('Present - {0} type', ks['type']),
                          tx("All seven main planets fall on one side of the Rahu-Ketu axis."),
                          tx("It may bring ups and downs, delays or a feeling of being held back in some years, and often progress comes in bursts. "
                          "Its strength depends a lot on the rest of the chart."),
                          tx("Steady effort, helping others and spiritual practice are the usual advice."),
                          "Needs some care", tr('Because all planets are on one side of Rahu and Ketu, life may feel eventful ({0} type).', ks['type'])))
    elif ks["partial"]:
        out.append(_dosha("Kalsarpa Dosha", False, "Not fully present (partial)",
                          tx("All planets except ") + _list(ks["odd_ones"]) + tx(" are on one side of the Rahu-Ketu axis."),
                          tx("The classical pattern is not complete, so its effect is usually mild or absent."),
                          "", "Mostly good", tx("Almost, but not fully, formed - usually nothing to worry about.")))
    else:
        out.append(_dosha("Kalsarpa Dosha", False, "Not present",
                          tx("All seven main planets on one side of the Rahu-Ketu axis."),
                          tx("Your planets are spread on both sides of the axis, so this pattern does not apply."),
                          "", "Good", "Your chart is free from this."))

    # Pitra dosha
    pd = assess_pitra_dosha(chart)
    flags = [k for k in ("rahu_ketu_in_9th", "sun_conjunct_rahu_ketu", "ninth_lord_afflicted") if pd[k]["present"]]
    if flags:
        out.append(_dosha("Pitra Dosha (ancestral pattern)", True, "Present (some signs)",
                          " ".join(pd[k]["detail"] for k in flags),
                          tx("It may show up as delays in luck, or family patterns you feel you are working through. Not every source agrees on this rule."),
                          tx("Respecting elders, charity in the family's name and steady effort are the traditional advice."),
                          "Mixed", tx("There are some signs of an ancestral pattern - read it as a gentle nudge to care for family roots.")))
    else:
        out.append(_dosha("Pitra Dosha (ancestral pattern)", False, "Not present",
                          tx("The 9th house, its lord or the Sun being troubled by Rahu, Ketu or harsh planets."),
                          "None of the usual signs are present.", "", "Good", "Nothing here to worry about."))

    # Guru Chandal
    gc = assess_guru_chandal_dosha(chart)
    out.append(_dosha("Guru Chandal Dosha", gc["present"], "Present" if gc["present"] else "Not present",
                      "Jupiter together with Rahu.",
                      (tx("Your wisdom and beliefs may be pulled toward unusual ideas, and you may question teachers or traditions. "
                       "It can also make you a bold, original thinker.")) if gc["present"] else "Jupiter and Rahu are not together.",
                      tx("Choosing guides carefully and checking advice against your own values helps.") if gc["present"] else "",
                      "Mixed" if gc["present"] else "Good",
                      tx("Your wisdom planet is mixed with a restless one - worth choosing teachers wisely.") if gc["present"] else
                      tx("Jupiter and Rahu are apart, so this worry does not apply to you.")))

    # Grahan
    gr = assess_grahan_dosha(chart)
    for key, lum, label in (("surya_grahan", "Sun", "Surya Grahan Dosha (Sun-Rahu/Ketu)"),
                            ("chandra_grahan", "Moon", "Chandra Grahan Dosha (Moon-Rahu/Ketu)")):
        r = gr[key]
        out.append(_dosha(label, r["present"], "Present" if r["present"] else "Not present",
                          tr('The {0} together with Rahu or Ketu.', lum),
                          ((tx("Confidence or father-related matters may feel shadowed at times.") if lum == "Sun" else
                            tx("Your mind may feel clouded or anxious at times.")) + tx(" Effects depend on the rest of the chart."))
                          if r["present"] else tr('The {0} is clear of the Rahu-Ketu shadow.', lum),
                          (tx("Sun: sun-gazing at sunrise, confidence-building routines. ") if lum == "Sun" else
                           "Calming routines, sleep and time in nature. ") if r["present"] else "",
                          "Mixed" if r["present"] else "Good",
                          (tr('The {0} is close to Rahu or Ketu, so it can feel shadowed at times - a tendency, not a fixed '
                              'result.', lum)
                           if r["present"] else tr('The {0} is clear of Rahu and Ketu, so this worry does not apply to you.', lum))))

    # Shrapit
    sp = assess_shrapit_dosha(chart)
    out.append(_dosha("Shrapit Dosha", sp["present"], "Present" if sp["present"] else "Not present",
                      "Saturn together with Rahu.",
                      (tx("Delays may pile on delays, and you may feel stuck or face sudden reversals in some years. "
                       "It is a tendency that steady effort tends to soften.")) if sp["present"] else "Saturn and Rahu are not together.",
                      tx("Discipline, honesty and service to others are the classic remedies.") if sp["present"] else "",
                      "Needs some care" if sp["present"] else "Good",
                      tx("Saturn and Rahu are together, so patience matters.") if sp["present"] else
                      tx("Saturn and Rahu are apart, so this worry does not apply to you.")))

    # Saturn's current phase
    now = sade_sati_now(chart, at)
    kind = now["kind"]
    if kind and kind.startswith("Sade"):
        gist = {"rising": tx("It starts gently - expenses, worries about the future and a sense of pressure may build."),
                "peak": tx("This is the heaviest stretch - responsibilities, slowdowns and lessons about patience may feel strongest."),
                "setting": tx("It is easing - things may slowly settle, with some last tests around money and family.")}
        phase = kind.split("- ")[1].split()[0]
        out.append(_dosha("Sade Sati (now)", True, tr('Running - {0}', kind.split('- ')[1]),
                          tx("Saturn passes over the sign before, the sign of, and the sign after your natal Moon, about 7.5 years."),
                          gist[phase] + tx(" Many people find it also brings maturity, discipline and lasting progress."),
                          tx("Patience, routine, honesty and helping others are the standard advice."), "Needs some care",
                          tx("Saturn is testing you now, but this is a strict-teacher phase, not a punishment.")))
    elif kind:
        out.append(_dosha("Dhaiya (now)", True, tr('Running - {0}', kind),
                          tx("Saturn spends about 2.5 years in the 4th or 8th sign from your Moon."),
                          tx("You may feel extra pressure around home, peace of mind, health or sudden events. It usually passes with steady effort."),
                          "Routine, patience and looking after health.", "Mixed", tx("A smaller Saturn phase - manageable with steady habits.")))
    else:
        out.append(_dosha("Sade Sati / Dhaiya (now)", False, "Not running",
                          tx("Saturn is not currently in a sensitive place from your Moon."),
                          tx("Saturn's heavier lessons are not pressing on you right now."), "", "Good",
                          tx("You are not in a Saturn testing phase at the moment.")))
    return out


def doshas_text(chart, at=None):
    parts = []
    for d in assess_doshas(chart, at):
        label = "What may happen" if d["present"] else "What this means"     # an absent dosha has nothing to "happen"
        body = (tr('Verdict: {0} - {1}.\n\nWhat it is: {2}\n\n{3}: {4}', d['tone'], d['status'], d['what'], label, d['may_happen']))
        if d["easing"]:
            body += tr('\n\nWhat can help: {0}', d['easing'])
        body += tr('\n\n[In simple terms: {0}]', d['plain'])
        parts.append(tr('--- {0} ---\n{1}', d['name'], body))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- lifetime Sade Sati / Dhaiya table
_SATURN_PHASES = {12: ("Sade Sati", "rising phase"), 1: ("Sade Sati", "peak phase"), 2: ("Sade Sati", "setting phase"),
                  4: ("Dhaiya (Small Panoti)", "Saturn in the 4th from Moon"), 8: ("Dhaiya (Small Panoti)", "Saturn in the 8th from Moon")}
_PHASE_PLAIN = tbl({
    "rising phase": "worries and expenses may start to build; a slow warm-up",
    "peak phase": "the heaviest stretch - responsibilities and patience are tested, and growth often follows",
    "setting phase": "pressure eases and things settle, with a few last tests",
    "Saturn in the 4th from Moon": "home, mother or peace of mind may need attention",
    "Saturn in the 8th from Moon": "sudden changes and health care may need attention",
})


def saturn_periods(chart, years=100, merge=False):
    """Saturn's stays in each sign from birth to `years` later, as [(sign, start, end)] (UTC dates)."""
    birth = _dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"]).replace(tzinfo=None)
    end = birth + _dt.timedelta(days=365.25 * years)
    step = _dt.timedelta(days=4)
    runs = []
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()

        def sign_at(t):
            jd = ephemeris.julian_day_ut(t.year, t.month, t.day, t.hour, t.minute, t.second, 0.0)
            return int(ephemeris.get_planet_longitude(jd, "Saturn") // 30)

        t, cur = birth, sign_at(birth)
        run_start = birth
        while t < end:
            nt = min(t + step, end)
            ns = sign_at(nt)
            if ns != cur:
                lo, hi = t, nt                       # bisect to the hour
                while hi - lo > _dt.timedelta(hours=1):
                    mid = lo + (hi - lo) / 2
                    if sign_at(mid) == cur:
                        lo = mid
                    else:
                        hi = mid
                runs.append([cur, run_start, hi])
                run_start, cur = hi, ns
            t = nt
        runs.append([cur, run_start, end])
    if not merge:                     # raw ingress list - a retrograde dip back into a sign shows as its own stay
        return [(SIGNS[s], a, b) for s, a, b in runs]
    # absorb short back-and-forth dips (retrograde re-entries) into the surrounding stay
    merged = []
    for run in runs:
        if merged and merged[-1][0] == run[0]:
            merged[-1][2] = run[2]
        else:
            merged.append(run)
    changed = True
    while changed:
        changed, i = False, 1
        while i < len(merged) - 1:
            if merged[i - 1][0] == merged[i + 1][0] and (merged[i][2] - merged[i][1]).days < 300:
                merged[i - 1][2] = merged[i + 1][2]
                del merged[i:i + 2]
                changed = True
            else:
                i += 1
    return [(SIGNS[s], a, b) for s, a, b in merged]


def sade_sati_table(chart, years=100):
    """Rows for every Sade Sati / Dhaiya stay: {kind, phase, sign, start, end, start_age, end_age, plain}."""
    birth = _dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"]).replace(tzinfo=None)
    moon = SIGNS.index(chart["planets"]["Moon"]["sign"])
    end_limit = birth + _dt.timedelta(days=365.25 * years)
    rows = []
    for sign, a, b in saturn_periods(chart, years):
        h = ((SIGNS.index(sign) - moon) % 12) + 1
        if h in _SATURN_PHASES:
            kind, phase = _SATURN_PHASES[h]
            rows.append({"kind": kind, "phase": phase, "sign": sign, "start": a.date(),
                         "end": (b - _dt.timedelta(days=1)).date() if b < end_limit else b.date(),
                         "start_age": round((a - birth).days / 365.25, 1), "end_age": round((b - birth).days / 365.25, 1),
                         "plain": _PHASE_PLAIN[phase]})
    return rows


def sade_sati_text(chart, years=100):
    rows = sade_sati_table(chart, years)
    lines = [tx("Sade Sati is Saturn's roughly 7.5-year walk over the sign before, the sign of and the sign after your Moon; "
             "Dhaiya (also called Small Panoti) is its 2.5-year stay in the 4th or 8th sign from your Moon. Both are read as "
             "times that test patience and reward steady work, not as fixed bad news. Saturn sometimes steps back into the "
             "earlier sign for a few months (it moves backwards for a while each year), so a phase can appear twice. "
             "Dates are approximate (a few days either way).")]
    for r in rows:
        lines.append(tr('{0} - {1}: {2:%d %b %Y} to {3:%d %b %Y} (age {4:.0f} to {5:.0f}). Likely feel: {6}.', r['kind'], r['phase'], r['start'], r['end'], max(r['start_age'], 0), r['end_age'], r['plain']))
    return "\n\n".join(lines)


# ---------------------------------------------------------------- one call for everything
def compute_extras(chart, at=None):
    return {
        "considerations": planet_considerations(chart), "friendship": friendship_tables(chart),
        "aspects": western_aspects(chart), "doshas": assess_doshas(chart, at),
        "sade_sati": sade_sati_table(chart), "shodashvarga": shodashvarga_table(chart),
    }


# ---------------------------------------------------------------- Sade Sati in detail, for this person
_PHASE_STORY = tbl({
    "rising phase": ("Saturn is in the sign before your Moon sign. It is the warm-up: expenses and worries about the future tend to "
                     "creep in, sleep or peace of mind may need protecting, and you may feel pressure to prove yourself."),
    "peak phase": ("Saturn is over your Moon sign itself. It is the most personal stretch: mood, energy and confidence feel tested, "
                   "responsibilities grow and results come slowly - yet it is also when patience and discipline build the most lasting strength."),
    "setting phase": ("Saturn is in the sign after your Moon sign. The pressure eases: money and family matters may still ask for care, "
                      "but you can usually feel things settling and the lessons turning into steadiness."),
})
_ADVICE = ("What usually helps: a steady daily routine, keeping promises, honest work, looking after sleep and health, "
           "helping people who are older or have less than you, and avoiding big risks or shortcuts while Saturn is testing you.")


def sade_sati_cycles(chart, years=100):
    """Each Sade Sati (three phases, ~7.5 years) as one cycle: {start, end, start_age, end_age, stays: [...]}."""
    rows = [r for r in sade_sati_table(chart, years) if r["kind"] == "Sade Sati"]
    cycles = []
    for r in rows:
        if cycles and (r["start"] - cycles[-1]["end"]).days < 500:
            cycles[-1]["stays"].append(r)
            cycles[-1]["end"], cycles[-1]["end_age"] = r["end"], r["end_age"]
        else:
            cycles.append({"start": r["start"], "end": r["end"], "start_age": r["start_age"], "end_age": r["end_age"], "stays": [r]})
    return cycles


def _stay_detail(chart, stay):
    """What one stay of Saturn (sign, phase) means for this chart."""
    sign = stay["sign"]
    house = (SIGNS.index(sign) - SIGNS.index(chart["ascendant"]["sign"])) % 12 + 1
    pts = chart["ashtakavarga"]["bhinnashtakavarga"]["Saturn"][sign]
    tone = "supportive" if pts >= 5 else "average" if pts >= 4 else "demanding"
    tail = {"supportive": tx(", so this part tends to be gentler than the general description"),
            "average": tx(", so expect the general description to apply"),
            "demanding": tx(", so this part may feel heavier than usual and reward extra patience")}[tone]
    word = {"supportive": tx("a supportive"), "average": tx("an average"), "demanding": tx("a demanding")}[tone]
    return {"house": house, "area": _HOUSE_AREA[house], "points": pts, "points_tone": tone,
            "text": (tr('Saturn is moving through {0}, your {1} house ({2}), so the pressure is felt most in {3}. Saturn '
                        'scores {4} of 8 points in {5} in your Ashtakvarga, which is {6} sign for it{7}.', sign, ordinal(house), _HOUSE_AREA[house], _HOUSE_AREA[house], pts, sign, word, tail))}


def sade_sati_detail_text(chart, at=None):
    """A personal walk-through of Sade Sati: where Saturn is now, how each phase may go for THIS chart, and the whole life's cycles."""
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    today = at.date()
    cons = planet_considerations(chart)
    sat, moon = cons["Saturn"], cons["Moon"]
    cycles = sade_sati_cycles(chart)
    parts = []

    rank = (sat["relation"] or "no special sign rank").lower()
    natal = (tr('Saturn in your birth chart looks {0}: it sits in {1} ({2}), in your {3} house, and rules your '
                '{4} house{5}. Your Moon looks {6} (in {7}, {8} house). ', sat['tone'].lower(), sat['sign'], rank, ordinal(sat['house']), _list(ordinal(h) for h in sat['lord_of']), 's' if len(sat['lord_of']) > 1 else '', moon['tone'].lower(), moon['sign'], ordinal(moon['house'])))
    if sat["tone"] in ("Good", "Mostly good"):
        natal += (tx("Because Saturn is well placed for you, Sade Sati tends to feel more like a strict but fair teacher: hard work is "
                  "usually rewarded, even if slowly."))
    elif sat["tone"] == "Mixed":
        natal += (tx("Because Saturn is mixed for you, expect some genuinely testing stretches and some where effort pays off; how you "
                  "handle the first half often decides how the second half feels."))
    else:
        natal += (tx("Because Saturn needs care in your chart, Sade Sati may feel heavier than average, so steady habits, health check-ups "
                  "and avoiding big risks matter more for you."))
    parts.append(tx("--- Sade Sati for you ---\n") + natal +
                 tx("\n\n[In simple terms: Sade Sati is Saturn's 7.5-year test. How hard it feels depends on how Saturn and your Moon are "
                 "placed in YOUR chart - described above. It is a tendency, never a fixed result.]"))

    kind = sade_sati_now(chart, at)["kind"]
    cur = next((c for c in cycles if c["start"] <= today <= c["end"]), None)
    if kind and kind.startswith("Sade") and cur:
        stay = next((s for s in cur["stays"] if s["start"] <= today <= s["end"]), cur["stays"][0])
        d = _stay_detail(chart, stay)
        left = (cur["end"] - today).days
        done = (today - cur["start"]).days
        total = max((cur["end"] - cur["start"]).days, 1)
        parts.append(tr('--- Where you are right now ---\nYou are in Sade Sati - {0}. This cycle began on {1:%d %b %Y} '
                        '(age {2:.0f}) and runs to about {3:%d %b %Y} (age {4:.0f}) - roughly {5}% is behind you and '
                        'about {6} years {7} months remain.\n\n{8}\n\n{9}\n\n{10}\n\n[In simple terms: you are in the {11} '
                        "stretch of Saturn's test. It is asking for patience in {12}. Keep routines steady and the "
                        'difficult months tend to pass with lasting lessons.]', stay['phase'], cur['start'], max(cur['start_age'], 0), cur['end'], cur['end_age'], done * 100 // total, left // 365, (left % 365) // 30, _PHASE_STORY[stay['phase']], d['text'], _ADVICE, stay['phase'].split()[0], d['area']))
    elif kind:
        parts.append(tr('--- Where you are right now ---\nSaturn is currently in a smaller test for you ({0}). It is a '
                        'shorter, milder version of Sade Sati; steady routines and looking after health and home are '
                        'enough for most people.', kind))
    else:
        nxt = next((c for c in cycles if c["start"] > today), None)
        parts.append(tx("--- Where you are right now ---\nYou are not in Sade Sati at the moment.") + (
            tr(' The next one begins around {0:%d %b %Y} (age {1:.0f}).', nxt['start'], nxt['start_age']) if nxt else ""))

    story = [tx("--- How each phase may go for you ---")]
    for phase in ("rising phase", "peak phase", "setting phase"):
        story.append(tr('{0}: {1}', phase.capitalize(), _PHASE_STORY[phase]))
    story.append(tx(_ADVICE))
    parts.append("\n\n".join(story))

    lines = [tx("--- Your Sade Sati cycles through life ---")]
    for i, c in enumerate(cycles, start=1):
        lines.append(tr('Cycle {0}: {1:.0f} to {2:.0f} years old ({3:%b %Y} - {4:%b %Y}).', i, max(c['start_age'], 0), c['end_age'], c['start'], c['end']))
        for s in c["stays"]:
            d = _stay_detail(chart, s)
            lines.append(tr("- {0} in {1} ({2:%d %b %Y} to {3:%d %b %Y}): pressure on {4}; Saturn's Ashtakvarga points here "
                            '{5}/8 ({6}).', s['phase'].capitalize(), s['sign'], s['start'], s['end'], d['area'], d['points'], d['points_tone']))
    parts.append("\n".join(lines))
    return "\n\n".join(parts)
