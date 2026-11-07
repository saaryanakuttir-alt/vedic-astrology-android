"""The knowledge-base tables wired into the engine in Nov 2026:
  kb/functional_nature.json -> remedy_plan.py (BPHS ch.34 functional benefics / malefics / yogakarakas)
  kb/gochara_vedha.json     -> transits.py and remedy_plan.py (Gochara from the Moon with Vedha)
  kb/shadbala_rules.json    -> shadbala.py (Drekkana Bala; Sphuta Drishti and Drik Bala computed but not yet totalled)
Run from android_app/:  python -m pytest tests/test_kb_wiring.py"""
import datetime
import json
import os
import sys

import pytest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

import remedy_plan  # noqa: E402
import shadbala  # noqa: E402
import transits  # noqa: E402
from panchanga import SIGNS  # noqa: E402

AT = datetime.datetime(2026, 9, 20, 12)


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah",
                               country_hint="IN", sex="Male")


@pytest.fixture(scope="module")
def reading(chart):
    from rule_engine import generate_reading
    return generate_reading(chart)


# ---------------------------------------------------------------- functional nature (BPHS ch.34)
def test_functional_nature_covers_every_ascendant_without_contradictions():
    for sign in SIGNS:
        fn = remedy_plan.functional_nature(sign)
        assert fn, sign
        assert set(fn.values()) <= {"yogakaraka", "benefic", "malefic", "neutral"}
        with open(os.path.join(APP, "engine", "kb", "functional_nature.json"), encoding="utf-8") as f:
            item = next(i for i in json.load(f)["items"] if i["ascendant"] == sign)
        assert not set(item["functional_benefics"]) & set(item["functional_malefics"]), sign
        assert not set(item["yogakarakas"]) & set(item["functional_malefics"]), sign


def test_functional_nature_spot_checks():
    assert remedy_plan.functional_nature("Taurus")["Saturn"] == "yogakaraka"
    assert remedy_plan.functional_nature("Cancer")["Mars"] == "yogakaraka"
    assert remedy_plan.functional_nature("Gemini")["Jupiter"] == "malefic"
    assert remedy_plan.functional_nature("Gemini")["Venus"] == "benefic"
    assert "Rahu" not in remedy_plan.functional_nature("Aries")


@pytest.mark.parametrize("asc", SIGNS)
def test_no_gemstone_for_a_functional_malefic(chart, reading, asc, monkeypatch):
    """Pretend every planet is troubled and active, for every ascendant: a BPHS functional malefic never gets a stone,
    and a BPHS functional benefic / yogakaraka always may."""
    fake = dict(chart, ascendant=dict(chart["ascendant"], sign=asc))
    first = SIGNS.index(asc)
    fake["houses"] = {h: SIGNS[(first + h - 1) % 12] for h in range(1, 13)}
    cons = remedy_plan.planet_considerations(chart)
    for c in cons.values():
        c["tone"] = "Challenging"
    monkeypatch.setattr(remedy_plan, "planet_considerations", lambda _c: cons)
    monkeypatch.setattr(remedy_plan, "_TRANSIT_TRIGGER", tuple(remedy_plan.BODIES))
    monkeypatch.setattr(transits, "gochara_now", lambda _c, _at: {p: {"house_from_moon": 8, "effective": "difficult", "by": []}
                                                                   for p in remedy_plan.BODIES})
    monkeypatch.setattr(transits, "sign_leaves", lambda _p, _at: None)
    plan = remedy_plan.remedy_plan(fake, reading, AT)
    fn = remedy_plan.functional_nature(asc)
    for item in plan["planets"]:
        p = item["planet"]
        assert p in plan["now"]["active"], p
        if fn.get(p) == "malefic":
            assert not item["stone_ok"] and item["level"] == remedy_plan.HELPFUL, (asc, p)
            assert "functional malefic" in item["why"]
        if fn.get(p) in ("benefic", "yogakaraka") and p not in ("Rahu", "Ketu"):
            assert item["level"] == remedy_plan.HIGH and item["stone_ok"], (asc, p)


def test_remedy_text_mentions_the_ascendant_rule_safely(chart, reading):
    text = remedy_plan.remedy_text(chart, reading, AT)
    assert "How to use these safely" in text


# ---------------------------------------------------------------- Gochara with Vedha
def _houses(**kw):
    base = {p: 2 for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")}
    base.update(kw)
    return base


def test_gochara_table_comes_from_the_kb():
    assert transits._GOCHARA_GOOD["Jupiter"] == {2, 5, 7, 9, 11}
    assert transits._GOCHARA_GOOD["Rahu"] == {3, 6, 11}                         # the KB's Saturn/Mars pattern
    assert transits._VEDHA["Venus"][1] == 8 and transits._VEDHA["Sun"][11] == 5


def test_vedha_blocks_a_good_transit():
    v = transits.gochara_verdict("Jupiter", _houses(Jupiter=5, Mars=4, Venus=7, Saturn=7, Sun=7, Mercury=7, Moon=7, Rahu=1, Ketu=7))
    assert v["favourable"] and v["effective"] == "blocked" and v["by"] == ["Mars"]


def test_good_transit_without_vedha():
    v = transits.gochara_verdict("Jupiter", _houses(Jupiter=5, Mars=6, Venus=6, Saturn=6, Sun=6, Mercury=6, Moon=6, Rahu=1, Ketu=7))
    assert v["effective"] == "good" and v["by"] == []


def test_vipareeta_vedha_eases_a_bad_transit():
    # Jupiter in the 4th (bad) is eased by a planet in the 5th, the favourable house whose Vedha house is the 4th
    v = transits.gochara_verdict("Jupiter", _houses(Jupiter=4, Venus=5, Mars=1, Saturn=1, Sun=1, Mercury=1, Moon=1, Rahu=1, Ketu=7))
    assert not v["favourable"] and v["effective"] == "eased" and v["by"] == ["Venus"]


def test_father_son_pairs_never_obstruct_each_other():
    v = transits.gochara_verdict("Sun", _houses(Sun=3, Saturn=9, Mars=1, Jupiter=1, Venus=1, Mercury=1, Moon=1, Rahu=1, Ketu=7))
    assert v["effective"] == "good"
    v = transits.gochara_verdict("Moon", _houses(Moon=3, Mercury=9, Sun=1, Mars=1, Jupiter=1, Venus=1, Saturn=1, Rahu=1, Ketu=7))
    assert v["effective"] == "good"


def test_rahu_and_ketu_do_not_obstruct_each_other():
    v = transits.gochara_verdict("Rahu", _houses(Rahu=6, Ketu=12, Sun=1, Moon=1, Mars=1, Mercury=1, Jupiter=1, Venus=1, Saturn=1))
    assert v["effective"] == "good"


def test_forecast_reports_vedha(chart):
    f = transits.compute_transit_forecast(chart, datetime.datetime(2026, 11, 7, 12))
    pt = f["planet_transits"]
    assert all(t["vedha"] in ("good", "blocked", "eased", "difficult") for t in pt.values())
    assert pt["Jupiter"]["vedha"] == "blocked" and pt["Jupiter"]["vedha_by"] == ["Mars"]      # Jupiter 5th, Mars 4th from the Moon
    assert "held back (Vedha) by Mars" in f["monthly_text"]


def test_jupiter_transit_trigger(chart, reading):
    plan = remedy_plan.remedy_plan(chart, reading, AT)
    g = plan["now"]["gochara"]["Jupiter"]
    assert ("Jupiter" in plan["now"]["active"]) == (g["effective"] == "difficult" or plan["now"]["periods"]["antar"] == "Jupiter")
    assert "Rahu" not in plan["now"]["active"] or plan["now"]["periods"]["maha"] == "Rahu" or plan["now"]["periods"]["antar"] == "Rahu"


def test_sign_leaves_is_in_the_future(chart):
    d = transits.sign_leaves("Jupiter", AT)
    assert d is not None and AT < d < AT + datetime.timedelta(days=500)


# ---------------------------------------------------------------- Shadbala rules
def test_drekkana_bala_follows_bphs():
    """BPHS 27.6: male planets in the 1st decanate, female in the 2nd, neuter (Mercury, Saturn) in the 3rd."""
    assert shadbala.drekkana_bala("Sun", 5) == 15 and shadbala.drekkana_bala("Sun", 15) == 0
    assert shadbala.drekkana_bala("Moon", 15) == 15 and shadbala.drekkana_bala("Venus", 25) == 0
    assert shadbala.drekkana_bala("Mercury", 25) == 15 and shadbala.drekkana_bala("Saturn", 15) == 0


@pytest.mark.parametrize("angle,value", [(0, 0), (30, 0), (60, 15), (90, 45), (120, 30), (150, 0), (180, 60), (210, 45),
                                         (240, 30), (270, 15), (300, 0), (330, 0)])
def test_sphuta_drishti_general_values(angle, value):
    assert abs(shadbala.sphuta_drishti("Sun", angle) - value) < 1e-9


def test_sphuta_drishti_special_aspects_reach_full_strength():
    assert shadbala.sphuta_drishti("Mars", 90) == 60 and shadbala.sphuta_drishti("Mars", 210) == 60
    assert shadbala.sphuta_drishti("Jupiter", 120) == 60 and shadbala.sphuta_drishti("Jupiter", 240) == 60
    assert shadbala.sphuta_drishti("Saturn", 60) == 60 and shadbala.sphuta_drishti("Saturn", 270) == 60


def test_drik_bala_is_computed_but_not_in_the_total(chart):
    r = shadbala.compute_shadbala(chart)
    for p in shadbala.SEVEN:
        assert "drik" in r[p] and -90 <= r[p]["drik"] <= 200
        assert abs(r[p]["total"] - sum(r[p][k] for k, _ in shadbala.COMPONENTS)) < 1e-9
    assert "drik" not in [k for k, _ in shadbala.COMPONENTS]
