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
requirements = python3,kivy==2.3.0,pyswisseph,tzdata

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
