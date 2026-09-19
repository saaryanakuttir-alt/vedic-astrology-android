"""Offline translation layer checks. Run from android_app/: python -m pytest tests/test_i18n.py"""
import os
import re
import sys

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import i18n  # noqa: E402
import i18n_bn  # noqa: E402
import i18n_hi  # noqa: E402


def test_hindi_and_bengali_cover_the_same_strings():
    assert set(i18n_hi.T) == set(i18n_bn.T), sorted(set(i18n_hi.T) ^ set(i18n_bn.T))[:5]


def test_no_empty_or_english_only_translations():
    for name, table in (("hi", i18n_hi.T), ("bn", i18n_bn.T)):
        for key, value in table.items():
            assert value.strip(), (name, key)
            assert re.search(r"[\u0900-\u097F\u0980-\u09FF]", value), (name, key, value)


def test_placeholders_are_preserved():
    slot = re.compile(r"\{[a-z_0-9]+\}")
    for table in (i18n_hi.T, i18n_bn.T):
        for key, value in table.items():
            assert sorted(slot.findall(key)) == sorted(slot.findall(value)), (key, value)


def test_t_falls_back_to_english_and_fills_slots():
    i18n.set_language("hi")
    assert i18n.t("Home") == "होम"
    assert i18n.t("Some text nobody translated yet") == "Some text nobody translated yet"
    assert i18n.t("Age {age}", age=24) == "Age 24"          # untranslated template still fills its slot
    i18n.set_language("bn")
    assert i18n.t("Home") == "হোম"
    i18n.set_language("xx")                                   # unknown code -> English
    assert i18n.get_language() == "en" and i18n.t("Home") == "Home"
