"""
tabs_home.py — the design's Home menu and Saved Charts (Library) screens.

Home is a 2-column grid of outlined cards. The 8 core cards match the
handoff exactly; the "More readings" section lists this app's other screens
(the design's placeholders are replaced by real content). Saved Charts lists
the six profile slots. The credit line lives at the foot of Home.
"""
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from ui import theme
from ui.app_state import PROFILE_IDS, PROFILE_LABELS
from ui.theme import HomeCard, OutlineBox

CREDIT = "Created by Sammya Das"

# (screen key, title, one-line description, icon, optional preset)
HOME_CORE = [
    ("entry", "Birth Chart", "Generate and view a chart", "diamond", None),
    ("chart", "Divisional Charts", "D9, D10 and more", "grid", "D9"),
    ("planets", "Planet in House", "Placement readings", "house", None),
    ("planets", "Planet in Sign", "Sign-based readings", "sign", None),
    ("houses", "House Lord Placements", "Lordship analysis", "key", None),
    ("yogas", "Classical Yogas", "Yoga combinations", "rings", None),
    ("dasha", "Mahadasha & Antardasha", "Planetary periods", "clock", None),
    ("library", "Saved Charts", "Your library", "book", None),
]
HOME_MORE = [
    ("chart", "Chart Diagram", "North / South Indian", "diamond", None),
    ("kundli", "Kundli Details", "Key facts & classifications", "card", None),
    ("ashtakvarga", "Ashtakvarga", "Sign-by-sign support", "grid", None),
    ("chalit", "Chalit", "Bhava house boundaries", "diamond", None),
    ("karmic", "Karmic & Past Life", "Old patterns, new direction", "infinity", None),
    ("life", "Life Predictions", "Career, wealth, family", "star", None),
    ("predictions", "Predictions", "Any date, year & transits", "calendar", None),
    ("medical", "Medical Astrology", "Body areas & constitution", "cross", None),
    ("relationship", "Relationship Themes", "Marriage & partnership", "heart", None),
    ("full", "Full Reading", "Everything in one report", "doc", None),
    ("family", "Family Compatibility", "Partner & child bonds", "people", None),
    ("sample", "Sample Charts", "Well-known public figures", "star", None),
    ("help", "Help & About", "FAQ and credits", "help", None),
]


class HomeScreen(BoxLayout):
    def __init__(self, store, goto, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.goto = goto
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        body = BoxLayout(orientation="vertical", size_hint_y=None, padding=(dp(18), dp(2), dp(18), dp(20)),
                         spacing=dp(12))
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        self.add_widget(scroll)

        sub = Label(text="Your birth-chart engine and classical interpretive library.", font_size="13sp",
                    color=theme.MUTED, halign="left", valign="middle", size_hint_y=None, height=dp(24))
        sub.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        body.add_widget(sub)
        body.add_widget(self._grid(HOME_CORE))

        more = Label(text="MORE READINGS", font_size="11sp", color=theme.ACCENT, halign="left", valign="middle",
                     size_hint_y=None, height=dp(28), bold=True)
        more.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        body.add_widget(more)
        body.add_widget(self._grid(HOME_MORE))

        credit = Label(text=CREDIT, font_size="12sp", color=theme.MUTED, italic=True,
                       size_hint_y=None, height=dp(44))
        body.add_widget(credit)

    def _grid(self, items):
        rows = (len(items) + 1) // 2
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=rows * dp(108) + (rows - 1) * dp(10))
        for key, title, desc, icon, preset in items:
            grid.add_widget(HomeCard(icon, title, desc,
                                     on_press_cb=lambda k=key, p=preset: self.goto(k, preset=p)))
        return grid

    def refresh(self):
        pass


class _LibraryRow(ButtonBehavior, OutlineBox):
    def __init__(self, initial, name, summary, generated, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(64))
        kwargs.setdefault("padding", (dp(12), dp(10)))
        kwargs.setdefault("spacing", dp(12))
        super().__init__(orientation="horizontal", **kwargs)
        av = Label(text=initial, bold=True, font_size="14sp", size_hint=(None, None), size=(dp(36), dp(36)),
                   pos_hint={"center_y": 0.5})
        with av.canvas.after:
            Color(*theme.DIVIDER)
            self._ring = Line(circle=(av.center_x, av.center_y, dp(18)), width=1.5)
        av.bind(pos=lambda inst, _v: setattr(self._ring, "circle", (inst.center_x, inst.center_y, dp(18))),
                size=lambda inst, _v: setattr(self._ring, "circle", (inst.center_x, inst.center_y, dp(18))))
        self.add_widget(av)
        col = BoxLayout(orientation="vertical")
        n = Label(text=name, bold=True, font_size="15sp", halign="left", valign="bottom")
        n.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        s = Label(text=summary, font_size="11sp", color=theme.MUTED, halign="left", valign="top")
        s.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        col.add_widget(n)
        col.add_widget(s)
        self.add_widget(col)
        tag = OutlineBox(accent=generated, size_hint=(None, None), size=(dp(84), dp(24)), pos_hint={"center_y": 0.5})
        tl = Label(text="Generated" if generated else "Draft", font_size="11sp",
                   color=theme.ACCENT if generated else theme.NEUTRAL_800)
        tag.add_widget(tl)
        self.add_widget(tag)
        self.bind(state=lambda inst, st: inst.set_accent(st == "down"))


class LibraryScreen(BoxLayout):
    """Saved Charts: the six profile slots. Tapping one loads it into the
    New Chart screen (the design's behaviour)."""

    def __init__(self, store, goto, on_open, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.goto = goto
        self.on_open = on_open
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.body = BoxLayout(orientation="vertical", size_hint_y=None, padding=(dp(18), dp(14), dp(18), dp(20)),
                              spacing=dp(10))
        self.body.bind(minimum_height=self.body.setter("height"))
        scroll.add_widget(self.body)
        self.add_widget(scroll)

    def refresh(self):
        self.body.clear_widgets()
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                  "October", "November", "December"]
        for pid in PROFILE_IDS:
            data = self.store.profiles[pid]
            inp = data["inputs"]
            name = (inp.get("name") or "").strip() or PROFILE_LABELS[pid]
            if str(inp.get("year") or "").isdigit() and str(inp.get("month") or "").isdigit() and str(inp.get("day") or "").isdigit():
                summary = f"{months[int(inp['month']) - 1]} {int(inp['day'])}, {inp['year']}"
                if inp.get("place"):
                    summary += f" · {inp['place']}"
            else:
                summary = "Empty - tap to enter birth details"
            row = _LibraryRow(name[:1].upper(), name, summary, data["chart"] is not None)
            row.bind(on_release=lambda inst, p=pid: self.on_open(p))
            self.body.add_widget(row)
