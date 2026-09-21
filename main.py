"""
main.py — Vedic Astrology (Android/Kivy port), Classical design.

A thin Kivy presentation layer over the SAME chart_engine logic used by the
Windows desktop app and the web app (see engine/, a bundled copy of
chart_engine/*.py + kb/ + data/): chart math, knowledge-base lookups, Chara
Karakas, Karmic & Past Life, Life Predictions, Medical Astrology, year-by-
year predictions and Family Compatibility are the engine's own output.
(This app has no lifespan/longevity or children predictions, and no sample
charts - see README_ANDROID.md.)

Navigation follows the Birth Chart App design handoff: a Home menu of cards,
a header whose gold diamond mark always returns Home, and a 4-tab bottom bar
(Chart / Dasha / Yogas / Library). Screens are built lazily on first visit,
so start-up only constructs Home.

Created by Sammya Das.
"""
import os
import sys

# The bundled chart_engine copy lives in engine/ next to this file and uses
# plain top-level imports internally, so engine/ must be on sys.path before
# anything imports from it.
_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

# Must run BEFORE `from kivy.core.window import Window` - Config values are
# read once, at Window creation. 'system' hands text focus straight to
# Android's own IME instead of a second Kivy-drawn keyboard. scroll_timeout
# is raised from Android's default 55ms so a slightly slow or slightly
# jittery finger tap inside a ScrollView (every form here) is still passed
# to the widget under it rather than being taken for the start of a scroll.
from kivy.config import Config
Config.set("kivy", "keyboard_mode", "system")
Config.set("widgets", "scroll_timeout", "250")

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout

# 'below_target' scrolls the focused field above the keyboard instead of
# resizing the whole Window on every keyboard show/hide.
Window.softinput_mode = "below_target"

from ui import keyboard, theme
from ui.app_state import ProfileStore
from ui.tabs_chart import ChartTab
from ui.tabs_entry import EntryScreen
from ui.tabs_extra import MedicalTab, PredictionsTab, RelationshipTab
from ui.tabs_family import FamilyTab
from ui.tabs_help import HelpTab
from ui.tabs_home import HomeScreen, LibraryScreen
from ui.tabs_insights import (
    DoshaTab, KPTab, MoreDashaTab, NatureTab, PlanetRelationsTab, PrastaraTab, ShodashvargaTab, StrengthTab, VarshaphalTab,
)
from ui.tabs_reports import FullReadingTab, KarmicTab, LifePredictionsTab
from ui.tabs_tables import (
    AshtakvargaTab, ChalitTab, DashaTab, HousesTab, KundliDetailsTab, PlanetsTab, YogasTab,
)

BOTTOM_NAV = [("entry", "Chart", "diamond"), ("dasha", "Dasha", "clock"),
              ("yogas", "Yogas", "rings"), ("library", "Library", "book")]


class VedicAstrologyApp(App):
    def build(self):
        self.title = "Vedic Astrology"
        # VEDIC_DATA_DIR lets the desktop tests keep their files out of the real app folder.
        self.store = ProfileStore(os.environ.get("VEDIC_DATA_DIR") or self.user_data_dir)
        # Built-in keyboard unless the user switched to the phone keyboard. Must be set
        # before any screen is built: text fields read it when they are created.
        keyboard.SERVICE.builtin = self.store.settings.get("keyboard", "builtin") != "phone"
        Window.clearcolor = theme.BG
        root = self._root = FloatLayout()
        self._build_ui(root)
        Window.bind(on_keyboard=self._on_keyboard)
        self.goto("home")
        return root

    def _build_ui(self, root):
        """(Re)build everything under `root`. Called at start-up and whenever the language changes."""
        self._screens = {}
        self.current_key = None

        # key -> (English header title, factory); titles are translated when shown
        self._registry = {
            "home": ("Home", lambda: HomeScreen(self.store, self.goto)),
            "entry": ("New Chart", lambda: EntryScreen(self.store, self._on_chart_generated, self.goto)),
            "library": ("Saved Charts", lambda: LibraryScreen(self.store, self.goto, self._load_saved)),
            "chart": ("Chart Diagram", lambda: ChartTab(self.store)),
            "kundli": ("Kundli Details", lambda: KundliDetailsTab(self.store)),
            "planets": ("Planets", lambda: PlanetsTab(self.store)),
            "planet_house": ("Planet in House", lambda: PlanetsTab(self.store, focus="house")),
            "planet_sign": ("Planet in Sign", lambda: PlanetsTab(self.store, focus="sign")),
            "houses": ("Houses", lambda: HousesTab(self.store)),
            "yogas": ("Classical Yogas", lambda: YogasTab(self.store)),
            "dasha": ("Mahadasha & Antardasha", lambda: DashaTab(self.store)),
            "ashtakvarga": ("Ashtakvarga", lambda: AshtakvargaTab(self.store)),
            "chalit": ("Chalit", lambda: ChalitTab(self.store)),
            "karmic": ("Karmic & Past Life", lambda: KarmicTab(self.store)),
            "life": ("Life Predictions", lambda: LifePredictionsTab(self.store)),
            "predictions": ("Predictions", lambda: PredictionsTab(self.store)),
            "medical": ("Medical Astrology", lambda: MedicalTab(self.store)),
            "relationship": ("Relationship Themes", lambda: RelationshipTab(self.store)),
            "nature": ("Your Nature", lambda: NatureTab(self.store)),
            "varshaphal": ("Varshaphal - Your Year", lambda: VarshaphalTab(self.store)),
            "kp": ("KP System", lambda: KPTab(self.store)),
            "strength": ("Planet Strength", lambda: StrengthTab(self.store)),
            "prastara": ("Ashtakvarga Detail", lambda: PrastaraTab(self.store)),
            "moredashas": ("Yogini, Char & Karakamsa", lambda: MoreDashaTab(self.store)),
            "doshas": ("Doshas & Sade Sati", lambda: DoshaTab(self.store)),
            "relations": ("Planet by Planet", lambda: PlanetRelationsTab(self.store)),
            "shodashvarga": ("Shodashvarga Table", lambda: ShodashvargaTab(self.store)),
            "full": ("Full Reading", lambda: FullReadingTab(self.store)),
            "family": ("Family Compatibility", lambda: FamilyTab(self.store)),
            "help": ("Help & About", lambda: HelpTab()),
        }

        root.add_widget(theme.GradientBackground(size_hint=(1, 1)))
        shell = self._shell = BoxLayout(orientation="vertical", size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.header = theme.AppHeader(on_home=lambda: self.goto("home"))
        self.content = BoxLayout(orientation="vertical")
        self.bottom = theme.BottomNav(BOTTOM_NAV, on_select=lambda k: self.goto(k))
        shell.add_widget(self.header)
        shell.add_widget(self.content)
        # The built-in keyboard is docked between the content and the bottom bar; while it is
        # up, the bottom bar steps aside so the form keeps as much room as possible.
        shell.add_widget(keyboard.SERVICE.make_panel())
        shell.add_widget(self.bottom)
        keyboard.SERVICE.on_visibility = self._on_keyboard_visibility
        root.add_widget(shell)


    # ------------------------------------------------------------------ navigation
    def goto(self, key, preset=None):
        if key not in self._registry:
            key = "home"
        keyboard.SERVICE.hide()
        # leaving the New Chart screen: keep whatever was typed
        leaving = self._screens.get(self.current_key)
        if leaving is not None and hasattr(leaving, "save_now"):
            leaving.save_now()

        title, factory = self._registry[key]
        screen = self._screens.get(key)
        if screen is None:
            screen = factory()
            self._screens[key] = screen
        self.content.clear_widgets()
        self.content.add_widget(screen)
        self.current_key = key
        self.header.set_title(title)
        self.bottom.set_active(key)
        if preset and hasattr(screen, "preset_varga"):
            screen.preset_varga(preset)
        if hasattr(screen, "refresh"):
            screen.refresh()

    def _load_saved(self, saved_id, slot_id):
        """A saved person was tapped in Saved Charts: put their details into
        the chosen profile slot, show New Chart, and generate the chart."""
        record = self.store.saved.get(saved_id)
        if record is None:
            return
        self.store.load_saved_into(slot_id, record)
        self.goto("entry")
        self._screens["entry"].generate_now()

    def _on_chart_generated(self, profile_switch_only):
        """Screens re-read the store in refresh() every time they are shown,
        so there is nothing to push here - kept as the callback the entry
        screen expects."""

    def _on_keyboard_visibility(self, visible):
        # Take the bottom bar OUT of the layout while the keyboard is up (rather than
        # shrinking it to zero height): its fixed-size icons and labels would still
        # overhang the bottom of the screen and swallow touches meant for the
        # keyboard's bottom row (space, Done, 0).
        if visible and self.bottom.parent is self._shell:
            self._shell.remove_widget(self.bottom)
        elif not visible and self.bottom.parent is None:
            self._shell.add_widget(self.bottom, index=0)

    def _on_keyboard(self, window, key, *args):
        # Android back button: close the built-in keyboard first, then step back to
        # Home, then let the OS exit.
        if key == 27 and keyboard.SERVICE.visible:
            keyboard.SERVICE.hide()
            return True
        if key == 27 and self.current_key != "home":
            self.goto("home")
            return True
        return False


if __name__ == "__main__":
    VedicAstrologyApp().run()
