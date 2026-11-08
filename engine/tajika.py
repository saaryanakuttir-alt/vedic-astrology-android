"""tajika.py - the Tajika extras of the yearly chart (Varshaphal): sign-based Tajika aspects, the sixteen Tajika
yogas, Pancha-vargiya bala, the five office-bearers and the lord of the year (Varshesh), and the Sahams.

Tajika is a separate system from the Parashari knowledge base; its tables live in kb/tajika_rules.json with
their sources (Balabhadra's Hayanaratna in Martin Gansten's translation, Tajika Neelakanthi as followed by
B. V. Raman). Wording is always a tendency for the year, never a fixed event.
"""
import json
import os

from astrology_tables import DEBILITATION_SIGN, EXALTATION_SIGN, OWN_SIGNS, SIGN_LORD
from combustion import is_combust
from divisional import d9_navamsa
from panchanga import SIGNS

_KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb", "tajika_rules.json")
_DATA = None
SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
BENEFICS = ("Jupiter", "Venus", "Mercury", "Moon")
MALEFICS = ("Mars", "Saturn")
KENDRA_PANAPHARA = {1, 2, 4, 5, 7, 8, 10, 11}
APOKLIMA = {3, 6, 9, 12}


def data():
    global _DATA
    if _DATA is None:
        with open(_KB, encoding="utf-8") as fh:
            _DATA = json.load(fh)
    return _DATA


def _sign_idx(lon):
    return int((lon % 360) // 30)


def _deg(lon):
    return (lon % 360) % 30


def sign_distance(from_lon, to_lon):
    """1-12: the sign of `to_lon` counted from the sign of `from_lon`."""
    return (_sign_idx(to_lon) - _sign_idx(from_lon)) % 12 + 1


def tajika_aspect(from_lon, to_lon):
    """(name, nature) of the Tajika aspect between two points by sign, or None (2/12 and 6/8 signs apart)."""
    a = data()["aspects"].get(str(sign_distance(from_lon, to_lon)))
    return tuple(a) if a else None


def faster(a, b):
    order = data()["speed_order"]
    return (a, b) if order.index(a) < order.index(b) else (b, a)


def orb(a, b):
    d = data()["deeptamsa"]
    return (d[a] + d[b]) / 2.0


# ---------------------------------------------------------------- Ithasala / Ishrafa
def relation(pl, a, b):
    """Ithasala / Ishrafa between planets a and b (any order) in the planet table `pl` ({name: {longitude, retrograde}}).
    Returns None or {fast, slow, kind ("Ithasala"/"Ishrafa"), type ("poorna"/"vartamana"/"bhavishyat"/None),
    aspect, nature, gap, limit}."""
    fast, slow = faster(a, b)
    lf, ls = pl[fast]["longitude"], pl[slow]["longitude"]
    limit = orb(fast, slow)
    asp = tajika_aspect(lf, ls)
    df, ds = _deg(lf), _deg(ls)
    if asp:
        if df <= ds and ds - df <= limit:
            if pl[fast].get("retrograde"):
                return None                                       # a retrograde faster planet behind gives no Ithasala
            gap = ds - df
            return {"fast": fast, "slow": slow, "kind": "Ithasala", "type": "poorna" if gap <= 1.0 else "vartamana",
                    "aspect": asp[0], "nature": asp[1], "gap": round(gap, 2), "limit": limit}
        if df - ds >= 1.0 and df - ds <= limit:
            return {"fast": fast, "slow": slow, "kind": "Ishrafa", "type": None, "aspect": asp[0], "nature": asp[1],
                    "gap": round(df - ds, 2), "limit": limit}
        if 0 < df - ds < 1.0:                                     # passed by less than a degree: still Ithasala
            return {"fast": fast, "slow": slow, "kind": "Ithasala", "type": "poorna", "aspect": asp[0], "nature": asp[1],
                    "gap": round(df - ds, 2), "limit": limit}
    # Bhavishyat (future) Ithasala: the faster planet is at the end of its sign and, on entering the next sign, will
    # apply to the slower planet within orbs
    nxt = (lf - df + 30) % 360
    asp2 = tajika_aspect(nxt, ls)
    if asp2 and not pl[fast].get("retrograde") and (30 - df) + ds <= limit:
        return {"fast": fast, "slow": slow, "kind": "Ithasala", "type": "bhavishyat", "aspect": asp2[0], "nature": asp2[1],
                "gap": round((30 - df) + ds, 2), "limit": limit}
    return None


def all_relations(pl):
    out = []
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1:]:
            r = relation(pl, a, b)
            if r:
                out.append(r)
    out.sort(key=lambda r: r["gap"])
    return out


def ithasala(pl, a, b):
    r = relation(pl, a, b) if a != b else None
    return r if r and r["kind"] == "Ithasala" else None


# ---------------------------------------------------------------- dignity and Pancha-vargiya bala
def _relation_grade(planet, lord, pl):
    """0 own, 1 friend, 2 neutral, 3 enemy. Tajika friendship by aspect in the yearly chart (Hayanaratna 2.4, first
    scheme): the lord in the 3rd, 5th, 9th or 11th sign from the planet is a friend, in the same, 4th, 7th or 10th an
    enemy, in the 2nd, 6th, 8th or 12th neutral."""
    if planet == lord:
        return 0
    d = sign_distance(pl[planet]["longitude"], pl[lord]["longitude"])
    return 1 if d in (3, 5, 9, 11) else (3 if d in (1, 4, 7, 10) else 2)


def hadda_lord(lon):
    pos = 0.0
    for lord, span in data()["hadda"][SIGNS[_sign_idx(lon)]]:
        pos += span
        if _deg(lon) < pos:
            return lord
    return data()["hadda"][SIGNS[_sign_idx(lon)]][-1][0]


def drekkana_lord(lon):
    return data()["drekkana"][SIGNS[_sign_idx(lon)]][min(int(_deg(lon) // 10), 2)]


def uchcha_bala(planet, lon):
    sign, deg = data()["exaltation_degree"][planet]
    fall = (SIGNS.index(sign) * 30 + deg + 180) % 360
    d = abs((lon - fall + 180) % 360 - 180)
    return d / 9.0


def pancha_vargiya(planet, pl):
    """{kshetra, uchcha, hadda, drekkana, navamsa, total (out of 20), rating} for a planet of the yearly chart
    (`pl` = its planets table). Friend / neutral / enemy is the compound relationship in that chart."""
    pts = data()["dignity_points"]
    lon = pl[planet]["longitude"]
    sign = SIGNS[_sign_idx(lon)]
    k = pts["kshetra"][_relation_grade(planet, SIGN_LORD[sign], pl)]
    h = pts["hadda"][_relation_grade(planet, hadda_lord(lon), pl)]
    dr = pts["drekkana"][_relation_grade(planet, drekkana_lord(lon), pl)]
    nav_sign = d9_navamsa(lon)
    n = pts["navamsa"][_relation_grade(planet, SIGN_LORD[nav_sign], pl)]
    u = uchcha_bala(planet, lon)
    total = (k + h + dr + n + u) / 4.0
    rating = "strong" if total > 10 else ("weak" if total < 5 else "middling")
    return {"kshetra": k, "uchcha": round(u, 2), "hadda": h, "drekkana": dr, "navamsa": n, "total": round(total, 2), "rating": rating}


# ---------------------------------------------------------------- the year's houses, day/night
def _house(lon, asc_lon):
    return (_sign_idx(lon) - _sign_idx(asc_lon)) % 12 + 1


def is_day(varsha):
    """True when the Sun is above the horizon at the moment of the yearly chart (between the descendant and the
    ascendant through the midheaven)."""
    return (varsha["planets"]["Sun"]["longitude"] - varsha["ascendant"]["longitude"]) % 360 > 180


def _aspects_lagna(pl, planet, asc_lon):
    return tajika_aspect(pl[planet]["longitude"], asc_lon) is not None


# ---------------------------------------------------------------- the five office-bearers and Varshesh
def office_bearers(chart, varsha, muntha_sign):
    day = is_day(varsha)
    vlag = varsha["ascendant"]["sign"]
    sun_s, moon_s = varsha["planets"]["Sun"]["sign"], varsha["planets"]["Moon"]["sign"]
    return [("Muntha lord", SIGN_LORD[muntha_sign]),
            ("Birth ascendant lord", SIGN_LORD[chart["ascendant"]["sign"]]),
            ("Year ascendant lord", SIGN_LORD[vlag]),
            ("Tri-rashi lord", data()["trirashi"][vlag][0 if day else 1]),
            ("Day/night lord", SIGN_LORD[sun_s if day else moon_s])]


def varshesh(chart, varsha, muntha_sign):
    """{"lord", "reason", "bearers": [{office, planet, bala, aspects_lagna}], "day"}."""
    pl = varsha["planets"]
    asc = varsha["ascendant"]["longitude"]
    rows = []
    for office, planet in office_bearers(chart, varsha, muntha_sign):
        rows.append({"office": office, "planet": planet, "bala": pancha_vargiya(planet, pl),
                     "aspects_lagna": _aspects_lagna(pl, planet, asc)})
    muntha_lord = rows[0]["planet"]
    order = {p: i for i, p in enumerate(r["planet"] for r in rows)}           # ties go to the earlier office (Muntha lord first)
    aspecting = sorted({r["planet"]: r for r in rows if r["aspects_lagna"]}.values(),
                       key=lambda r: (-r["bala"]["total"], order[r["planet"]]))
    non_moon = [r for r in aspecting if r["planet"] != "Moon"]
    if aspecting and all(r["bala"]["total"] < 5 for r in rows):
        lord, reason = muntha_lord, "all_weak"
    elif non_moon:
        lord, reason = non_moon[0]["planet"], "strongest_aspecting"
    elif aspecting:
        lord, reason = aspecting[0]["planet"], "moon_only"
    else:
        lord, reason = muntha_lord, "none_aspects"
    return {"lord": lord, "reason": reason, "bearers": rows, "day": is_day(varsha)}


# ---------------------------------------------------------------- Sahams
def _between(c, b, a):
    """True when point c lies on the zodiacal arc going forward from b to a."""
    return (c - b) % 360 <= (a - b) % 360


def _bhava_madhyas(varsha):
    from chalit import compute_bhava_madhyas
    return compute_bhava_madhyas(varsha["ascendant"]["longitude"], varsha["ascendant"]["mc_longitude"])


def sahams(varsha):
    """[{name, meaning, longitude, sign, degree, house, lord, lord_house, lord_aspects, verdict}] for the yearly chart."""
    pl = varsha["planets"]
    asc = varsha["ascendant"]["longitude"]
    day = is_day(varsha)
    madhya = _bhava_madhyas(varsha)
    pts = {p: pl[p]["longitude"] for p in SEVEN}
    pts["Asc"] = asc
    pts["AscLord"] = pl[SIGN_LORD[varsha["ascendant"]["sign"]]]["longitude"]
    pts["Cancer15"] = 105.0
    for h in (2, 9, 11):
        pts[f"H{h}"] = madhya[h - 1]
        pts[f"H{h}Lord"] = pl[SIGN_LORD[SIGNS[_sign_idx(madhya[h - 1])]]]["longitude"]
    pts["SunSignLord"] = pl[SIGN_LORD[pl["Sun"]["sign"]]]["longitude"]
    pts["MoonSignLord"] = pl[SIGN_LORD[pl["Moon"]["sign"]]]["longitude"]
    out, done = [], {}
    for s in data()["sahams"]:
        a, b, c = s["a"], s["b"], s["c"]
        if s["name"] == "Samartha" and SIGN_LORD[varsha["ascendant"]["sign"]] == "Mars":
            a, b = "Jupiter", "Mars"                                # Mars rules the ascendant: Mars to Jupiter
        if not day:
            if s["night"] == "reverse":
                a, b = b, a
            elif s["night"] == "gaurava":
                b, c = "Sun", "Moon"
            elif s["night"] == "karyasiddhi":
                b, c = "Moon", "MoonSignLord"
        va, vb, vc = (done.get(x, pts.get(x)) for x in (a, b, c))
        lon = (va - vb + vc) % 360
        if not _between(vc, vb, va):
            lon = (lon + 30) % 360
        done[s["name"]] = lon
        sign = SIGNS[_sign_idx(lon)]
        lord = SIGN_LORD[sign]
        lord_house = _house(pl[lord]["longitude"], asc)
        looks = tajika_aspect(pl[lord]["longitude"], lon) is not None
        score = (1 if looks else 0) + (1 if lord_house in (1, 2, 4, 5, 7, 9, 10, 11) else 0) \
            + (1 if pancha_vargiya(lord, pl)["total"] >= 10 else 0) - (1 if lord_house in (6, 8, 12) else 0) \
            - (1 if _combust(pl, lord) or (pl[lord].get("retrograde") and lord not in ("Sun", "Moon")) else 0)
        verdict = "supported" if score >= 3 else ("care" if score <= 0 else "mixed")
        out.append({"name": s["name"], "meaning": s["meaning"], "longitude": lon, "sign": sign, "degree": round(_deg(lon), 2),
                    "house": _house(lon, asc), "lord": lord, "lord_house": lord_house, "lord_aspects": looks, "verdict": verdict,
                    "malefic": bool(s.get("malefic"))})
    return out


# ---------------------------------------------------------------- the sixteen yogas
def _dignified(planet, lon):
    sign = SIGNS[_sign_idx(lon)]
    return sign in OWN_SIGNS[planet] or EXALTATION_SIGN[planet] == sign


def _combust(pl, p):
    if p == "Sun":
        return False
    return is_combust(p, pl["Sun"]["longitude"], pl[p]["longitude"], bool(pl[p].get("retrograde")))


def _malefic_aspect(pl, p):
    """Mars or Saturn joins or aspects `p` by a Tajika aspect within orbs."""
    for m in MALEFICS:
        if m == p:
            continue
        if tajika_aspect(pl[m]["longitude"], pl[p]["longitude"]) and abs(_deg(pl[m]["longitude"]) - _deg(pl[p]["longitude"])) <= orb(m, p):
            return m
    return None


def _benefic_aspect(pl, p):
    for b in ("Jupiter", "Venus"):
        if b != p and tajika_aspect(pl[b]["longitude"], pl[p]["longitude"]) and \
                abs(_deg(pl[b]["longitude"]) - _deg(pl[p]["longitude"])) <= orb(b, p):
            return b
    return None


def planet_condition(varsha, p):
    """("kuttha" | "durupha" | None, [reasons]) for one planet of the yearly chart."""
    pl, asc = varsha["planets"], varsha["ascendant"]["longitude"]
    lon = pl[p]["longitude"]
    house = _house(lon, asc)
    bad = []
    if p != "Sun" and _combust(pl, p):
        bad.append("combust")
    if pl[p].get("retrograde") and p not in ("Sun", "Moon"):
        bad.append("retrograde")
    if house in (6, 8, 12):
        bad.append(f"house {house}")
    own = OWN_SIGNS[p]
    if any((_sign_idx(lon) - SIGNS.index(s)) % 12 == 6 for s in own):
        bad.append("7th from own sign")
    m = _malefic_aspect(pl, p)
    if m:
        bad.append(f"aspected by {m}")
    if bad:
        return "durupha", bad
    if _dignified(p, lon) and (house in (1, 4, 7, 10) or _aspects_lagna(pl, p, asc)):
        return "kuttha", ["own or exalted", "angle or aspects ascendant", "direct, not combust", "free of Mars and Saturn"]
    return None, []


def pair_yogas(varsha, a, b):
    """The Tajika yogas between significators a (ascendant lord) and b (lord of the matter). Returns a list of
    {"yoga", "detail"} dicts (possibly empty)."""
    pl, asc = varsha["planets"], varsha["ascendant"]["longitude"]
    found = []
    if a == b:
        return found
    rel = relation(pl, a, b)
    ith = rel if rel and rel["kind"] == "Ithasala" else None
    if rel:
        found.append({"yoga": rel["kind"], "detail": rel})
    if ith:
        fast, slow = ith["fast"], ith["slow"]
        moon_links = [x for x in (a, b) if x != "Moon" and ithasala(pl, "Moon", x)]
        if "Moon" in (a, b) or moon_links:
            found.append({"yoga": "Kambool", "detail": {"with": moon_links}})
        else:
            moon_seen = any(tajika_aspect(pl[x]["longitude"], pl["Moon"]["longitude"]) for x in (a, b))
            outside = [p for p in SEVEN if p not in (a, b, "Moon") and ithasala(pl, "Moon", p)
                       and _dignified(p, pl["Moon"]["longitude"])]
            if not moon_seen and outside:
                found.append({"yoga": "Gairi-kambool", "detail": {"with": outside}})
            elif not moon_seen:
                found.append({"yoga": "Khallasara", "detail": {}})
        order = data()["speed_order"]
        for m in MALEFICS:
            if m in (a, b) or order.index(m) <= order.index(fast):
                continue
            asp = tajika_aspect(pl[m]["longitude"], pl[fast]["longitude"])
            if asp and asp[1] == "inimical" and abs(_deg(pl[m]["longitude"]) - _deg(pl[fast]["longitude"])) <= data()["deeptamsa"][m]:
                found.append({"yoga": "Manau", "detail": {"by": m}})
                break
        hit = [x for x in (a, b) if (pl[x].get("retrograde") and x not in ("Sun", "Moon")) or _combust(pl, x)
               or _house(pl[x]["longitude"], asc) in (6, 8, 12)]
        if hit:
            found.append({"yoga": "Radda", "detail": {"planets": hit}})
        if _dignified(slow, pl[slow]["longitude"]) and not _dignified(fast, pl[fast]["longitude"]):
            found.append({"yoga": "Duhphali-kuttha", "detail": {"slow": slow}})
        if all(pancha_vargiya(x, pl)["total"] < 5 for x in (a, b)):
            found.append({"yoga": "Dutthottha-davira", "detail": {}})
    else:
        order = data()["speed_order"]
        for t in SEVEN:
            if t in (a, b):
                continue
            if ithasala(pl, t, a) and ithasala(pl, t, b):
                quicker = order.index(t) < min(order.index(a), order.index(b))
                slower = order.index(t) > max(order.index(a), order.index(b))
                if quicker:
                    found.append({"yoga": "Nakta", "detail": {"via": t}})
                elif slower:
                    found.append({"yoga": "Yamaya", "detail": {"via": t}})
        for x in (a, b):
            lon = pl[x]["longitude"]
            if _dignified(x, lon) and _deg(lon) >= 30 - data()["deeptamsa"][x] / 2.0:
                for t in SEVEN:
                    if t in (a, b) or not _dignified(t, pl[t]["longitude"]):
                        continue
                    r = ithasala(pl, x, t)
                    if r and r["type"] == "bhavishyat" and r["fast"] == x:
                        found.append({"yoga": "Tambira", "detail": {"from": x, "to": t}})
    return found


def ikkavala_induvara(varsha):
    asc = varsha["ascendant"]["longitude"]
    houses = {_house(varsha["planets"][p]["longitude"], asc) for p in SEVEN}
    if houses <= KENDRA_PANAPHARA:
        return "Ikkavala"
    if houses <= APOKLIMA:
        return "Induvara"
    return None


def house_yogas(varsha):
    """For each house 2-12: {house, lord, yogas} between the yearly ascendant lord and that house's lord."""
    asc_sign = varsha["ascendant"]["sign"]
    a = SIGN_LORD[asc_sign]
    out = []
    for h in range(2, 13):
        b = SIGN_LORD[SIGNS[(SIGNS.index(asc_sign) + h - 1) % 12]]
        out.append({"house": h, "lord": b, "same": a == b, "yogas": pair_yogas(varsha, a, b)})
    return {"lagna_lord": a, "houses": out}


def tajika_extras(chart, varsha, muntha_sign):
    """Everything this module adds to a Varshaphal: aspects, yogas, strength, Varshesh and Sahams."""
    pl = varsha["planets"]
    return {"day": is_day(varsha), "relations": all_relations(pl), "general": ikkavala_induvara(varsha),
            "bala": {p: pancha_vargiya(p, pl) for p in SEVEN},
            "conditions": {p: planet_condition(varsha, p) for p in SEVEN},
            "varshesh": varshesh(chart, varsha, muntha_sign), "houses": house_yogas(varsha), "sahams": sahams(varsha)}
