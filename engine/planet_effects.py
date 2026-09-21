"""planet_effects.py - a detailed, sectioned explanation of every planet in the person's own chart:
what its house does, what its sign does, how it gets on with the sign's ruler, special conditions
(combust / retrograde / vargottama), what it rules and looks at, and a plain-words verdict.

Returns structured data so the app can give each planet its own banner and labelled sections, and
the PDF can print the same thing:  [{planet, banner, sections: [(label, text), ...]}, ...]
"""
from extras import BODIES, _HOUSE_AREA, ordinal, planet_considerations, _list
from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)

GLANCE, SIMPLE = "At a glance", "In simple terms"      # the two sections Compact mode keeps


def _entry_text(entry, *fields):
    """Join the non-empty text fields of a knowledge-base entry into paragraphs."""
    return "\n\n".join(str(entry[f]).strip() for f in fields if entry and entry.get(f))


def _wanted(kind, focus):
    """Sections shared by both views (kind "both"), plus the house-only or sign-only ones (focus = None keeps everything).
    The kind is decided here, in English, so it never depends on the (possibly translated) heading text."""
    return focus is None or kind == "both" or kind == focus


def planet_effects(chart, reading, focus=None):
    """focus: None (everything), "house" (the house side only) or "sign" (the sign side only)."""
    cons = planet_considerations(chart)
    out = []
    for p in BODIES:
        d, c = (reading["planets"].get(p) or {}), cons[p]
        sign, house = c["sign"], c["house"]
        area = _HOUSE_AREA[house]
        rel = tr(' - {0}', c['relation'].lower()) if c["relation"] else ""
        secs = [("both", GLANCE, tr('{0} is in {1}{2}, in your {3} house ({4}). Verdict: {5}. {6}.', p, sign, rel, ordinal(house), area, c['tone'], c['summary'].split('. It rules')[0]))]

        ih = d.get("in_house")
        if ih:
            secs.append(("house", tr('{0} in the {1} house - {2}', p, ordinal(house), ih.get('house_theme', area)),
                         _entry_text(ih, "summary", "effects", "dignity_note")))
        isg = d.get("in_sign")
        if isg:
            theme = isg.get('sign_theme', '')
            secs.append(("sign", tr('{0} in {1} - {2}', p, sign, theme) if theme else tr('{0} in {1}', p, sign),
                         _entry_text(isg, "summary", "effects")))
        lr = d.get("sign_lord_relationship")
        if lr and lr.get("reading"):
            r = lr["reading"]
            secs.append(("sign", tr('{0} and {1}, the ruler of {2} - {3}', p, lr.get('lord'), sign, r.get('grade_english', lr.get('grade', ''))),
                         _entry_text(r, "summary", "effects")))
        specials = []
        for key, label in (("combustion", "Very close to the Sun (combust)"), ("retrograde_reading", "Moving backwards (retrograde)")):
            entry = d.get(key)
            if entry:
                specials.append(("sign", label, _entry_text(entry.get("reading") if "reading" in entry else entry, "summary", "effects")))
        vg = d.get("vargottama")
        if vg and vg.get("is_vargottama") and vg.get("reading"):
            specials.append(("sign", tx("Same sign in the Rasi and Navamsha charts (vargottama)"), _entry_text(vg["reading"], "summary")))
        secs.extend(s for s in specials if s[2])

        rules = (tx("Rules your ") + _list(tr('{0} house ({1})', ordinal(h), _HOUSE_AREA[h]) for h in c["lord_of"]) + "."
                 if c["lord_of"] else tx("As a shadow planet it does not rule a house of its own."))
        looks = (tx("Looks at your ") + _list(tr('{0} house ({1})', ordinal(h), _HOUSE_AREA[h]) for h in c["aspects_houses"]) + "."
                 if c["aspects_houses"] else "")
        by = tr('It is looked at by {0}.', _list(c['aspected_by'])) if c["aspected_by"] else tx("No other planet looks at it directly.")
        secs.append(("house", tx("What it rules and looks at"), " ".join(x for x in (rules, looks, by) if x)))
        secs.append(("both", tx("Why the verdict is '") + tx(c["tone"]) + "'",
                     ("; ".join(c["reasons"]).capitalize() + ".") if c["reasons"] else tx("Nothing special helps or hurts it.")))
        secs.append(("both", tx("What may happen"), c["effects"]))
        gloss = (d.get("plain_gloss") or "").strip()
        secs.append(("both", SIMPLE, gloss or c["summary"]))
        where = {"house": tr('{0} house', ordinal(house)), "sign": sign}.get(focus, tr('{0}, {1} house', sign, ordinal(house)))
        out.append({"planet": p, "tone": c["tone"], "banner": tr('{0}  -  {1}  -  {2}', p.upper(), where, c['tone']),
                    "sections": [(label, text) for kind, label, text in secs if text and _wanted(kind, focus)]})
    return out


def planet_effects_text(chart, reading, compact=False):
    """The same content as plain text in the '--- Heading ---' convention (for screens that show text)."""
    parts = []
    for e in planet_effects(chart, reading):
        parts.append(tr('=== {0} ===', e['banner']))
        for label, text in e["sections"]:
            if compact and label not in (GLANCE, SIMPLE):
                continue
            parts.append(tr('--- {0} ---\n{1}', label, text))
    return "\n\n".join(parts)
