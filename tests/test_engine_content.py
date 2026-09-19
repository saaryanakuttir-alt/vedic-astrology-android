"""The Android app must never output lifespan / time-of-death or children
predictions. Runs the real engine on several births and scans every string
in the resulting reading. (NOT packaged into the APK - `tests` is excluded in
buildozer.spec.)  Run from android_app/:  python -m pytest tests/test_engine_content.py
"""
import json
import os
import re
import sys

import pytest

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

BIRTHS = [
    dict(name="A", birth_date=(1990, 6, 15), birth_time=(14, 30, 0), place_name="Mumbai", country_hint="IN"),
    dict(name="B", birth_date=(1988, 11, 3), birth_time=(9, 15, 0), place_name="Delhi", country_hint="IN"),
    dict(name="C", birth_date=(2016, 4, 22), birth_time=(7, 45, 0), place_name="Bengaluru", country_hint="IN"),
    dict(name="D", birth_date=(1975, 1, 9), birth_time=(23, 5, 0), place_name="Chennai", country_hint="IN"),
    dict(name="E", birth_date=(1962, 8, 30), birth_time=(4, 40, 0), place_name="Kolkata", country_hint="IN"),
]

# Words that would mean a death / lifespan / children output. Deliberately
# NOT flagged: the nakshatra mythology text ("Yama, god of death") and the
# word "child" inside Family Compatibility (that report compares real,
# already-generated charts; it predicts nothing about having children).
FORBIDDEN = re.compile(
    r"\b(longevity|lifespan|life span|ayurdaya|ayushkaraka|maraka|vulnerable period|"
    r"most likely age|children|progeny|offspring|family-size|childless\w*|putra-karaka)\b",
    re.I,
)
ALLOWED_CONTEXT = re.compile(r"Yama|life-death-rebirth|god of death|fertility", re.I)


def _strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}/{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")


@pytest.fixture(scope="module")
def readings():
    from birth_chart import compute_birth_chart
    from rule_engine import generate_reading
    out = []
    for b in BIRTHS:
        chart = compute_birth_chart(**b)
        out.append((b["name"], chart, generate_reading(chart)))
    return out


def test_no_death_or_children_text_anywhere_in_a_reading(readings):
    bad = []
    for name, _chart, reading in readings:
        for path, s in _strings(json.loads(json.dumps(reading, default=str))):
            for sentence in re.split(r"(?<=[.!?])\s+", s):
                if FORBIDDEN.search(sentence) and not ALLOWED_CONTEXT.search(sentence):
                    bad.append((name, path, sentence[:140]))
    assert not bad, "\n".join(map(str, bad[:15]))


def test_removed_sections_are_really_gone(readings):
    for _n, _c, reading in readings:
        lp = reading["life_predictions"]
        assert "children" not in lp
        assert "longevity_and_lifespan" not in lp
        titles = " | ".join(v["title"] for v in lp.values() if isinstance(v, dict))
        assert "Children" not in titles and "Longevity" not in titles


def test_saptamsa_children_chart_has_no_reading(readings):
    for _n, _c, reading in readings:
        assert "D7" not in reading["chart_descriptions"]
        assert "D7" not in reading["divisional_chart_overviews"]
        for planet in reading["planets"].values():
            assert "D7" not in planet["vargas"]


def test_everything_else_still_generates(readings):
    for _n, _c, reading in readings:
        assert reading["life_predictions"]["career_and_profession"]["text"]
        assert reading["life_predictions"]["health_and_vitality"]["text"]
        assert reading["karmic_and_past_life"]["soul_narrative"]
        assert reading["medical_astrology"]["text"]
        assert not reading["warnings"], reading["warnings"][:3]


def test_yearly_relationship_outlook(readings):
    import re
    for _n, _c, reading in readings:
        y = reading["relationship_themes"]["yearly_outlook"]
        ages = [e["age"] for e in y["years"]]
        assert ages == list(range(6, 81)), "one entry per year from age 6 to 80"
        assert {e["level"] for e in y["years"]} <= {"Low", "Moderate", "High", "Very high"}
        assert "not a real probability" in y["caveat"]
        # childhood and teens: friendships / emotional bonds only - never romance, partnership or physical wording
        for e in y["years"]:
            if e["age"] < 18:
                text = e["plain"] + " " + e["kind"]
                assert not re.search(r"romance|romantic|partner|marriage|physical|intima|love and|attraction", text, re.I), (e["age"], text)
        assert all(a >= 18 for a in y["standouts"])
