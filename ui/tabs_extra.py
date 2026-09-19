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
from kivy.uix.label import Label

from ui import theme
from ui.app_state import PROFILE_LABELS
from ui.tabs_reports import _BaseReportTab
from ui.theme import ThemedButton, ThemedTextInput
from ui.widgets import CaptionLabel, LongText


class MedicalTab(_BaseReportTab):
    caption = (
        "Traditional Vedic 'medical astrology': which body areas your own planets classically emphasize, "
        "your Ayurvedic constitution, and age windows traditionally worth being mindful during. "
        "Symbolic only - NOT a diagnosis and never a substitute for a doctor."
    )

    def _build_text(self, reading):
        m = reading.get("medical_astrology")
        if not m:
            return "Medical astrology data is not available for this chart."
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        lines = [f"=== Medical Astrology - {name} ===\n", m["caveat"] + "\n"]
        if m.get("dosha"):
            d = m["dosha"]
            lines.append(f"\n--- Ayurvedic constitution (Prakriti) ---\nPrimarily {d['primary']} - {d['primary_description']}.")
            if d.get("secondary") and d["secondary"] != d["primary"]:
                lines.append(f"Your Moon adds a {d['secondary']} flavor - {d['secondary_description']}.")
            if d.get("balance_tip"):
                lines.append(d["balance_tip"])
        lines.append("\n\n--- The full reading ---\n" + m["text"])
        return "\n".join(lines)


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
    """Pick a date (YYYY-MM-DD, default today) and get, in one place, that
    date's Dasha/Muntha year note and a transit (Gochara) forecast computed
    for that exact date - the same combination the web app's Predictions tab
    shows, computed here from the on-device engine."""

    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.add_widget(CaptionLabel(
            "Pick any date - past, present or future - and get that date's full picture: which Dasha/Muntha "
            "year it falls in, plus that date's own weekly/monthly transit outlook. General tendencies for the "
            "period, not fixed events."
        ))
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8),
                        padding=(dp(10), dp(2)))
        self.date_input = ThemedTextInput(multiline=False, text=datetime.date.today().isoformat(),
                                          hint_text="YYYY-MM-DD", size_hint_y=None, height=dp(46))
        go = ThemedButton(text="Get prediction", variant="primary", size_hint=(None, None), size=(dp(150), dp(46)))
        go.bind(on_release=lambda *_: self.refresh())
        row.add_widget(self.date_input)
        row.add_widget(go)
        self.add_widget(row)
        self.text_view = LongText()
        self.add_widget(self.text_view)

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

        raw = (self.date_input.text or "").strip()
        try:
            target = datetime.datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return "Enter the date as YYYY-MM-DD, for example 2027-03-15."
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
        else:
            lines.append("This date falls outside the computed 0-100 year Dasha timeline for this chart.")
        lines.append(f"\n\n--- Transit outlook as of {target.date().isoformat()} (birth Moon in {forecast['moon_sign']}) ---\n")
        lines.append(forecast["monthly_text"])
        lines.append("\n" + forecast["weekly_text"])
        lines.append("\n\n" + forecast["caveat"])
        lines.append("\n" + reading["year_by_year"]["caveat"])
        return "\n".join(lines)
