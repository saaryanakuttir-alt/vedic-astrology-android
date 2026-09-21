"""prastara.py - Prastharashtakvarga: for each planet's Bhinnashtakvarga, WHO gives each point. Rows are the eight
contributors (Sun ... Saturn and the Lagna), columns the twelve signs; a 1 means that contributor gives a point
to the sign. The column totals are exactly the planet's Bhinnashtakvarga row.
"""
from ashtakvarga import PLANET_ORDER, _CONTRIBUTIONS, _positions_to_signs
from panchanga import SIGNS

CONTRIBUTORS = PLANET_ORDER + ["Lagna"]


def prastara(chart, target):
    """{"rows": {contributor: [12 x 0/1]}, "totals": [12 ints]} for one planet's Prastharashtakvarga."""
    signs = {p: chart["planets"][p]["sign"] for p in PLANET_ORDER}
    signs["Lagna"] = chart["ascendant"]["sign"]
    rows = {}
    for contributor, positions in _CONTRIBUTIONS[target].items():
        got = _positions_to_signs(SIGNS.index(signs[contributor]), positions)
        rows[contributor] = [1 if i in got else 0 for i in range(12)]
    totals = [sum(r[i] for r in rows.values()) for i in range(12)]
    return {"rows": {c: rows[c] for c in CONTRIBUTORS if c in rows}, "totals": totals}


def all_prastara(chart):
    return {p: prastara(chart, p) for p in PLANET_ORDER}
