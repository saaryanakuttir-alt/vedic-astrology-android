"""Unit tests for ui/persist.py (saved birth details + settings). Pure Python,
no Kivy. Run from android_app/:  python -m pytest tests/test_persist.py"""
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP not in sys.path:
    sys.path.insert(0, APP)

from ui.persist import SavedBirths, Settings, is_complete  # noqa: E402


def _birth(name="Asha Rao", **over):
    b = {"name": name, "sex": "Female", "year": "1990", "month": "6", "day": "15", "hour": "14", "minute": "30",
         "second": "0", "place": "Mumbai", "country": "IN", "use_manual_coords": False, "lat": "", "lon": "",
         "tz": "", "time_known": "yes", "place_meta": {"lat": 19.07, "lng": 72.88, "country": "IN"}}
    b.update(over)
    return b


def test_save_reload_and_only_birth_fields_are_kept(tmp_path):
    path = tmp_path / "saved.json"
    store = SavedBirths(str(path))
    item = store.save({**_birth(), "chart": {"huge": "object"}, "reading": {"x": 1}})
    assert item and "chart" not in item["inputs"] and "reading" not in item["inputs"]
    again = SavedBirths(str(path))
    assert [p["inputs"]["name"] for p in again.all()] == ["Asha Rao"]
    assert again.get(item["id"])["inputs"]["place_meta"]["country"] == "IN"


def test_same_person_updates_instead_of_duplicating(tmp_path):
    store = SavedBirths(str(tmp_path / "s.json"))
    a = store.save(_birth())
    b = store.save(_birth(place="Pune"))            # same name + date + time, corrected place
    assert a["id"] == b["id"] and len(store.all()) == 1
    assert store.all()[0]["inputs"]["place"] == "Pune"
    store.save(_birth("Ravi Kumar", year="1988"))
    assert len(store.all()) == 2


def test_incomplete_details_are_not_saved(tmp_path):
    store = SavedBirths(str(tmp_path / "s.json"))
    assert store.save(_birth(year="")) is None
    assert store.save(_birth(place="")) is None
    assert store.save(_birth(place="", use_manual_coords=True, lat="1", lon="2", tz="Asia/Kolkata")) is not None
    assert not is_complete({"name": "x"})


def test_newest_first_and_delete(tmp_path):
    store = SavedBirths(str(tmp_path / "s.json"))
    first = store.save(_birth("One"))
    second = store.save(_birth("Two", year="1991"))
    assert [p["inputs"]["name"] for p in store.all()] == ["Two", "One"]
    assert store.delete(first["id"]) and not store.delete(first["id"])
    assert [p["id"] for p in SavedBirths(str(tmp_path / "s.json")).all()] == [second["id"]]


def test_corrupt_file_is_set_aside_not_fatal(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{ not json", encoding="utf-8")
    store = SavedBirths(str(path))
    assert store.all() == []
    assert (tmp_path / "s.json.bad").exists()
    assert store.save(_birth()) is not None          # and it keeps working afterwards


def test_settings_round_trip(tmp_path):
    path = str(tmp_path / "settings.json")
    s = Settings(path)
    assert s.get("keyboard", "builtin") == "builtin"
    s.set("keyboard", "phone")
    assert Settings(path).get("keyboard") == "phone"
