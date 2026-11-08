"""Tajika extras of the yearly chart (engine/tajika.py, kb/tajika_rules.json)."""
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

import tajika  # noqa: E402
import varshaphal  # noqa: E402

FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|childless\w*|death|die)\b", re.I)


@pytest.fixture(scope="module")
def kottayam():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="K", birth_date=(1990, 2, 17), birth_time=(10, 0, 0), place_name="Kottayam")


@pytest.fixture(scope="module")
def howrah():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah")


def _pl(**lons):
    return {p: {"longitude": lon, "retrograde": False} for p, lon in lons.items()}


def test_kb_tables():
    with open(os.path.join(HERE, "..", "engine", "kb", "tajika_rules.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    assert FORBIDDEN.search(json.dumps(d)) is None
    for sign, terms in d["hadda"].items():
        assert sum(n for _, n in terms) == 30 and sorted(p for p, _ in terms) == ["Jupiter", "Mars", "Mercury", "Saturn", "Venus"]
    assert len(d["trirashi"]) == 12 and len(d["sahams"]) == len({s["name"] for s in d["sahams"]})
    assert not {"Putra", "Mrityu", "Roga", "Bandhana", "Paradara"} & {s["name"] for s in d["sahams"]}


def test_aspects_by_sign():
    assert tajika.tajika_aspect(5, 65) == ("sextile", "friendly")          # Aries -> Gemini (3rd)
    assert tajika.tajika_aspect(5, 125) == ("trine", "friendly")           # Aries -> Leo (5th)
    assert tajika.tajika_aspect(5, 95) == ("square", "inimical")           # Aries -> Cancer (4th)
    assert tajika.tajika_aspect(5, 185) == ("opposition", "inimical")
    assert tajika.tajika_aspect(5, 15) == ("conjunction", "inimical")
    assert tajika.tajika_aspect(5, 35) is None and tajika.tajika_aspect(5, 155) is None   # 2nd and 6th signs


def test_ithasala_ishrafa_and_kinds():
    # Mercury (faster) 10 Aries, Jupiter 14 Leo: trine, Mercury behind by 4 < (7 + 9) / 2
    r = tajika.relation(_pl(Mercury=10, Jupiter=134), "Jupiter", "Mercury")
    assert (r["fast"], r["slow"], r["kind"], r["type"], r["aspect"]) == ("Mercury", "Jupiter", "Ithasala", "vartamana", "trine")
    assert tajika.relation(_pl(Mercury=13.5, Jupiter=134), "Mercury", "Jupiter")["type"] == "poorna"
    r = tajika.relation(_pl(Mercury=17, Jupiter=134), "Mercury", "Jupiter")
    assert r["kind"] == "Ishrafa" and r["gap"] == 3
    assert tajika.relation(_pl(Mercury=10, Jupiter=150), "Mercury", "Jupiter") is None          # 20 degrees: beyond orbs
    assert tajika.relation(_pl(Mercury=10, Jupiter=44), "Mercury", "Jupiter") is None           # 2nd sign: no aspect
    # Bhavishyat: Venus at 28 Aries will enter Taurus... Jupiter at 2 Cancer is 3rd from Taurus (sextile)
    r = tajika.relation(_pl(Venus=28, Jupiter=92), "Venus", "Jupiter")
    assert r["kind"] == "Ithasala" and r["type"] == "bhavishyat" and r["gap"] == 4
    pl = _pl(Mercury=10, Jupiter=134)
    pl["Mercury"]["retrograde"] = True
    assert tajika.relation(pl, "Mercury", "Jupiter") is None


def test_pancha_vargiya_matches_published_report(kottayam):
    """Prokerala's sample Varshaphal report (17 Feb 1990, 10:00, Kottayam) lists these Pancha-vargiya points."""
    expected = {2024: {"Mercury": [15, 5.41, 3.75, 5, 2.5], "Venus": [15, 11.15, 3.75, 2.5, 1.25],
                       "Mars": [15, 17.93, 3.75, 2.5, 1.25], "Jupiter": [7.5, 11.13, 3.75, 7.5, 3.75]},
                2025: {"Moon": [15, 4.13, 3.75, 5, 2.5], "Mercury": [7.5, 3.81, 15, 10, 1.25]}}
    for year, rows in expected.items():
        pl = varshaphal.varsha_chart(kottayam, year)["planets"]
        for planet, want in rows.items():
            b = tajika.pancha_vargiya(planet, pl)
            got = [b["kshetra"], b["uchcha"], b["hadda"], b["drekkana"], b["navamsa"]]
            assert got[0] == want[0] and got[2:] == want[2:], (year, planet, got)
            assert abs(got[1] - want[1]) < 0.02, (year, planet, got)


def test_saham_thirty_degree_rule():
    assert tajika._between(50, 10, 100) and not tajika._between(150, 10, 100)
    assert tajika._between(5, 300, 20)                                # the arc may cross 0 Aries


def test_varshaphal_extras(howrah, kottayam):
    for chart in (howrah, kottayam):
        for year in (2025, 2026):
            vp = varshaphal.varshaphal(chart, year)
            x = vp["tajika_extras"]
            vs = x["varshesh"]
            assert vs["lord"] in tajika.SEVEN and len(vs["bearers"]) == 5
            assert vs["bearers"][0]["planet"] == tajika.SIGN_LORD[vp["muntha"]["sign"]]
            if vs["reason"] == "strongest_aspecting":
                chosen = next(r for r in vs["bearers"] if r["planet"] == vs["lord"])
                assert chosen["aspects_lagna"]
                assert all(r["bala"]["total"] <= chosen["bala"]["total"] for r in vs["bearers"]
                           if r["aspects_lagna"] and r["planet"] != "Moon")
            assert all(0 <= b["total"] <= 20 for b in x["bala"].values())
            assert len(x["sahams"]) == 26 and all(0 <= s["longitude"] < 360 for s in x["sahams"])
            assert {s["verdict"] for s in x["sahams"]} <= {"supported", "mixed", "care"}
            names = {y["yoga"] for h in x["houses"]["houses"] for y in h["yogas"]}
            assert names <= set(tajika.data()["yogas"])
            text = varshaphal.varshaphal_text(vp)
            for part in ("Lord of the year", "Sahams", "Life areas this year"):
                assert part in text
            assert FORBIDDEN.search(text) is None
