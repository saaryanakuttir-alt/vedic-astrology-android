"""engine/extras.py (doshas, Sade Sati table, planet verdicts, friendships, aspects, Shodashvarga) and
the new divisional charts D27 / D40 / D45. The reference values come from the AstroSage report for
Sammya Das (29 May 1992, 07:06, Howrah) that the feature was checked against.
Run from android_app/:  python -m pytest tests/test_extras.py"""
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
from panchanga import SIGNS  # noqa: E402

# Words the Android app must never output (same list as test_engine_content.py)
FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|childless\w*|death|die)\b", re.I)


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah",
                               country_hint="IN", sex="Male")


def test_new_divisional_charts_match_astrosage(chart):
    # sign numbers (1 = Aries) for Lagna, Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu,
    # read from the reference report's Shodashvarga table
    expected = {"D27": [8, 4, 5, 7, 1, 11, 12, 2, 8, 2], "D40": [8, 1, 7, 2, 9, 5, 8, 3, 11, 11],
                "D45": [7, 2, 8, 8, 9, 11, 7, 2, 9, 9]}
    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    for key, numbers in expected.items():
        got = [SIGNS.index(chart["ascendant"]["vargas"][key]) + 1] + [SIGNS.index(chart["planets"][p]["vargas"][key]) + 1 for p in order]
        assert got == numbers, key


def test_shodashvarga_has_fifteen_charts_and_no_saptamsa(chart):
    rows = extras.shodashvarga_table(chart)
    keys = [r["key"] for r in rows]
    assert len(rows) == 15 and "D7" not in keys and keys[0] == "D1" and keys[-1] == "D60"
    assert all(len(r["signs"]) == 10 and all(s in SIGNS for s in r["signs"].values()) for r in rows)


def test_sade_sati_table_matches_astrosage_dates(chart):
    rows = extras.sade_sati_table(chart, years=110)
    starts = {(r["phase"], r["start"]) for r in rows}
    # the 2086-91 block of the reference report (start dates are identical)
    for phase, day in (("rising phase", datetime.date(2086, 11, 10)), ("peak phase", datetime.date(2087, 2, 8)),
                       ("setting phase", datetime.date(2088, 7, 18)), ("peak phase", datetime.date(2088, 10, 31)),
                       ("setting phase", datetime.date(2089, 4, 6))):
        assert any(p == phase and abs((d - day).days) <= 1 for p, d in starts), (phase, day)
    assert all(r["end"] >= r["start"] for r in rows)
    assert {r["kind"].split(" (")[0] for r in rows} == {"Sade Sati", "Dhaiya"}


def test_doshas_verdicts_and_tones(chart):
    doshas = extras.assess_doshas(chart, at=datetime.datetime(2026, 9, 20, 12))
    names = [d["name"] for d in doshas]
    assert any(n.startswith("Manglik") for n in names) and any(n.startswith("Kalsarpa") for n in names)
    for d in doshas:
        assert d["tone"] in extras.TONES and d["status"] and d["plain"]
    by_name = {d["name"].split(" (")[0]: d for d in doshas}
    assert by_name["Manglik"]["present"] is True                 # Mars is 12th from the Moon
    assert by_name["Kalsarpa Dosha"]["present"] is False         # AstroSage: free from Kalsarpa
    assert by_name["Sade Sati"]["present"] is True and "rising" in by_name["Sade Sati"]["status"]


def test_planet_verdicts_are_plain_and_not_absolute(chart):
    cons = extras.planet_considerations(chart)
    assert set(cons) == set(extras.BODIES)
    assert cons["Sun"]["relation"] == "Enemy sign" and cons["Saturn"]["relation"] == "Own sign"
    assert cons["Mars"]["aspects_houses"] == [1, 4, 5] and cons["Jupiter"]["aspects_houses"] == [7, 9, 11]
    assert cons["Sun"]["lord_of"] == [3] and cons["Mars"]["lord_of"] == [6, 11]
    text = extras.planet_considerations_text(chart)
    assert text.count("--- ") >= 9 and "What may happen" in text and "In simple terms" in text
    assert re.search(r"\b(will definitely|is certain|guaranteed)\b", text, re.I) is None


def test_friendships_and_aspects(chart):
    fr = extras.friendship_tables(chart)
    seven = list(fr["compound"])
    assert len(seven) == 7
    for a in seven:
        for b in seven:
            if a != b:
                assert fr["temporary"][a][b] == fr["temporary"][b][a]          # temporary friendship is mutual
                assert fr["compound"][a][b] in {"Adhi Mitra", "Mitra", "Sama", "Shatru", "Adhi Shatru"}
    aspects = extras.western_aspects(chart)
    assert any(a["a"] == "Mercury" and a["b"] == "Venus" and a["aspect"] == "Conjunction" for a in aspects)
    assert all(a["orb"] >= 0 for a in aspects)


def test_house_verdicts_and_running_period(chart):
    hv = extras.house_verdicts(chart)
    assert [v["house"] for v in hv] == list(range(1, 13))
    assert all(v["tone"] in extras.TONES and v["may_happen"] for v in hv)
    when = datetime.datetime(2026, 9, 20, 12)
    o = extras.period_outlook(chart, when)
    assert (o["mahadasha"], o["antardasha"]) == ("Moon", "Jupiter")      # Moon mahadasha 2022-2032; Moon-Rahu ends late 2025
    assert "Where you are right now" in extras.period_text(chart, when)


def test_no_death_or_children_wording_in_the_new_texts(chart):
    blob = "\n".join([extras.doshas_text(chart), extras.planet_considerations_text(chart), extras.sade_sati_text(chart),
                     extras.houses_text(chart), extras.period_text(chart)])
    assert FORBIDDEN.search(blob) is None, FORBIDDEN.search(blob)
