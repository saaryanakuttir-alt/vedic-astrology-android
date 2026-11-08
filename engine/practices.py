"""practices.py - meditation, breath and yoga practices matched to the chart, the running periods and the person's age.

A modern Jyotish-Ayurveda layer on top of the remedy logic (engine/remedy_plan.py), kept apart from the Parashari
knowledge base. The practices and their sources (Hatha Yoga Pradipika, Gheranda Samhita, Yoga Sutras, Bihar School)
are in kb/practices.json. How a practice is chosen:
  * focus planets: planets that are weak or troubled in the chart AND active now (running Mahadasha/Antardasha,
    Sade Sati, a difficult Jupiter transit) - exactly the planets the Remedies screen lists;
  * period planets: the lords of the running Mahadasha and Antardasha, so the practice follows the period even when
    the planet is comfortable;
  * a base practice from the Moon's sign element (the mind's temperament);
  * the age band sets the time per practice and the highest level shown (no strong breathing or locks under 18,
    and none newly started over 60).
"""
import datetime as _dt
import json
import os

_KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb", "practices.json")
_DATA = None
_LEVEL_RANK = {"gentle": 0, "moderate": 1, "advanced": 2}
KUNDALINI_GENTLE = ("ajapa", "chakra_awareness")
KUNDALINI_ADVANCED = ("mula_bandha", "jalandhara_bandha", "uddiyana_bandha", "kumbhaka", "maha_bandha")
_DAY = {"Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday", "Mercury": "Wednesday", "Jupiter": "Thursday",
        "Venus": "Friday", "Saturn": "Saturday", "Rahu": "Saturday", "Ketu": "Tuesday"}


def data():
    global _DATA
    if _DATA is None:
        with open(_KB, encoding="utf-8") as fh:
            _DATA = json.load(fh)
    return _DATA


def practice(pid):
    return next(p for p in data()["practices"] if p["id"] == pid)


def age_years(chart, today=None):
    y, m, d = (int(v) for v in chart["birth_input"]["birth_date"].split("-"))
    today = today or _dt.date.today()
    return today.year - y - ((today.month, today.day) < (m, d))


def age_band(age):
    return next(b for b in data()["ages"] if b["from"] <= age < b["to"])


def allowed(pid, band):
    """True when the practice suits this age band (level not above the band's limit and some time is given)."""
    p = practice(pid)
    return _LEVEL_RANK[p["level"]] <= _LEVEL_RANK[band["max_level"]] and p["minutes"][band["minutes"]] > 0


def _entry(pid, band, planet=None):
    p = practice(pid)
    return {**p, "minutes_now": p["minutes"][band["minutes"]], "for_planet": planet,
            "caution_text": [data()["cautions"][c] for c in p["cautions"]]}


def planet_practices(planet, band, limit=2, avoid=()):
    """Up to `limit` practices for a planet that suit the age band, preferring ones not already in `avoid`."""
    ok = [pid for pid in data()["planets"][planet]["practices"] if allowed(pid, band)]
    ok = [pid for pid in ok if pid not in avoid] + [pid for pid in ok if pid in avoid]
    return [_entry(pid, band, planet) for pid in ok[:limit]]


def moon_element(chart):
    sign = chart["planets"]["Moon"]["sign"]
    return next((name, e) for name, e in data()["elements"].items() if sign in e["signs"])


def practice_plan(chart, reading, today=None, at=None):
    """{"age", "band", "base", "focus": [...], "periods": [...], "kundalini": {"gentle": [...], "advanced": [...],
    "advanced_allowed"}, "routine": {...}}."""
    import remedy_plan
    today = today or _dt.date.today()
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    age = age_years(chart, today)
    band = age_band(age)
    plan = remedy_plan.remedy_plan(chart, reading, at)
    order = {remedy_plan.HIGH: 0, remedy_plan.CARE: 1, remedy_plan.HELPFUL: 2, remedy_plan.OPTIONAL: 3}
    elem_name, elem = moon_element(chart)
    base_id = elem["practice"] if allowed(elem["practice"], band) else "breath_awareness"
    base = {"element": elem_name, "why": elem["why"], "practice": _entry(base_id, band)}
    used = {base_id}
    focus_items = sorted((i for i in plan["planets"] if i["active_reason"] and i["level"] in order),
                         key=lambda i: order[i["level"]])
    focus = []
    for i in focus_items:
        prs = planet_practices(i["planet"], band, avoid=used)
        used |= {x["id"] for x in prs}
        focus.append({"planet": i["planet"], "why": i["active_reason"], "tone": i["tone"], "level": i["level"],
                      "theme": data()["planets"][i["planet"]]["theme"], "day": _DAY[i["planet"]], "mantra": i.get("mantra"),
                      "practices": prs})
    run = plan["now"]["periods"]
    periods = []
    if run:
        seen = {f["planet"] for f in focus}
        for key, end_key, label in (("maha", "maha_end", "Main period (Mahadasha)"), ("antar", "antar_end", "Sub-period (Antardasha)")):
            p = run[key]
            if p in seen:
                continue
            seen.add(p)
            prs = planet_practices(p, band, limit=1, avoid=used)
            used |= {x["id"] for x in prs}
            periods.append({"planet": p, "label": label, "until": run[end_key], "theme": data()["planets"][p]["theme"],
                            "day": _DAY[p], "practices": prs,
                            "mantra": ((reading.get("remedies") or {}).get("mantras", {}).get(p) or {}).get("beej_mantra")})
    advanced_ok = band["max_level"] == "advanced"
    kundalini = {"gentle": [_entry(pid, band) for pid in KUNDALINI_GENTLE],
                 "advanced": [_entry(pid, band) for pid in KUNDALINI_ADVANCED] if advanced_ok else [],
                 "advanced_allowed": advanced_ok}
    # a simple daily shape: the base practice every morning, one focus/period practice, and rest in the evening
    first = next(([x] for grp in focus + periods for x in grp["practices"] if x["id"] != base_id), [])
    routine = {"morning": [base["practice"]] + first,
               "evening": [_entry("yoga_nidra", band)] if band["id"] in ("adult", "senior") else [_entry("bhramari", band)]}
    routine["total_minutes"] = sum(p["minutes_now"] for p in routine["morning"] + routine["evening"])
    return {"age": age, "band": band, "base": base, "focus": focus, "periods": periods, "kundalini": kundalini,
            "routine": routine, "safety": data()["safety"]}
