"""Desktop smoke test for the Android UI (NOT packaged into the APK - the
`tests` dir is excluded in buildozer.spec). Needs: pip install kivy==2.3.1
pyswisseph tzdata filetype pytest. Run:  python tests/desktop_smoke.py
Drives the real widget tree with synthetic touches: every screen opens, the
New Chart form takes input, a chart generates, and each screen renders."""
import os, sys, time, traceback
os.environ["KIVY_NO_ARGS"] = "1"
import tempfile
os.environ.setdefault("KIVY_HOME", os.path.join(tempfile.gettempdir(), "kivy_smoke_home"))
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
os.chdir(APP)

from kivy.config import Config
Config.set("graphics", "width", "412")
Config.set("graphics", "height", "892")
Config.set("graphics", "resizable", "0")

import main as appmain
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.tests.common import UnitTestTouch

FAILS = []
def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond: FAILS.append(msg)

def pump(n=8, dt=0.03):
    for _ in range(n):
        EventLoop.idle(); time.sleep(dt)

def center(w): return w.to_window(*w.center)

def scroll_into_view(w):
    from kivy.uix.scrollview import ScrollView
    p = w.parent
    while p is not None:
        if isinstance(p, ScrollView) and p.do_scroll_y:
            try: p.scroll_to(w, padding=20, animate=False)
            except Exception: pass
            pump(3)
            return
        p = p.parent

def tap(w, hold=0.03):
    scroll_into_view(w)
    x, y = center(w)
    t = UnitTestTouch(x, y); t.touch_down(); pump(2); time.sleep(hold)
    t.touch_up(); pump(14, 0.05)

def walk(w, out=None):
    out = [] if out is None else out
    out.append(w)
    for c in w.children: walk(c, out)
    return out

def texts(root):
    return [str(getattr(w, "text", "")) for w in walk(root) if hasattr(w, "text")]

app = appmain.VedicAstrologyApp()
root = app.build()
Window.add_widget(root)
pump(25)

print("== screens open without error, with a chart-less store")
for key in list(app._registry):
    try:
        app.goto(key); pump(6)
        scr = app._screens[key]
        check(scr.width > 100 and scr.height > 100, f"{key}: laid out ({scr.width:.0f}x{scr.height:.0f})")
    except Exception:
        traceback.print_exc(); check(False, f"{key}: raised")
app.goto("home"); pump(4)
check(app.header.title_label.text == "Home", "header title is Home")

print("== Home cards navigate")
home = app._screens["home"]
cards = [w for w in walk(home) if type(w).__name__ == "HomeCard"][::-1]   # insertion order
check(len(cards) == 21, f"21 home cards (got {len(cards)})")
tap(cards[0])
check(app.current_key == "entry", "Birth Chart card -> entry")
app.goto("home"); pump(3)
# Divisional Charts card presets D9
tap(cards[1])
check(app.current_key == "chart", "Divisional Charts card -> chart")
check("D9" in app._screens["chart"].varga_spinner.text or "Navamsa" in app._screens["chart"].varga_spinner.text, "chart preset to D9")

print("== entry form via touch")
app.goto("entry"); pump(8)
e = app._screens["entry"]
tap(e.name_input)
check(e.name_input.focus, "tap focuses Name field")
e.name_input.insert_text("Asha Rao")
check(e.name_input.text == "Asha Rao", "typing lands in Name field")
e.day_spinner.text = "15"; e.month_spinner.text = "June"; e.year_input.text = "1990"
e.hour_spinner.text = "2"; e.minute_spinner.text = "30"; e.ampm_spinner.text = "PM"
# time toggle
tap(e.time_seg._buttons["Unknown"]); pump(4)
check(e.time_seg.selected == "Unknown" and e.time_note.parent is e.time_box, "Unknown time shows the noon note")
tap(e.time_seg._buttons["Known"]); pump(4)
check(e.time_row.parent is e.time_box, "Known time shows h/m/ampm row")
# place suggestions
e.place_input.text = ""
e.place_input.text = "mum"
pump(20, 0.05)
sug = [w for w in walk(e.suggest_box) if type(w).__name__ == "Button"][::-1]   # insertion order: Mumbai first
check(len(sug) >= 1, f"city suggestions appear ({len(sug)})")
if sug:
    tap(sug[0]); pump(4)
    check(e.place_input.text == "Mumbai" and e._place_meta and e._place_meta["country"] == "IN", "picking a city fills place + country")
# generate via touch
tap(e.generate_btn); pump(30, 0.06)
prof = app.store.profiles["self"]
check(prof["chart"] is not None and prof["reading"] is not None, "Generate builds chart + reading")
if prof["chart"]:
    check(prof["chart"]["ascendant"]["sign"] == "Virgo", f"Lagna Virgo (got {prof['chart']['ascendant']['sign']})")
    check(prof["inputs"]["hour"] == "14", f"2:30 PM stored as 14h (got {prof['inputs']['hour']!r})")
check(e.result_holder.height > 0, "result card is shown")
rtxt = " | ".join(texts(e.result_holder))
check("Lagna" in rtxt and "Moon" in rtxt and "Sun" in rtxt, f"result tags real signs: {rtxt[:80]}")

print("== every screen renders content for the generated chart")
for key in list(app._registry):
    try:
        app.goto(key); pump(10)
    except Exception:
        traceback.print_exc(); check(False, f"{key}: raised with chart")
        continue
    scr = app._screens[key]
    t = " ".join(texts(scr))
    check(len(t) > 20, f"{key}: has text ({len(t)} chars)")
    bad = [x for x in ("Traceback", "hit an error", "Could not build") if x in t]
    check(not bad, f"{key}: no error text {bad}")

print("== new sections carry the new content")
app.goto("medical"); pump(10)
check(any("Ayurvedic" in x for x in texts(app._screens["medical"])), "Medical shows Ayurvedic constitution")
app.goto("predictions"); pump(10)
check(any("Dasha & Muntha" in x for x in texts(app._screens["predictions"])), "Predictions shows year note")
app.goto("relationship"); pump(10)
check(any("tendency, not a count" in x for x in texts(app._screens["relationship"])), "Relationship shows count tendency")
app.goto("chart"); pump(10)
check(any("In plain terms" in x for x in texts(app._screens["chart"].explain)), "Chart shows plain explanation")
app.goto("help"); pump(6)
check(any("Sammya Das" in x for x in texts(app._screens["help"])), "Help shows credit")
app.goto("home"); pump(4)
check(any("Sammya Das" in x for x in texts(app._screens["home"])), "Home shows credit")

print("== library + profile switching")
app.goto("library"); pump(8)
rows = [w for w in walk(app._screens["library"]) if type(w).__name__ == "_LibraryRow"][::-1]
check(len(rows) == 6, f"6 library rows ({len(rows)})")
tap(rows[1]); pump(6)
check(app.current_key == "entry" and app.store.current_profile_id == "partner", "library row opens that slot in entry")

print("== example family")
e = app._screens["entry"]
e._fill_example_all(); pump(10)
check(all(app.store.profiles[p]["chart"] is not None for p in app.store.profiles), "example family generated all 6")

print("\nRESULT:", "PASS" if not FAILS else f"{len(FAILS)} FAILURE(S)")
for f in FAILS: print(" -", f)
sys.exit(0 if not FAILS else 1)
