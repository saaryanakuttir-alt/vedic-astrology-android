"""
app_state.py — the profile data model shared across every screen, ported
from the desktop app's gui_app.py (PROFILE_IDS / PROFILE_LABELS / the
per-profile {"inputs", "chart", "reading"} dict) with all tkinter Variable
plumbing removed. This is plain Python state; each screen reads/writes it
directly and calls back into whatever needs to refresh.
"""

CHILD_SLOT_COUNT = 4

PROFILE_IDS = ["self", "partner"] + [f"child_{i}" for i in range(1, CHILD_SLOT_COUNT + 1)]

PROFILE_LABELS = {"self": "Self (Native)", "partner": "Life Partner"}
PROFILE_LABELS.update({f"child_{i}": f"Child {i}" for i in range(1, CHILD_SLOT_COUNT + 1)})

BLANK_INPUTS = {
    "name": "", "sex": "", "year": "", "month": "", "day": "",
    "hour": "", "minute": "", "second": "0",
    "place": "", "country": "",
    "use_manual_coords": False, "lat": "", "lon": "", "tz": "",
}


class ProfileStore:
    """Holds every profile's raw form inputs plus its last-generated chart
    and reading (both None until Generate Chart succeeds for that profile).
    """

    def __init__(self):
        self.profiles = {
            pid: {"inputs": dict(BLANK_INPUTS), "chart": None, "reading": None}
            for pid in PROFILE_IDS
        }
        self.current_profile_id = "self"

    @property
    def current(self):
        return self.profiles[self.current_profile_id]

    def generated_children(self):
        """[(label, chart, reading), ...] for every Child slot that has a
        generated chart — the shape family_bonds.build_family_compatibility_report
        expects for its `children` argument."""
        out = []
        for i in range(1, CHILD_SLOT_COUNT + 1):
            pid = f"child_{i}"
            data = self.profiles[pid]
            if data["chart"] is not None and data["reading"] is not None:
                out.append((PROFILE_LABELS[pid], data["chart"], data["reading"]))
        return out
