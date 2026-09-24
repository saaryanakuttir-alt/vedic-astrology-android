"""Unit tests for engine/edition.py (the full vs lite/compact build split) and for consistency
between it and main.py / ui/tabs_home.py. Pure Python, no Kivy - run from android_app/:
python -m pytest tests/test_edition.py"""
import importlib
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in (APP, os.path.join(APP, "engine")):
    if d not in sys.path:
        sys.path.insert(0, d)

import edition  # noqa: E402


def _reload_with_env(value):
    """engine/edition.py reads VEDIC_EDITION once, at import time - reload it under a
    changed/removed env var the way the real app never does but a test needs to."""
    if value is None:
        os.environ.pop("VEDIC_EDITION", None)
    else:
        os.environ["VEDIC_EDITION"] = value
    return importlib.reload(edition)


def test_default_edition_is_full():
    mod = _reload_with_env(None)
    assert mod.EDITION == "full"
    importlib.reload(edition)


def test_full_edition_sees_every_key():
    mod = _reload_with_env("full")
    assert mod.visible("literally_anything_not_a_real_key")
    importlib.reload(edition)


def test_lite_edition_only_sees_free_screens():
    mod = _reload_with_env("lite")
    for key in mod.FREE_SCREENS:
        assert mod.visible(key)
    assert not mod.visible("yogas")            # a Premium-only screen must not leak into lite
    assert not mod.visible("dasha")
    assert not mod.visible("full")             # "full" here is the Full Reading SCREEN key, not the edition
    importlib.reload(edition)


def _registry_keys():
    """main.py's `self._registry = {...}` keys, without importing kivy."""
    src = open(os.path.join(APP, "main.py"), encoding="utf-8").read()
    block = re.search(r"self\._registry = \{(.*?)\n\s*\}\n", src, re.S).group(1)
    return set(re.findall(r'^\s*"([a-z_]+)":', block, re.M))


def _home_card_keys():
    """Every (key, title, desc, icon, preset) card key in ui/tabs_home.py's HOME_CORE + HOME_GROUPS."""
    src = open(os.path.join(APP, "ui", "tabs_home.py"), encoding="utf-8").read()
    return set(re.findall(r'\(\s*"([a-z_]+)",\s*"[^"]*",\s*"[^"]*",\s*"[a-z]+",', src))


def test_free_screens_are_all_real_registry_keys():
    # every key promised to lite users must actually be something main.py can build -
    # a typo here would silently vanish from Home instead of erroring.
    assert edition.FREE_SCREENS <= _registry_keys()


def test_free_screens_all_have_a_home_card():
    # (except "home" itself, which isn't a card - it's where the cards live)
    assert edition.FREE_SCREENS - {"home"} <= _home_card_keys()


def test_lite_bottom_nav_only_uses_free_screens():
    src = open(os.path.join(APP, "main.py"), encoding="utf-8").read()
    block = re.search(r"BOTTOM_NAV_LITE = \[(.*?)\]\n", src, re.S).group(1)
    keys = re.findall(r'\("([a-z_]+)"', block)
    assert keys, "BOTTOM_NAV_LITE should not be empty"
    for key in keys:
        assert key in edition.FREE_SCREENS, f"BOTTOM_NAV_LITE points at {key!r}, which lite hides"


def test_ci_can_flip_the_default_to_lite():
    # build-apk.yml does `sed -i 's/"VEDIC_EDITION", "full"/"VEDIC_EDITION", "lite"/' engine/edition.py` -
    # this exact substring must appear, and appear exactly once, or that sed silently does nothing.
    src = open(os.path.join(APP, "engine", "edition.py"), encoding="utf-8").read()
    assert src.count('"VEDIC_EDITION", "full"') == 1


def test_buildozer_lite_profile_has_a_distinct_package_id():
    spec = open(os.path.join(APP, "buildozer.spec"), encoding="utf-8").read()
    main_name = re.search(r"^package\.name\s*=\s*(\S+)", spec, re.M).group(1)
    lite_block = re.search(r"\[app@lite\](.*?)(?:\n\[|\Z)", spec, re.S).group(1)
    lite_name = re.search(r"^package\.name\s*=\s*(\S+)", lite_block, re.M).group(1)
    assert lite_name != main_name
