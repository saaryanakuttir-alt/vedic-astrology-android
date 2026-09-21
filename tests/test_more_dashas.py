"""Yogini dasha, Char dasha, Jaimini karakas / Karakamsa, Mahadasha verdicts and the sectioned planet effects.
Reference values: the AstroSage report for Sammya Das (29 May 1992, 07:06, Howrah).
Run from android_app/:  python -m pytest tests/test_more_dashas.py"""
import datetime
import os
import re
import sys

import pytest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

import more_dashas as md  # noqa: E402
import planet_effects as pe  # noqa: E402

FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|childless\w*|death|die)\b", re.I)


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah",
                               country_hint="IN", sex="Male")


@pytest.fixture(scope="module")
def reading(chart):
    from rule_engine import generate_reading
    return generate_reading(chart)


def test_char_dasha_matches_astrosage(chart):
    rows = md.char_dasha(chart)
    assert [(r["sign"][:3].upper(), r["years"]) for r in rows] == [
        ("GEM", 11), ("TAU", 12), ("ARI", 11), ("PIS", 7), ("AQU", 2), ("CAP", 12), ("SAG", 8), ("SCO", 4), ("LIB", 7),
        ("VIR", 4), ("LEO", 3), ("CAN", 3)]
    assert rows[0]["start"].date() == datetime.date(1992, 5, 29) and rows[3]["start"].date() == datetime.date(2026, 5, 29)
    first = [a["sign"][:3].upper() for a in rows[0]["antardashas"]]
    assert first[:4] == ["TAU", "ARI", "PIS", "AQU"] and first[-1] == "GEM"


def test_yogini_dasha_matches_astrosage_within_a_few_days(chart):
    rows = md.yogini_dasha(chart)
    expected = [("Br", datetime.date(1994, 12, 24)), ("Ba", datetime.date(1999, 12, 24)), ("Ul", datetime.date(2005, 12, 24)),
                ("Si", datetime.date(2012, 12, 24)), ("Sn", datetime.date(2020, 12, 24)), ("Ma", datetime.date(2021, 12, 24)),
                ("Pi", datetime.date(2023, 12, 24)), ("Dh", datetime.date(2026, 12, 24))]
    for row, (code, day) in zip(rows, expected):
        assert row["code"] == code and abs((row["end"].date() - day).days) <= 3, (code, row["end"])
    assert all(a["end"] > rows[0]["start"] for a in rows[0]["antardashas"])          # nothing that ended before birth


def test_karakas_and_karakamsa_match_astrosage(chart):
    ks = md.karakas(chart)
    assert [(k["chara"], k["sthira"]) for k in ks] == [("Saturn", "Sun"), ("Mars", "Mercury"), ("Sun", "Mars"), ("Jupiter", "Moon"),
                                                        ("Mercury", "Jupiter"), ("Venus", "Saturn"), ("Moon", "Venus")]
    assert md.karakamsa_sign(chart) == "Leo"
    view = md.with_karakamsa(chart)
    assert view["ascendant"]["vargas"]["KM"] == "Leo" and "KM" not in chart["ascendant"]["vargas"]      # original untouched


def test_mahadasha_text_rates_every_period(chart):
    text = md.mahadasha_text(chart, datetime.datetime(2026, 9, 20, 12))
    assert text.count("Mahadasha") >= 9 and "running now" in text and "What may happen" in text
    assert FORBIDDEN.search(text + md.karakamsa_text(chart)) is None


def test_planet_effects_have_clear_sections_for_every_planet(chart, reading):
    effects = pe.planet_effects(chart, reading)
    assert [e["planet"] for e in effects] == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    for e in effects:
        labels = [label for label, _ in e["sections"]]
        assert labels[0] == pe.GLANCE and labels[-1] == pe.SIMPLE, e["planet"]
        assert any("house" in l and e["planet"] in l for l in labels), e["planet"]      # house section
        assert "What it rules and looks at" in labels and "What may happen" in labels
        assert e["banner"].startswith(e["planet"].upper())
    sun = " ".join(t for _, t in effects[0]["sections"])
    assert "12th house" in sun and FORBIDDEN.search(pe.planet_effects_text(chart, reading)) is None
    assert len(pe.planet_effects_text(chart, reading, compact=True)) < len(pe.planet_effects_text(chart, reading)) / 2
