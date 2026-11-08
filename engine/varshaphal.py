"""varshaphal.py - the yearly (Tajika) chart: the Varsha Pravesh moment when the Sun returns to its birth
position, the chart cast for it, the Muntha, the Mudda Vimshottari periods of the year and a plain
good / mixed / needs-care outlook for that year. Wording is a tendency, never a fixed event.
"""
import datetime as _dt
import zoneinfo

import swisseph as swe

import ephemeris
from extras import BODIES, _HOUSE_AREA, _TONE_GIST, _TONE_PHRASE, ordinal, house_verdicts, planet_considerations
from panchanga import SIGNS
from i18n import tbl, tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)
import tajika

_DAYS_PER_YEAR = 365.2422
_MUDDA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
_MUDDA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
_NAKSHATRA_LORD = [_MUDDA_ORDER[i % 9] for i in range(27)]            # Ashwini -> Ketu, Bharani -> Venus, ...

_MUNTHA_KIND = {h: "good" for h in (1, 2, 3, 5, 9, 10, 11)}
_MUNTHA_KIND.update({4: "mixed", 7: "mixed", 6: "care", 8: "care", 12: "care"})
_MUNTHA_TEXT = tbl({
    "good": "The Muntha falls in a supportive house, so the year's main focus tends to go well and give you backing in %s.",
    "mixed": "The Muntha falls in a house that brings a mix of easy and effortful stretches, so %s may ask for some give-and-take this year.",
    "care": "The Muntha falls in a house that asks for care, so %s may need extra patience and looking after this year.",
})


def _sun_return_jd(natal_sun_lon, near_jd):
    """The Julian day (UT) at which the sidereal Sun is at `natal_sun_lon`, found from a starting guess."""
    jd = near_jd
    for _ in range(12):
        lon = ephemeris.get_planet_longitude(jd, "Sun")
        diff = (natal_sun_lon - lon + 180) % 360 - 180
        jd += diff / 0.9856
        if abs(diff) < 1e-8:
            break
    return jd


def _jd_to_utc(jd):
    y, m, d, h = swe.revjul(jd)
    return _dt.datetime(y, m, d) + _dt.timedelta(hours=h)


def return_moment(chart, year):
    """UTC datetime of the Sun's return to its birth degree in calendar `year`."""
    bi = chart["birth_input"]
    by, bm, bd = (int(x) for x in bi["birth_date"].split("-"))
    with ephemeris.EPHEMERIS_LOCK:
        ephemeris.ensure_sidereal_mode()
        guess = swe.julday(year, bm, bd, 12.0)
        jd = _sun_return_jd(chart["planets"]["Sun"]["longitude"], guess)
    return _jd_to_utc(jd)


def varsha_chart(chart, year):
    """The chart cast for the Varsha Pravesh moment of `year`, at the birth place."""
    from birth_chart import compute_birth_chart
    loc, bi = chart["resolved_location"], chart["birth_input"]
    utc = return_moment(chart, year).replace(tzinfo=_dt.timezone.utc)
    local = utc.astimezone(zoneinfo.ZoneInfo(loc["tz_name"]))
    v = compute_birth_chart(name=tr('{0} - Varsha {1}', chart.get('name') or 'Chart', year), birth_date=(local.year, local.month, local.day),
                            birth_time=(local.hour, local.minute, local.second), place_name=bi.get("place_name") or "",
                            latitude=loc["latitude"], longitude=loc["longitude"], tz_name=loc["tz_name"],
                            dasha_years_forward=2, sex=bi.get("sex"))
    v["varsha"] = {"year": year, "local": local.replace(tzinfo=None), "utc": utc.replace(tzinfo=None)}
    return v


def muntha(chart, varsha, age):
    """Muntha: the birth Lagna sign moved forward one sign for each completed year of age."""
    idx = (SIGNS.index(chart["ascendant"]["sign"]) + age) % 12
    sign = SIGNS[idx]
    house = (idx - SIGNS.index(varsha["ascendant"]["sign"])) % 12 + 1
    return {"sign": sign, "house": house}


def mudda_dasha(chart, varsha, age):
    """The nine Mudda Vimshottari periods of the year (the 120-year cycle squeezed into one solar year).
    The first period belongs to the lord of the nakshatra reached by moving the birth Moon nakshatra on by
    one nakshatra per completed year."""
    span = 360.0 / 27
    nak_no = int(chart["planets"]["Moon"]["longitude"] // span)          # 0-based
    idx = _MUDDA_ORDER.index(_NAKSHATRA_LORD[(nak_no + age) % 27])
    start = varsha["varsha"]["local"]          # shown in the birth place's own time
    year_days = _DAYS_PER_YEAR
    out, t = [], start
    for k in range(9):
        lord = _MUDDA_ORDER[(idx + k) % 9]
        end = t + _dt.timedelta(days=_MUDDA_YEARS[lord] * 3 * year_days / 360.0)
        out.append({"lord": lord, "start": t, "end": end, "days": round((end - t).total_seconds() / 86400)})
        t = end
    return out


def _house_text(kind, house):
    return _MUNTHA_TEXT[kind] % _HOUSE_AREA[house]


def varshaphal(chart, year):
    """Everything for one year: {year, age, varsha (chart), local, muntha, mudda, outlook}. `year` is the
    calendar year in which the birthday falls; age = completed years at that birthday."""
    birth_year = int(chart["birth_input"]["birth_date"][:4])
    age = year - birth_year
    v = varsha_chart(chart, year)
    m = muntha(chart, v, age)
    mudda = mudda_dasha(chart, v, age)
    cons = planet_considerations(v)
    hv = {h["house"]: h for h in house_verdicts(v)}
    lagna_lord = hv[1]["lord"]
    for period in mudda:
        c = cons[period["lord"]]
        period.update(house=c["house"], tone=c["tone"], area=_HOUSE_AREA[c["house"]])
    kind = _MUNTHA_KIND[m["house"]]
    summary = (tr('The year starting {0:%d %b %Y} has the {1} sign rising. Its ruler {2} {3} in the yearly chart. '
                  'The Muntha is in {4}, the {5} house ({6}). ', v['varsha']['local'], v['ascendant']['sign'], lagna_lord, _TONE_PHRASE[cons[lagna_lord]['tone']], m['sign'], ordinal(m['house']), _HOUSE_AREA[m['house']]) + _house_text(kind, m["house"]))
    return {"year": year, "age": age, "varsha": v, "local": v["varsha"]["local"], "muntha": {**m, "kind": kind},
            "mudda": mudda, "lagna_lord": lagna_lord, "lagna_lord_tone": cons[lagna_lord]["tone"], "summary": summary,
            "houses": [hv[h] for h in range(1, 13)], "considerations": cons, "tajika": tajika_yogas(v),
            "tajika_extras": tajika.tajika_extras(chart, v, m["sign"])}


def varshaphal_text(vp, compact=False):
    """Reader-friendly text in the '--- Heading ---' convention."""
    parts = [tr('--- Your year from {0:%d %b %Y} (age {1}) ---\n{2}\n\n[In simple terms: the yearly chart is a '
                'fresh map for the year that begins on your birthday. The Muntha shows the life area that gets '
                'the spotlight, and the periods below show how the mood changes through the year. These are '
                'tendencies, not fixed events.]', vp['local'], vp['age'], vp['summary'])]
    tone_idx = {"Good": 0, "Mostly good": 0, "Mixed": 1, "Needs some care": 2, "Challenging": 2}
    from extras import _EFFECTS
    parts.append(tx("--- The year's periods (Mudda Dasha) ---\nThe year is split into nine periods, each coloured by one planet as placed in "
                 "the yearly chart."))
    for p in vp["mudda"]:
        line = (tr('{0} period, {1:%d %b %Y} to {2:%d %b %Y} ({3} days): {4} {5} in the yearly chart and sits in '
                   'the {6} house, so this stretch is felt through {7}.', p['lord'], p['start'], p['end'], p['days'], p['lord'], _TONE_PHRASE[p['tone']], ordinal(p['house']), p['area']))
        if not compact:
            line += tx(" What may happen: ") + _EFFECTS[p["lord"]][tone_idx[p["tone"]]]
        parts.append(line)
    if not compact:
        parts.append(varshesh_text(vp))
        parts.append(tajika_text(vp))
        parts.append(house_yogas_text(vp))
        parts.append(sahams_text(vp))
        parts.append(tx("--- The yearly chart's 12 houses at a glance ---\n") + "\n\n".join(
            tr('{0} house ({1}): {2}. {3}', ordinal(h['house']), h['area'], h['tone'], h['may_happen']) for h in vp["houses"]))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- Tajika: aspects by sign, yogas, year lord, Sahams
def tajika_yogas(varsha_chart):
    """Ithasala and Ishrafa among the seven planets of the yearly chart (engine/tajika.py): Tajika aspects go by sign,
    the faster planet must be behind the slower one in degrees (Ithasala) or past it by at least a degree (Ishrafa),
    and the gap must be within half the sum of their orbs."""
    return tajika.all_relations(varsha_chart["planets"])


_ASPECT_WORDS = tbl({"conjunction": "together in one sign", "sextile": "in a friendly sextile (3rd/11th signs)",
                     "trine": "in a very friendly trine (5th/9th signs)", "square": "in a testing square (4th/10th signs)",
                     "opposition": "opposite each other (7th sign)"})
_BENEFIC = ("Jupiter", "Venus", "Mercury", "Moon")


def tajika_text(vp):
    """Plain-words reading of the yearly chart's planet links."""
    yogas = vp["tajika"]
    if not yogas:
        return (tx("--- Planet links in the yearly chart ---\nNo two planets are close to an exact angle in this yearly chart, so no one "
                "planet-to-planet link stands out. [In simple terms: nothing special is being pulled together or pulled apart by the planets.]"))
    lines = [tx("--- Planet links in the yearly chart (Tajika yogas) ---\nIn Tajika, planets look at each other by sign: the 3rd/11th and "
                "5th/9th signs are friendly, the same sign, the 4th/10th and the 7th are testing, and the 2nd/12th and 6th/8th signs do not "
                "look at each other at all. 'Coming together' (Ithasala) means the faster planet is still behind the slower one within their "
                "orbs, so what they stand for tends to be building this year. 'Moving apart' (Ishrafa) means it has already passed, so the "
                "matter tends to be fading or settled.")]
    for y in yogas:
        if y["kind"] == "Ithasala":
            state = {"poorna": tx("coming together and almost exact"), "bhavishyat": tx("about to come together when the faster one changes sign")}.get(
                y["type"], tx("coming together"))
        else:
            state = tx("moving apart")
        feel = tx("an easy, supportive link") if y["nature"] == "friendly" else tx("a testing link that asks for effort")
        lines.append(tr('{0} and {1} are {2}, {3} ({4} degrees): {5}.', y['fast'], y['slow'], _ASPECT_WORDS[y['aspect']], state, y['gap'], feel))
    lines.append(tx("[In simple terms: the tighter the gap, the stronger the link. Easy links help things run smoothly; testing links bring "
                    "friction that can also push you to act. Tendencies only.]"))
    return "\n\n".join(lines)


_OFFICE = tbl({"Muntha lord": "Muntha lord", "Birth ascendant lord": "Birth ascendant lord", "Year ascendant lord": "Year ascendant lord",
               "Tri-rashi lord": "Tri-rashi lord", "Day/night lord": "Day/night lord"})
_VARSHESH_WHY = tbl({
    "strongest_aspecting": "it is the strongest of the five office-bearers (by Pancha-vargiya bala) that looks at the year's rising sign",
    "moon_only": "the Moon is the only office-bearer that looks at the year's rising sign",
    "none_aspects": "none of the five office-bearers looks at the year's rising sign, so the Muntha lord takes the role",
    "all_weak": "all five office-bearers are weak (under 5 points), so the Muntha lord takes the role",
})
_RATING = tbl({"strong": "strong", "middling": "middling", "weak": "weak"})


def varshesh_text(vp):
    x = vp["tajika_extras"]
    vs = x["varshesh"]
    lord = vs["lord"]
    bala = x["bala"][lord]
    house = vp["considerations"][lord]["house"]
    out = [tr('--- Lord of the year (Varshesh): {0} ---\n{0} rules this year because {1}. It sits in the {2} house of the yearly chart '
              '({3}) with {4:.1f} points out of 20 ({5}).', lord, _VARSHESH_WHY[vs['reason']], ordinal(house), _HOUSE_AREA[house],
              bala['total'], _RATING[bala['rating']])]
    tone = vp["considerations"][lord]["tone"]
    out.append(tr('[In simple terms: the lord of the year sets the year\'s overall tone. {0} {1} in this chart, so its themes colour the '
                  'year and {2} gets extra attention.]', lord, _TONE_PHRASE[tone], _HOUSE_AREA[house]))
    out.append(tx("The year is cast by day.") if vs["day"] else tx("The year is cast by night."))
    return "\n\n".join(out)


_YOGA_PHRASE = tbl({
    "Ithasala": "the year's ascendant lord {a} and {b} are coming together, so this area tends to move forward",
    "Ishrafa": "the link between {a} and {b} has just passed its peak, so this area may have peaked or slip away",
    "Nakta": "it comes through another person's help ({via} carries the link)",
    "Yamaya": "it comes through a senior person or adviser ({via} carries the link)",
    "Kambool": "the Moon backs it, which makes it more likely",
    "Gairi-kambool": "support comes from outside the usual circle",
    "Khallasara": "but the Moon gives no support, which weakens the promise",
    "Manau": "but {by} interferes, which can spoil or delay it",
    "Radda": "but {planets} is held back (retrograde, combust or in the 6th, 8th or 12th house), so results may come late",
    "Duhphali-kuttha": "the slower planet is in its own or exaltation sign, which still favours it",
    "Dutthottha-davira": "both planets are weak, so it comes through someone else's help",
    "Tambira": "help arrives later in the year as {from} moves on to {to}",
})


def house_yogas_text(vp):
    x = vp["tajika_extras"]
    hy = x["houses"]
    a = hy["lagna_lord"]
    lines = [tr('--- Life areas this year (Tajika yogas with the year\'s ascendant lord {0}) ---\nTajika judges each life area by the '
                'link between the lord of the year\'s rising sign and the lord of that house.', a)]
    general = x["general"]
    if general == "Ikkavala":
        lines.append(tx("[Ikkavala: all seven planets are in angular or following houses, a sign of rising fortunes this year; a feared "
                        "difficulty tends to turn around.]"))
    elif general == "Induvara":
        lines.append(tx("[Induvara: all seven planets are in falling houses, so the year asks for patience and results come slowly.]"))
    found = False
    for h in hy["houses"]:
        if not h["yogas"]:
            continue
        found = True
        bits = []
        for y in h["yogas"]:
            d = y["detail"]
            t = lambda v: tx(v) if v else ""
            fmt = {"a": t(a), "b": t(h["lord"]), "via": t(d.get("via", "")), "by": t(d.get("by", "")),
                   "planets": ", ".join(tx(x) for x in d.get("planets", [])), "from": t(d.get("from", "")), "to": t(d.get("to", ""))}
            phrase = _YOGA_PHRASE[y["yoga"]].format(**fmt)
            if y["yoga"] == "Ishrafa" and a in _BENEFIC and h["lord"] in _BENEFIC:
                phrase += tx(" (between gentle planets this is not harmful)")
            bits.append(f"{tx(y['yoga'])}: {phrase}")
        lines.append(tr('{0} house - {1} (lord {2}): ', ordinal(h['house']), _HOUSE_AREA[h['house']], h['lord']) + "; ".join(bits) + ".")
    if not found:
        lines.append(tx("No Tajika yoga links the year's ascendant lord with another house lord this year, so no single life area is "
                        "especially pushed forward or held back by it."))
    lines.append(tx("[In simple terms: Ithasala, Kambool, Nakta and Yamaya help a life area along; Ishrafa, Manau, Khallasara and Radda "
                    "slow it or take the shine off. Tendencies for the year, not fixed events.]"))
    return "\n\n".join(lines)


_SAHAM_VERDICT = tbl({"supported": "supported", "mixed": "mixed", "care": "needs care"})


def sahams_text(vp):
    sh = vp["tajika_extras"]["sahams"]
    good = [s for s in sh if s["verdict"] == "supported" and not s["malefic"]]
    care = [s for s in sh if s["verdict"] == "care" and not s["malefic"]]
    active = [s for s in sh if s["verdict"] == "supported" and s["malefic"]]
    lines = [tx("--- Sahams (sensitive points of the year) ---\nA Saham is a point worked out from two planets and the rising degree; "
                "the house it falls in and the condition of its ruler show how that matter fares this year. A Saham is supported when its "
                "ruler looks at it, sits in a good house and is strong, and needs care when its ruler is weak, in the 6th, 8th or 12th "
                "house, combust or retrograde.")]
    if good:
        lines.append(tx("Supported this year: ") + ", ".join(tr('{0} ({1})', s["name"], tx(s["meaning"])) for s in good) + ".")
    if care:
        lines.append(tx("Needs care this year: ") + ", ".join(tr('{0} ({1})', s["name"], tx(s["meaning"])) for s in care) + ".")
    if active:
        lines.append(tx("More active this year, so handle calmly: ") + ", ".join(tr('{0} ({1})', s["name"], tx(s["meaning"])) for s in active) + ".")
    lines.append(tx("[In simple terms: Sahams point to the parts of life most likely to go well or ask for attention this year. The full "
                    "table is below.]"))
    return "\n\n".join(lines)
