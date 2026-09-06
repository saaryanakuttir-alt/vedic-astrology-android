[app]

title = Vedic Astrology
package.name = vedicastrology
package.domain = org.vedicastro

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,csv,tab,txt
source.include_patterns = engine/kb/*.json,engine/data/*.csv,engine/data/*.tab
source.exclude_dirs = tests,bin,.github,__pycache__

version = 1.0

# pyswisseph: no official python-for-android recipe exists, so this project
# ships one (see recipes/pyswisseph/__init__.py) via p4a.local_recipes below.
# tzdata: Android's Python build does not reliably expose the system IANA
# timezone database to Python's stdlib zoneinfo module, so the pure-Python
# `tzdata` package (bundles the IANA database itself) is required for
# timezone_resolver.py's zoneinfo.ZoneInfo(...) calls to work correctly.
#
# kivy: pinned to 2.3.1, NOT 2.3.0. Kivy 2.3.0's own pyproject.toml forces
# an exact `cython==3.0.0` inside python-for-android's isolated build venv
# for the kivy recipe specifically, regardless of any Cython version
# installed outside it (see the "Install build dependencies" workflow
# step) - and Cython 3.0.0 predates Python 3.13's removal of the private
# _PyLong_AsByteArray() C-API function, so every Kivy .pyx-generated file
# fails with "too few arguments to function call, expected 6, have 5"
# against this runner's Python 3.14 host build. Kivy 2.3.1 (Dec 2024)
# widened its Cython range (cython_min/cython_max) and explicitly added
# Python 3.13 support, which carries the fix.
requirements = python3,kivy==2.3.1,pyswisseph,tzdata

p4a.local_recipes = ./recipes

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

android.permissions = INTERNET

# Android API levels — 21 (Lollipop) covers effectively all real devices
# still in use; target the latest stable API p4a supports well.
android.minapi = 21
android.api = 33
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
