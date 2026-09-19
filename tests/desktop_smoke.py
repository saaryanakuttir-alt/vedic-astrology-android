"""Desktop smoke test for the Android UI (NOT packaged into the APK - the
`tests` dir is excluded in buildozer.spec). Needs: pip install kivy==2.3.1
pyswisseph tzdata filetype pytest. Run:  python tests/desktop_smoke.py
Drives the real widget tree with synthetic touches: every screen opens, the
New Chart form takes input, a chart generates, and each screen renders."""
import os, sys, time, traceback
os.environ["KIVY_NO_ARGS"] = "1"
import tempfile
os.environ.setdefault("KIVY_HOME", os.path.join(tempfile.gettempdir(), "kivy_smoke_home"))
# keep saved people / settings out of the real app folder, and start empty
os.environ["VEDIC_DATA_DIR"] = tempfile.mkdtemp(prefix="vedic_smoke_data_")
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
    for _ in range(60):                      # bounded: the chain ends at the Window, whose parent is itself
        if p is None or p is Window:
            return
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
check(len(cards) == 20, f"20 home cards (got {len(cards)})")
check(not any("Sample" in str(getattr(c, "text", "")) for c in walk(home)), "no Sample Charts card on Home")
check("sample" not in app._registry, "no sample screen registered")
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
from ui import keyboard as kbmod
panel = kbmod.SERVICE.panel
check(kbmod.SERVICE.builtin, "built-in keyboard is the default")
tap(e.name_input)
check(e.name_input.focus, "tap focuses Name field")
check(panel.visible and panel.target is e.name_input, "built-in keyboard opens for the Name field")
check(app.bottom.parent is None, "bottom bar steps aside while the keyboard is up")

def press(label):
    keys = [w for w in walk(panel) if type(w).__name__ == "_Key" and w.text == label]
    assert keys, f"no key {label!r} on the keyboard"
    tap(keys[0], hold=0.02)

for ch in "asha":
    press(ch if ch != "a" or e.name_input.text else "A")   # first letter arrives capitalised
press("space")
for ch in "rao":
    press(ch if ch != "r" else "R")
check(e.name_input.text == "Asha Rao", f"typing on the built-in keyboard (got {e.name_input.text!r})")
tap([w for w in walk(panel) if type(w).__name__ == "_Key" and w.kind == "back"][0], hold=0.02)
check(e.name_input.text == "Asha Ra", "backspace key deletes")
press("o")
check(e.name_input.text == "Asha Rao", "typing continues after backspace")
tap(e.year_input)
check(panel.visible and panel.mode == "number", "Year field gets the number pad")
for ch in "1990":
    press(ch)
check(e.year_input.text == "1990", f"number pad types the year (got {e.year_input.text!r})")
press("Done")
check(not panel.visible and app.bottom.parent is not None and app.bottom.height > 0, "Done closes the keyboard and restores the bottom bar")
e.day_spinner.text = "15"; e.month_spinner.text = "June"
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
check("Year by year from age" not in " ".join(texts(app._screens["relationship"])), "Relationship has no year-by-year prediction")
app.goto("chart"); pump(10)
check(any("In plain terms" in x for x in texts(app._screens["chart"].explain)), "Chart shows plain explanation")
app.goto("help"); pump(6)
check(any("Sammya Das" in x for x in texts(app._screens["help"])), "Help shows credit")
app.goto("home"); pump(4)
check(any("Sammya Das" in x for x in texts(app._screens["home"])), "Home shows credit")

print("== saved birth details (quick recall)")
saved = app.store.saved.all()
check(len(saved) == 1 and saved[0]["inputs"]["name"] == "Asha Rao", "Generate saved the details automatically")
e = app._screens["entry"]
e.save_details(); pump(3)
check(len(app.store.saved.all()) == 1, "saving the same person again updates, not duplicates")
# a second person, then recall the first into the Partner slot
app.store.current_profile_id = "partner"
app.goto("entry"); pump(6)
e.name_input.text = "Ravi Kumar"; e.year_input.text = "1988"
e.day_spinner.text = "3"; e.month_spinner.text = "November"
e.hour_spinner.text = "9"; e.minute_spinner.text = "15"; e.ampm_spinner.text = "AM"
e.place_input.text = "Delhi"; pump(20, 0.05)
sug = [w for w in walk(e.suggest_box) if type(w).__name__ == "Button"][::-1]
check(len(sug) >= 1, "Delhi suggestions appear")
tap(sug[0]); pump(4)
tap(e.generate_btn); pump(30, 0.06)
check(len(app.store.saved.all()) == 2, f"second person saved (status: {e.status_label.text!r}, form name {e.name_input.text!r}, place {e.place_input.text!r})")
app.goto("library"); pump(8)
rows = [w for w in walk(app._screens["library"]) if type(w).__name__ == "_SavedRow"][::-1]
check(len(rows) == 2, f"Saved Charts lists both people ({len(rows)})")
lib = app._screens["library"]
lib.slot_spinner.text = "Child 1"
names = [a.text for r in rows for a in walk(r) if type(a).__name__ == "Label"]
check("Asha Rao" in names, "row shows the saved name")
target = [r for r in rows if any(getattr(w, "text", "") == "Asha Rao" for w in walk(r))][0]
tap(target); pump(40, 0.06)
check(app.current_key == "entry" and app.store.current_profile_id == "child_1", "tapping a saved person opens New Chart on the chosen slot")
c1 = app.store.profiles["child_1"]
check(c1["chart"] is not None and c1["inputs"]["name"] == "Asha Rao", "chart was generated straight from the saved details")
check(c1["chart"]["ascendant"]["sign"] == app.store.profiles["self"]["chart"]["ascendant"]["sign"], "recalled chart matches the original")
# persistence across app restarts
from ui.persist import SavedBirths
again = SavedBirths(os.path.join(os.environ["VEDIC_DATA_DIR"], "saved_births.json"))
check(len(again.all()) == 2, "saved people are on disk")
# delete
app.goto("library"); pump(6)
first_id = app.store.saved.all()[0]["id"]
app.store.saved.delete(first_id); app.goto("library"); pump(6)
rows = [w for w in walk(app._screens["library"]) if type(w).__name__ == "_SavedRow"]
check(len(rows) == 1, "delete removes a saved person")

print("== chart diagram: no stale labels when the person or style changes")
from ui import tabs_chart
for pid in ("self", "partner", "child_1", "self", "partner"):
    app.store.current_profile_id = pid
    app.goto("chart"); pump(14)
    cv = app._screens["chart"].canvas_widget
    check(len(cv.children) == 0, f"{pid}: chart has no child label widgets")
n_north = len(cv.canvas.children)
for style in ("South Indian", "North Indian", "South Indian", "North Indian"):
    app._screens["chart"].style_spinner.text = style; pump(14)
check(len(cv.canvas.children) == n_north, f"redraws do not accumulate canvas instructions ({len(cv.canvas.children)} vs {n_north})")

print("== chart style switch, Medical body map, Predictions pickers, fields outside a ScrollView")
app.store.current_profile_id = "self"
app.goto("chart"); pump(10)
ct = app._screens["chart"]
ct.style_spinner.text = "South Indian"; pump(12)
check(app.store.chart_style == "South Indian" and ct.style_spinner.text == "South Indian"
      and ct.canvas_widget.style == "South Indian", "Chart Diagram: choosing South Indian sticks")
ct.style_spinner.text = "North Indian"; pump(12)
check(ct.canvas_widget.style == "North Indian" and app.store.chart_style == "North Indian", "...and back to North Indian")

app.goto("medical"); pump(12)
med = app._screens["medical"]
canv = [w for w in walk(med) if type(w).__name__ == "BodyMapCanvas"]
check(len(canv) == 1 and len(canv[0].children) == 0 and len(canv[0].canvas.children) > 5, "Medical shows a body-map chart")
check(canv[0].body_short.get(1) == "Head" and canv[0].body_short.get(12) == "Feet", "body map knows the body areas")
mtext = " ".join(texts(med))
check(mtext.count("[In simple terms") >= 6, f"Medical paragraphs carry friendly explanations ({mtext.count('[In simple terms')})")
check(mtext.count("Ayurvedic constitution (Prakriti)") == 1, "constitution appears once, not twice")
mseg = [w for w in walk(med) if type(w).__name__ == "SegmentedControl"][0]
mseg.select("South Indian"); pump(12)
check(canv[0].style == "South Indian", "Medical: switch the body map to South Indian")
mseg.select("North Indian"); pump(8)

app.goto("predictions"); pump(10)
pr = app._screens["predictions"]
tap(pr.year_input)
check(panel.visible and panel.mode == "number", "Predictions year field opens the number pad (and does not freeze)")
pr.year_input.text = ""
for ch in "2027":
    press(ch)
press("Done"); pump(8)
pr.month_spinner.text = "March"; pr.day_spinner.text = "15"; pump(12)
ptxt = " ".join(texts(pr.text_view))
check("2027-03-15" in ptxt, "Predictions computed for the picked date")
check(ptxt.count("[In simple terms") >= 3, f"Predictions carry friendly explanations ({ptxt.count('[In simple terms')})")
pr.year_input.text = "3000"; pr.refresh(); pump(6)
check("between 1900 and 2100" in " ".join(texts(pr.text_view)), "out-of-range year gives a message, not a crash")

app.goto("help"); pump(8)
hp = app._screens["help"]
tap(hp.search_input)
check(panel.visible, "Help search box opens the keyboard without freezing")
press("Done")

print("== language switch (offline Hindi / Bengali)")
import i18n
app.goto("home"); pump(8)
check(len([w for w in walk(app._screens["home"]) if type(w).__name__ == "LanguageBar"]) == 1, "Home has the language bar")
app.set_language("hi"); pump(12)
check(i18n.get_language() == "hi" and app.header.title_label.text == "\u0939\u094b\u092e", "Hindi: header title translated")
check(any("\u091c\u0928\u094d\u092e \u0915\u0941\u0902\u0921\u0932\u0940" in x for x in texts(app._screens["home"])), "Hindi: Home cards translated")
check(app.store.settings.get("language") == "hi", "the language choice is remembered")
app.goto("entry"); pump(8); check(app.current_key == "entry", "screens still open in Hindi")
app.set_language("bn"); pump(12)
check(i18n.get_language() == "bn" and app.current_key == "entry", "Bengali: switching keeps you on the same screen")
app.set_language("en"); pump(12)
check(i18n.get_language() == "en" and app.header.title_label.text == "New Chart", "back to English")

print("\nRESULT:", "PASS" if not FAILS else f"{len(FAILS)} FAILURE(S)")
for f in FAILS: print(" -", f)
sys.exit(0 if not FAILS else 1)
