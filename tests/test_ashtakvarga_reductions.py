"""Trikona and Ekadhipatya Shodhana, Shodhya Pinda and Kakshya (engine/ashtakvarga_reductions.py).
Run from android_app/:  python -m pytest tests/test_ashtakvarga_reductions.py"""
import datetime
import os
import sys

import pytest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

import ashtakvarga_reductions as red  # noqa: E402
from panchanga import SIGNS  # noqa: E402


def row(values):
    return dict(zip(SIGNS, values))


def as_list(r):
    return [r[s] for s in SIGNS]


def test_trikona_rules():
    # Aries/Leo/Sag 5,3,4 -> minus 3; Taurus/Virgo/Cap has a 0 -> unchanged; Gem/Lib/Aqu all 2 -> all 0;
    # Can/Sco/Pis 6,1,2 -> minus 1
    r = row([5, 0, 2, 6, 3, 4, 2, 1, 4, 3, 2, 2])
    assert as_list(red.trikona_shodhana(r)) == [2, 0, 0, 5, 0, 4, 0, 0, 1, 3, 0, 1]


# A published worked example (horosoft.net, "Ekadhipatya Shodan"): Libra, Scorpio and Aquarius are occupied.
EXAMPLE_OCCUPIED = {"Libra", "Scorpio", "Aquarius"}
EXAMPLE = {   # contributor: (after Trikona, after Ekadhipatya)
    "Sun": ([0, 2, 0, 2, 5, 3, 0, 0, 3, 0, 1, 2], [0, 2, 0, 2, 5, 3, 0, 0, 2, 0, 1, 2]),
    "Moon": ([1, 0, 1, 5, 3, 1, 0, 0, 0, 1, 0, 4], [1, 0, 0, 5, 3, 0, 0, 0, 0, 1, 0, 4]),
    "Mars": ([0, 0, 0, 0, 3, 4, 1, 0, 1, 0, 0, 3], [0, 0, 0, 0, 3, 4, 1, 0, 1, 0, 0, 1]),
    "Mercury": ([0, 1, 0, 0, 4, 2, 2, 0, 1, 0, 1, 1], [0, 0, 0, 0, 4, 2, 2, 0, 0, 0, 1, 0]),
    "Jupiter": ([1, 0, 3, 3, 2, 1, 0, 3, 0, 1, 3, 0], [0, 0, 1, 3, 2, 1, 0, 3, 0, 0, 3, 0]),
    "Venus": ([0, 0, 2, 1, 1, 2, 1, 1, 1, 1, 0, 0], [0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0]),
    "Saturn": ([0, 0, 1, 2, 2, 4, 2, 0, 0, 1, 0, 3], [0, 0, 1, 2, 2, 1, 2, 0, 0, 1, 0, 3]),
    "Lagna": ([0, 0, 1, 1, 1, 3, 0, 1, 0, 3, 3, 0], [0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 3, 0]),
}


@pytest.mark.parametrize("name", list(EXAMPLE))
def test_ekadhipatya_matches_published_example(name):
    before, after = EXAMPLE[name]
    assert as_list(red.ekadhipatya_shodhana(row(before), EXAMPLE_OCCUPIED)) == after


def test_ekadhipatya_each_rule():
    occ = {"Aries"}
    def pair(a, b, occupied):   # Aries / Scorpio values with everything else zero
        r = row([a, 0, 0, 0, 0, 0, 0, b, 0, 0, 0, 0])
        out = red.ekadhipatya_shodhana(r, occupied)
        return out["Aries"], out["Scorpio"]
    assert pair(3, 5, occ) == (3, 3)              # empty Scorpio has more -> lowered to occupied Aries
    assert pair(5, 3, occ) == (5, 0)              # empty has fewer -> 0
    assert pair(4, 4, occ) == (4, 0)              # equal, one occupied -> empty becomes 0
    assert pair(4, 4, set()) == (0, 0)            # both empty and equal -> both 0
    assert pair(2, 6, set()) == (2, 2)            # both empty, unequal -> larger lowered to smaller
    assert pair(2, 6, {"Aries", "Scorpio"}) == (2, 6)   # both occupied -> unchanged
    assert pair(0, 6, set()) == (0, 6)            # a zero -> unchanged


def test_cancer_and_leo_are_never_reduced_by_ekadhipatya():
    r = row([1, 1, 1, 7, 7, 1, 1, 1, 1, 1, 1, 1])
    out = red.ekadhipatya_shodhana(r, set())
    assert out["Cancer"] == 7 and out["Leo"] == 7


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah",
                               country_hint="IN", sex="Male")


def test_reductions_on_a_real_chart(chart):
    r = red.reductions(chart)
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        d = r[p]
        assert all(0 <= d["ekadhipatya"][s] <= d["trikona"][s] <= d["raw"][s] for s in SIGNS)
        assert d["shodhya_pinda"] == d["rasi_pinda"] + d["graha_pinda"]
        assert d["rasi_pinda"] == sum(d["ekadhipatya"][s] * red.RASI_MULTIPLIER[s] for s in SIGNS)
    assert r["sarva_reduced"] == {s: sum(r[p]["ekadhipatya"][s] for p in red.PLANET_ORDER) for s in SIGNS}


def test_kakshya_boundaries():
    assert red.kakshya_of(0.0)[:2] == (0, "Saturn")
    assert red.kakshya_of(3.74)[:2] == (0, "Saturn")
    assert red.kakshya_of(3.75)[:2] == (1, "Jupiter")
    assert red.kakshya_of(29.99)[:2] == (7, "Lagna")
    assert red.kakshya_of(30 + 11.3)[:2] == (3, "Sun")       # 11 deg 18 min of Taurus: the 4th Kakshya


def test_kakshya_transit_uses_prastara(chart):
    import prastara
    k = red.kakshya_now(chart, datetime.datetime(2026, 11, 7, 12))
    for p, t in k.items():
        grid = prastara.prastara(chart, p)
        assert t["lord_gives_point"] == bool(grid["rows"][t["lord"]][SIGNS.index(t["sign"])])
        assert t["start"] <= t["degree"] < t["end"]
        assert t["bindus"] == chart["ashtakavarga"]["bhinnashtakavarga"][p][t["sign"]]
