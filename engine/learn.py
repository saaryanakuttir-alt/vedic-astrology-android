"""learn.py - Learn Astrology: lessons and glossary (kb/learn.json) and a step-by-step walkthrough of the user's own
chart, using the same chart data the rest of the app reads. Teaching only: no new predictions are made here."""
import datetime as _dt
import json
import os

from astrology_tables import DEBILITATION_SIGN, EXALTATION_SIGN, OWN_SIGNS, SIGN_LORD, aspect_distances_for
from combustion import is_combust
from extras import BODIES, ordinal
from i18n import tbl, tr, tx  # noqa: F401 - translation helpers (engine/i18n.py)
from panchanga import SIGNS

_KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb", "learn.json")
_DATA = None

HOUSE_AREA = {1: "self and body", 2: "money, family and speech", 3: "courage, effort and siblings", 4: "home, mother and comfort",
              5: "learning, creativity and romance", 6: "work, service and rivals", 7: "marriage and partners",
              8: "sudden changes and shared money", 9: "luck, father, teachers and faith", 10: "career and status",
              11: "gains, income and friends", 12: "expenses, rest and foreign lands"}
ELEMENT = {s: e for e, signs in (("fire", ("Aries", "Leo", "Sagittarius")), ("earth", ("Taurus", "Virgo", "Capricorn")),
                                 ("air", ("Gemini", "Libra", "Aquarius")), ("water", ("Cancer", "Scorpio", "Pisces")))
           for s in signs}
QUALITY = {s: q for q, signs in (("movable", ("Aries", "Cancer", "Libra", "Capricorn")), ("fixed", ("Taurus", "Leo", "Scorpio", "Aquarius")),
                                 ("dual", ("Gemini", "Virgo", "Sagittarius", "Pisces"))) for s in signs}


def data():
    global _DATA
    if _DATA is None:
        with open(_KB, encoding="utf-8") as fh:
            _DATA = json.load(fh)
    return _DATA


def lessons():
    return data()["lessons"]


def lesson(lid):
    return next(l for l in lessons() if l["id"] == lid)


def glossary(query=""):
    """Glossary entries whose term or meaning contains `query` (case-insensitive), sorted by term."""
    q = (query or "").strip().lower()
    rows = [g for g in data()["glossary"] if not q or q in g["term"].lower() or q in g["meaning"].lower()]
    return sorted(rows, key=lambda g: g["term"].lower())


def _area(h):
    return tx(HOUSE_AREA[h])


def _lord_house(chart, house):
    sign = SIGNS[(SIGNS.index(chart["ascendant"]["sign"]) + house - 1) % 12]
    lord = SIGN_LORD[sign]
    return sign, lord, chart["planets"][lord]["house"]


def _dignity(p, sign):
    if p in ("Rahu", "Ketu"):
        return None
    if EXALTATION_SIGN.get(p) == sign:
        return "exalted"
    if DEBILITATION_SIGN.get(p) == sign:
        return "debilitated"
    if sign in OWN_SIGNS.get(p, []):
        return "own"
    return None


# ------------------------------------------------------------------ walkthrough steps
def step_lagna(chart, reading, at):
    asc = chart["ascendant"]["sign"]
    sign, lord, lh = _lord_house(chart, 1)
    return tr('Your rising sign (Lagna) is {0} ({1} element, {2} quality). Its lord is {3}, which sits in your {4} house ({5}). So the '
              'way you meet life is coloured by {0}, and your energy tends to flow towards {5}.',
              asc, tx(ELEMENT[asc]), tx(QUALITY[asc]), lord, ordinal(lh), _area(lh))


def step_moon(chart, reading, at):
    m = chart["planets"]["Moon"]
    return tr('Your Moon is in {0}, in your {1} house ({2}), in the nakshatra {3} (pada {4}), ruled by {5}. The Moon shows the '
              'mind and feelings; {3} is your birth star, and {5} decided the first period of your Vimshottari dasha.',
              m["sign"], ordinal(m["house"]), _area(m["house"]), m["nakshatra"], m["nakshatra_pada"], m["nakshatra_lord"])


def step_sun_moon(chart, reading, at):
    s, m = chart["planets"]["Sun"], chart["planets"]["Moon"]
    return tr('Your Sun is in {0} in the {1} house ({2}), and your Moon is in {3} in the {4} house ({5}). The Sun shows the '
              'self and vitality; the Moon shows the mind.', s["sign"], ordinal(s["house"]), _area(s["house"]),
              m["sign"], ordinal(m["house"]), _area(m["house"]))


def step_houses(chart, reading, at):
    occ = {}
    for p in BODIES:
        occ.setdefault(chart["planets"][p]["house"], []).append(p)
    busy = sorted(occ.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    parts = [tr('the {0} house ({1}): {2}', ordinal(h), _area(h), ", ".join(tx(p) for p in ps)) for h, ps in sorted(occ.items())]
    empty = [h for h in range(1, 13) if h not in occ]
    text = tr('Planets sit in these houses - {0}.', "; ".join(parts))
    if busy and len(busy[0][1]) >= 2:
        text += " " + tr('Your busiest house is the {0} ({1}), so that area of life carries a lot of your chart\'s energy.',
                         ordinal(busy[0][0]), _area(busy[0][0]))
    if empty:
        text += " " + tr('Houses {0} are empty; they are judged by their lords, not by the emptiness.', ", ".join(str(h) for h in empty))
    return text


def step_lords(chart, reading, at):
    groups = {}
    for h in (1, 4, 7, 10):
        sign, lord, lh = _lord_house(chart, h)
        groups.setdefault(lord, []).append(h)
    out = []
    for lord, houses in groups.items():
        lh = chart["planets"][lord]["house"]
        if len(houses) == 1:
            h = houses[0]
            out.append(tr('The lord of your {0} house ({1}) is {2}, placed in the {3} house ({4}), which links {1} with {4}.',
                          ordinal(h), _area(h), lord, ordinal(lh), _area(lh)))
        else:
            out.append(tr('{0} rules both your {1} and {2} houses ({3}; {4}) and sits in the {5} house ({6}), which links both '
                          'areas with {6}.', lord, ordinal(houses[0]), ordinal(houses[1]), _area(houses[0]), _area(houses[1]),
                          ordinal(lh), _area(lh)))
    return " ".join(out)


def step_dignity(chart, reading, at):
    pl = chart["planets"]
    sun = pl["Sun"]["longitude"]
    found = {"exalted": [], "own": [], "debilitated": []}
    retro, comb = [], []
    for p in BODIES:
        d = _dignity(p, pl[p]["sign"])
        if d:
            found[d].append(tr('{0} in {1}', p, pl[p]["sign"]))
        if p not in ("Sun", "Moon", "Rahu", "Ketu") and pl[p].get("retrograde"):
            retro.append(tx(p))
        if p not in ("Sun", "Rahu", "Ketu") and is_combust(p, sun, pl[p]["longitude"], bool(pl[p].get("retrograde"))):
            comb.append(tx(p))
    lines = []
    if found["exalted"]:
        lines.append(tr('Exalted (at their strongest): {0}.', ", ".join(found["exalted"])))
    if found["own"]:
        lines.append(tr('In their own sign (comfortable): {0}.', ", ".join(found["own"])))
    if found["debilitated"]:
        lines.append(tr('Debilitated (needing support): {0}.', ", ".join(found["debilitated"])))
    if retro:
        lines.append(tr('Retrograde: {0}.', ", ".join(retro)))
    if comb:
        lines.append(tr('Combust (close to the Sun): {0}.', ", ".join(comb)))
    if not lines:
        lines.append(tx("None of your planets is exalted, debilitated or in its own sign, so their strength comes mainly from "
                        "the houses they sit in and the aspects they receive."))
    return " ".join(lines)


def step_aspects(chart, reading, at):
    out = []
    for p in ("Jupiter", "Saturn", "Mars"):
        h = chart["planets"][p]["house"]
        houses = sorted({((h - 1 + d - 1) % 12) + 1 for d in aspect_distances_for(p)})
        out.append(tr('{0} in your {1} house aspects houses {2}.', p, ordinal(h), ", ".join(str(x) for x in houses)))
    return " ".join(out) + " " + tx("Jupiter's aspect protects and expands the houses it looks at; Saturn's asks for patience "
                                    "and effort there; Mars's adds energy.")


def step_yogas(chart, reading, at):
    present = [y for y in (reading.get("yogas_present") or []) if y.get("present")]
    if not present:
        return tx("No classical yoga from the app's list is fully formed in your chart; that is common, and the chart is then "
                  "read through its houses, lords and periods.")
    hard = [y for y in present if "dosha" in ((y.get("kb_entry") or {}).get("yoga_type") or "").lower()]
    good = [y for y in present if y not in hard]
    parts = []
    if good:
        parts.append(tr('Supportive yogas in your chart: {0}.', ", ".join(tx(y["name"]) for y in good[:6])))
    if hard:
        parts.append(tr('Challenging combinations (doshas) in your chart: {0}. These show areas that need care, not fixed '
                        'outcomes, and many have classical cancellations.', ", ".join(tx(y["name"]) for y in hard[:6])))
    return " ".join(parts) + " " + tx("Open the Yogas screen to see how each is formed and how strong it is.")


def step_dasha(chart, reading, at):
    import remedy_plan
    run = remedy_plan.running_periods(chart, at)
    if not run:
        return tx("The running period could not be worked out for this chart.")
    return tr('You are in the main period (Mahadasha) of {0} until {1:%b %Y}, and the sub-period (Antardasha) of {2} until '
              '{3:%b %Y}. {0} sits in your {4} house ({5}) and {2} in your {6} house ({7}), so these areas are in focus now.',
              run["maha"], run["maha_end"], run["antar"], run["antar_end"],
              ordinal(chart["planets"][run["maha"]]["house"]), _area(chart["planets"][run["maha"]]["house"]),
              ordinal(chart["planets"][run["antar"]]["house"]), _area(chart["planets"][run["antar"]]["house"]))


def step_transits(chart, reading, at):
    import transits
    from extras import sade_sati_now
    ss = sade_sati_now(chart, at)
    g = transits.gochara_now(chart, at)["Jupiter"]
    sat = (tr('Saturn is now in {0}, the {1} sign from your Moon: {2}.', ss["saturn_sign"], ordinal(ss["house_from_moon"]), ss["kind"])
           if ss["kind"] else tr('Saturn is now in {0}, the {1} sign from your Moon, so you are not in Sade Sati.',
                                  ss["saturn_sign"], ordinal(ss["house_from_moon"])))
    jup = tr('Jupiter is in {0}, the {1} sign from your Moon, which is traditionally {2}.', g["sign"], ordinal(g["house_from_moon"]),
             tx("a favourable place") if g["favourable"] else tx("a less favourable place"))
    return sat + " " + jup


def step_navamsa(chart, reading, at):
    d9 = chart["ascendant"]["vargas"].get("D9")
    varg = [tx(p) for p in BODIES if chart["planets"][p]["vargas"].get("D9") == chart["planets"][p]["sign"]]
    text = tr('Your Navamsa (D9) rising sign is {0}.', d9)
    text += " " + (tr('Vargottama planets (same sign in D1 and D9, a mark of strength): {0}.', ", ".join(varg)) if varg else
                   tx("None of your planets is vargottama."))
    return text


def step_synthesis(chart, reading, at):
    return tx("Now look for themes that repeat. If the same house or planet appears in several of the steps above (for "
              "example as the Lagna lord, in a yoga and as the running dasha), that area is a real theme of your chart. "
              "One factor alone is only a hint.")


STEPS = [
    ("lagna", "Your rising sign", "signs", step_lagna),
    ("moon", "Your Moon and birth star", "nakshatras", step_moon),
    ("houses", "Which houses hold planets", "houses", step_houses),
    ("lords", "Where the key house lords sit", "lords", step_lords),
    ("dignity", "How strong each planet is", "dignity", step_dignity),
    ("aspects", "Who looks at what", "aspects", step_aspects),
    ("yogas", "Your yogas", "yogas", step_yogas),
    ("dasha", "Your running period", "dashas", step_dasha),
    ("transits", "Current transits", "transits", step_transits),
    ("navamsa", "The Navamsa check", "vargas", step_navamsa),
    ("synthesis", "Putting it together", "method", step_synthesis),
]
_EXTRA = {"sun_moon": step_sun_moon}


def walkthrough(chart, reading, at=None):
    """[{"id", "title", "lesson", "text"}] - the user's own chart, read step by step."""
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    return [{"id": sid, "title": title, "lesson": lid, "text": fn(chart, reading, at)} for sid, title, lid, fn in STEPS]


def try_in_chart(step_id, chart, reading, at=None):
    """The 'In your chart' text for a lesson's `try` key, or None."""
    if not step_id:
        return None
    at = at or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    fn = _EXTRA.get(step_id) or next((f for sid, _t, _l, f in STEPS if sid == step_id), None)
    return fn(chart, reading, at) if fn else None
