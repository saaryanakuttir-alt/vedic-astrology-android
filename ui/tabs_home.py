"""
tabs_home.py — the design's Home menu and Saved Charts (Library) screens.

Home is a 2-column grid of outlined cards. The 8 core cards match the
handoff exactly; the "More readings" section lists this app's other screens
(the design's placeholders are replaced by real content). Saved Charts lists
the birth details saved on this device, for one-tap recall. The credit line
lives at the foot of Home.
"""
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from ui import theme
from ui.app_state import PROFILE_IDS, PROFILE_LABELS
from ui.theme import HomeCard, OutlineBox, ThemedButton, ThemedSpinner
from ui.version import VERSION

CREDIT = "Created by Sammya Das"

# (screen key, title, one-line description, icon, optional preset)
HOME_CORE = [
    ("entry", "Birth Chart", "Generate and view a chart", "diamond", None),
    ("chart", "Divisional Charts", "D9, D10 and more", "grid", "D9"),
    ("planet_house", "Planet in House", "Which life area each planet is in", "house", None),
    ("planet_sign", "Planet in Sign", "How each planet behaves in its sign", "sign", None),
    ("houses", "House Lord Placements", "Lordship analysis", "key", None),
    ("yogas", "Classical Yogas", "Yoga combinations", "rings", None),
    ("dasha", "Mahadasha & Antardasha", "Planetary periods", "clock", None),
    ("library", "Saved Charts", "Your saved birth details", "book", None),
]
HOME_GROUPS = [
    ("CHARTS & TABLES", [
        ("chart", "Chart Diagram", "North / South Indian", "diamond", None),
        ("kundli", "Kundli Details", "Key facts & classifications", "card", None),
        ("shodashvarga", "Shodashvarga Table", "All 15 divisional charts", "grid", None),
        ("ashtakvarga", "Ashtakvarga", "Sign-by-sign support", "grid", None),
        ("prastara", "Ashtakvarga Detail", "Who gives each point", "grid", None),
        ("chalit", "Chalit", "Bhava house boundaries", "diamond", None),
        ("kp", "KP System", "Cusps, star & sub lords", "grid", None),
    ]),
    ("READINGS", [
        ("nature", "Your Nature", "Character, career, hobbies", "star", None),
        ("life", "Life Predictions", "Career, wealth, family", "star", None),
        ("karmic", "Karmic & Past Life", "Old patterns, new direction", "infinity", None),
        ("medical", "Medical Astrology", "Body areas & constitution", "cross", None),
        ("relationship", "Relationship Themes", "Marriage & partnership", "heart", None),
        ("full", "Full Reading", "Everything in one report", "doc", None),
    ]),
    ("TIMING & YEARS", [
        ("moredashas", "More Dashas", "Yogini, Char & Karakamsa", "hourglass", None),
        ("varshaphal", "Varshaphal", "Your year, from birthday", "calendar", None),
        ("predictions", "Predictions", "Any date, year & transits", "calendar", None),
    ]),
    ("STRENGTH, DOSHAS & REMEDIES", [
        ("relations", "Planet by Planet", "Good, mixed or needs care?", "gem", None),
        ("strength", "Planet Strength", "How strong is each planet?", "gem", None),
        ("doshas", "Doshas & Sade Sati", "Manglik, Kalsarpa, Saturn", "warn", None),
        ("remedies", "Remedies", "What helps right now", "key", None),
    ]),
    ("PEOPLE & HELP", [
        ("family", "Family Compatibility", "Partner & child bonds", "people", None),
        ("help", "Help & About", "FAQ and credits", "help", None),
    ]),
]
HOME_MORE = [card for _title, cards in HOME_GROUPS for card in cards]      # flat list of every card in the groups


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

        for title, cards in HOME_GROUPS:
            heading = Label(text=title, font_size="11sp", color=theme.ACCENT, halign="left", valign="middle",
                            size_hint_y=None, height=dp(28), bold=True)
            heading.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
            body.add_widget(heading)
            body.add_widget(self._grid(cards))

        credit = Label(text=f"{CREDIT}  -  version {VERSION}", font_size="12sp", color=theme.MUTED, italic=True,
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


_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"]


def describe_birth(inp):
    """'June 15, 1990 · 2:30 PM · Mumbai' for a saved person's inputs."""
    try:
        text = f"{_MONTHS[int(inp['month']) - 1]} {int(inp['day'])}, {inp['year']}"
    except (KeyError, ValueError, IndexError, TypeError):
        return "Incomplete details"
    if inp.get("time_known") == "no":
        text += " · time unknown"
    elif str(inp.get("hour", "")).isdigit():
        hh, mm = int(inp["hour"]), int(inp.get("minute") or 0)
        text += f" · {hh % 12 or 12}:{mm:02d} {'PM' if hh >= 12 else 'AM'}"
    place = (inp.get("place") or "").strip()
    if place:
        text += f" · {place}"
    elif inp.get("use_manual_coords"):
        text += " · exact coordinates"
    return text


class _SavedRow(ButtonBehavior, OutlineBox):
    """One saved person: avatar initial, name, birth summary, and a Delete
    button. Tapping anywhere else on the row loads them."""

    def __init__(self, initial, name, summary, on_delete, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(64))
        kwargs.setdefault("padding", (dp(12), dp(10), dp(8), dp(10)))
        kwargs.setdefault("spacing", dp(10))
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
        n = Label(text=name, bold=True, font_size="15sp", halign="left", valign="bottom", shorten=True,
                  shorten_from="right")
        n.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        s = Label(text=summary, font_size="11sp", color=theme.MUTED, halign="left", valign="top", shorten=True,
                  shorten_from="right")
        s.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        col.add_widget(n)
        col.add_widget(s)
        self.add_widget(col)
        delete = ThemedButton(text="Delete", variant="ghost", size_hint=(None, None), size=(dp(64), dp(32)),
                              font_size="12sp", pos_hint={"center_y": 0.5})
        delete.bind(on_release=lambda *_: on_delete())
        self.add_widget(delete)
        self.bind(state=lambda inst, st: inst.set_accent(st == "down"))


class LibraryScreen(BoxLayout):
    """Saved Charts: the birth details saved on this device, newest first.
    Tapping a person loads them into the chosen profile slot and generates
    their chart straight away."""

    def __init__(self, store, goto, on_load, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.goto = goto
        self.on_load = on_load

        bar = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(84), spacing=dp(6),
                        padding=(dp(18), dp(10), dp(18), dp(4)))
        hint = Label(text="Tap a person to load them and generate their chart.", font_size="12.5sp",
                     color=theme.MUTED, halign="left", valign="middle", size_hint_y=None, height=dp(20))
        hint.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        bar.add_widget(hint)
        row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))
        cap = Label(text="Load into", font_size="12.5sp", color=theme.INK_SOFT, size_hint=(None, 1),
                    width=dp(70), halign="left", valign="middle")
        cap.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        self.slot_spinner = ThemedSpinner(text=PROFILE_LABELS["self"], values=[PROFILE_LABELS[p] for p in PROFILE_IDS])
        row.add_widget(cap)
        row.add_widget(self.slot_spinner)
        bar.add_widget(row)
        self.add_widget(bar)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.body = BoxLayout(orientation="vertical", size_hint_y=None, padding=(dp(18), dp(8), dp(18), dp(20)),
                              spacing=dp(10))
        self.body.bind(minimum_height=self.body.setter("height"))
        scroll.add_widget(self.body)
        self.add_widget(scroll)

    def _slot_id(self):
        for pid in PROFILE_IDS:
            if PROFILE_LABELS[pid] == self.slot_spinner.text:
                return pid
        return self.store.current_profile_id

    def refresh(self):
        self.slot_spinner.text = PROFILE_LABELS[self.store.current_profile_id]
        self.body.clear_widgets()
        people = self.store.saved.all()
        if not people:
            empty = Label(text="No saved birth details yet.\n\nGenerate a chart on the New Chart screen and its "
                               "details are saved here automatically, ready to load in one tap.",
                          font_size="13sp", color=theme.MUTED, halign="left", valign="top", size_hint_y=None,
                          height=dp(120))
            empty.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
            self.body.add_widget(empty)
            return
        for item in people:
            inp = item["inputs"]
            name = (inp.get("name") or "").strip() or "Unnamed"
            row = _SavedRow(name[:1].upper(), name, describe_birth(inp),
                            on_delete=lambda i=item["id"], n=name: self._confirm_delete(i, n))
            row.bind(on_release=lambda inst, i=item["id"]: self.on_load(i, self._slot_id()))
            self.body.add_widget(row)

    def _confirm_delete(self, saved_id, name):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        msg = Label(text=f"Remove {name} from your saved birth details?", halign="center", valign="middle")
        msg.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        content.add_widget(msg)
        buttons = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(46))
        popup = Popup(title="Delete saved details", content=content, size_hint=(0.86, None), height=dp(220))
        cancel = ThemedButton(text="Cancel", variant="secondary")
        cancel.bind(on_release=popup.dismiss)
        confirm = ThemedButton(text="Delete", variant="primary")

        def _do(*_):
            self.store.saved.delete(saved_id)
            popup.dismiss()
            self.refresh()

        confirm.bind(on_release=_do)
        buttons.add_widget(cancel)
        buttons.add_widget(confirm)
        content.add_widget(buttons)
        popup.open()
