"""
tabs_extra.py — screens for the newer readings: Predictions (any date: the
Dasha/Muntha year context AND a transit forecast computed for that exact
date), Medical Astrology, and Relationship Themes. Each is built from the
reading the shared chart engine already produced - no new astrology here,
just presentation on the same LongText widget the other report tabs use.
"""
import datetime
import traceback

from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from ui import theme
from ui.app_state import PROFILE_LABELS
from ui.tabs_reports import _BaseReportTab
from ui.tabs_chart import BodyMapCanvas
from ui.tabs_entry import MONTHS
from ui.theme import SegmentedControl, ThemedButton, ThemedSpinner, ThemedTextInput
from ui.widgets import CaptionLabel, FlowText, LongText


def _weather(text, span):
    """One friendly sentence summarising a transit outlook: mostly easy or effortful?"""
    easy = text.count("favourable")
    hard = text.count("mixed") + text.count("effortful") + text.count("challenging")
    if easy > hard:
        mood = "mostly friendly for you"
    elif hard > easy:
        mood = "a bit more effortful than usual"
    else:
        mood = "a balanced mix of easy and harder influences"
    return (f"for this {span} the planets in the sky are {mood}. It is like a weather forecast for your life at "
            "that time - some easier days, some harder ones, nothing fixed.")


class MedicalTab(BoxLayout):
    """Medical Astrology: the body-map chart (the birth chart with each house
    labelled by the body area it stands for, shaded where a planet classically
    asking for extra care sits), a plain-words guide to reading it, then the
    full reading - every paragraph followed by an "[In simple terms: ...]"
    explanation. One ScrollView holds all of it so the chart scrolls with the text."""

    caption = (
        "Traditional Vedic 'medical astrology': which body areas your own planets classically emphasize, "
        "your Ayurvedic constitution, and age windows traditionally worth being mindful during. "
        "Symbolic only - NOT a diagnosis and never a substitute for a doctor."
    )

    LEGEND = (
        "How to read the body map: each triangle or diamond is one of your 12 houses, and each house stands "
        "for a part of the body, from the head (house 1) down to the feet (house 12). Planets sitting in a "
        "house classically colour that body area. Shaded houses hold a planet that classical texts link with "
        "strain or caution (Sun, Mars, Saturn, Rahu, Ketu); the others are empty or have a supportive planet. "
        "[In simple terms: picture your body laid over the chart like a map. The shaded spots are just the "
        "areas astrology says deserve a little extra care - it is a symbolic map, not a scan, and nothing "
        "on it means something is wrong.]"
    )

    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.content = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        self.add_widget(scroll)
        self._scroll = scroll
        self._chart = None

    def refresh(self):
        reading = self.store.current["reading"]
        chart = self.store.current["chart"]
        self.content.clear_widgets()
        self._chart = None
        self.content.add_widget(CaptionLabel(self.caption))
        m = reading.get("medical_astrology") if reading else None
        if not m or chart is None:
            note = FlowText()
            note.set_text("No chart generated yet for this profile." if not m else
                          "Medical astrology data is not available for this chart.")
            self.content.add_widget(note)
            return
        try:
            self._build(reading, chart, m)
        except Exception:  # noqa: BLE001 - show the error on screen rather than a blank tab
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:MedicalTab: failed:\n{tb}")
            err = FlowText()
            err.set_text("This tab hit an error while building - details below so it can be reported:\n\n" + tb)
            self.content.add_widget(err)
        self._scroll.scroll_y = 1

    def _build(self, reading, chart, m):
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        title = FlowText()
        title.set_text(f"=== Medical Astrology - {name} ===")
        self.content.add_widget(title)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), padding=(dp(10), dp(3)))
        seg = SegmentedControl(["North Indian", "South Indian"], selected=self.store.chart_style,
                               on_select=self._on_style)
        row.add_widget(seg)
        row.add_widget(BoxLayout())
        self.content.add_widget(row)

        chart_widget = BodyMapCanvas(size_hint_y=None, height=dp(340))
        chart_widget.body_short = {a["house"]: a["short"] for a in m["body_areas"]}
        chart_widget.set_chart(chart, "D1", self.store.chart_style)
        self.content.add_widget(chart_widget)
        self.content.bind(width=lambda inst, w: setattr(chart_widget, "height", min(max(w, dp(300)), dp(440))))
        chart_widget.height = min(max(self.content.width, dp(300)), dp(440))
        self._chart = chart_widget

        legend = FlowText()
        legend.set_text(self.LEGEND)
        self.content.add_widget(legend)

        body = FlowText()
        body.set_text(m["caveat"] + "\n\n" + m["text"])
        self.content.add_widget(body)

    def _on_style(self, choice):
        self.store.chart_style = choice
        if self._chart is not None:
            self._chart.set_chart(self.store.current["chart"], "D1", choice)


class RelationshipTab(_BaseReportTab):
    caption = (
        "Classical indicators of relationship TENDENCIES in your OWN chart - never predictions of behaviour and "
        "never evidence about a partner. Includes a marriage/relationship-count tendency (a band, not a number) "
        "and a karmic read on why relationships take the shape they do."
    )

    def _build_text(self, reading):
        rel = reading.get("relationship_themes")
        if not rel:
            return "Relationship themes are not available for this chart."
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        lines = [f"=== Relationship Themes - {name} ===\n", rel["caveat"] + "\n"]
        if rel.get("plain_summary"):
            lines.append("\n" + rel["plain_summary"])
        mct = rel.get("marriage_count_tendency")
        if mct:
            lines.append("\n\n--- How many marriages/relationships? (a tendency, not a count) ---")
            lines.append(mct["caveat"])
            lines.append(f"This chart leans toward: {mct['tendency']}.")
            for i in mct.get("indicators", []):
                lines.append(f"- {i}")
        if rel.get("deep_discussion"):
            lines.append("\n\n--- Full discussion ---\n" + rel["deep_discussion"])
        return "\n".join(lines)


class PredictionsTab(BoxLayout):
    """Pick a date (day / month pickers plus a year box, default today) and get, in one place, that
    date's Dasha/Muntha year note and a transit (Gochara) forecast computed
    for that exact date - the same combination the web app's Predictions tab
    shows, computed here from the on-device engine."""

    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.add_widget(CaptionLabel(
            "Pick any date - past, present or future - and get that date's full picture: which Dasha/Muntha "
            "year it falls in, plus that date's own weekly/monthly transit outlook. General tendencies for the "
            "period, not fixed events. [In simple terms: choose a day, month and year and tap Get prediction; "
            "you get the general mood of that period, like a weather forecast for your life - not a promise.]"
        ))
        today = datetime.date.today()
        # Pickers instead of typing "YYYY-MM-DD": nothing to type but a 4-digit year, which
        # gets the number pad on the built-in keyboard.
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8),
                        padding=(dp(10), dp(2)))
        self.day_spinner = ThemedSpinner(text=str(today.day), values=[str(i) for i in range(1, 32)], size_hint_x=1)
        self.month_spinner = ThemedSpinner(text=MONTHS[today.month - 1], values=MONTHS, size_hint_x=1.7)
        self.year_input = ThemedTextInput(multiline=False, input_filter="int", text=str(today.year), hint_text="Year",
                                          kb_layout="number", size_hint_x=1.2, size_hint_y=None, height=dp(46))
        for w in (self.day_spinner, self.month_spinner, self.year_input):
            row.add_widget(w)
        self.add_widget(row)
        buttons = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8),
                            padding=(dp(10), dp(2)))
        now_btn = ThemedButton(text="Today", variant="ghost", size_hint=(None, None), size=(dp(90), dp(46)))
        now_btn.bind(on_release=lambda *_: self._set_today())
        go = ThemedButton(text="Get prediction", variant="primary", size_hint=(1, None), height=dp(46))
        go.bind(on_release=lambda *_: self.refresh())
        buttons.add_widget(now_btn)
        buttons.add_widget(go)
        self.add_widget(buttons)
        # picking a day/month, or finishing the year (keyboard closed), updates the prediction
        self.day_spinner.bind(text=lambda *_: self.refresh())
        self.month_spinner.bind(text=lambda *_: self.refresh())
        self.year_input.bind(focus=lambda inst, focused: None if focused else self.refresh())
        self.text_view = LongText()
        self.add_widget(self.text_view)

    def _set_today(self):
        today = datetime.date.today()
        self.day_spinner.text, self.month_spinner.text = str(today.day), MONTHS[today.month - 1]
        self.year_input.text = str(today.year)
        self.refresh()

    def refresh(self):
        data = self.store.current
        if data["reading"] is None or data["chart"] is None:
            self.text_view.set_text("No chart generated yet for this profile.")
            return
        try:
            self.text_view.set_text(self._build(data["chart"], data["reading"]))
        except Exception:  # noqa: BLE001 - show the error on screen rather than a blank tab
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:PredictionsTab: failed:\n{tb}")
            self.text_view.set_text("Could not build this prediction:\n\n" + tb)

    def _build(self, chart, reading):
        import life_timeline
        from transits import compute_transit_forecast

        try:
            year = int((self.year_input.text or "").strip())
            target = datetime.datetime(year, MONTHS.index(self.month_spinner.text) + 1, int(self.day_spinner.text))
        except ValueError:
            return "That is not a real date (for example 31 June, or no year entered). Pick the day and month, and type a 4-digit year."
        if not 1900 <= target.year <= 2100:
            return "Pick a year between 1900 and 2100."
        at_dt = target.replace(hour=12, minute=0, second=0, microsecond=0)

        age = life_timeline.age_for_date(chart, at_dt)
        years = {y["age"]: y for y in reading["year_by_year"]["years"]}
        entry = years.get(age)
        forecast = compute_transit_forecast(chart, at_dt)

        lines = [f"=== {target.date().isoformat()} - age {age} ===\n"]
        if entry:
            lines.append("--- Dasha & Muntha for this year ---")
            periods = f"{entry['mahadasha_lord']} Mahadasha / {entry['antardasha_lord']} Antardasha"
            if entry.get("pratyantardasha_lord"):
                periods += f" / {entry['pratyantardasha_lord']} Pratyantardasha"
            lines.append(f"{periods} - Muntha in {entry['muntha_sign']} - {entry.get('leaning', '')}\n")
            lines.append(entry["note"])
            spot = (f"the spotlight is on {entry['muntha_theme']}" if entry.get("muntha_theme")
                    else "no single area dominates")
            overall = f" Overall it is {entry['leaning']}." if entry.get("leaning") else ""
            lines.append(f"\n[In simple terms: at this age you are in a {entry['mahadasha_lord']} chapter of life, "
                         f"and {spot}.{overall} Think of it as the season you are in, not a fixed event.]")
        else:
            lines.append("This date falls outside the computed 0-100 year Dasha timeline for this chart.")
        lines.append(f"\n\n--- Transit outlook as of {target.date().isoformat()} (birth Moon in {forecast['moon_sign']}) ---\n")
        lines.append(forecast["monthly_text"])
        lines.append(f"\n[In simple terms: {_weather(forecast['monthly_text'], 'month')}]")
        lines.append("\n" + forecast["weekly_text"])
        lines.append(f"\n[In simple terms: {_weather(forecast['weekly_text'], 'week')}]")
        lines.append("\n\n" + forecast["caveat"])
        lines.append("\n" + reading["year_by_year"]["caveat"])
        return "\n".join(lines)
