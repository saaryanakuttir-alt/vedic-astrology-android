"""
persist.py — the little bit of on-device storage this app has: the birth
details people save for quick recall, and a couple of settings. Plain JSON
files in the app's private data folder (App.user_data_dir on Android), so it
stays fully offline and nothing is ever uploaded.

Writes are atomic (write a temp file, then replace) so a crash or a killed
app can never leave a half-written file, and a corrupt or unreadable file is
set aside as *.bad and replaced by an empty one rather than crashing start-up.
"""
import json
import os
import time
import uuid

MAX_SAVED = 200

# The birth-detail fields worth remembering (the same keys the New Chart form
# writes into a profile's "inputs"). Anything else (charts, readings) is not
# stored - they are cheap to regenerate and large.
BIRTH_KEYS = (
    "name", "sex", "year", "month", "day", "hour", "minute", "second",
    "place", "country", "use_manual_coords", "lat", "lon", "tz", "time_known", "place_meta",
)


class _JsonFile:
    def __init__(self, path):
        self.path = path

    def read(self, default):
        try:
            with open(self.path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return default
        except (OSError, ValueError):
            try:
                os.replace(self.path, self.path + ".bad")
            except OSError:
                pass
            return default

    def write(self, data):
        try:
            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False   # storage full / read-only: the app keeps working, just without saving


def _birth_only(inputs):
    return {k: inputs.get(k) for k in BIRTH_KEYS if k in inputs}


def is_complete(inputs):
    """Enough to be worth saving: a date of birth plus either a place or coordinates."""
    if not all(str(inputs.get(k) or "").strip().isdigit() for k in ("year", "month", "day")):
        return False
    return bool((inputs.get("place") or "").strip() or inputs.get("use_manual_coords"))


def same_person(a, b):
    """Do two sets of birth details describe the same person, so that saving
    again UPDATES the existing entry instead of adding a duplicate?

    TODO(human): decide the rule. The default below treats two entries as the
    same person when the name (ignoring case and extra spaces) AND the date
    and time of birth all match. Other reasonable choices: ignore the name
    and match on date + time + place (so fixing a typo in the name updates
    rather than duplicates), or never match (every save adds a new row).
    """
    def key(x):
        return ((x.get("name") or "").strip().lower(), str(x.get("year")), str(x.get("month")),
                str(x.get("day")), str(x.get("hour")), str(x.get("minute")))
    return key(a) == key(b)


class SavedBirths:
    """Saved people, newest first. Each entry: {"id", "saved_at", "inputs"}."""

    def __init__(self, path):
        self._file = _JsonFile(path)
        data = self._file.read({"people": []})
        people = data.get("people") if isinstance(data, dict) else None
        self._items = [p for p in (people or []) if isinstance(p, dict) and isinstance(p.get("inputs"), dict)]
        self._sort()

    def _sort(self):
        self._items.sort(key=lambda p: p.get("saved_at", 0), reverse=True)

    def _flush(self):
        return self._file.write({"version": 1, "people": self._items})

    def all(self):
        return list(self._items)

    def get(self, saved_id):
        return next((p for p in self._items if p.get("id") == saved_id), None)

    def save(self, inputs):
        """Add (or update, per same_person) and return the entry, or None if
        the details are too incomplete to be worth keeping."""
        if not is_complete(inputs):
            return None
        birth = _birth_only(inputs)
        now = time.time()
        for item in self._items:
            if same_person(item["inputs"], birth):
                item["inputs"], item["saved_at"] = birth, now
                break
        else:
            item = {"id": uuid.uuid4().hex[:12], "saved_at": now, "inputs": birth}
            self._items.append(item)
        self._sort()
        del self._items[MAX_SAVED:]               # newest first, so this drops the oldest
        self._flush()
        return item

    def delete(self, saved_id):
        before = len(self._items)
        self._items = [p for p in self._items if p.get("id") != saved_id]
        if len(self._items) != before:
            self._flush()
            return True
        return False


class Settings:
    def __init__(self, path):
        self._file = _JsonFile(path)
        data = self._file.read({})
        self._data = data if isinstance(data, dict) else {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        if self._data.get(key) != value:
            self._data[key] = value
            self._file.write(self._data)
