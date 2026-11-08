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
    assert len(ids) == 14 and len(set(ids)) == 14
    for l in learn.lessons():
        assert l["title"] and l["sections"]
        for heading, text in l["sections"]:
            assert heading and len(text) > 20


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
    assert "Aquarius" in steps["navamsa"]["text"] and "Sun" in steps["navamsa"]["text"]


def test_lesson_try_keys_resolve(chart_reading):
    c, r = chart_reading
    for l in learn.lessons():
        out = learn.try_in_chart(l.get("try"), c, r, dt.datetime(2026, 11, 8))
        assert (out is None) == (l.get("try") is None)
