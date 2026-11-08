"""KP cusp sub lord judgement and the 1-249 horary table (engine/kp_judgement.py, kb/kp_house_groups.json)."""
import datetime
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

import kp  # noqa: E402
import kp_judgement as kj  # noqa: E402

FORBIDDEN = re.compile(r"\b(longevity|lifespan|life span|ayurdaya|maraka|children|progeny|offspring|childless\w*|death|die)\b", re.I)


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah")


def _dms(x):
    total = round((x % 30) * 3600)
    return total // 3600, total // 60 % 60, total % 60


def test_249_rows_cover_the_zodiac():
    rows = kj.HORARY
    assert len(rows) == 249
    assert rows[0]["start"] == 0 and abs(rows[-1]["end"] - 360) < 1e-9
    for a, b in zip(rows, rows[1:]):
        assert abs(a["end"] - b["start"]) < 1e-9
    assert [r["number"] for r in rows] == list(range(1, 250))


def test_known_rows():
    r1, r2, r249 = kj.horary_row(1), kj.horary_row(2), kj.horary_row(249)
    assert (r1["sign"], r1["star_lord"], r1["sub_lord"], _dms(r1["end"])) == ("Aries", "Ketu", "Ketu", (0, 46, 40))
    assert (r2["star_lord"], r2["sub_lord"], _dms(r2["end"])) == ("Ketu", "Venus", (3, 0, 0))
    assert (r249["sign"], r249["star_lord"], r249["sub_lord"], _dms(r249["start"])) == ("Pisces", "Mercury", "Saturn", (27, 53, 20))
    r22, r23 = kj.horary_row(22), kj.horary_row(23)          # Krittika's Rahu sub crosses from Aries into Taurus
    assert (r22["sign"], r23["sign"]) == ("Aries", "Taurus")
    assert r22["sub_lord"] == r23["sub_lord"] == "Rahu" and r22["star_lord"] == r23["star_lord"] == "Sun"
    assert _dms(r22["start"]) == (29, 13, 20) and _dms(r23["end"]) == (1, 13, 20)


def test_exactly_six_split_subs_at_sign_boundaries():
    splits = [(a["number"], b["number"]) for a, b in zip(kj.HORARY, kj.HORARY[1:])
              if a["star_lord"] == b["star_lord"] and a["sub_lord"] == b["sub_lord"]]
    assert splits == [(22, 23), (62, 63), (105, 106), (145, 146), (188, 189), (228, 229)]
    for a, _b in splits:
        assert abs(kj.horary_row(a)["end"] % 30) < 1e-9


def test_rows_agree_with_kp_lords():
    for r in kj.HORARY:
        mid = (r["start"] + r["end"]) / 2
        sl, st, sb, _ = kp.lords(mid)
        assert (sl, st, sb) == (r["sign_lord"], r["star_lord"], r["sub_lord"])


def test_bad_number_rejected():
    for n in (0, 250):
        with pytest.raises(ValueError):
            kj.horary_row(n)


@pytest.mark.parametrize("number", [1, 23, 100, 137, 249])
def test_horary_chart_puts_the_number_on_the_ascendant(number):
    t = kj.horary_tables(number, datetime.datetime(2026, 11, 7, 6, 30), 22.57688, 88.31857, "Asia/Kolkata")
    c1, row = t["cusps"][0], t["row"]
    assert (c1["sign_lord"], c1["star_lord"], c1["sub_lord"]) == (row["sign_lord"], row["star_lord"], row["sub_lord"])
    assert abs(((t["cusps"][6]["longitude"] - c1["longitude"]) % 360) - 180) < 0.01
    assert t["house_system"] == "P" and t["ruling"]["Day lord"] == "Saturn"          # 7 Nov 2026 is a Saturday


def test_horary_works_in_polar_latitudes():
    t = kj.horary_tables(5, datetime.datetime(2026, 11, 7, 6, 30), 70.0, 25.0)
    assert t["house_system"] == "O" and t["cusps"][0]["sub_lord"] == kj.horary_row(5)["sub_lord"]


def test_kb_rules():
    with open(os.path.join(HERE, "..", "engine", "kb", "kp_house_groups.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert FORBIDDEN.search(json.dumps(data)) is None
    assert sorted(int(k) for k in data["cusps"]) == list(range(1, 13))
    by = {m["id"]: m for m in data["matters"]}
    assert by["marriage"]["houses"] == [2, 7, 11] and by["marriage"]["against"] == [1, 6, 10]
    assert by["career"]["houses"] == [2, 6, 10, 11] and by["career"]["against"] == [1, 5, 9]
    assert by["foreign"]["houses"] == [3, 9, 12] and by["property_buy"]["houses"] == [4, 11, 12]
    for m in data["matters"]:
        if "against_note" not in m:                       # the plain rule: the 12th from each needed house
            assert m["against"] == sorted({(h - 2) % 12 + 1 for h in m["houses"]} - set(m["houses"]))
        assert not set(m["against"]) & set(m["houses"])


def _fake(sub_lord_star, star_house, star_owns, retro=False):
    """Tables where cusp 7's sub lord is Venus, in the star of `sub_lord_star`."""
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lords = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
             "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
    cusps = []
    for i in range(12):
        lord = lords[signs[i]]
        if i + 1 in star_owns:
            lord = sub_lord_star
        elif lord == sub_lord_star:
            lord = "Sun"
        cusps.append({"cusp": i + 1, "sign_lord": lord, "sub_lord": "Venus" if i == 6 else "Sun"})
    planets = [{"planet": p, "house": 3, "star_lord": "Sun", "sign_lord": "Mars", "retrograde": False} for p in kp.ORDER]
    for p in planets:
        if p["planet"] == "Venus":
            p.update(star_lord=sub_lord_star, house=9)
        if p["planet"] == sub_lord_star:
            p.update(house=star_house, retrograde=retro)
    return {"cusps": cusps, "planets": planets}


def test_judge_verdicts():
    assert kj.judge(_fake("Jupiter", 7, {2, 11}), "marriage")["verdict"] == "promised"
    j = kj.judge(_fake("Jupiter", 7, {2, 10}), "marriage")
    assert j["verdict"] == "mixed" and j["against"] == [10]
    j = kj.judge(_fake("Jupiter", 4, {5}), "marriage")             # only Venus's own signs (2 and 7) help
    assert j["verdict"] == "weak" and j["for"] == [2, 7]
    j = kj.judge(_fake("Jupiter", 4, {5}), "foreign", cusp=7)       # judged from cusp 7 (sub lord Venus, sitting in 9)
    assert j["cusp"] == 7 and j["verdict"] == "weak" and j["for"] == [9]
    t = _fake("Jupiter", 4, {5})
    for p in t["planets"]:
        if p["planet"] == "Venus":
            p["house"] = 6
    for c in t["cusps"]:
        if c["sign_lord"] == "Venus":
            c["sign_lord"] = "Sun"
    assert kj.judge(t, "foreign", cusp=7)["verdict"] == "not_shown"
    assert kj.judge(_fake("Jupiter", 7, {2, 11}, retro=True), "marriage")["retro"] == "retro_star"


def test_cusp_readings_on_a_real_chart(chart):
    t = kp.kp_tables(chart)
    readings = kj.cusp_readings(t)
    assert [r["cusp"] for r in readings] == list(range(1, 13))
    ids = {j["matter"]["id"] for r in readings for j in r["judgements"]}
    assert ids == {m["id"] for m in kj.matters()}
    for r in readings:
        assert r["sub_lord"] == t["cusps"][r["cusp"] - 1]["sub_lord"]
        for j in r["judgements"]:
            assert j["verdict"] in ("promised", "mixed", "weak", "not_shown")
            assert set(j["for"]) <= set(j["matter"]["houses"])
    for m in kj.matters():
        assert set(kj.timing_planets(t, m["id"])) <= set(kp.ORDER)
