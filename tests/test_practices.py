"""Meditation and practice plan (engine/practices.py, kb/practices.json)."""
import datetime
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

import practices  # noqa: E402

FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|death|die|cure[sd]?)\b", re.I)
AT = datetime.datetime(2026, 11, 8, 12)
TODAY = datetime.date(2026, 11, 8)


def _chart(**kw):
    from birth_chart import compute_birth_chart
    from rule_engine import generate_reading
    c = compute_birth_chart(**kw)
    return c, generate_reading(c)


@pytest.fixture(scope="module")
def charts():
    return {
        "adult": _chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah"),
        "young": _chart(name="Y", birth_date=(2000, 2, 10), birth_time=(10, 0, 0), place_name="Delhi"),
        "teen": _chart(name="T", birth_date=(2012, 3, 1), birth_time=(9, 0, 0), place_name="Delhi"),
        "senior": _chart(name="O", birth_date=(1955, 8, 1), birth_time=(6, 0, 0), place_name="Kolkata"),
    }


def test_kb_integrity():
    with open(os.path.join(HERE, "..", "engine", "kb", "practices.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    text = json.dumps({k: v for k, v in d.items() if k != "sources"})
    assert FORBIDDEN.search(text) is None
    ids = [p["id"] for p in d["practices"]]
    assert len(ids) == len(set(ids))
    for p in d["practices"]:
        assert p["level"] in d["levels"] and set(p["cautions"]) <= set(d["cautions"]) and p["source"] and len(p["steps"]) >= 3
        assert set(p["minutes"]) == {"young", "adult", "senior"}
        if p["level"] == "advanced":
            assert "teacher" in p["cautions"], p["id"]
            assert p["minutes"]["senior"] == 0
    for planet, v in d["planets"].items():
        assert set(v["practices"]) <= set(ids) and len(v["practices"]) == 3
    assert set(d["planets"]) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    forceful = {"kapalabhati", "bhastrika"}
    for p in d["practices"]:
        if p["id"] in forceful:
            assert "forceful_breath" in p["cautions"]
        if p["id"] == "trataka":
            assert "eyes" in p["cautions"]


@pytest.mark.parametrize("age,band", [(10, "teen"), (17, "teen"), (18, "young"), (29, "young"), (30, "adult"), (59, "adult"), (60, "senior"), (95, "senior")])
def test_age_bands(age, band):
    assert practices.age_band(age)["id"] == band


def test_levels_by_age():
    teen, senior, adult = (practices.age_band(a) for a in (15, 70, 40))
    for pid in ("kapalabhati", "bhastrika", "mula_bandha", "kumbhaka", "trataka", "asana_flow"):
        assert not practices.allowed(pid, teen)
    for pid in ("kapalabhati", "bhastrika", "mula_bandha", "maha_bandha"):
        assert not practices.allowed(pid, senior) and practices.allowed(pid, adult)
    for pid in ("nadi_shodhana", "yoga_nidra", "bhramari", "breath_awareness"):
        assert practices.allowed(pid, teen) and practices.allowed(pid, senior)


def test_plans(charts):
    for key, (chart, reading) in charts.items():
        plan = practices.practice_plan(chart, reading, TODAY, AT)
        assert plan["band"]["id"] == key
        allowed_level = plan["band"]["max_level"]
        every = [plan["base"]["practice"]] + [p for g in plan["focus"] + plan["periods"] for p in g["practices"]]
        every += plan["kundalini"]["gentle"] + plan["kundalini"]["advanced"] + plan["routine"]["morning"] + plan["routine"]["evening"]
        for p in every:
            assert practices._LEVEL_RANK[p["level"]] <= practices._LEVEL_RANK[allowed_level], (key, p["id"])
            assert p["minutes_now"] > 0
        assert (len(plan["kundalini"]["advanced"]) == 5) == (key in ("adult", "young"))
        morning = [p["id"] for p in plan["routine"]["morning"]]
        assert len(morning) == len(set(morning))
        for f in plan["focus"]:
            assert f["why"] and f["practices"]
        assert {f["planet"] for f in plan["focus"]}.isdisjoint({p["planet"] for p in plan["periods"]})


def test_moon_element(charts):
    chart, _ = charts["adult"]
    name, e = practices.moon_element(chart)
    assert chart["planets"]["Moon"]["sign"] in e["signs"]
