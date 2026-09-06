"""
family_bonds.py — readable narrative layers built on top of already-computed
facts, for two family relationships this project treats very differently on
purpose:

1. **Self <-> Life Partner**: `narrate_ashtakoot()` takes compatibility.py's
   raw Ashtakoot Guna Milan result (the classical 36-point MARRIAGE
   compatibility system) and adds a readable paragraph per koota plus an
   overall relationship synthesis. This is the classically correct use of
   Ashtakoot — it is a marriage-compatibility technique, nothing else.

3. **Karmic dimension, any two family members**: `build_karmic_family_connection()` adds a
   past-life/karmic-goal layer on top of EITHER relationship above — it reuses each person's
   own already-computed `karmic_and_past_life` fields (past_life_identity, main_karmic_goal,
   Rahu/Atmakaraka) rather than inventing a two-chart karmic technique, and reflects on how
   each person's Rahu-direction growth is the kind of unfamiliar ground the OTHER person can
   help hold. Included automatically for Self<->Life Partner and for Self<->every generated
   Child in `build_family_compatibility_report()` below.

2. **Self <-> Child (or any parent <-> child pair)**: `build_parent_child_connection()`
   deliberately does NOT run Ashtakoot Guna Milan on a parent/child pair —
   doing so would misapply a spouse-compatibility system to a relationship
   it was never designed to score, which would be a real methodological
   error, not a simplification worth documenting. Instead this builds a
   separate, appropriately-scoped "thematic connection" from three things
   that DO classically apply to any relationship:
     - **Moon-sign element** (Agni/fire, Prithvi/earth, Vayu/air, Jala/water)
       resonance — a broad classical temperament framework, presented as
       exactly that: broad, not a precise scored system.
     - **Gana** (Deva/Manushya/Rakshasa, from each person's own Avkahada
       Chakra) as a temperament-compatibility descriptor — reusing the
       SAME Gana classification Ashtakoot itself uses, just without
       Ashtakoot's marriage-specific scoring around it.
     - **Putrakaraka (parent) <-> Atmakaraka (child)**, the Jaimini
       significators for "this parent's disposition toward children" and
       "this child's own core nature" respectively (see chara_karaka.py) —
       compared thematically (are they the same planet, natural friends,
       or natural enemies per astrology_tables' classical friendship
       table), not scored numerically.

Everything here is presented as a traditional, symbolic lens for
reflection — not a scored verdict, not a claim about literal past-life
history between the two specific people, and not a substitute for actually
getting to know each other.
"""
from astrology_tables import SIGN_LORD

_KOOTA_DOMAIN_BLURBS = {
    "Varna": (
        "Varna reflects a broad spiritual/temperamental hierarchy between the two people — "
        "traditionally read as whether one partner's natural disposition can comfortably "
        "'lead' the household's spiritual and ethical tone without friction. Classically it's "
        "considered the lightest-weighted koota (1 of 36 points) precisely because it captures "
        "such a broad, background quality rather than a decisive one on its own."
    ),
    "Vashya": (
        "Vashya describes mutual magnetism and the capacity for each partner to hold the "
        "other's attention and cooperation — literally 'the ability to be drawn toward and "
        "stay attracted to' one another. It is traditionally read alongside Yoni as one of "
        "the more instinctive, less consciously-controlled dimensions of a relationship's "
        "day-to-day chemistry."
    ),
    "Tara": (
        "Tara (via each partner's nakshatra count from the other's) is read as an indicator "
        "of general wellbeing each partner brings to the other — health, safety, and everyday "
        "good fortune within the relationship. Because it's calculated bidirectionally (each "
        "partner counted from the other), it can score a partial result even when only one "
        "direction of the count lands favorably."
    ),
    "Yoni": (
        "Yoni, keyed to the symbolic animal of each partner's nakshatra, is the koota most "
        "associated with physical and instinctive compatibility — the bodily, non-verbal "
        "register of the relationship, sometimes described as how naturally two people's "
        "underlying temperaments 'move' alongside each other outside of conscious effort."
    ),
    "Graha Maitri": (
        "Graha Maitri compares the natural classical friendship between the planetary rulers "
        "of each partner's Moon sign — read as mental and intellectual compatibility, how "
        "naturally the two minds cooperate on ideas, values, and everyday decisions. It "
        "carries real weight (5 of 36 points) because classical texts treat a shared or "
        "friendly mental wavelength as foundational to a lasting partnership."
    ),
    "Gana": (
        "Gana (Deva/divine, Manushya/human, or Rakshasa/turbulent temperament) is read as "
        "basic temperament compatibility — how naturally the two personalities' underlying "
        "dispositions, energy levels, and emotional styles coexist day to day, independent "
        "of how much either partner consciously tries."
    ),
    "Bhakoot": (
        "Bhakoot, based on the angular distance between the two Moon signs, is traditionally "
        "tied to the relationship's capacity for love, family growth, and long-term "
        "prosperity together — several classical texts specifically connect it to the ease "
        "of building a shared household and raising a family over time."
    ),
    "Nadi": (
        "Nadi is the single highest-weighted koota (8 of 36 points) and is traditionally read "
        "as a genetic/constitutional compatibility marker most associated with the health and "
        "ease of having children together — its outsized weight reflects how seriously "
        "classical texts treat this particular dimension relative to the other seven."
    ),
}

_KOOTA_CONFIDENCE_NOTES = {
    "Varna": "Sourcing confidence: high — Varna's element-based derivation and its directional (higher-rank-should-not-be-lower) rule are described identically across every classical and contemporary source checked while building this project.",
    "Vashya": "Sourcing confidence: high for the whole-sign version used here — the one documented gap is that Sagittarius and Capricorn classically split at their midpoint into two different Vashya categories, which this project's whole-sign approach does not implement (see avkahada.py's own note).",
    "Tara": "Sourcing confidence: high — the nakshatra-count-modulo-9 method and which remainders count as unfavorable are consistently described across sources with no meaningful disagreement found.",
    "Yoni": "Sourcing confidence: high for same-animal and the 7 classical enemy pairs, but a documented simplification for everything else — no source found spells out a complete, consistent friendly/neutral/unfriendly matrix for every remaining animal pair, so this project scores those as a flat neutral rather than guessing at finer distinctions.",
    "Graha Maitri": "Sourcing confidence: high for the underlying planetary friendship table itself (cross-checked against its well-known asymmetric quirks), but the exact numeric point values for the two 'middle' friend/neutral/enemy combinations follow the best-supported convention rather than a single directly-cited numeric source.",
    "Gana": "Sourcing confidence: high — the three Gana groups and their pairwise point values are stable across every source checked.",
    "Bhakoot": "Sourcing confidence: moderate-high — the three dosha-causing sign-distance pairs and the lord-friendship cancellation rule are cited consistently, though not verified here against a primary classical Sanskrit text directly.",
    "Nadi": "Sourcing confidence: high for the base same/different-Nadi score, but classical cancellation exceptions (e.g. same nakshatra with different pada) are described inconsistently across sources and are deliberately NOT auto-applied here.",
}

_KOOTA_REFLECTION_PROMPTS = {
    "Varna": "Worth reflecting on: do the two of you find it easy to agree on values and who takes the lead in which areas of shared life, without it feeling like a power struggle?",
    "Vashya": "Worth reflecting on: does the everyday pull toward each other feel mutual and comfortable, or does it feel more one-sided?",
    "Tara": "Worth reflecting on: do you tend to bring out steadiness and wellbeing in each other, especially during stressful periods?",
    "Yoni": "Worth reflecting on: does physical and instinctive rapport come naturally, or does it need more deliberate attention than other parts of the relationship?",
    "Graha Maitri": "Worth reflecting on: when you disagree, does it feel like two compatible minds working through a problem, or two very different operating systems?",
    "Gana": "Worth reflecting on: do your baseline energy levels and emotional tempos match well, or does one of you regularly need to slow down (or speed up) for the other?",
    "Bhakoot": "Worth reflecting on: does building a shared life together — home, finances, family plans — feel like it flows, or does it take unusually deliberate coordination?",
    "Nadi": "Worth reflecting on: this specific koota is the one classical texts most flag for a conversation with a qualified astrologer rather than a DIY reading, given the cancellation-exception ambiguity documented in compatibility.py.",
}


def _koota_score_phrase(koota):
    pts, mx = koota["points"], koota["max_points"]
    if pts == mx:
        return "scores the full available points here"
    if pts == 0:
        return "scores zero here — the classical caution point for this specific koota"
    return f"scores a partial {pts} of {mx} points here"


def narrate_ashtakoot(result, label_a="Self", label_b="Life Partner"):
    """
    result: the dict returned by compatibility.compute_ashtakoot().
    Returns result with two additions:
        result["kootas"][i]["narrative"]  — a paragraph per koota
        result["overall_narrative"]       — a long-form synthesis paragraph
    (mutates and returns the same dict for convenience).
    """
    for koota in result["kootas"]:
        name = koota["koota"]
        blurb = _KOOTA_DOMAIN_BLURBS.get(name, "")
        prompt = _KOOTA_REFLECTION_PROMPTS.get(name, "")
        confidence = _KOOTA_CONFIDENCE_NOTES.get(name, "")
        phrase = _koota_score_phrase(koota)
        detail_bits = [f"{k.replace('_', ' ')}: {v}" for k, v in koota.items()
                        if k not in ("koota", "max_points", "points") and v is not None]
        detail_text = "; ".join(detail_bits)
        koota["narrative"] = (
            f"{name} ({koota['points']}/{koota['max_points']} points): {blurb} Between "
            f"{label_a} and {label_b}, this pairing {phrase}"
            + (f" — {detail_text}." if detail_text else ".")
            + (f" {prompt}" if prompt else "")
            + (f" {confidence}" if confidence else "")
        )

    total, mx = result["total_points"], result["max_points"]
    strong = [k["koota"] for k in result["kootas"] if k["points"] == k["max_points"]]
    weak = [k["koota"] for k in result["kootas"] if k["points"] == 0]
    overall = (
        f"Across all eight kootas, {label_a} and {label_b} score {total:.1f} out of {mx} "
        f"points — {result['verdict']}. "
    )
    if strong:
        overall += f"The strongest-scoring areas are {', '.join(strong)}, suggesting these are natural points of ease in the relationship. "
    if weak:
        overall += (
            f"The koota(s) scoring zero — {', '.join(weak)} — are the classical areas this "
            f"system flags for conscious attention rather than automatic ease; this does not "
            f"mean incompatibility, only that these specific dimensions may take more "
            f"deliberate effort than others. "
        )
    if result.get("nadi_dosha_present"):
        overall += (
            "Nadi Dosha (same Nadi group) is present — classically the most cautioned "
            "combination in this system, though traditional texts also describe cancellation "
            "exceptions that a qualified astrologer should confirm rather than assuming either way. "
        )
    if result.get("bhakoot_dosha_present"):
        overall += (
            "Bhakoot Dosha (an inauspicious Moon-sign distance not cancelled by lord-friendship) "
            "is also present, traditionally read as worth attention for long-term family growth "
            "and harmony specifically. "
        )
    overall += (
        "As with every technique in this project, Ashtakoot is one traditional lens among "
        "several a real relationship should be evaluated by — see compatibility.py's own "
        "docstring for exactly which parts of this scoring are well-sourced versus documented "
        "simplification. In practice, a high total score is best read as 'several structural "
        "supports are already in place,' not as a guarantee, and a lower or partial score is "
        "best read as 'certain dimensions may need more conscious attention,' not as a verdict "
        "against the relationship — every long-term partnership, regardless of its Ashtakoot "
        "total, still depends far more on how two specific people choose to treat each other "
        "day to day than on any one classical calculation. The eight koota breakdowns below are "
        "meant to be read as a map of WHERE to pay attention, not as a substitute for actually "
        f"getting to know how {label_a} and {label_b} communicate, handle stress, and support "
        "each other in practice."
    )
    result["overall_narrative"] = overall
    result["methodology_note"] = (
        "Ashtakoot Guna Milan compares eight dimensions ('kootas') of each partner's Moon "
        "sign and nakshatra, weighted from 1 to 8 points (36 total), and is the most widely "
        "used classical Vedic marriage-compatibility technique. Varna, Gana, Nadi, and the "
        "Tara counting method are consistently described identically across every classical "
        "and contemporary source checked while building this project — high confidence. "
        "Yoni's finer middle tier and Graha Maitri's exact middle-combination point values are "
        "documented simplifications where sources genuinely disagree (see compatibility.py). "
        "The full breakdown below shows each koota's domain, this specific pairing's score, "
        "and a reflection prompt — not a pass/fail judgment on the relationship itself."
    )
    return result


# ---------------------------------------------------------------------------
# Parent <-> Child thematic connection (NOT Ashtakoot — see module docstring)
# ---------------------------------------------------------------------------
_ELEMENT_BY_SIGN = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

_ELEMENT_RESONANCE = {
    frozenset({"Fire", "Air"}): ("classically complementary", "fire and air traditionally sustain and energize each other"),
    frozenset({"Earth", "Water"}): ("classically complementary", "earth and water traditionally nurture and give shape to each other"),
    frozenset({"Fire", "Water"}): ("classically contrasting", "fire and water traditionally temper and challenge each other, needing conscious patience"),
    frozenset({"Earth", "Air"}): ("classically contrasting", "earth and air traditionally move at different paces, needing conscious patience"),
    frozenset({"Fire", "Earth"}): ("classically mixed", "fire and earth traditionally combine drive with practicality once aligned"),
    frozenset({"Air", "Water"}): ("classically mixed", "air and water traditionally combine ideas with feeling once aligned"),
}

_GANA_RESONANCE = {
    frozenset({"Deva"}): "both share the Deva (refined/gentle) temperament group — an easy natural resonance",
    frozenset({"Manushya"}): "both share the Manushya (balanced/human) temperament group — a grounded natural resonance",
    frozenset({"Rakshasa"}): "both share the Rakshasa (intense/driven) temperament group — a high-energy natural resonance",
    frozenset({"Deva", "Manushya"}): "one Deva, one Manushya — a generally cooperative pairing classically considered mild and workable",
    frozenset({"Manushya", "Rakshasa"}): "one Manushya, one Rakshasa — a pairing classical texts suggest benefits from patience with differing paces and intensities",
    frozenset({"Deva", "Rakshasa"}): "one Deva, one Rakshasa — the temperamentally furthest-apart classical pairing, traditionally suggesting real value in deliberately meeting each other's very different natural styles",
}

_PARENT_CHILD_CAVEAT = (
    "This is a thematic, symbolic exploration, not a scored compatibility test — Ashtakoot "
    "Guna Milan is a classical MARRIAGE-compatibility system and is deliberately not applied "
    "here to a parent/child pair, which it was never designed to evaluate. Nothing below "
    "describes a literal past-life history between these two specific people; it reads "
    "classical significators symbolically, the same way the Karmic & Past Life tab does for "
    "an individual chart."
)


def build_parent_child_connection(parent_reading, parent_karakas, parent_avkahada,
                                   parent_moon_sign, parent_moon_nakshatra,
                                   child_reading, child_karakas, child_avkahada,
                                   child_moon_sign, child_moon_nakshatra,
                                   parent_label="Self", child_label="Child"):
    """
    parent_reading / child_reading: the dict from rule_engine.generate_reading()
        for each person (used for planets_reading via ["planets"]).
    parent_karakas / child_karakas: rule_engine reading["chara_karakas"].
    parent_avkahada / child_avkahada: chart["avkahada_chakra"] for each person.
    parent_moon_sign / child_moon_sign, *_moon_nakshatra: each person's Moon
        placement (chart["planets"]["Moon"]["sign"/"nakshatra"]).

    Returns a dict: {"elemental_resonance": {...}, "temperament_resonance": {...},
                      "putrakaraka_atmakaraka_link": {...}, "narrative": "...",
                      "caveat": "..."}
    """
    import chara_karaka
    from compatibility import _natural_relation  # reuse the already-verified friendship table

    parent_element = _ELEMENT_BY_SIGN[parent_moon_sign]
    child_element = _ELEMENT_BY_SIGN[child_moon_sign]
    if parent_element == child_element:
        elemental = {
            "parent_element": parent_element, "child_element": child_element,
            "relation": "same element",
            "note": f"Both Moon signs share the {parent_element} element — a natural, intuitive resonance in temperament and emotional pacing.",
        }
    else:
        key = frozenset({parent_element, child_element})
        relation, note = _ELEMENT_RESONANCE.get(key, ("classically mixed", "these elements combine in varied ways depending on the rest of each chart"))
        elemental = {"parent_element": parent_element, "child_element": child_element, "relation": relation, "note": note.capitalize() + "."}

    parent_gana = parent_avkahada["gana"]
    child_gana = child_avkahada["gana"]
    gana_key = frozenset({parent_gana, child_gana})
    temperament = {
        "parent_gana": parent_gana, "child_gana": child_gana,
        "note": _GANA_RESONANCE.get(gana_key, f"{parent_gana} and {child_gana} — a mixed temperament pairing.").capitalize() + ".",
    }

    pk = chara_karaka.get_karaka(parent_karakas, "PK")
    ak = chara_karaka.get_karaka(child_karakas, "AK")
    if pk["planet"] == ak["planet"]:
        pk_ak_relation = (
            f"{parent_label}'s Putrakaraka (children significator) and {child_label}'s own "
            f"Atmakaraka (soul significator) are the SAME planet ({pk['planet']}) — a notable "
            f"classical resonance, traditionally read as an unusually direct thematic thread "
            f"between what {parent_label} seeks through children and what {child_label}'s own "
            f"chart centers its identity around."
        )
    else:
        rel_forward = _natural_relation(pk["planet"], ak["planet"])
        rel_backward = _natural_relation(ak["planet"], pk["planet"])
        if "friend" in (rel_forward, rel_backward):
            tone = "a naturally cooperative classical relationship (at least one of the two planets calls the other a natural friend)"
        elif "enemy" in (rel_forward, rel_backward):
            tone = "a classically effortful relationship (at least one of the two planets calls the other a natural enemy) — traditionally read as more growth-through-friction than automatic ease"
        else:
            tone = "a classically neutral relationship — neither particularly easy nor particularly effortful by planetary temperament alone"
        pk_ak_relation = (
            f"{parent_label}'s Putrakaraka is {pk['planet']}; {child_label}'s Atmakaraka is "
            f"{ak['planet']}. By classical planetary friendship, {pk['planet']} and "
            f"{ak['planet']} share {tone}."
        )
    putrakaraka_link = {"parent_putrakaraka": pk["planet"], "child_atmakaraka": ak["planet"], "note": pk_ak_relation}

    narrative = (
        f"Three traditional threads, read together, sketch a symbolic picture of the "
        f"{parent_label}-{child_label} bond. First, by Moon-sign element: {elemental['note']} "
        f"Second, by temperament group (Gana): {temperament['note']} Third, by Jaimini "
        f"significator: {putrakaraka_link['note']} None of this is a scored verdict the way "
        f"Ashtakoot is for a marriage — it is a thematic lens for reflecting on natural "
        f"tendencies in how {parent_label} and {child_label} may relate, not a prediction or a "
        f"claim about a specific shared history."
    )

    reflection = (
        f"In practice, these three threads are most useful as a starting point for noticing "
        f"patterns rather than as an explanation to lean on too heavily. An elemental match "
        f"(or mismatch) between {parent_label} and {child_label} says something about natural "
        f"pacing — how quickly each of you moves through emotions, decisions, or excitement — "
        f"and mismatches here are common and workable, not a warning sign. The Gana comparison "
        f"speaks to baseline temperament: a shared Gana often means {parent_label} and "
        f"{child_label} 'get' each other's moods quickly, while a mixed Gana pairing (as with "
        f"any two family members) simply means each may need to explain their own reactions a "
        f"little more explicitly for the other to follow. The Putrakaraka-Atmakaraka thread is "
        f"the most classically specific of the three: it points at what {parent_label}'s own "
        f"chart says about parenting instinctively, set against what {child_label}'s own chart "
        f"says about their core drive — where those two align, parenting can feel intuitive; "
        f"where they differ, {parent_label} may find that supporting {child_label} well means "
        f"consciously stepping outside a first instinct rather than assuming it will land the "
        f"same way it would for a differently-wired child."
    )

    methodology_note = (
        "This parent-child thematic connection deliberately uses three DIFFERENT classical "
        "tools than Ashtakoot, because Ashtakoot itself was designed and is taught exclusively "
        "as a marriage-compatibility system between prospective spouses — applying its scoring "
        "to a parent and child would misuse a technique outside its intended scope, not merely "
        "simplify it. Moon-sign element (Tattva) theory groups the 12 signs into Fire (Agni), "
        "Earth (Prithvi), Air (Vayu), and Water (Jala) — a broad classical temperament "
        "framework used across both marriage and family analysis, not marriage-specific. Gana "
        "(Deva/Manushya/Rakshasa) is the same nakshatra-based temperament classification "
        "Ashtakoot itself draws on for its own Gana koota, reused here purely as a "
        "temperament descriptor with no marriage-specific scoring attached. The Putrakaraka "
        "(Jaimini's children-significator) and Atmakaraka (soul-significator) comparison is "
        "the most classically specific of the three: Putrakaraka describes a PARENT's own "
        "disposition toward children in general, while Atmakaraka describes a CHILD's own "
        "core identity — comparing the two speaks to how naturally that parent's instinctive "
        "parenting style may resonate with that particular child's nature, not a verdict on "
        "the relationship's quality."
    )

    return {
        "elemental_resonance": elemental,
        "temperament_resonance": temperament,
        "putrakaraka_atmakaraka_link": putrakaraka_link,
        "narrative": narrative,
        "reflection": reflection,
        "methodology_note": methodology_note,
        "caveat": _PARENT_CHILD_CAVEAT,
    }


def _individual_relational_disposition(reading, label):
    """An excerpt of ONE person's own relational significators (already
    computed by rule_engine's karmic section and house-lord readings) —
    used as context before comparing two charts, so the Family
    Compatibility report reads as a continuation of that person's own
    profile rather than a cold start. Combines the Jaimini Atmakaraka/
    Darakaraka/Putrakaraka significators with the traditional Parashari
    7th-house-lord placement (the classical marriage-house significator),
    so both astrological frameworks this project uses are represented."""
    k = reading["karmic_and_past_life"]
    ak, dk, pk = k["atmakaraka"], k["darakaraka"], k["putrakaraka"]
    seventh = reading["house_lords"][7]

    bits = [
        f"{label}'s Atmakaraka (soul-significator) is {ak['planet']} in {ak['sign']}, house "
        f"{ak['house']} — the core drive this person's chart is organized around."
    ]
    bits.append(
        f"{label}'s Darakaraka (Jaimini's spouse-significator) is {dk['planet']}, placed in "
        f"{dk['sign']}, house {dk['house']}."
    )
    if dk.get("in_sign_effects"):
        bits.append(dk["in_sign_effects"])
    if seventh.get("reading"):
        bits.append(
            f"By the older Parashari system, the 7th house (marriage/partnership) is ruled by "
            f"{seventh['lord']} (in {seventh['lord_sign']}), placed in house "
            f"{seventh['placed_in_house']}: {seventh['reading'].get('effects') or seventh['reading'].get('summary')}"
        )
    bits.append(
        f"{label}'s Putrakaraka (children-significator) is {pk['planet']}, placed in "
        f"{pk['sign']}, house {pk['house']}."
    )
    if pk.get("in_sign_effects"):
        bits.append(pk["in_sign_effects"])
    return " ".join(bits)


_KARMIC_FAMILY_CAVEAT = (
    "This karmic view is a symbolic, traditional lens — it reads each person's own Ketu "
    "(past-life imprint), Rahu (this-life growth direction), and Atmakaraka (soul focus), then "
    "reflects on how the two might support each other. It is NOT a claim about a literal shared "
    "past life between these two specific people, and NOT a verdict on the relationship."
)


def build_karmic_family_connection(a_reading, a_label, b_reading, b_label):
    """A karmic-lens layer over any two family members: what past-life
    imprint each carries, what each one's main goal this life is, and how
    each can practically support the other toward that goal. Reuses the
    per-person karmic fields rule_engine already computes (past_life_identity,
    main_karmic_goal, rahu, atmakaraka) so nothing new is invented here."""
    ka = a_reading["karmic_and_past_life"]
    kb = b_reading["karmic_and_past_life"]

    def past_life_line(k, label):
        pli = k.get("past_life_identity")
        if pli and pli.get("summary"):
            return f"{label}: {pli['summary']}"
        ketu = k.get("ketu", {})
        return (f"{label}: Ketu in {ketu.get('sign', '?')} (house {ketu.get('house', '?')}) marks "
                f"the strongest past-life imprint.")

    def goal_line(k, label):
        goal = k.get("main_karmic_goal")
        if goal:
            return f"{label}'s main goal this life: {goal}"
        rahu = k.get("rahu", {})
        return (f"{label}'s growth this life pulls toward Rahu in {rahu.get('sign', '?')} "
                f"(house {rahu.get('house', '?')}) — the unfamiliar direction the soul is here to develop.")

    past_lives = (
        "Past-life imprints each person carries into this bond:\n"
        + past_life_line(ka, a_label) + "\n" + past_life_line(kb, b_label)
    )
    goals = (
        "The main goals of this life for each:\n"
        + goal_line(ka, a_label) + "\n" + goal_line(kb, b_label)
    )

    # How each can support the other: each person's growth direction (Rahu)
    # is exactly the ground the OTHER can help hold, since Rahu's territory
    # is by definition unfamiliar and uncomfortable at first.
    a_rahu = ka.get("rahu", {})
    b_rahu = kb.get("rahu", {})
    support = (
        "How each can support the other toward these goals:\n"
        f"{a_label} grows by leaning into the themes of Rahu in {a_rahu.get('sign', '?')} "
        f"(house {a_rahu.get('house', '?')}) — territory that feels unfamiliar at first, so "
        f"{b_label} helps most by encouraging {a_label} there rather than letting them retreat to "
        f"the old, over-comfortable Ketu pattern. "
        f"Reciprocally, {b_label} grows by leaning into Rahu in {b_rahu.get('sign', '?')} "
        f"(house {b_rahu.get('house', '?')}), and {a_label} helps most by steadying and "
        f"encouraging {b_label} in exactly that direction. In practice, each person's natural "
        f"past-life strengths (their Ketu arena) are often precisely what the other one is still "
        f"reaching to build (their Rahu direction) — which is what makes family members such "
        f"effective, if sometimes uncomfortable, mirrors for each other's growth."
    )

    narrative = past_lives + "\n\n" + goals + "\n\n" + support + "\n\n" + _KARMIC_FAMILY_CAVEAT
    return {
        "past_lives": past_lives,
        "goals": goals,
        "support": support,
        "narrative": narrative,
        "caveat": _KARMIC_FAMILY_CAVEAT,
    }


def build_family_compatibility_report(self_reading, self_chart, partner_reading=None, partner_chart=None,
                                       children=None, self_label="Self", partner_label="Life Partner"):
    """
    Assembles the full, readable Family Compatibility report: each
    generated person's own relational disposition (from their individual
    karmic section), the Self<->Partner Ashtakoot breakdown (if a partner
    chart is given), and a Self<->Child thematic connection for every
    entry in `children` (a list of (label, chart, reading) tuples).

    Returns {"text": "<<the full assembled report, ready to display/export>>",
             "ashtakoot": {...} or None, "parent_child": {label: {...}, ...}}
    """
    import compatibility as compat

    children = children or []
    sections = []
    sections.append(
        f"=== Family Compatibility Report ===\n\n"
        f"This report brings together everyone whose chart has been generated so far — "
        f"{self_label}"
        + (f", {partner_label}" if partner_chart else "")
        + (f", and {', '.join(c[0] for c in children)}" if children else "")
        + ". It starts with each person's own relational disposition (already computed on their "
        "individual Karmic & Past Life tab), then adds cross-chart comparisons: Ashtakoot Guna "
        "Milan for Self and Life Partner specifically (the classical marriage-compatibility "
        "technique), and a separately-scoped thematic connection for Self and each child (which "
        "deliberately does NOT use Ashtakoot — see the Parent-Child section below for why)."
    )

    sections.append("--- " + self_label + "'s Own Relational Disposition ---\n" +
                     _individual_relational_disposition(self_reading, self_label))

    ashtakoot_result = None
    if partner_chart and partner_reading:
        sections.append("--- " + partner_label + "'s Own Relational Disposition ---\n" +
                         _individual_relational_disposition(partner_reading, partner_label))

        def person(chart):
            return {
                "moon_sign": chart["planets"]["Moon"]["sign"],
                "nakshatra": chart["planets"]["Moon"]["nakshatra"],
                "sex": chart["birth_input"]["sex"],
            }
        ashtakoot_result = narrate_ashtakoot(
            compat.compute_ashtakoot(person(self_chart), person(partner_chart)),
            self_label, partner_label,
        )
        koota_lines = "\n\n".join(k["narrative"] for k in ashtakoot_result["kootas"])
        sections.append(
            f"--- Ashtakoot Guna Milan: {self_label} <-> {partner_label} ---\n"
            f"{ashtakoot_result['methodology_note']}\n\n{koota_lines}\n\n{ashtakoot_result['overall_narrative']}"
        )
        # Karmic dimension for the couple: past-life imprints, each one's
        # main goal this life, and how they can support each other toward it.
        partner_karmic = build_karmic_family_connection(self_reading, self_label, partner_reading, partner_label)
        sections.append(
            f"--- Karmic Connection: {self_label} <-> {partner_label} (past lives, goals & mutual support) ---\n"
            f"{partner_karmic['narrative']}"
        )

    parent_child_results = {}
    for child_label, child_chart, child_reading in children:
        pcc = build_parent_child_connection(
            self_reading, self_reading["chara_karakas"], self_chart["avkahada_chakra"],
            self_chart["planets"]["Moon"]["sign"], self_chart["planets"]["Moon"]["nakshatra"],
            child_reading, child_reading["chara_karakas"], child_chart["avkahada_chakra"],
            child_chart["planets"]["Moon"]["sign"], child_chart["planets"]["Moon"]["nakshatra"],
            self_label, child_label,
        )
        parent_child_results[child_label] = pcc
        sections.append(
            f"--- Parent-Child Thematic Connection: {self_label} <-> {child_label} ---\n"
            f"{pcc['methodology_note']}\n\n{pcc['narrative']}\n\n{pcc['reflection']}\n\n{pcc['caveat']}"
        )
        # Karmic dimension for the parent-child pair too: past-life imprints,
        # each one's main goal this life, and how they can support each other.
        child_karmic = build_karmic_family_connection(self_reading, self_label, child_reading, child_label)
        pcc["karmic_connection"] = child_karmic
        sections.append(
            f"--- Karmic Connection: {self_label} <-> {child_label} (past lives, goals & mutual support) ---\n"
            f"{child_karmic['narrative']}"
        )

    sections = [s for s in sections if s]

    return {
        "text": "\n\n".join(sections),
        "ashtakoot": ashtakoot_result,
        "parent_child": parent_child_results,
    }
