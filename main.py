"""
main.py — Vedic Astrology (Android/Kivy port).

This app is a thin Kivy presentation layer over the SAME chart_engine
logic used by the Windows desktop app (see engine/, a bundled copy of
chart_engine/*.py + kb/ + data/, unmodified) - the chart math, knowledge-
base lookups, Chara Karakas, Karmic & Past Life narrative, Life
Predictions, and Family Compatibility report are byte-identical to the
desktop app's; only the UI toolkit changed (tkinter -> Kivy, since
tkinter does not exist on Android).

Root layout: one TabbedPanel, mirroring the desktop app's ttk.Notebook -
Profile & Birth Data, Chart, Kundli Details, Planets, Houses, Yogas,
Dasha, Ashtakvarga, Chalit, Karmic & Past Life, Life Predictions, Full
Reading, Family Compatibility.
"""
import os
import sys

# The bundled chart_engine copy lives in engine/ next to this file, and
# uses plain top-level imports internally (import ashtakvarga, from
# astrology_tables import ..., etc.) exactly like it does inside the
# desktop app's own folder - so engine/ just needs to be on sys.path
# before anything imports from it. Doing this before importing kivy
# keeps import order simple and matches how chart_engine's own tests run.
_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

from ui import theme
from ui.app_state import ProfileStore
from ui.tabs_profile import ProfileTab
from ui.tabs_chart import ChartTab
from ui.tabs_tables import (
    KundliDetailsTab, PlanetsTab, HousesTab, YogasTab, DashaTab, AshtakvargaTab, ChalitTab,
)
from ui.tabs_reports import KarmicTab, LifePredictionsTab, FullReadingTab
from ui.tabs_family import FamilyTab
from ui.tabs_help import HelpTab


class VedicAstrologyApp(App):
    def build(self):
        self.title = "Vedic Astrology"
        self.store = ProfileStore()
        Window.clearcolor = theme.BG

        # A GradientBackground behind everything, so any sliver visible
        # around/behind the TabbedPanel reads as the same deep-indigo
        # "celestial" look the desktop/web apps use, not flat black.
        root = FloatLayout()
        root.add_widget(theme.GradientBackground(size_hint=(1, 1)))

        tabs = TabbedPanel(do_default_tab=False, tab_pos="top_mid", tab_height="40dp",
                            size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
                            background_color=(0.24, 0.27, 0.5, 1))

        self.profile_tab = ProfileTab(self.store, on_chart_generated=self._on_chart_generated)
        self.chart_tab = ChartTab(self.store)
        self.kundli_tab = KundliDetailsTab(self.store)
        self.planets_tab = PlanetsTab(self.store)
        self.houses_tab = HousesTab(self.store)
        self.yogas_tab = YogasTab(self.store)
        self.dasha_tab = DashaTab(self.store)
        self.ashtakvarga_tab = AshtakvargaTab(self.store)
        self.chalit_tab = ChalitTab(self.store)
        self.karmic_tab = KarmicTab(self.store)
        self.life_predictions_tab = LifePredictionsTab(self.store)
        self.full_reading_tab = FullReadingTab(self.store)
        self.family_tab = FamilyTab(self.store)
        self.help_tab = HelpTab()

        self._refreshable_tabs = [
            self.chart_tab, self.kundli_tab, self.planets_tab, self.houses_tab,
            self.yogas_tab, self.dasha_tab, self.ashtakvarga_tab, self.chalit_tab,
            self.karmic_tab, self.life_predictions_tab, self.full_reading_tab,
        ]

        # Icon-prefixed tab titles - zero image assets, but an immediate,
        # low-risk step toward a more "graphical" tab strip than plain text.
        for title, content in [
            ("\U0001FA90  Profile & Birth Data", self.profile_tab),
            ("\U0001F30C  Chart", self.chart_tab),
            ("\U0001F4CB  Kundli Details", self.kundli_tab),
            ("♇  Planets", self.planets_tab),
            ("\U0001F3E0  Houses", self.houses_tab),
            ("✨  Yogas", self.yogas_tab),
            ("⏳  Dasha", self.dasha_tab),
            ("\U0001F4CA  Ashtakvarga", self.ashtakvarga_tab),
            ("\U0001F4D0  Chalit", self.chalit_tab),
            ("\U0001F52E  Karmic & Past Life", self.karmic_tab),
            ("\U0001F52D  Life Predictions", self.life_predictions_tab),
            ("\U0001F4D6  Full Reading", self.full_reading_tab),
            ("\U0001F46A  Family Compatibility", self.family_tab),
            ("❓  Help & FAQ", self.help_tab),
        ]:
            item = TabbedPanelItem(text=title)
            item.add_widget(content)
            tabs.add_widget(item)

        root.add_widget(tabs)
        return root

    def _on_chart_generated(self, profile_switch_only):
        """Called by ProfileTab whenever the selected profile changes OR a
        chart is (re)generated - refreshes every other tab so they always
        reflect the currently selected profile, exactly like gui_app.py's
        _populate_all_tabs() did on the desktop."""
        for tab in self._refreshable_tabs:
            tab.refresh()
        # Family Compatibility is deliberately NOT auto-refreshed here (it
        # has its own "Compute" button, same as the desktop app) since it
        # can depend on THREE profiles at once (Self/Partner/Child) rather
        # than just the currently selected one.


if __name__ == "__main__":
    VedicAstrologyApp().run()
