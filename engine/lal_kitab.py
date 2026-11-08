"""lal_kitab.py - Lal Kitab, kept apart from the Parashari knowledge base: the fixed-house chart, each planet's
standing in its house (pakka ghar, exalted, debilitated, good or weak house), the nine debts (rin), the 35-year
planetary cycle and the Lal Kitab Varshphal (yearly chart from the 120-year table). The tables and their sources
are in kb/lal_kitab.json. Wording is always a tendency with traditional, optional remedies.
"""
import datetime as _dt
import json
import os

_KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb", "lal_kitab.json")
_DATA = None
NINE = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def data():
    global _DATA
    if _DATA is None:
        with open(_KB, encoding="utf-8") as fh:
            _DATA = json.load(fh)
    return _DATA


def lk_houses(chart):
    """{planet: house 1-12}: the Lal Kitab chart keeps the birth-chart house of every planet (whole signs from the
    ascendant); house 1 is then read as Aries, house 2 as Taurus and so on."""
    return {p: int(chart["planets"][p]["house"]) for p in NINE}


def status(planet, house):
    """("pakka" | "exalted" | "debilitated" | "good" | "weak" | "neutral", tone "good"/"mixed"/"care")."""
    p = data()["planets"][planet]
    if house in p["exalted"] and house not in p["debilitated"]:
        return "exalted", "good"
    if house in p["pakka_ghar"]:
        return "pakka", "good" if house not in p["debilitated"] else "mixed"
    if house in p["debilitated"]:
        return "debilitated", "care"
    if house in p["good"]:
        return "good", "good"
    if house in p["weak"]:
        return "weak", "care"
    return "neutral", "mixed"


def placements(houses):
    """[{planet, house, status, tone, with}] for a {planet: house} map (birth or yearly chart)."""
    out = []
    for p in NINE:
        h = houses[p]
        st, tone = status(p, h)
        out.append({"planet": p, "house": h, "status": st, "tone": tone,
                    "with": [q for q in NINE if q != p and houses[q] == h]})
    return out


def debts(houses):
    """The rin (debts) present: [{id, name, meaning, why, remedy, by: [planets]}]."""
    out = []
    for r in data()["rinas"]:
        by = [p for p in r["planets"] if houses[p] in r["houses"]]
        if by:
            out.append({**r, "by": by})
    return out


def _birth_date(chart):
    y, m, d = (int(v) for v in chart["birth_input"]["birth_date"].split("-"))
    return _dt.date(y, m, d)


def _add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:                                           # 29 Feb
        return d.replace(year=d.year + years, day=28)


def cycle(chart, today=None):
    """The 35-year cycle: [{planet, years, start, end, start_age, end_age, now}] for the cycle running today, plus
    "cycle_no" (1 = ages 0-35, 2 = 35-70, ...)."""
    birth = _birth_date(chart)
    today = today or _dt.date.today()
    age = (today - birth).days / 365.2425
    n = int(age // 35)
    rows, a = [], n * 35
    for planet, yrs in data()["cycle"]:
        start, end = _add_years(birth, a), _add_years(birth, a + yrs)
        rows.append({"planet": planet, "years": yrs, "start_age": a, "end_age": a + yrs, "start": start, "end": end,
                     "now": start <= today < end})
        a += yrs
    return {"cycle_no": n + 1, "periods": rows}


def running_year(chart, today=None):
    """The running year of life (1 from birth to the first birthday)."""
    birth = _birth_date(chart)
    today = today or _dt.date.today()
    completed = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    return completed + 1


def varshphal(chart, year_no):
    """The Lal Kitab yearly chart for running year `year_no` (1-120): {year_no, start, end, houses, placements,
    debts, moves: [{planet, birth_house, year_house}]}."""
    if not 1 <= year_no <= 120:
        raise ValueError("Lal Kitab Varshphal covers running years 1 to 120.")
    row = data()["varshphal_table"][year_no - 1]
    birth = lk_houses(chart)
    year = {p: row[h - 1] for p, h in birth.items()}
    b = _birth_date(chart)
    return {"year_no": year_no, "start": _add_years(b, year_no - 1), "end": _add_years(b, year_no), "houses": year,
            "placements": placements(year), "debts": debts(year),
            "moves": [{"planet": p, "birth_house": birth[p], "year_house": year[p]} for p in NINE]}


_STATUS_TEXT = {
    "pakka": "This is {p}'s own permanent house (pakka ghar), so it is at home here and gives steady results.",
    "exalted": "Lal Kitab counts this house as {p}'s house of exaltation, so it gives its best here.",
    "debilitated": "Lal Kitab counts this house as {p}'s house of debilitation, so its results are weak here and a remedy helps.",
    "good": "Lal Kitab counts this among {p}'s good houses, so it tends to help.",
    "weak": "Lal Kitab counts this among {p}'s weak houses, so its results may disappoint unless supported.",
    "neutral": "This house is neither especially good nor weak for {p}; the planets with it and the house it looks at decide.",
}


def reading(planet, house, with_=()):
    """A short Lal Kitab reading for one planet in one house (English template pieces; the UI translates)."""
    p = data()["planets"][planet]
    st, tone = status(planet, house)
    parts = {"planet": planet, "house": house, "house_area": data()["houses"][str(house)], "stands_for": p["stands_for"],
             "status": st, "status_text": _STATUS_TEXT[st], "tone": tone, "remedy": p["remedy"] if tone != "good" else None,
             "friends_with": [q for q in with_ if q in p["friends"]], "enemies_with": [q for q in with_ if q in p["enemies"]]}
    return parts


def lal_kitab(chart, today=None):
    houses = lk_houses(chart)
    yr = running_year(chart, today)
    return {"houses": houses, "placements": placements(houses), "debts": debts(houses), "cycle": cycle(chart, today),
            "running_year": yr, "varshphal": varshphal(chart, min(max(yr, 1), 120))}
