"""
app_state.py — the profile data model shared across every screen, ported
from the desktop app's gui_app.py (PROFILE_IDS / PROFILE_LABELS / the
per-profile {"inputs", "chart", "reading"} dict) with all tkinter Variable
plumbing removed. This is plain Python state; each screen reads/writes it
directly and calls back into whatever needs to refresh.

The store also owns the two things kept on the device between runs (see
ui/persist.py): `saved` (birth details saved for quick recall) and `settings`.
"""
import copy
import os
import tempfile

from ui.persist import SavedBirths, Settings

CHILD_SLOT_COUNT = 2      # the profile row on New Chart shows Self, Life Partner and two child slots

PROFILE_IDS = ["self", "partner"] + [f"child_{i}" for i in range(1, CHILD_SLOT_COUNT + 1)]

PROFILE_LABELS = {"self": "Self (Native)", "partner": "Life Partner"}
PROFILE_LABELS.update({f"child_{i}": f"Child {i}" for i in range(1, CHILD_SLOT_COUNT + 1)})

BLANK_INPUTS = {
    "name": "", "sex": "", "year": "", "month": "", "day": "",
    "hour": "", "minute": "", "second": "0",
    "place": "", "country": "",
    "use_manual_coords": False, "lat": "", "lon": "", "tz": "",
    "time_known": "yes",
}


class ProfileStore:
    """Holds every profile's raw form inputs plus its last-generated chart
    and reading (both None until Generate Chart succeeds for that profile).
    """

    def __init__(self, data_dir=None):
        data_dir = data_dir or tempfile.mkdtemp(prefix="vedic_astrology_")
        self.data_dir = data_dir
        self.saved = SavedBirths(os.path.join(data_dir, "saved_births.json"))
        self.settings = Settings(os.path.join(data_dir, "settings.json"))
        self.profiles = {
            pid: {"inputs": dict(BLANK_INPUTS), "chart": None, "reading": None}
            for pid in PROFILE_IDS
        }
        self.current_profile_id = "self"
        # Chart diagram style, chosen on the New Chart screen (North/South).
        self.chart_style = "North Indian"

    @property
    def current(self):
        return self.profiles[self.current_profile_id]

    def load_saved_into(self, slot_id, record):
        """Put a saved person's birth details into a profile slot (no chart
        yet - the caller generates it) and make that slot current."""
        inputs = dict(BLANK_INPUTS)
        inputs.update(copy.deepcopy(record["inputs"]))
        self.profiles[slot_id] = {"inputs": inputs, "chart": None, "reading": None}
        self.current_profile_id = slot_id

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
