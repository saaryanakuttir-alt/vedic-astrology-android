"""
divisional.py — computes the resulting SIGN for a planet in each of the 12
vargas (divisional charts) covered by this project's knowledge base, given
its D1 (Rasi) sidereal longitude.

Each function's confidence level is noted in its docstring:

  VERIFIED    = confirmed against 2+ independent online sources during this
                project's verification passes (see divisional_charts.json
                and the divisional_D*_planet_in_sign.json verification_pass
                blocks).
  HIGH RECALL = extremely standard, uniformly-taught classical rule with
                very low ambiguity risk (D3/D4/D7/D9/D10/D12) — not freshly
                re-verified via live web search in this engine-building
                session, but consistent across virtually every classical
                and software source.
  NEEDS CHECK = starting-sign specifics not yet independently re-verified
                via live web search.

A follow-up online verification pass (after this module was first written)
confirmed D16, D20, and D24 exactly as implemented against BPHS-citing
sources (barbarapijan.com, blog.indianastrologysoftware.com,
astronavprayas.wordpress.com's direct BPHS Ch.6 translation — all three
agree independently). They are now marked VERIFIED below.

D60 was found to be genuinely disputed across sources during that same
pass — three incompatible descriptions of the sign-counting rule exist in
circulation. The originally-implemented "odd sign: same sign, even sign:
7th sign from it" rule turned out to have the WEAKEST sourcing (a single
site, no classical citation, no worked example) and has been REPLACED with
the rule backed by the strongest evidence found: a worked numerical example
attributed directly to Parashara (vedastrology.blogspot.com/2011/12/divisional-charts-d60.html)
and the literal BPHS-derived formula appearing near-verbatim on three
independent sites (including Wikipedia's Shashtyamsha article) — "multiply
the degrees traversed by 2, divide by 12, the remainder (0-indexed) is how
many signs forward from the natal sign to count; this counting is the SAME
for odd and even signs — the odd/even distinction only reverses which
direction the 60 named deities/benefic-malefic labels are read in, which
this module does not implement." D60 stays flagged below as the one varga
still worth a second cross-check against a reference chart from established
software (Jagannatha Hora / Parashara's Light) before relying on it, since
even the best-sourced variant found here wasn't cross-confirmed against
software source code.

Every function takes a D1 sidereal longitude in degrees [0, 360) and
returns the resulting sign name from panchanga.SIGNS.
"""
from panchanga import SIGNS, get_sign

MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
FIXED = {"Taurus", "Leo", "Scorpio", "Aquarius"}
DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}


def _sign_index(name):
    return SIGNS.index(name)


def _offset_sign(sign_name, offset):
    """Sign `offset` positions forward from sign_name (0 = same sign)."""
    return SIGNS[(_sign_index(sign_name) + offset) % 12]


def _is_odd_sign(sign_name):
    """Odd/even by classical convention: Aries=1st=odd, Taurus=2nd=even, etc."""
    return (_sign_index(sign_name) + 1) % 2 == 1


# ---------------------------------------------------------------------------
# D2 — Hora  [VERIFIED]
# ---------------------------------------------------------------------------
def d2_hora(longitude):
    sign, deg = get_sign(longitude)
    first_half = deg < 15.0
    if _is_odd_sign(sign):
        return "Leo" if first_half else "Cancer"
    else:
        return "Cancer" if first_half else "Leo"


# ---------------------------------------------------------------------------
# D3 — Drekkana  [HIGH RECALL]
# ---------------------------------------------------------------------------
def d3_drekkana(longitude):
    sign, deg = get_sign(longitude)
    part = int(deg // 10.0)  # 0, 1, or 2
    offset = {0: 0, 1: 4, 2: 8}[part]  # same sign, 5th from it, 9th from it
    return _offset_sign(sign, offset)


# ---------------------------------------------------------------------------
# D4 — Chaturthamsha  [HIGH RECALL]
# ---------------------------------------------------------------------------
def d4_chaturthamsha(longitude):
    sign, deg = get_sign(longitude)
    part = int(deg // 7.5)  # 0, 1, 2, or 3
    offset = {0: 0, 1: 3, 2: 6, 3: 9}[part]  # same, 4th, 7th, 10th from it
    return _offset_sign(sign, offset)


# ---------------------------------------------------------------------------
# D7 — Saptamsha  [HIGH RECALL]
# ---------------------------------------------------------------------------
def d7_saptamsha(longitude):
    sign, deg = get_sign(longitude)
    span = 30.0 / 7.0
    part = int(deg // span)
    part = min(part, 6)
    start_offset = 0 if _is_odd_sign(sign) else 6  # odd: from itself; even: from 7th from it
    return _offset_sign(sign, (start_offset + part) % 12)


# ---------------------------------------------------------------------------
# D9 — Navamsa  [HIGH RECALL — this one is very widely and consistently taught]
# ---------------------------------------------------------------------------
def d9_navamsa(longitude):
    sign, deg = get_sign(longitude)
    span = 30.0 / 9.0
    part = int(deg // span)
    part = min(part, 8)
    if sign in MOVABLE:
        start_offset = 0     # starts from the same sign
    elif FIXED and sign in FIXED:
        start_offset = 8     # starts from the 9th sign from it
    else:  # dual
        start_offset = 4     # starts from the 5th sign from it
    return _offset_sign(sign, (start_offset + part) % 12)


# ---------------------------------------------------------------------------
# D10 — Dashamsha  [HIGH RECALL]
# ---------------------------------------------------------------------------
def d10_dashamsha(longitude):
    sign, deg = get_sign(longitude)
    span = 3.0
    part = int(deg // span)
    part = min(part, 9)
    start_offset = 0 if _is_odd_sign(sign) else 8  # odd: from itself; even: from 9th from it
    return _offset_sign(sign, (start_offset + part) % 12)


# ---------------------------------------------------------------------------
# D12 — Dwadashamsha  [HIGH RECALL — same for every sign, no odd/even split]
# ---------------------------------------------------------------------------
def d12_dwadashamsha(longitude):
    sign, deg = get_sign(longitude)
    span = 2.5
    part = int(deg // span)
    part = min(part, 11)
    return _offset_sign(sign, part)  # always starts from the same sign


# ---------------------------------------------------------------------------
# D16 — Shodashamsha  [VERIFIED — confirmed against BPHS Ch.6 via 3
# independent sources, see module docstring]
# ---------------------------------------------------------------------------
_D16_START_BY_MODALITY = {"movable": "Aries", "fixed": "Leo", "dual": "Sagittarius"}


def d16_shodashamsha(longitude):
    sign, deg = get_sign(longitude)
    span = 30.0 / 16.0
    part = int(deg // span)
    part = min(part, 15)
    modality = "movable" if sign in MOVABLE else ("fixed" if sign in FIXED else "dual")
    start_sign = _D16_START_BY_MODALITY[modality]
    return _offset_sign(start_sign, part)


# ---------------------------------------------------------------------------
# D20 — Vimshamsha  [VERIFIED — confirmed against BPHS Ch.6 via 3
# independent sources, see module docstring]
# ---------------------------------------------------------------------------
_D20_START_BY_MODALITY = {"movable": "Aries", "fixed": "Sagittarius", "dual": "Leo"}


def d20_vimshamsha(longitude):
    sign, deg = get_sign(longitude)
    span = 1.5
    part = int(deg // span)
    part = min(part, 19)
    modality = "movable" if sign in MOVABLE else ("fixed" if sign in FIXED else "dual")
    start_sign = _D20_START_BY_MODALITY[modality]
    return _offset_sign(start_sign, part)


# ---------------------------------------------------------------------------
# D24 — Chaturvimshamsha  [VERIFIED — confirmed against BPHS Ch.6 via 3
# independent sources, see module docstring]
# ---------------------------------------------------------------------------
def d24_chaturvimshamsha(longitude):
    sign, deg = get_sign(longitude)
    span = 1.25
    part = int(deg // span)
    part = min(part, 23)
    start_sign = "Leo" if _is_odd_sign(sign) else "Cancer"
    return _offset_sign(start_sign, part)


# ---------------------------------------------------------------------------
# D30 — Trimshamsha  [VERIFIED — exact BPHS scheme confirmed against 2
# independent sources]
# ---------------------------------------------------------------------------
# (degree_start, degree_end, lord, resulting_sign)
_D30_ODD = [(0, 5, "Mars", "Aries"), (5, 10, "Saturn", "Aquarius"), (10, 18, "Jupiter", "Sagittarius"),
            (18, 25, "Mercury", "Gemini"), (25, 30, "Venus", "Libra")]
_D30_EVEN = [(0, 5, "Venus", "Taurus"), (5, 12, "Mercury", "Virgo"), (12, 20, "Jupiter", "Pisces"),
             (20, 25, "Saturn", "Capricorn"), (25, 30, "Mars", "Scorpio")]


def d30_trimshamsha(longitude):
    sign, deg = get_sign(longitude)
    table = _D30_ODD if _is_odd_sign(sign) else _D30_EVEN
    for start, end, lord, result_sign in table:
        if start <= deg < end or (end == 30 and deg == 30):
            return result_sign
    return table[-1][3]  # deg == 30.0 edge case


def d30_trimshamsha_lord(longitude):
    """Returns which of the 5 planetary lords (Mars/Saturn/Jupiter/Mercury/Venus)
    governs this exact degree — the traditional D30 technique that
    divisional_D30_planet_in_sign.json's calculation_note flags as a
    separate, not-yet-implemented layer. Included here since we have the
    table anyway."""
    sign, deg = get_sign(longitude)
    table = _D30_ODD if _is_odd_sign(sign) else _D30_EVEN
    for start, end, lord, result_sign in table:
        if start <= deg < end or (end == 30 and deg == 30):
            return lord
    return table[-1][2]


# ---------------------------------------------------------------------------
# D60 — Shashtiamsha  [BEST AVAILABLE, still worth a software cross-check —
# see module docstring for the corrected-vs-original rule and why. This
# module gives only the resulting SIGN; classical Shashtiamsha also assigns
# each of the 60 divisions its own presiding deity with a benefic/malefic
# quality, which is a separate lookup this module does not implement.]
#
# Formula (per the BPHS-derived wording on Wikipedia's Shashtyamsha article,
# astronavprayas.wordpress.com's direct BPHS Ch.6 translation, and the
# worked Parashara-attributed example on vedastrology.blogspot.com):
# multiply the degrees already traversed in the current sign by 2, take the
# integer part, divide by 12 — the remainder is how many signs FORWARD from
# the natal sign to count. This is the SAME for odd and even signs; the
# classical odd/even distinction only reverses which direction the 60 named
# deities/benefic-malefic labels are read in (not implemented here).
# ---------------------------------------------------------------------------
def d60_shashtiamsha(longitude):
    sign, deg = get_sign(longitude)
    offset = int(deg * 2) % 12
    return _offset_sign(sign, offset)


# ---------------------------------------------------------------------------
VARGA_FUNCTIONS = {
    "D2": d2_hora,
    "D3": d3_drekkana,
    "D4": d4_chaturthamsha,
    "D7": d7_saptamsha,
    "D9": d9_navamsa,
    "D10": d10_dashamsha,
    "D12": d12_dwadashamsha,
    "D16": d16_shodashamsha,
    "D20": d20_vimshamsha,
    "D24": d24_chaturvimshamsha,
    "D30": d30_trimshamsha,
    "D60": d60_shashtiamsha,
}

NEEDS_CHECK_VARGAS = {"D60"}  # D16/D20/D24 confirmed via online verification pass; see module docstring


def compute_all_vargas(d1_longitude):
    """Returns {"D2": "Leo", "D3": "Scorpio", ...} for all 12 vargas."""
    return {varga: fn(d1_longitude) for varga, fn in VARGA_FUNCTIONS.items()}
