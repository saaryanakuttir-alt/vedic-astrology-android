"""planet_effects.py - a detailed, sectioned explanation of every planet in the person's own chart:
what its house does, what its sign does, how it gets on with the sign's ruler, special conditions
(combust / retrograde / vargottama), what it rules and looks at, and a plain-words verdict.

Returns structured data so the app can give each planet its own banner and labelled sections, and
the PDF can print the same thing:  [{planet, banner, sections: [(label, text), ...]}, ...]
"""
from extras import BODIES, _HOUSE_AREA, ordinal, planet_considerations, _list

GLANCE, SIMPLE = "At a glance", "In simple terms"      # the two sections Compact mode keeps


def _entry_text(entry, *fields):
    """Join the non-empty text fields of a knowledge-base entry into paragraphs."""
    return "\n\n".join(str(entry[f]).strip() for f in fields if entry and entry.get(f))


def _wanted(label, planet, focus):
    """Sections shared by both views, plus the house-only or sign-only ones (focus = None keeps everything)."""
    if focus is None or label in (GLANCE, SIMPLE, "What may happen") or label.startswith("Why the verdict"):
        return True
    is_house = label.startswith(f"{planet} in the ") or label == "What it rules and looks at"
    return is_house if focus == "house" else not is_house


def planet_effects(chart, reading, focus=None):
    """focus: None (everything), "house" (the house side only) or "sign" (the sign side only)."""
    cons = planet_considerations(chart)
    out = []
    for p in BODIES:
        d, c = (reading["planets"].get(p) or {}), cons[p]
        sign, house = c["sign"], c["house"]
        area = _HOUSE_AREA[house]
        rel = f" - {c['relation'].lower()}" if c["relation"] else ""
        secs = [(GLANCE, f"{p} is in {sign}{rel}, in your {ordinal(house)} house ({area}). Verdict: {c['tone']}. "
                         f"{c['summary'].split('. It rules')[0]}.")]

        ih = d.get("in_house")
        if ih:
            secs.append((f"{p} in the {ordinal(house)} house - {ih.get('house_theme', area)}",
                         _entry_text(ih, "summary", "effects", "dignity_note")))
        isg = d.get("in_sign")
        if isg:
            secs.append((f"{p} in {sign} - {isg.get('sign_theme', '')}".rstrip(" -"), _entry_text(isg, "summary", "effects")))
        lr = d.get("sign_lord_relationship")
        if lr and lr.get("reading"):
            r = lr["reading"]
            secs.append((f"{p} and {lr.get('lord')}, the ruler of {sign} - {r.get('grade_english', lr.get('grade', ''))}",
                         _entry_text(r, "summary", "effects")))
        specials = []
        for key, label in (("combustion", "Very close to the Sun (combust)"), ("retrograde_reading", "Moving backwards (retrograde)")):
            entry = d.get(key)
            if entry:
                specials.append((label, _entry_text(entry.get("reading") if "reading" in entry else entry, "summary", "effects")))
        vg = d.get("vargottama")
        if vg and vg.get("is_vargottama") and vg.get("reading"):
            specials.append(("Same sign in the Rasi and Navamsha charts (vargottama)", _entry_text(vg["reading"], "summary")))
        secs.extend(s for s in specials if s[1])

        rules = ("Rules your " + _list(f"{ordinal(h)} house ({_HOUSE_AREA[h]})" for h in c["lord_of"]) + "."
                 if c["lord_of"] else "As a shadow planet it does not rule a house of its own.")
        looks = ("Looks at your " + _list(f"{ordinal(h)} house ({_HOUSE_AREA[h]})" for h in c["aspects_houses"]) + "."
                 if c["aspects_houses"] else "")
        by = f"It is looked at by {_list(c['aspected_by'])}." if c["aspected_by"] else "No other planet looks at it directly."
        secs.append(("What it rules and looks at", " ".join(x for x in (rules, looks, by) if x)))
        secs.append(("Why the verdict is '" + c["tone"] + "'",
                     ("; ".join(c["reasons"]).capitalize() + ".") if c["reasons"] else "Nothing special helps or hurts it."))
        secs.append(("What may happen", c["effects"]))
        gloss = (d.get("plain_gloss") or "").strip()
        secs.append((SIMPLE, gloss or c["summary"]))
        where = {"house": f"{ordinal(house)} house", "sign": sign}.get(focus, f"{sign}, {ordinal(house)} house")
        out.append({"planet": p, "tone": c["tone"], "banner": f"{p.upper()}  -  {where}  -  {c['tone']}",
                    "sections": [s for s in secs if s[1] and _wanted(s[0], p, focus)]})
    return out


def planet_effects_text(chart, reading, compact=False):
    """The same content as plain text in the '--- Heading ---' convention (for screens that show text)."""
    parts = []
    for e in planet_effects(chart, reading):
        parts.append(f"=== {e['banner']} ===")
        for label, text in e["sections"]:
            if compact and label not in (GLANCE, SIMPLE):
                continue
            parts.append(f"--- {label} ---\n{text}")
    return "\n\n".join(parts)
