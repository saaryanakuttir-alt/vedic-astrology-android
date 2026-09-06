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

# Pin python-for-android to its last pre-rewrite release (Jan 2024). Buildozer
# git-clones p4a fresh on every build (not a pip dependency) and defaults to
# "master" - which had no releases between 2024.01.21 and 2026.05.09, then
# jumped straight to targeting Python 3.14 as the on-device CPython. That
# jump broke this build twice: Python 3.13 removed a private C-API function
# Kivy's Cython-generated code needs (fixed by bumping kivy to 2.3.1 above),
# and separately pip's own venv bootstrap breaks under 3.14 with an
# unrelated ImportError. v2024.01.21 predates Python 3.13/3.14 entirely and
# targets a mature, widely-used CPython version, sidestepping both at once.
p4a.branch = v2024.01.21

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

android.permissions = INTERNET

# Android API levels. minapi bumped from 21 to 26: the pinned
# python-for-android (v2024.01.21) builds CPython 3.11 for the device, and
# CPython's grp module calls setgrent()/getgrent()/endgrent(), which
# Android's Bionic libc only declares at API 26+. Building against ndk-api
# 21 made those implicit declarations a fatal -Werror compile error
# (grpmodule.c) - raising the floor to 26 (Android 8.0, still ~95%+ of
# active devices) makes them available and lets CPython compile. See the
# grpmodule.c errors in the earlier CI logs.
android.minapi = 26
android.api = 33
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
