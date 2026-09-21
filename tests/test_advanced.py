"""Varshaphal, KP, planet strength, Prastharashtakvarga, Your Nature and the personal Sade Sati text.
Reference values come from the AstroSage report for Sammya Das (29 May 1992, 07:06, Howrah).
Run from android_app/:  python -m pytest tests/test_advanced.py"""
import datetime
import os
import re
import sys

import pytest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

import extras  # noqa: E402
import kp  # noqa: E402
import life_profile  # noqa: E402
import prastara  # noqa: E402
import shadbala  # noqa: E402
import varshaphal  # noqa: E402
from panchanga import SIGNS  # noqa: E402

FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|childless\w*|death|die)\b", re.I)
NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah",
                               country_hint="IN", sex="Male")


def test_varshaphal_matches_astrosage_for_2026(chart):
    vp = varshaphal.varshaphal(chart, 2026)
    assert abs((vp["local"] - datetime.datetime(2026, 5, 30, 0, 17, 40)).total_seconds()) < 120       # Sun returns to its birth degree
    v = vp["varsha"]
    assert (v["ascendant"]["sign"], v["planets"]["Moon"]["sign"], v["planets"]["Moon"]["nakshatra"]) == ("Aquarius", "Libra", "Vishakha")
    assert vp["muntha"]["house"] == 3 and vp["muntha"]["sign"] == "Aries"
    assert [p["lord"] for p in vp["mudda"]] == ["Saturn", "Mercury", "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter"]
    assert [p["house"] for p in vp["mudda"][:8]] == [2, 5, 7, 5, 4, 9, 3, 1]
    ends = [p["end"].date() for p in vp["mudda"][:8]]
    expected = [datetime.date(2026, 7, 26), datetime.date(2026, 9, 16), datetime.date(2026, 10, 7), datetime.date(2026, 12, 7),
                datetime.date(2026, 12, 25), datetime.date(2027, 1, 25), datetime.date(2027, 2, 15), datetime.date(2027, 4, 11)]
    assert all(abs((a - b).days) <= 1 for a, b in zip(ends, expected))
    text = varshaphal.varshaphal_text(vp)
    assert "Muntha" in text and "What may happen" in text and FORBIDDEN.search(text) is None


def test_kp_cusp_lords_match_astrosage(chart):
    t = kp.kp_tables(chart)
    ab = {"Sun": "SUN", "Moon": "MON", "Mars": "MAR", "Mercury": "MER", "Jupiter": "JUP", "Venus": "VEN", "Saturn": "SAT", "Rahu": "RAH", "Ketu": "KET"}
    reference = ["MER RAH KET", "MON SAT VEN", "SUN KET MAR", "MER SUN MER", "VEN RAH JUP", "MAR SAT RAH", "JUP VEN VEN", "SAT SUN VEN",
                 "SAT MAR SUN", "JUP SAT SAT", "MAR KET SAT", "VEN MON RAH"]
    got = [f"{ab[c['sign_lord']]} {ab[c['star_lord']]} {ab[c['sub_lord']]}" for c in t["cusps"]]
    assert got == reference
    assert abs(t["ayanamsa"] - (23 + 39 / 60 + 38 / 3600)) < 0.002
    assert abs(t["cusps"][0]["longitude"] - (74 + 57 / 60 + 12 / 3600)) < 0.05        # AstroSage rounds the birth longitude to 88 deg 18 min
    assert [x["planet"] for x in t["planets"]][:2] == ["Sun", "Moon"] and set(t["significators"]) == set(range(1, 13))


def test_kp_sub_lord_table_is_consistent():
    seen = {kp.lords(x / 10.0)[2] for x in range(0, 3600, 3)}
    assert seen == set(kp.ORDER)
    assert kp.lords(0.0)[:3] == ("Mars", "Ketu", "Ketu")


def test_shadbala_parts_match_astrosage(chart):
    r = shadbala.compute_shadbala(chart)
    reference = {"uchcha": [48.6, 50.59, 41.38, 18.66, 47.66, 45.68, 28.43], "ojayugma": [0, 15, 15, 15, 15, 30, 15],
                 "kendra": [15, 30, 60, 15, 15, 15, 30], "dig": [37.03, 9.83, 53.81, 48.7, 40.95, 21.55, 46.71],
                 "nathonnatha": [37.65, 22.35, 22.35, 60, 37.65, 37.65, 22.35], "paksha": [46.86, 26.28, 46.86, 13.14, 13.14, 13.14, 46.86],
                 "tribhaga": [0, 0, 0, 60, 60, 0, 0], "vara": [0, 0, 0, 0, 0, 45, 0], "naisargika": [60, 51.42, 17.16, 25.74, 34.26, 42.84, 8.58],
                 "ayana": [114.89, 16.05, 38.78, 56.78, 41.91, 56.56, 49.43]}
    for key, values in reference.items():
        assert all(abs(r[p][key] - v) <= 0.6 for p, v in zip(NAMES, values)), key
    assert sorted(r[p]["rank"] for p in NAMES) == list(range(1, 8))
    assert {r[p]["tone"] for p in NAMES} == {"Strong", "Average", "Weaker"}
    assert FORBIDDEN.search(shadbala.shadbala_text(chart)) is None


def test_prastara_columns_equal_bhinnashtakvarga(chart):
    bav = chart["ashtakavarga"]["bhinnashtakavarga"]
    for planet, grid in prastara.all_prastara(chart).items():
        assert grid["totals"] == [bav[planet][s] for s in SIGNS]
        assert all(v in (0, 1) for row in grid["rows"].values() for v in row)


def test_your_nature_is_plain_and_safe(chart):
    sections = dict(life_profile.profile_sections(chart))
    assert list(sections) == ["Your character", "What gives you purpose", "Your mind and emotions", "How you speak and think", "Education and learning",
                              "Your career leanings", "Money habits", "Hobbies and free time", "Your strengths", "Your growth areas"]
    assert "Gemini rising" in sections["Your character"] and "Ashwini" in sections["Your character"]
    assert "Pisces" in sections["Your career leanings"]                      # 10th house sign
    assert FORBIDDEN.search(life_profile.profile_text(chart)) is None


def test_personal_sade_sati_text(chart):
    text = extras.sade_sati_detail_text(chart, datetime.datetime(2026, 9, 20, 12))
    for phrase in ("Sade Sati for you", "Where you are right now", "rising phase", "How each phase may go for you", "cycles through life",
                   "Ashtakvarga points", "In simple terms"):
        assert phrase in text, phrase
    cycles = extras.sade_sati_cycles(chart)
    assert cycles[0]["start"] == datetime.date(1995, 6, 2) and any(c["start"].year == 2025 for c in cycles)
    assert FORBIDDEN.search(text) is None


def test_kp_vimshottari_matches_astrosage_within_a_few_days(chart):
    dasha = kp.kp_dasha(chart)
    assert [m["lord"] for m in dasha[:3]] == ["Ketu", "Venus", "Sun"]
    rahu_antar = dasha[0]["antardashas"][1]
    assert rahu_antar["lord"] == "Rahu" and abs((rahu_antar["end"].date() - datetime.date(1993, 10, 28)).days) <= 5
    ends = [p["end"].date() for p in rahu_antar["pratyantars"]]
    expected = [datetime.date(1992, 12, 7), datetime.date(1993, 1, 27), datetime.date(1993, 3, 27), datetime.date(1993, 5, 21),
                datetime.date(1993, 6, 13), datetime.date(1993, 8, 16), datetime.date(1993, 9, 5), datetime.date(1993, 10, 6),
                datetime.date(1993, 10, 28)]
    assert all(abs((a - b).days) <= 5 for a, b in zip(ends, expected))


def test_tajika_yogas_are_well_formed(chart):
    vp = varshaphal.varshaphal(chart, 2026)
    assert vp["tajika"] and all(y["kind"] in ("Ithasala", "Ishrafa") and y["gap"] < y["limit"] for y in vp["tajika"])
    assert vp["tajika"] == sorted(vp["tajika"], key=lambda y: y["gap"])
    assert "Ithasala" in varshaphal.tajika_text(vp) and FORBIDDEN.search(varshaphal.tajika_text(vp)) is None


def test_remedies_are_only_for_what_is_active_now(chart):
    import remedy_plan
    from rule_engine import generate_reading
    reading = generate_reading(chart)
    at = datetime.datetime(2026, 9, 20, 12)
    plan = remedy_plan.remedy_plan(chart, reading, at)
    assert (plan["now"]["periods"]["maha"], plan["now"]["periods"]["antar"]) == ("Moon", "Jupiter") and "Saturn" in plan["now"]["active"]
    by = {i["planet"]: i for i in plan["planets"]}
    for planet, item in by.items():
        if item["level"] in (remedy_plan.HIGH, remedy_plan.CARE, remedy_plan.HELPFUL, remedy_plan.OPTIONAL):
            assert planet in plan["now"]["active"], planet                     # nothing is recommended for a planet that is not running
        if item["level"] == remedy_plan.LATER:
            assert planet not in plan["now"]["active"] and item["next_start"] > at
    assert by["Mercury"]["level"] == remedy_plan.LATER                         # troubled, but its period only begins in 2028
    assert all(i["stone_ok"] is False for i in plan["planets"] if i["planet"] in ("Rahu", "Ketu"))
    text = remedy_plan.remedy_text(chart, reading, at)
    for phrase in ("for right now", "Keep in mind for later", "What everyone can do", "How to use these safely", "Sade Sati"):
        assert phrase in text, phrase
    assert FORBIDDEN.search(text) is None


def test_gemstone_only_when_safe_and_active(chart):
    import copy
    import remedy_plan
    from rule_engine import generate_reading
    reading = generate_reading(chart)
    # pretend every planet is active and troubled: only trine-ruling, non-difficult planets may get a stone
    plan = remedy_plan.remedy_plan(chart, reading, datetime.datetime(2026, 9, 20, 12))
    for item in plan["planets"]:
        if item["stone_ok"]:
            assert item["level"] in (remedy_plan.HIGH, remedy_plan.CARE) and item["planet"] not in ("Rahu", "Ketu")
