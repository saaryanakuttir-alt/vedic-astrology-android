"""Learn Astrology: lessons, glossary and the walk-through of the user's own chart."""
import datetime as dt
import json
import os
import re

import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))

import learn  # noqa: E402
from birth_chart import compute_birth_chart  # noqa: E402
from rule_engine import generate_reading  # noqa: E402

KB = os.path.join(os.path.dirname(learn.__file__), "kb", "learn.json")
POLICY = re.compile(r"\b(death|die|lifespan|longevity|maraka|life expectancy|miscarriage|childless)\b", re.I)


@pytest.fixture(scope="module")
def chart_reading():
    c = compute_birth_chart(name="S", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah")
    return c, generate_reading(c)


def test_lessons_well_formed():
    ids = [l["id"] for l in learn.lessons()]
    assert len(ids) == 15 and len(set(ids)) == 15
    for l in learn.lessons():
        assert l["title"] and l["sections"]
        for sec in l["sections"]:
            assert sec[0] and len(sec[1]) > 20
            assert len(sec) == 2 or sec[2] in ("north_template", "south_template")


def test_glossary_links_to_real_lessons_and_search():
    ids = {l["id"] for l in learn.lessons()}
    gl = learn.glossary()
    assert len(gl) >= 50 and all(g["lesson"] in ids for g in gl)
    assert [g["term"] for g in gl] == sorted((g["term"] for g in gl), key=str.lower)
    assert any(g["term"] == "Mahadasha" for g in learn.glossary("dasha"))
    assert learn.glossary("zzzz") == []


def test_no_policy_words_in_kb():
    text = open(KB, encoding="utf-8").read()
    assert not POLICY.search(text)


def test_walkthrough_known_chart(chart_reading):
    c, r = chart_reading
    steps = {s["id"]: s for s in learn.walkthrough(c, r, dt.datetime(2026, 11, 8))}
    lesson_ids = {l["id"] for l in learn.lessons()}
    assert all(s["lesson"] in lesson_ids for s in steps.values())
    assert "Gemini" in steps["lagna"]["text"] and "Mercury" in steps["lagna"]["text"] and "12th" in steps["lagna"]["text"]
    assert "Ashwini" in steps["moon"]["text"] and "Ketu" in steps["moon"]["text"]
    assert "busiest house is the 12th" in steps["houses"]["text"]
    assert "Mercury rules both your 1st and 4th" in steps["lords"]["text"]
    assert "Saturn in Capricorn" in steps["dignity"]["text"] and "Retrograde: Saturn" in steps["dignity"]["text"]
    assert "Jupiter in your 3rd house aspects houses 7, 9, 11" in steps["aspects"]["text"]
    assert "Kendra-Trikona Raja Yoga" in steps["yogas"]["text"]
    assert "Moon until Nov 2032" in steps["dasha"]["text"]
    assert "Sade Sati" in steps["transits"]["text"]
    assert "number 3, so your rising sign is Gemini" in steps["picture"]["text"]
    assert "the 11th box you reach is Aries" in steps["picture"]["text"] and steps["picture"]["diagram"]
    assert "Aquarius" in steps["navamsa"]["text"] and "Sun" in steps["navamsa"]["text"]


def test_lesson_try_keys_resolve(chart_reading):
    c, r = chart_reading
    for l in learn.lessons():
        out = learn.try_in_chart(l.get("try"), c, r, dt.datetime(2026, 11, 8))
        assert (out is None) == (l.get("try") is None)


def test_picture_guide(chart_reading):
    c, r = chart_reading
    guide = learn.picture_guide()
    assert len(guide) >= 12 and len({g["id"] for g in guide}) == len(guide)
    ex = {g["example"]: learn.picture_example(g["example"], c, r) for g in guide if g.get("example")}
    assert "top diamond shows 3, so your rising sign is Gemini" in ex["north_signs"]["text"]
    cols, rows = ex["north_signs"]["table"]
    assert len(rows) == 12 and rows[11][:3] == ["12th", "2", "Taurus"] and "Sun" in rows[11][3]
    assert "10 Pisces" in ex["south_count"]["text"] and "7th house is the Sagittarius box" in ex["south_count"]["text"]
    assert "Rahu is in the 7th house" in ex["conjunctions"]["text"]
    assert "Jupiter sits in your 3rd house (Leo)" in ex["aspects"]["text"] and "7th, 9th, 11th" in ex["aspects"]["text"]
    assert "10th house box holds Pisces; its lord is Jupiter" in ex["lords"]["text"]
    assert "shows 11" in ex["navamsa"]["text"]
    quiz = ex["quiz"]["quiz"]
    assert len(quiz) == 6 and quiz[5][1].startswith("The 12th house (Taurus)")


def test_deeper_lessons_and_planet_lore():
    assert sum(len(l["sections"]) for l in learn.lessons()) >= 100
    lore = learn.planet_lore()
    assert [x["planet"] for x in lore] == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    assert all(x["form"] and x["story"] for x in lore)
    assert learn.planet_image("no-such-planet") is None
    assert all(learn.planet_image(x["id"]) for x in lore), "every planet has its picture in assets/planets/"
