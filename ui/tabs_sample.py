"""
tabs_sample.py — Sample Charts tab: browse real, sourced-birth-time public
figures and load one straight into the currently selected profile slot.
Port of gui_app.py's Sample Charts tab / the web app's Sample Charts tab
onto Kivy widgets - see engine/sample_charts.py and sample_profiles.json
for how strict the birth-time sourcing bar was (20 of the originally-
confirmed 45 names were left out for lacking a genuinely documented one).

Every widget below is constructed fresh with its final text already set,
the same "never mutate .text on an already-rendered widget" pattern
widgets.py's SimpleTable and LongText both use - see LongText's own
_make_label docstring for why that specifically matters on this project.
"""
import traceback

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.logger import Logger

from ui.widgets import CaptionLabel
from ui.app_state import PROFILE_LABELS


def _show_message(title, text):
    from kivy.uix.popup import Popup
    content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
    msg_label = Label(text=text, valign="top")
    msg_label.bind(size=lambda inst, size: setattr(msg_label, "text_size", size))
    content.add_widget(msg_label)
    popup = Popup(title=title, content=content, size_hint=(0.85, 0.5))
    close_btn = Button(text="OK", size_hint_y=None, height=dp(44))
    close_btn.bind(on_release=popup.dismiss)
    content.add_widget(close_btn)
    popup.open()


class SampleChartsTab(BoxLayout):
    def __init__(self, store, on_chart_generated, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.on_chart_generated = on_chart_generated

        self.add_widget(CaptionLabel(
            "Real, publicly documented birth data for well-known figures - tap one to load "
            "and generate its chart into the CURRENTLY SELECTED profile (see the Profile & "
            "Birth Data tab). Every name here has a genuinely sourced birth time; many "
            "originally-considered names were left out for lacking one."
        ))

        self.status_area = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(28))
        self.add_widget(self.status_area)
        self._set_status("Tap a profile below to load and generate it.")

        scroller = ScrollView()
        self.list_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=(0, dp(6)))
        self.list_grid.bind(minimum_height=self.list_grid.setter("height"))
        scroller.add_widget(self.list_grid)
        self.add_widget(scroller)

        self._build_list()

    def _set_status(self, text):
        # Rebuilds the status Label from scratch rather than mutating one
        # in place - see widgets.py LongText._make_label's docstring for
        # why this project specifically avoids that pattern now.
        self.status_area.clear_widgets()
        label = Label(text=text, size_hint_y=None, halign="left", valign="middle",
                      text_size=(None, None))
        label.bind(texture_size=lambda inst, ts: setattr(label, "height", max(dp(28), ts[1] + dp(6))))
        label.bind(width=lambda inst, w: setattr(label, "text_size", (w, None)))
        self.status_area.add_widget(label)
        self.status_area.height = label.height

    def _build_list(self):
        try:
            import sample_charts
            profiles = sample_charts.list_profiles()
        except Exception:
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:SampleChartsTab: list_profiles failed:\n{tb}")
            self.list_grid.add_widget(Label(
                text="Could not load the sample profile list:\n\n" + tb,
                size_hint_y=None, height=dp(400), halign="left", valign="top",
                text_size=(dp(600), None),
            ))
            return

        by_category = {}
        for p in profiles:
            by_category.setdefault(p["category"], []).append(p)

        for category in sorted(by_category):
            header = Label(
                text=category, size_hint_y=None, height=dp(32), bold=True,
                halign="left", valign="middle", color=(1, 0.85, 0.3, 1),
            )
            header.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
            self.list_grid.add_widget(header)

            for profile in by_category[category]:
                bd = profile["birth_date"]
                btn_text = (
                    f"{profile['name']}  [{profile['time_confidence']}]\n"
                    f"{profile['notable_for']}\n"
                    f"{bd['year']:04d}-{bd['month']:02d}-{bd['day']:02d}, {profile['birth_place']}"
                )
                btn = Button(
                    text=btn_text, size_hint_y=None, height=dp(84), halign="left", valign="top",
                    text_size=(None, None), padding=(dp(10), dp(8)),
                )
                btn.bind(width=lambda inst, w: setattr(inst, "text_size", (w - dp(20), None)))
                btn.bind(on_release=lambda inst, pid=profile["id"]: self._load_profile(pid))
                self.list_grid.add_widget(btn)

    def _load_profile(self, profile_id):
        import sample_charts
        from rule_engine import generate_reading

        profile = sample_charts.get_profile(profile_id)
        if profile is None:
            return

        self._set_status(f"Generating {profile['name']}...")
        try:
            chart = sample_charts.generate_chart_for_profile(profile_id)
            reading = generate_reading(chart)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:SampleChartsTab: generate failed for {profile_id}:\n{tb}")
            _show_message("Could not generate chart", str(exc))
            self._set_status(f"Error generating {profile['name']} - see the popup.")
            return

        profile_id_slot = self.store.current_profile_id
        bd, bt = profile["birth_date"], profile["birth_time"]
        self.store.profiles[profile_id_slot]["inputs"] = {
            "name": profile["name"], "sex": profile["sex"] or "",
            "year": str(bd["year"]), "month": str(bd["month"]), "day": str(bd["day"]),
            "hour": str(bt["hour"]), "minute": str(bt["minute"]), "second": "0",
            "place": profile["geocode_place"], "country": profile["country_hint"],
            "use_manual_coords": False, "lat": "", "lon": "", "tz": "",
        }
        self.store.profiles[profile_id_slot]["chart"] = chart
        self.store.profiles[profile_id_slot]["reading"] = reading

        self._set_status(
            f"Loaded {profile['name']} into {PROFILE_LABELS[profile_id_slot]} - "
            f"Ascendant {chart['ascendant']['sign']} {chart['ascendant']['degree_in_sign']:.2f} degrees."
        )
        self.on_chart_generated(profile_switch_only=False)
