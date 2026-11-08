"""Lal Kitab module (engine/lal_kitab.py, kb/lal_kitab.json)."""
import datetime
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

import lal_kitab as lk  # noqa: E402

FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|childless\w*|death|die|son|grandson)\b", re.I)


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah")


def test_kb_is_clean_and_complete():
    with open(os.path.join(HERE, "..", "engine", "kb", "lal_kitab.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    text = json.dumps({k: v for k, v in d.items() if k != "varshphal_table"})
    assert FORBIDDEN.search(text) is None
    assert set(d["planets"]) == set(lk.NINE) and sorted(int(h) for h in d["houses"]) == list(range(1, 13))
    assert sum(n for _, n in d["cycle"]) == 35 and [p for p, _ in d["cycle"]][:3] == ["Saturn", "Rahu", "Ketu"]
    assert len(d["rinas"]) == 9


def test_varshphal_table_rows():
    t = lk.data()["varshphal_table"]
    assert len(t) == 120 and all(sorted(r) == list(range(1, 13)) for r in t)
    assert t[0] == [1, 9, 10, 3, 5, 2, 11, 7, 6, 12, 4, 8]
    assert t[1] == [4, 1, 12, 9, 3, 7, 5, 6, 2, 8, 10, 11]
    assert t[15][0] == 3                    # Bhandari: a planet in house 1 is in house 3 in the 16th year
    assert t[34] == [8, 10, 12, 6, 7, 2, 4, 5, 9, 3, 11, 1] and t[35] == [6, 8, 7, 2, 12, 10, 5, 9, 3, 11, 1, 4]


def test_debts_follow_the_enemy_rule():
    planets = lk.data()["planets"]
    owner = {"pitri": "Jupiter", "self": "Sun", "matri": "Moon", "stri": "Venus", "relatives": "Mars", "sister": "Mercury",
             "cruelty": "Saturn", "betrayal": "Rahu", "nature": "Ketu"}
    for r in lk.data()["rinas"]:
        assert set(r["planets"]) <= set(planets[owner[r["id"]]]["enemies"]), r["id"]
    houses = {p: 3 for p in lk.NINE}
    houses["Ketu"] = 4
    assert [d["id"] for d in lk.debts(houses)] == ["matri", "sister"]          # Ketu in 4; the Moon in 3


def test_status_rules():
    assert lk.status("Sun", 1)[0] == "exalted" and lk.status("Jupiter", 2)[0] == "pakka"
    assert lk.status("Saturn", 1) == ("debilitated", "care") and lk.status("Venus", 12)[0] == "exalted"
    assert lk.status("Mars", 4)[1] == "care"


def test_cycle_and_running_year(chart):
    c = lk.cycle(chart, datetime.date(2026, 11, 7))
    assert c["cycle_no"] == 1 and sum(p["years"] for p in c["periods"]) == 35
    assert [p["planet"] for p in c["periods"] if p["now"]] == ["Mercury"]          # ages 33-35
    assert c["periods"][0]["start"] == datetime.date(1992, 5, 29)
    assert lk.running_year(chart, datetime.date(2026, 11, 7)) == 35
    assert lk.running_year(chart, datetime.date(1992, 6, 1)) == 1


def test_varshphal(chart):
    birth = lk.lk_houses(chart)
    for n in (1, 35, 120):
        v = lk.varshphal(chart, n)
        row = lk.data()["varshphal_table"][n - 1]
        assert all(v["houses"][p] == row[birth[p] - 1] for p in lk.NINE)
    with pytest.raises(ValueError):
        lk.varshphal(chart, 121)


def test_full_reading_is_clean(chart):
    x = lk.lal_kitab(chart, datetime.date(2026, 11, 7))
    blob = []
    for p in x["placements"]:
        r = lk.reading(p["planet"], p["house"], p["with"])
        blob += [r["stands_for"], r["house_area"], r["status_text"], r["remedy"] or ""]
    for d in x["debts"]:
        blob += [d["meaning"], d["why"], d["remedy"]]
    assert FORBIDDEN.search(" ".join(blob)) is None
