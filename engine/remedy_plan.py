"""remedy_plan.py - "Remedies for you": only what is needed NOW. A planet is considered only when (1) it looks weak or
troubled in this chart AND (2) it is active in the person's life at the moment - it rules the running Mahadasha or
Antardasha, or it is Saturn during Sade Sati / Dhaiya. Troubled planets that are not active yet are listed as "later"
with the date their period begins. Active planets get a gemstone only where that is traditionally safe (the planet
rules a trine house and no difficult house), otherwise a mantra, charity, a fast and a colour. A short "for everyone"
section lists the everyday habits that suit anybody.

It reuses the remedy knowledge base already in the reading (stones, substitutes, mantras, daan, vrat, rudraksha,
colours). Everything is traditional guidance, never a prescription. Nothing here concerns lifespan or children.
"""
import datetime as _dt

import shadbala
from extras import BODIES, _TONE_PHRASE, _lordships, assess_doshas, ordinal, planet_considerations, sade_sati_now

HIGH, CARE, HELPFUL, OPTIONAL = "Highly recommended", "Recommended with care", "Helpful without a gemstone", "Optional"
LATER, NONE = "Not needed right now", "No remedy needed"
LEVELS = [HIGH, CARE, HELPFUL, OPTIONAL, LATER, NONE]
_TRINE, _DIFFICULT, _KENDRA = {1, 5, 9}, {6, 8, 12}, {4, 7, 10}

_SAFETY = ("Mantras, charity and fasting carry no risk, so start there. A gemstone is worn on the body and is traditionally chosen with a "
           "qualified astrologer, tried for a few weeks first (stop if you feel unsettled), and never bought under pressure or beyond your "
           "means. None of this replaces medical, legal or financial advice.")

EVERYONE = [
    "Begin the day calmly: a few minutes of quiet, prayer or slow breathing before you look at your phone.",
    "Keep one small weekly act of giving: feed birds or animals, help someone in need, or donate food or clothes.",
    "Respect your parents and elders: call, visit and listen, even when it is inconvenient.",
    "Keep your promises, speak truthfully and avoid gossip - these steady every chart.",
    "Look after the basics: regular sleep and meals, some daily sunlight and a walk.",
    "Choose a simple prayer or mantra from your own tradition and repeat it daily (108 times or ten minutes). Steady practice matters more "
    "than the exact words.",
    "Once a week, write down three things you are grateful for.",
    "Treat every remedy as optional: never put your health, money or family peace at risk for one.",
]


def _houses(houses):
    """'1st house' / '1st and 4th houses' for a list of house numbers."""
    names = [ordinal(h) for h in houses]
    if not names:
        return ""
    return (names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]) + (" house" if len(names) == 1 else " houses")


def _asdt(v):
    v = _dt.datetime.fromisoformat(v) if isinstance(v, str) else v
    return v.replace(tzinfo=None) if v.tzinfo else v


def running_periods(chart, at):
    """{"maha": lord, "antar": lord, "maha_end": date, "antar_end": date} at `at`, or None."""
    for maha in chart["dasha"]["timeline"]:
        ms, me = _asdt(maha["start"]), _asdt(maha["end"])
        if ms <= at < me:
            for an in maha["antardashas"]:
                if _asdt(an["start"]) <= at < _asdt(an["end"]):
                    return {"maha": maha["lord"], "antar": an["lord"], "maha_end": me, "antar_end": _asdt(an["end"])}
    return None


def next_period_start(chart, planet, at, horizon_years=25):
    """When the next Mahadasha or Antardasha of `planet` begins (datetime) or None."""
    best = None
    limit = at + _dt.timedelta(days=365.25 * horizon_years)
    for maha in chart["dasha"]["timeline"]:
        ms = _asdt(maha["start"])
        if maha["lord"] == planet and at < ms < limit:
            best = ms if best is None or ms < best else best
        for an in maha["antardashas"]:
            s = _asdt(an["start"])
            if an["lord"] == planet and at < s < limit:
                best = s if best is None or s < best else best
    return best


def remedy_plan(chart, reading, at=None):
    """{"now": {...}, "planets": [item...], "doshas": [(name, text, active)], "avoid": [str], "everyone": [str], "caveat": str}."""
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    cons = planet_considerations(chart)
    strength = shadbala.compute_shadbala(chart)
    lords = _lordships(chart)
    rem = reading["remedies"]
    run = running_periods(chart, at)
    saturn_test = sade_sati_now(chart, at)["kind"]
    active = {}
    if run:
        active[run["maha"]] = f"it rules your running main period (Mahadasha) until {run['maha_end']:%b %Y}"
        if run["antar"] == run["maha"]:
            active[run["antar"]] = f"it rules both your main period and your running sub-period (Antardasha, until {run['antar_end']:%b %Y})"
        else:
            active[run["antar"]] = f"it rules your running sub-period (Antardasha) until {run['antar_end']:%b %Y}"
    if saturn_test:
        active["Saturn"] = (active["Saturn"] + " and Saturn is also in a testing stretch (" + saturn_test.lower() + ")"
                            if "Saturn" in active else f"Saturn is in a testing stretch for you ({saturn_test.lower()})")

    items = []
    for p in BODIES:
        c = cons[p]
        weak_rank = p in strength and strength[p]["tone"] == "Weaker"
        strong_need = c["tone"] in ("Needs some care", "Challenging")
        mild_need = c["tone"] == "Mixed" and (weak_rank or p in ("Rahu", "Ketu"))
        houses = lords[p]
        trine, difficult = bool(_TRINE & set(houses)), bool(_DIFFICULT & set(houses))
        reason = active.get(p)
        when = next_period_start(chart, p, at)
        if not (strong_need or mild_need):
            level = NONE
            why = (f"Your {p} period is active because {reason}, and it looks comfortable, so it should feel supportive - no remedy needed."
                   if reason else "It looks comfortable in your chart, so no remedy is needed.")
        elif not reason:
            level = LATER
            why = (f"It {_TONE_PHRASE[c['tone']]} in your chart, but it is not active in your life right now. " +
                   (f"Its next period begins about {when:%b %Y}; that is the time to think about a remedy." if when else
                    "No period of it begins soon, so nothing is needed."))
        elif p in ("Rahu", "Ketu"):
            level = HELPFUL if strong_need else OPTIONAL
            why = (f"It is active because {reason}, and it {_TONE_PHRASE[c['tone']]}. It is a shadow planet, so a gemstone is not normally advised "
                   "without an expert; a mantra and charity are gentler.")
        elif strong_need and trine and not difficult:
            level = HIGH
            why = (f"It is active because {reason}, and it {_TONE_PHRASE[c['tone']]}. It rules your {_houses(houses)} (supportive for you), "
                   "so strengthening it is traditionally considered safe and useful.")
        elif strong_need and not difficult and (set(houses) & (_KENDRA | {2, 11})):
            level = CARE
            why = (f"It is active because {reason}, and it {_TONE_PHRASE[c['tone']]}. It rules a neutral house ({_houses(houses)}), so a stone "
                   "may help but is best confirmed by an astrologer first; a mantra is the gentle first step.")
        elif strong_need:
            level = HELPFUL
            why = (f"It is active because {reason}, and it {_TONE_PHRASE[c['tone']]}. But it rules a difficult or mixed house "
                   f"({_houses(houses) or 'none'}), so a gemstone could strengthen its troublesome side. A mantra, charity and fasting are the "
                   "safer way to ease it.")
        else:
            level = OPTIONAL
            why = (f"It is active because {reason}, and it looks mixed and a little weaker than the others, so a light practice such as a "
                   "mantra may help, but nothing is needed.")
        gem, mantra = rem["gemstones"].get(p, {}), rem["mantras"].get(p, {})
        items.append({
            "planet": p, "level": level, "tone": c["tone"], "why": why, "active_reason": reason, "next_start": when,
            "stone": gem.get("stone"), "sanskrit": gem.get("sanskrit"), "substitutes": gem.get("substitutes") or [], "metal": gem.get("metal"),
            "finger": gem.get("finger"), "day": gem.get("day") or mantra.get("day"),
            "mantra": mantra.get("beej_mantra"), "japa": mantra.get("japa_count"), "best_time": mantra.get("best_time"),
            "daan": (rem["daan"].get(p) or {}).get("articles"), "vrat": (rem["vrat"].get(p) or {}).get("method"),
            "rudraksha": (rem["rudraksha"].get(p) or {}).get("mukhi"), "colors": (rem["colors"].get(p) or {}).get("favorable_colors"),
            "stone_ok": level in (HIGH, CARE) and p not in ("Rahu", "Ketu"),
        })
    recommended = [i["stone"] for i in items if i["stone_ok"] and i["stone"]]
    avoid = [f"Do not wear {x['a_stone']} and {x['b_stone']} together: {x['why']}" for x in rem.get("combinations_to_avoid", [])
             if x["a_stone"] in recommended and x["b_stone"] in recommended]
    return {"now": {"periods": run, "saturn": saturn_test, "active": sorted(active)}, "planets": items,
            "doshas": _dosha_practices(chart, rem, at, set(active)), "avoid": avoid, "everyone": EVERYONE, "caveat": _SAFETY}


# dosha -> planets whose activity makes its practice relevant now (Sade Sati / Dhaiya are active whenever present)
_DOSHA_PLANETS = {"Manglik": {"Mars"}, "Kalsarpa": {"Rahu", "Ketu"}, "Guru Chandal": {"Jupiter", "Rahu"}, "Surya Grahan": {"Sun", "Rahu", "Ketu"},
                  "Chandra Grahan": {"Moon", "Rahu", "Ketu"}, "Shrapit": {"Saturn", "Rahu"}, "Pitra": {"Sun", "Rahu", "Ketu"}}


def _dosha_practices(chart, rem, at, active):
    out = []
    mantra = lambda p: (rem["mantras"].get(p) or {}).get("beej_mantra") or ""
    text_for = {
        "Manglik": f"Mars themes: chant {mantra('Mars')} on Tuesdays, keep calm and patient in partnerships, and channel energy into exercise or "
                   "service. Traditionally the dosha is also seen as balanced when the partner has it too.",
        "Sade Sati": f"Saturn's test: chant {mantra('Saturn')} or read the Hanuman Chalisa on Saturdays, donate black sesame, mustard oil or warm "
                     "clothing to those in need, look after elders, keep a steady routine and avoid big risks.",
        "Kalsarpa": "Chant 'Om Namah Shivaya' regularly, keep to a steady routine and do regular charity; the pattern is traditionally seen as "
                    "easing with patience and service.",
        "Guru Chandal": f"Respect teachers and elders, choose guides carefully, and chant {mantra('Jupiter')} on Thursdays.",
        "Surya Grahan": f"Greet the sunrise, keep to a steady morning routine and chant {mantra('Sun')} on Sundays.",
        "Chandra Grahan": f"Keep calm evening routines and enough sleep, and chant {mantra('Moon')} on Mondays.",
        "Shrapit": f"Honest work, service to others, and {mantra('Saturn')} on Saturdays; patience is the traditional advice.",
        "Pitra": "Care for elders and respect family traditions, and give food or help to people in need in your family's name.",
    }
    for d in assess_doshas(chart, at):
        if not d["present"]:
            continue
        n = d["name"]
        key = "Sade Sati" if n.startswith(("Sade Sati", "Dhaiya")) else next((k for k in text_for if n.startswith(k)), None)
        if not key:
            continue
        is_active = key == "Sade Sati" or bool(_DOSHA_PLANETS.get(key, set()) & active)
        out.append((n, text_for[key], is_active))
    return out


def remedy_text(chart, reading, at=None, compact=False):
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    plan = remedy_plan(chart, reading, at)
    run = plan["now"]["periods"]
    now_line = (f"Right now you are in the {run['maha']} main period (until {run['maha_end']:%b %Y}) and the {run['antar']} sub-period "
                f"(until {run['antar_end']:%b %Y})." if run else "")
    if plan["now"]["saturn"]:
        now_line += f" Saturn is in a testing stretch for you ({plan['now']['saturn'].lower()})."
    parts = ["--- Remedies for you, for right now ---\nOnly what is needed for the periods you are living through now is listed. A planet is "
             "considered only when it looks weak or troubled in YOUR chart AND is active at the moment. " + now_line +
             "\n\n[In simple terms: most people need only one or two of these - start with the mantra and everyday habits, and add a stone "
             "later only if an astrologer you trust agrees. Nothing here is a cure or a guarantee.]"]
    current = [i for i in plan["planets"] if i["level"] in (HIGH, CARE, HELPFUL, OPTIONAL)]
    if not current:
        parts.append("Nothing more is needed for your current periods: the planets running now look comfortable in your chart. The everyday "
                     "habits below are enough.")
    for level in (HIGH, CARE, HELPFUL, OPTIONAL):
        group = [i for i in plan["planets"] if i["level"] == level]
        if not group:
            continue
        parts.append(f"--- {level} ---")
        for i in group:
            summary = f"{i['planet']} ({i['tone'].lower()} in your chart): {i['why']}"
            plain = (f"[In simple terms: {i['planet']} is active now and may need support. " +
                     (f"Wearing {i['stone']} is the traditional choice, or you can chant its mantra and give the donation instead.]"
                      if i["stone_ok"] else "A simple mantra and a small weekly donation are the safe way to ease it.]"))
            if compact:
                parts.append(summary + " " + plain)
                continue
            detail = []
            if i["stone_ok"] and i["stone"]:
                sub = f" Milder substitutes: {', '.join(i['substitutes'])}." if i["substitutes"] else ""
                detail.append(f"Gemstone: {i['stone']} ({i['sanskrit']}), set in {i['metal']}, worn on the "
                              f"{i['finger'].lower() if i['finger'] else 'finger an astrologer advises'}, on a {i['day']}.{sub}")
            elif i["stone"] and i["planet"] in ("Rahu", "Ketu"):
                detail.append(f"Gemstone: {i['stone']} is traditionally linked with {i['planet']}, but it is not advised without an expert.")
            else:
                detail.append(f"Gemstone: not advised for {i['planet']} in your chart.")
            alt = []
            if i["mantra"]:
                alt.append(f"chant '{i['mantra']}' ({i['japa']} repetitions is the full traditional count; 108 a day is a common lighter "
                           f"practice), best at {i['best_time']}")
            if i["daan"]:
                alt.append(f"donate {i['daan'].lower()} on {i['day']}")
            if i["vrat"]:
                alt.append(f"observe the {i['day']} fast in the way that suits you")
            if i["colors"]:
                alt.append(f"favour {i['colors'].lower()} on {i['day']}")
            if i["rudraksha"]:
                alt.append(f"a {i['rudraksha']}-mukhi rudraksha bead is sometimes worn")
            detail.append("Stone-free alternative (or in addition): " + "; ".join(alt) + ".")
            parts.append(summary + "\n\n" + "\n".join(detail) + "\n\n" + plain)
    if plan["avoid"]:
        parts.append("--- Combinations to avoid ---\n" + "\n".join(plan["avoid"]))
    active_dosha = [(n, t) for n, t, a in plan["doshas"] if a]
    if active_dosha:
        parts.append("--- For the doshas that are active now ---\n" + "\n\n".join(f"{n}: {t}" for n, t in active_dosha))
    later = [i for i in plan["planets"] if i["level"] == LATER]
    quiet = [n for n, _t, a in plan["doshas"] if not a]
    if later or quiet:
        lines = ["--- Keep in mind for later ---\nThese look troubled in your chart but are not active now, so nothing is needed yet:"]
        lines += [f"- {i['planet']}: " + (f"its next period begins about {i['next_start']:%b %Y}." if i["next_start"] else "no period of it begins soon.")
                  for i in later]
        if quiet:
            lines.append("- Doshas in your chart that are not active now: " + ", ".join(quiet) + ". Their practices matter mainly when the "
                         "planets involved are running.")
        parts.append("\n".join(lines))
    parts.append("--- What everyone can do ---\nThese everyday habits suit any chart and need no expert:\n" +
                 "\n".join(f"- {t}" for t in plan["everyone"]))
    parts.append("--- How to use these safely ---\n" + plan["caveat"])
    return "\n\n".join(parts)
