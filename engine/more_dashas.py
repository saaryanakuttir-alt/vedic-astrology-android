"""more_dashas.py - a second and third planetary-period system (Yogini Dasha, Jaimini Char Dasha), the
Jaimini significators with the Karakamsa chart, and plain-words verdicts for every Vimshottari
Mahadasha. Everything is derived from the chart dict; wording follows extras.py (tendencies, never
fixed events; nothing about lifespan or children).
"""
import copy
import datetime as _dt

from extras import (BODIES, _EFFECTS, _HOUSE_AREA, _TONE_PHRASE, ordinal, planet_considerations)
from astrology_tables import SIGN_LORD
from panchanga import SIGNS
from i18n import join_list, tbl, tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

DAY = 365.25
_ONE_DAY = _dt.timedelta(days=1)


def _birth(chart):
    return _dt.datetime.fromisoformat(chart["resolved_datetime"]["utc"]).replace(tzinfo=None)


def _naive(v):
    v = _dt.datetime.fromisoformat(v) if isinstance(v, str) else v
    return v.replace(tzinfo=None) if v.tzinfo else v


def _add_years(t, years):
    return t + _dt.timedelta(days=years * DAY)


# ---------------------------------------------------------------- Yogini Dasha (36-year cycle)
YOGINIS = [("Mangala", "Ma", 1), ("Pingala", "Pi", 2), ("Dhanya", "Dh", 3), ("Bhramari", "Br", 4),
           ("Bhadrika", "Ba", 5), ("Ulka", "Ul", 6), ("Siddha", "Si", 7), ("Sankata", "Sn", 8)]
_YOGINI_MEANING = tbl({
    "Mangala": "good fortune and auspicious beginnings", "Pingala": "some stress, ups and downs and effort",
    "Dhanya": "money, comfort and growth", "Bhramari": "restlessness, travel and changes",
    "Bhadrika": "steady progress and gains through work", "Ulka": "pressure, hard work and testing times",
    "Siddha": "achievement, success and recognition", "Sankata": "obstacles and a need for patience",
})


def yogini_dasha(chart, years=100):
    """[{name, code, years, start, end, antardashas: [{name, code, start, end}]}] from birth to `years`."""
    birth = _birth(chart)
    moon = chart["planets"]["Moon"]
    span = 360.0 / 27
    nak = int(moon["longitude"] // span) + 1                     # 1 = Ashwini
    idx = (nak + 3) % 8 or 8                                       # 1..8 -> Mangala..Sankata
    idx -= 1
    left = 1 - (moon["longitude"] % span) / span                   # share of the first period still to run
    out = []
    t = birth - _dt.timedelta(days=YOGINIS[idx][2] * (1 - left) * DAY)      # when the first period began
    limit = _add_years(birth, years)
    while t < limit:
        name, code, yrs = YOGINIS[idx]
        end = _add_years(t, yrs)
        subs, s = [], t
        for k in range(8):
            n2, c2, y2 = YOGINIS[(idx + k) % 8]
            e = _add_years(s, yrs * y2 / 36.0)
            if e > birth:
                subs.append({"name": n2, "code": c2, "start": max(s, birth), "end": e})
            s = e
        out.append({"name": name, "code": code, "years": yrs, "start": max(t, birth), "end": end,
                    "true_start": t, "antardashas": subs})
        t, idx = end, (idx + 1) % 8
    return out


# ---------------------------------------------------------------- Jaimini Char Dasha
_DIRECT_SEQUENCE = {"Aries", "Taurus", "Cancer", "Libra", "Sagittarius", "Aquarius"}   # others run backwards
_SAVYA_COUNT = {"Aries", "Taurus", "Gemini", "Libra", "Scorpio", "Sagittarius"}        # count years forwards
_CO_LORD = {"Scorpio": ("Mars", "Ketu"), "Aquarius": ("Saturn", "Rahu")}


def _char_lord(chart, sign):
    """The ruler used to count the years; for Scorpio and Aquarius the stronger of the two rulers
    (more planets with it, then one not in a 6th/8th/12th place from the sign, then the higher degree)."""
    if sign not in _CO_LORD:
        return SIGN_LORD[sign]
    pl = chart["planets"]

    def key(p):
        crowd = sum(1 for q in BODIES if q != p and pl[q]["sign"] == pl[p]["sign"])
        away = (SIGNS.index(pl[p]["sign"]) - SIGNS.index(sign)) % 12 + 1
        return (crowd, away not in (6, 8, 12), pl[p]["degree_in_sign"])

    return max(_CO_LORD[sign], key=key)


def _char_years(chart, sign):
    lord = _char_lord(chart, sign)
    ls, s = SIGNS.index(chart["planets"][lord]["sign"]), SIGNS.index(sign)
    count = ((ls - s) % 12 + 1) if sign in _SAVYA_COUNT else ((s - ls) % 12 + 1)
    return (count - 1) or 12


def char_dasha(chart):
    """The 12 Char Mahadashas from the Lagna sign, each with its 12 sign sub-periods."""
    birth = _birth(chart)
    lagna = chart["ascendant"]["sign"]
    step = 1 if lagna in _DIRECT_SEQUENCE else -1
    out, t = [], birth
    for k in range(12):
        sign = SIGNS[(SIGNS.index(lagna) + step * k) % 12]
        yrs = _char_years(chart, sign)
        subs, s = [], t
        for j in range(1, 13):
            e = _add_years(s, yrs / 12.0)
            subs.append({"sign": SIGNS[(SIGNS.index(sign) + step * j) % 12], "start": s, "end": e})
            s = e
        out.append({"sign": sign, "years": yrs, "start": t, "end": _add_years(t, yrs), "antardashas": subs})
        t = _add_years(t, yrs)
    return out


# ---------------------------------------------------------------- Jaimini significators and Karakamsa
_KARAKA_ROLES = tbl([("Atmakaraka", "the soul - your core drive"), ("Amatyakaraka", "career and advisers"),
                 ("Bhratrukaraka", "brothers, sisters and courage"), ("Matrukaraka", "mother and inner peace"),
                 ("Putrakaraka", "intellect and creativity"), ("Gnatikaraka", "relatives and rivals"),
                 ("Darakaraka", "spouse and partnerships")])
_FIXED_KARAKA = ["Sun", "Mercury", "Mars", "Moon", "Jupiter", "Saturn", "Venus"]       # Sthira karakas, same role order
_KARAKAMSA_TRAIT = tbl({
    "Aries": "a bold, self-starting way of following your purpose", "Taurus": "steady, practical, comfort-loving aims",
    "Gemini": "curious, communicative and skill-based aims", "Cancer": "caring, home- and people-centred aims",
    "Leo": "leadership, recognition and a wish to shine in your own right", "Virgo": "service, detail and useful skills",
    "Libra": "fairness, partnership and beauty", "Scorpio": "depth, research and transformation",
    "Sagittarius": "learning, teaching and higher ideals", "Capricorn": "discipline, structure and long-term achievement",
    "Aquarius": "ideas, groups and doing things differently", "Pisces": "imagination, compassion and spiritual leanings",
})


def karakas(chart):
    """The seven Chara karakas: planets ranked by degree within their sign (highest = Atmakaraka)."""
    ranked = sorted(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"],
                    key=lambda p: -chart["planets"][p]["degree_in_sign"])
    return [{"role": r, "meaning": m, "chara": p, "sthira": f}
            for (r, m), p, f in zip(_KARAKA_ROLES, ranked, _FIXED_KARAKA)]


def karakamsa_sign(chart):
    """The Atmakaraka's sign in the Navamsha (D9) chart."""
    return chart["planets"][karakas(chart)[0]["chara"]]["vargas"]["D9"]


def with_karakamsa(chart):
    """A copy of `chart` with a 'KM' divisional view: the birth-chart planets counted from the Karakamsa sign."""
    c = copy.deepcopy(chart)
    c["ascendant"]["vargas"]["KM"] = karakamsa_sign(chart)
    for p in c["planets"].values():
        p["vargas"]["KM"] = p["sign"]
    return c


def karakamsa_text(chart):
    ks, ak = karakamsa_sign(chart), karakas(chart)[0]["chara"]
    house_of = lambda s: (SIGNS.index(s) - SIGNS.index(ks)) % 12 + 1
    inside = [p for p in BODIES if house_of(chart["planets"][p]["sign"]) == 1]
    twelfth = [p for p in BODIES if house_of(chart["planets"][p]["sign"]) == 12]
    bits = [tr("Your Atmakaraka (the planet that stands for your soul's drive) is {0}. Its sign in the Navamsha "
               'chart, {1}, is your Karakamsa. It points to {2}.', ak, ks, _KARAKAMSA_TRAIT[ks])]
    bits.append(tr("Planets sitting in the Karakamsa sign: {0}. Planets in the house just before it: {1}.",
                   join_list(inside) if inside else tx("none"), join_list(twelfth) if twelfth else tx("none")))
    if any(p in ("Jupiter", "Venus", "Mercury", "Moon") for p in inside):
        bits.append(tx("A gentle planet inside the Karakamsa may make it easier to follow your purpose with support from others."))
    elif any(p in ("Saturn", "Mars", "Rahu", "Ketu", "Sun") for p in inside):
        bits.append(tx("A strong or restless planet inside the Karakamsa may make your path more intense and self-driven."))
    bits.append(tx("[In simple terms: the Karakamsa is a hint about the kind of life goals that feel most 'you'. It is a tendency to reflect on, "
                "not a prediction.]"))
    return "\n\n".join(bits)


# ---------------------------------------------------------------- plain words for each Vimshottari Mahadasha
def mahadasha_text(chart, at=None):
    """A verdict paragraph for every Mahadasha; the running one also lists its sub-periods."""
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    cons = planet_considerations(chart)
    birth = _birth(chart)
    fmt = lambda d: tr('{0:%d %b %Y}', d)

    def line(p, s, e, label):
        c = cons[p]
        area = _HOUSE_AREA[c["house"]]
        idx = {"Good": 0, "Mostly good": 0, "Mixed": 1, "Needs some care": 2, "Challenging": 2}[c["tone"]]
        return (tr('{0} ({1} to {2}): {3} {4} in your chart and sits in your {5} house, so this time is felt mostly '
                   'through {6}. What may happen: {7}', label, fmt(s), fmt(e), p, _TONE_PHRASE[c['tone']], ordinal(c['house']), area, _EFFECTS[p][idx]))

    parts = [tx("--- What each Mahadasha may feel like ---\nEach long life period takes the mood of its ruling planet. Below, "
             "each one is rated Good, Mixed or Needs care from how that planet is placed in YOUR chart, with what may happen. "
             "[In simple terms: think of these as the seasons of your life. None is fixed - they describe likely moods and themes.]")]
    for m in chart["dasha"]["timeline"]:
        s, e = max(_naive(m["start"]), birth), _naive(m["end"])
        now = " - running now" if _naive(m["start"]) <= at < e else ""
        parts.append(tr('--- {0} Mahadasha{1} ---\n', m['lord'], now) + line(m["lord"], s, e, tr('{0} period', m['lord'])))
        if now:
            subs = [tr('- {0}', line(a['lord'], _naive(a['start']), _naive(a['end']), tr('{0} sub-period', a['lord'])))
                    for a in m["antardashas"] if _naive(a["end"]) > at]
            parts.append(tx("Sub-periods still to come inside this Mahadasha:\n\n") + "\n\n".join(subs[:9]))
    return "\n\n".join(parts)
