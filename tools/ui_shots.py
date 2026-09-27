"""ui_shots.py - desktop screenshots of app screens (phone-sized window) for design review.

    python tools/ui_shots.py OUT_DIR [lang] [screen ...]      (venv python; default screens below)

Seeds one sample person, generates the chart, opens each screen and saves OUT_DIR/<screen>.png.
"""
import os
import sys
import tempfile
import time

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["VEDIC_DATA_DIR"] = tempfile.mkdtemp(prefix="vedic_shots_")
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(APP, "engine"), APP]
os.chdir(APP)
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "412")
Config.set("graphics", "height", "892")
import main as appmain  # noqa: E402
from kivy.base import EventLoop  # noqa: E402
from kivy.core.window import Window  # noqa: E402

OUT = sys.argv[1]
LANG = sys.argv[2] if len(sys.argv) > 2 else "en"
SCREENS = sys.argv[3:] or ["home", "entry", "chart", "planets", "dasha", "yogas", "library", "full"]


def pump(n=8, dt=0.03):
    for _ in range(n):
        EventLoop.idle()
        time.sleep(dt)


os.makedirs(OUT, exist_ok=True)
app = appmain.VedicAstrologyApp()
root = app.build()
Window.add_widget(root)
pump(20)
app.goto("entry")
pump(6)
e = app._screens["entry"]
app.store.current_profile_id = "self"
app.store.profiles["self"]["inputs"].update({"name": "Asha Rao", "sex": "Female", "year": "1990", "month": "6", "day": "15",
                                             "hour": "14", "minute": "30", "second": "0", "place": "Mumbai", "country": "IN",
                                             "use_manual_coords": False, "time_known": "yes", "place_meta": None})
e._load_profile_into_form()
assert e._generate_current_profile(quiet=True)
if LANG != "en":
    app.set_language(LANG)
    pump(20)
if os.environ.get("SHOT_THEME"):              # e.g. SHOT_THEME=light - goes through the app's own switch
    app.set_theme(os.environ["SHOT_THEME"])
    pump(20)
for key in SCREENS:
    if key not in app._registry and key != "home":
        print("skip", key)
        continue
    app.goto(key)
    pump(25)
    root.export_to_png(os.path.join(OUT, f"{key}.png"))
    print("saved", key)
