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

# ---------------------------------------------------------------- shared vocabulary
TONES = ["Good", "Mostly good", "Mixed", "Needs some care", "Challenging"]

# (key, name, what this chart is used to look at). D7 is deliberately absent (see module docstring).
SHODASHVARGA = [
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
]
BODIES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

_HOUSE_AREA = {
    1: "your body, looks and personality", 2: "money, family and speech", 3: "courage, effort and siblings",
    4: "home, mother and inner peace", 5: "studies, creativity and fun", 6: "work, debts and health habits",
    7: "marriage and partnerships", 8: "sudden changes and hidden matters", 9: "luck, teachers and travel",
    10: "career and reputation", 11: "gains and friends", 12: "expenses, sleep and foreign places",
}
_ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(n):
    return _ORD.get(n, f"{n}th")


def _list(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


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
_SIGNIFIES = {
    "Sun": "confidence, health, father figures and standing in society",
    "Moon": "mind, mood, mother and everyday comfort",
    "Mars": "energy, courage, drive and how you handle conflict",
    "Mercury": "thinking, speech, learning, business and skills",
    "Jupiter": "wisdom, growth, teachers, money and good fortune",
    "Venus": "love, comfort, art, pleasures and vehicles",
    "Saturn": "hard work, discipline, patience and responsibility",
    "Rahu": "big ambitions, sudden pushes, foreign things and restlessness",
    "Ketu": "detachment, intuition, letting go and spiritual interest",
}

# What may happen when the planet is doing well / mixed / needs care. Always tendencies.
_EFFECTS = {
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
}

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
    return {"friend": "Friendly sign", "neutral": "Neutral sign", "enemy": "Enemy sign"}[
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
            reasons.append(f"it sits in a strong place ({rel.lower()})")
        elif rel == "Friendly sign":
            score += 1
            reasons.append("it sits in a friendly sign")
        elif rel == "Enemy sign":
            score -= 1
            reasons.append("it sits in an unfriendly sign")
        elif rel == "Debilitated":
            score -= 2
            reasons.append("it sits in a weak sign (debilitated)")
        house = d["house"]
        if p in _BENEFICS:
            if house in (6, 8, 12):
                score -= 1
                reasons.append(f"the {ordinal(house)} house is a tougher house for a helpful planet")
            elif house != 3:
                score += 1
                reasons.append(f"the {ordinal(house)} house suits a helpful planet")
        else:
            if house in (3, 6, 10, 11):
                score += 1
                reasons.append(f"the {ordinal(house)} house is a house where strong planets tend to do well")
            elif house in (8, 12):
                score -= 1
                reasons.append(f"the {ordinal(house)} house is a tougher house for this planet")
        combust = False
        limit = _COMBUST_LIMIT.get(p)
        if limit:
            gap = abs((d["longitude"] - sun_lon + 180) % 360 - 180)
            if gap <= limit:
                combust = True
                score -= 1
                reasons.append("it is very close to the Sun (combust), which can dim its results")
        helpers = [q for q in aspected_by[p] if q in ("Jupiter", "Venus")]
        strainers = [q for q in aspected_by[p] if q in ("Saturn", "Mars", "Rahu", "Ketu")]
        if helpers:
            score += 1
            reasons.append(f"it gets a supportive look from {_list(helpers)}")
        if strainers:
            score -= 1
            reasons.append(f"it gets a pressuring look from {_list(strainers)}")
        tone = _tone_from_score(score)
        idx = {"Good": 0, "Mostly good": 0, "Mixed": 1, "Needs some care": 2, "Challenging": 2}[tone]
        lord_txt = ""
        if lords[p]:
            lord_txt = f" It rules your {_list(ordinal(h) for h in lords[p])} house{'s' if len(lords[p]) > 1 else ''}."
        area = _HOUSE_AREA[house]
        simple = (f"{p} stands for {_SIGNIFIES[p]}. In your chart it sits in the {ordinal(house)} house, so its effects "
                  f"show up mostly in {area}.{lord_txt}")
        out[p] = {
            "planet": p, "sign": d["sign"], "house": house, "relation": rel, "lord_of": lords[p],
            "aspects_houses": aspecting[p], "aspected_by": aspected_by[p], "combust": combust,
            "retrograde": bool(d.get("retrograde")), "score": score, "tone": tone,
            "reasons": reasons, "summary": simple, "effects": _EFFECTS[p][idx],
        }
    return out


_TONE_GIST = {
    "Good": "it is more of a helper than a hurdle for the areas it touches",
    "Mostly good": "it mostly helps, with the odd bump along the way",
    "Mixed": "expect a blend of easy and effortful stretches in the areas it touches",
    "Needs some care": "the areas it touches may need extra patience and looking after",
    "Challenging": "the areas it touches may ask a lot of you, so steady habits and patience matter most",
}


_TONE_PHRASE = {"Good": "looks good", "Mostly good": "looks mostly good", "Mixed": "looks mixed",
                "Needs some care": "needs some care", "Challenging": "looks challenging"}


def planet_considerations_text(chart):
    """Reader-friendly paragraphs: one block per planet, in the '--- Heading ---' convention."""
    parts = []
    for p, c in planet_considerations(chart).items():
        rel = f" ({c['relation'].lower()})" if c["relation"] else ""
        facts = f"{p} is in {c['sign']}{rel}, in your {ordinal(c['house'])} house."
        if c["lord_of"]:
            facts += f" It is the lord of the {_list(ordinal(h) for h in c['lord_of'])} house{'s' if len(c['lord_of']) > 1 else ''}."
        facts += " It looks at the " + _list(ordinal(h) for h in c["aspects_houses"]) + " house" + ("s" if len(c["aspects_houses"]) > 1 else "") + "."
        if c["aspected_by"]:
            facts += " It is looked at by " + _list(c["aspected_by"]) + "."
        why = ("Why this verdict: " + "; ".join(c["reasons"]) + ".") if c["reasons"] else "Why this verdict: nothing special helps or hurts it."
        if c["retrograde"] and p not in ("Rahu", "Ketu"):
            why += " It is moving backwards (retrograde), which classical texts read as a more inward, delayed or intense version of its themes."
        parts.append(f"--- {p}: {c['tone']} ---\n{c['summary']}\n\n{facts}\n\n{why}\n\nWhat may happen: {c['effects']}\n\n"
                     f"[In simple terms: {p} {_TONE_PHRASE[c['tone']]} in your chart - {_TONE_GIST[c['tone']]}.]")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- the 12 houses and the running period
_HOUSE_TEMPLATE = {
    "Good": "{area} tend to go smoothly and give you support.",
    "Mostly good": "{area} mostly go well, with a few bumps along the way.",
    "Mixed": "{area} bring a mix of easy and effortful stretches.",
    "Needs some care": "{area} may need extra care and patience; steady effort usually helps.",
    "Challenging": "{area} may ask a lot of you, so steady habits and patience matter most.",
}


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
            reasons.append(f"its ruler {lord} is strong ({c['relation'].lower()})")
        elif c["relation"] == "Friendly sign":
            score += 1
            reasons.append(f"its ruler {lord} sits in a friendly sign")
        elif c["relation"] == "Enemy sign":
            score -= 1
            reasons.append(f"its ruler {lord} sits in an unfriendly sign")
        elif c["relation"] == "Debilitated":
            score -= 2
            reasons.append(f"its ruler {lord} is weak (debilitated)")
        lh = pl[lord]["house"]
        if h not in (6, 8, 12):
            if lh in (1, 4, 5, 7, 9, 10, 11):
                score += 1
                reasons.append(f"{lord} is placed in the {ordinal(lh)} house, a helpful spot")
            elif lh in (6, 8, 12):
                score -= 1
                reasons.append(f"{lord} is placed in the {ordinal(lh)} house, a tougher spot")
        occupants = [p for p in BODIES if pl[p]["house"] == h]
        good_occ = [p for p in occupants if p in ("Jupiter", "Venus", "Mercury", "Moon")]
        bad_occ = [p for p in occupants if p in ("Saturn", "Mars", "Rahu", "Ketu", "Sun")]
        if good_occ and h not in (6, 8, 12):
            score += 1
            reasons.append(f"{_list(good_occ)} bring support from inside the house")
        if bad_occ and h not in (3, 6, 10, 11):
            score -= 1
            reasons.append(f"{_list(bad_occ)} add pressure from inside the house")
        elif bad_occ:
            score += 1
            reasons.append(f"{_list(bad_occ)} can do well here")
        helpers = [q for q in aspected_by_house(chart, h) if q in ("Jupiter", "Venus")]
        if helpers:
            score += 1
            reasons.append(f"{_list(helpers)} look at it kindly")
        pts = sav[sign]
        if pts >= 30:
            score += 1
            reasons.append(f"the sign has a high support score ({pts} points)")
        elif pts <= 22:
            score -= 1
            reasons.append(f"the sign has a low support score ({pts} points)")
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
    parts = ["--- Your 12 houses at a glance ---\nEach house is one area of life. For each: is it looking good, mixed or in need of "
             "care, and what may happen. [In simple terms: this is the quick overview - the sections below explain each area "
             "in more depth.]"]
    for v in house_verdicts(chart):
        why = ("Because " + "; ".join(v["reasons"]) + ".") if v["reasons"] else "Nothing special helps or hurts it."
        parts.append(f"{ordinal(v['house'])} house ({v['area']}): {v['tone']}. {v['may_happen']} {why}")
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
    return ("--- Where you are right now ---\n"
            f"Your main life period (Mahadasha) is {o['mahadasha']}, which looks {o['maha_tone'].lower()} in your chart. "
            f"What may happen: {o['maha_effects']}\n\n"
            f"Inside it you are in the {o['antardasha']} sub-period (Antardasha), which looks {o['antar_tone'].lower()}. "
            f"What may happen: {o['antar_effects']}\n\n"
            f"[In simple terms: the {o['mahadasha']} season sets the general mood of these years and the {o['antardasha']} "
            "sub-period is the weather within it. These are tendencies, not fixed events.]")


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
_ASPECT_PLAIN = {
    "blend": "these two energies mix together and act as one, for better or worse depending on the planets",
    "easy": "these two energies support each other, so this area tends to run smoothly",
    "tense": "these two energies pull against each other, which can feel like friction but also drives action",
}


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
    return {12: "Sade Sati - rising phase", 1: "Sade Sati - peak phase", 2: "Sade Sati - setting phase",
            4: "Dhaiya (Saturn in the 4th from Moon)", 8: "Dhaiya (Saturn in the 8th from Moon)"}.get(house_from_moon)


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
        eased_by.append("Mars is in a strong sign of its own or exaltation")
    _asp, _by = _aspects_on(chart)
    if "Jupiter" in _by["Mars"]:
        eased_by.append("Jupiter looks at Mars and softens it")
    if not hit:
        out.append(_dosha("Manglik (Mangal) Dosha", False, "Not present",
                          "Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house from the Lagna, Moon or Venus.",
                          "Nothing to worry about here - Mars does not sit in a tense marriage house.",
                          "", "Good", "Mars is not in a sensitive place, so this worry does not apply to you."))
    else:
        strength = "stronger" if len(hit) >= 2 else "mild"
        tone = "Needs some care" if len(hit) >= 2 else "Mixed"
        out.append(_dosha("Manglik (Mangal) Dosha", True, f"Present ({strength}) - counted from {_list(hit)}",
                          "Mars sits in the 1st, 2nd, 4th, 7th, 8th or 12th house counted from " + _list(hit) + ".",
                          "It may bring a hot temper, quick reactions or delays and friction in marriage or close partnerships. "
                          "Many people with it have happy marriages, and it is traditionally seen as balanced when the partner also has it.",
                          ("It may be eased because " + _list(eased_by) + ". ") if eased_by else
                          "Patience, calm talk and choosing a partner who understands your fire usually help.",
                          tone, "Mars is in a sensitive spot, so relationships may need extra patience - it is a tendency, not a fixed fate."))

    # Kalsarpa
    ks = kalsarpa(chart)
    if ks["full"]:
        out.append(_dosha("Kalsarpa Dosha", True, f"Present - {ks['type']} type",
                          "All seven main planets fall on one side of the Rahu-Ketu axis.",
                          "It may bring ups and downs, delays or a feeling of being held back in some years, and often progress comes in bursts. "
                          "Its strength depends a lot on the rest of the chart.",
                          "Steady effort, helping others and spiritual practice are the usual advice.",
                          "Needs some care", f"Because all planets are on one side of Rahu and Ketu, life may feel eventful ({ks['type']} type)."))
    elif ks["partial"]:
        out.append(_dosha("Kalsarpa Dosha", False, "Not fully present (partial)",
                          "All planets except " + _list(ks["odd_ones"]) + " are on one side of the Rahu-Ketu axis.",
                          "The classical pattern is not complete, so its effect is usually mild or absent.",
                          "", "Mostly good", "Almost, but not fully, formed - usually nothing to worry about."))
    else:
        out.append(_dosha("Kalsarpa Dosha", False, "Not present",
                          "All seven main planets on one side of the Rahu-Ketu axis.",
                          "Your planets are spread on both sides of the axis, so this pattern does not apply.",
                          "", "Good", "Your chart is free from this."))

    # Pitra dosha
    pd = assess_pitra_dosha(chart)
    flags = [k for k in ("rahu_ketu_in_9th", "sun_conjunct_rahu_ketu", "ninth_lord_afflicted") if pd[k]["present"]]
    if flags:
        out.append(_dosha("Pitra Dosha (ancestral pattern)", True, "Present (some signs)",
                          " ".join(pd[k]["detail"] for k in flags),
                          "It may show up as delays in luck, or family patterns you feel you are working through. Not every source agrees on this rule.",
                          "Respecting elders, charity in the family's name and steady effort are the traditional advice.",
                          "Mixed", "There are some signs of an ancestral pattern - read it as a gentle nudge to care for family roots."))
    else:
        out.append(_dosha("Pitra Dosha (ancestral pattern)", False, "Not present",
                          "The 9th house, its lord or the Sun being troubled by Rahu, Ketu or harsh planets.",
                          "None of the usual signs are present.", "", "Good", "Nothing here to worry about."))

    # Guru Chandal
    gc = assess_guru_chandal_dosha(chart)
    out.append(_dosha("Guru Chandal Dosha", gc["present"], "Present" if gc["present"] else "Not present",
                      "Jupiter together with Rahu.",
                      ("Your wisdom and beliefs may be pulled toward unusual ideas, and you may question teachers or traditions. "
                       "It can also make you a bold, original thinker.") if gc["present"] else "Jupiter and Rahu are not together.",
                      "Choosing guides carefully and checking advice against your own values helps." if gc["present"] else "",
                      "Mixed" if gc["present"] else "Good",
                      "Your wisdom planet is mixed with a restless one - worth choosing teachers wisely." if gc["present"] else
                      "Jupiter and Rahu are apart, so this worry does not apply to you."))

    # Grahan
    gr = assess_grahan_dosha(chart)
    for key, lum, label in (("surya_grahan", "Sun", "Surya Grahan Dosha (Sun-Rahu/Ketu)"),
                            ("chandra_grahan", "Moon", "Chandra Grahan Dosha (Moon-Rahu/Ketu)")):
        r = gr[key]
        out.append(_dosha(label, r["present"], "Present" if r["present"] else "Not present",
                          f"The {lum} together with Rahu or Ketu.",
                          (("Confidence or father-related matters may feel shadowed at times." if lum == "Sun" else
                            "Your mind may feel clouded or anxious at times.") + " Effects depend on the rest of the chart.")
                          if r["present"] else f"The {lum} is clear of the Rahu-Ketu shadow.",
                          ("Sun: sun-gazing at sunrise, confidence-building routines. " if lum == "Sun" else
                           "Calming routines, sleep and time in nature. ") if r["present"] else "",
                          "Mixed" if r["present"] else "Good",
                          (f"The {lum} is close to Rahu or Ketu, so it can feel shadowed at times - a tendency, not a fixed result."
                           if r["present"] else f"The {lum} is clear of Rahu and Ketu, so this worry does not apply to you.")))

    # Shrapit
    sp = assess_shrapit_dosha(chart)
    out.append(_dosha("Shrapit Dosha", sp["present"], "Present" if sp["present"] else "Not present",
                      "Saturn together with Rahu.",
                      ("Delays may pile on delays, and you may feel stuck or face sudden reversals in some years. "
                       "It is a tendency that steady effort tends to soften.") if sp["present"] else "Saturn and Rahu are not together.",
                      "Discipline, honesty and service to others are the classic remedies." if sp["present"] else "",
                      "Needs some care" if sp["present"] else "Good",
                      "Saturn and Rahu are together, so patience matters." if sp["present"] else
                      "Saturn and Rahu are apart, so this worry does not apply to you."))

    # Saturn's current phase
    now = sade_sati_now(chart, at)
    kind = now["kind"]
    if kind and kind.startswith("Sade"):
        gist = {"rising": "It starts gently - expenses, worries about the future and a sense of pressure may build.",
                "peak": "This is the heaviest stretch - responsibilities, slowdowns and lessons about patience may feel strongest.",
                "setting": "It is easing - things may slowly settle, with some last tests around money and family."}
        phase = kind.split("- ")[1].split()[0]
        out.append(_dosha("Sade Sati (now)", True, f"Running - {kind.split('- ')[1]}",
                          "Saturn passes over the sign before, the sign of, and the sign after your natal Moon, about 7.5 years.",
                          gist[phase] + " Many people find it also brings maturity, discipline and lasting progress.",
                          "Patience, routine, honesty and helping others are the standard advice.", "Needs some care",
                          "Saturn is testing you now, but this is a strict-teacher phase, not a punishment."))
    elif kind:
        out.append(_dosha("Dhaiya (now)", True, f"Running - {kind}",
                          "Saturn spends about 2.5 years in the 4th or 8th sign from your Moon.",
                          "You may feel extra pressure around home, peace of mind, health or sudden events. It usually passes with steady effort.",
                          "Routine, patience and looking after health.", "Mixed", "A smaller Saturn phase - manageable with steady habits."))
    else:
        out.append(_dosha("Sade Sati / Dhaiya (now)", False, "Not running",
                          "Saturn is not currently in a sensitive place from your Moon.",
                          "Saturn's heavier lessons are not pressing on you right now.", "", "Good",
                          "You are not in a Saturn testing phase at the moment."))
    return out


def doshas_text(chart, at=None):
    parts = []
    for d in assess_doshas(chart, at):
        label = "What may happen" if d["present"] else "What this means"     # an absent dosha has nothing to "happen"
        body = (f"Verdict: {d['tone']} - {d['status']}.\n\nWhat it is: {d['what']}\n\n{label}: {d['may_happen']}")
        if d["easing"]:
            body += f"\n\nWhat can help: {d['easing']}"
        body += f"\n\n[In simple terms: {d['plain']}]"
        parts.append(f"--- {d['name']} ---\n{body}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- lifetime Sade Sati / Dhaiya table
_SATURN_PHASES = {12: ("Sade Sati", "rising phase"), 1: ("Sade Sati", "peak phase"), 2: ("Sade Sati", "setting phase"),
                  4: ("Dhaiya (Small Panoti)", "Saturn in the 4th from Moon"), 8: ("Dhaiya (Small Panoti)", "Saturn in the 8th from Moon")}
_PHASE_PLAIN = {
    "rising phase": "worries and expenses may start to build; a slow warm-up",
    "peak phase": "the heaviest stretch - responsibilities and patience are tested, and growth often follows",
    "setting phase": "pressure eases and things settle, with a few last tests",
    "Saturn in the 4th from Moon": "home, mother or peace of mind may need attention",
    "Saturn in the 8th from Moon": "sudden changes and health care may need attention",
}


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
    lines = ["Sade Sati is Saturn's roughly 7.5-year walk over the sign before, the sign of and the sign after your Moon; "
             "Dhaiya (also called Small Panoti) is its 2.5-year stay in the 4th or 8th sign from your Moon. Both are read as "
             "times that test patience and reward steady work, not as fixed bad news. Saturn sometimes steps back into the "
             "earlier sign for a few months (it moves backwards for a while each year), so a phase can appear twice. "
             "Dates are approximate (a few days either way)."]
    for r in rows:
        lines.append(f"{r['kind']} - {r['phase']}: {r['start']:%d %b %Y} to {r['end']:%d %b %Y} "
                     f"(age {max(r['start_age'], 0):.0f} to {r['end_age']:.0f}). Likely feel: {r['plain']}.")
    return "\n\n".join(lines)


# ---------------------------------------------------------------- one call for everything
def compute_extras(chart, at=None):
    return {
        "considerations": planet_considerations(chart), "friendship": friendship_tables(chart),
        "aspects": western_aspects(chart), "doshas": assess_doshas(chart, at),
        "sade_sati": sade_sati_table(chart), "shodashvarga": shodashvarga_table(chart),
    }
