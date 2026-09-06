"""
tabs_reports.py — the three long-form text tabs: Karmic & Past Life, Life
Predictions, and Full Reading. The text-assembly logic here is a direct
port of gui_app.py's _populate_karmic_tab / _populate_life_predictions_tab
/ _populate_reading_tab (pure string building, nothing tkinter-specific
about it) onto the LongText widget instead of a tk.Text.
"""
from kivy.uix.boxlayout import BoxLayout

from ui.widgets import LongText
from ui.app_state import PROFILE_LABELS


class _BaseReportTab(BoxLayout):
    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.text_view = LongText()
        self.add_widget(self.text_view)

    def refresh(self):
        raise NotImplementedError


class KarmicTab(_BaseReportTab):
    def refresh(self):
        reading = self.store.current["reading"]
        if reading is None:
            self.text_view.set_text("No chart generated yet for this profile.")
            return
        k = reading["karmic_and_past_life"]
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        lines = [f"=== Karmic & Past Life Perspective - {name} ===\n", k["caveat"] + "\n"]

        ak, dk, pk = k["atmakaraka"], k["darakaraka"], k["putrakaraka"]
        lines.append(
            "\n--- Chara Karakas (Jaimini significators) ---\n"
            f"Atmakaraka (soul): {ak['planet']} in {ak['sign']}, house {ak['house']} ({ak['nakshatra']})\n"
            f"Darakaraka (spouse): {dk['planet']} in {dk['sign']}, house {dk['house']} ({dk['nakshatra']})\n"
            f"Putrakaraka (children): {pk['planet']} in {pk['sign']}, house {pk['house']} ({pk['nakshatra']})"
        )
        lines.append("\n\n--- The Soul's Narrative ---\n")
        lines.append(k["soul_narrative"])

        for key, title in (("purva_punya_house_5", "5th House - Purva Punya (past-life merit)"),
                            ("dharma_house_9", "9th House - Dharma (fortune / higher purpose)"),
                            ("moksha_house_12", "12th House - Moksha (endings / past attachments)")):
            h = k[key]
            lines.append(f"\n\n--- {title} (reference) ---")
            lines.append(f"Lord: {h['lord']} in {h['lord_sign']}, placed in house {h['placed_in_house']}")
            if h.get("effects") or h.get("summary"):
                lines.append(h.get("effects") or h.get("summary"))

        self.text_view.set_text("\n".join(lines))


class LifePredictionsTab(_BaseReportTab):
    def refresh(self):
        reading = self.store.current["reading"]
        if reading is None:
            self.text_view.set_text("No chart generated yet for this profile.")
            return
        lp = reading["life_predictions"]
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        lines = [f"=== Life Predictions - {name} ===\n", lp["caveat"] + "\n"]
        for key, entry in lp.items():
            if key == "caveat" or not isinstance(entry, dict):
                continue
            lines.append(f"\n--- {entry['title']} ---")
            lines.append(entry["text"] or "(not enough KB data to synthesize this area for this chart)")
        self.text_view.set_text("\n".join(lines))


class FullReadingTab(_BaseReportTab):
    def refresh(self):
        reading = self.store.current["reading"]
        if reading is None:
            self.text_view.set_text("No chart generated yet for this profile.")
            return
        r = reading
        profile_label = PROFILE_LABELS[self.store.current_profile_id]
        lines = [f"=== {r['name'] or 'Birth Chart'} ({profile_label}) ===\n"]
        lines.append(f"Ascendant: {r['ascendant']['sign']} ({r['ascendant']['degree_in_sign']:.2f} degrees)\n")

        lines.append("\n--- Planets ---")
        for planet, detail in r["planets"].items():
            lines.append(f"\n{planet}: {detail['sign']}, house {detail['house']} "
                         f"({detail['nakshatra']} pada {detail['nakshatra_pada']})")
            if detail["in_sign"]:
                lines.append(f"   {detail['in_sign'].get('effects') or detail['in_sign']['summary']}")
            if detail["in_house"]:
                lines.append(f"   {detail['in_house'].get('effects') or detail['in_house']['summary']}")

        lines.append("\n\n--- Yogas present ---")
        present = [y for y in r["yogas"] if y["present"]]
        if present:
            for y in present:
                lines.append(f"\n{y['id']} {y['name']}: {y['details']}")
        else:
            lines.append("\n(none of the 24 checked yogas are formed in this chart)")

        running = r["dasha"]["running_at_birth"]
        lines.append(f"\n\n--- Dasha running at birth: {running['mahadasha_lord']} Mahadasha / "
                     f"{running['antardasha_lord']} Antardasha ---")
        if running["mahadasha_reading"]:
            lines.append(f"\n{running['mahadasha_reading']['general_effects']}")
        if running["antardasha_reading"]:
            lines.append(f"\n{running['antardasha_reading']['summary']}")

        lines.append("\n\n--- Life Predictions ---")
        lp = r["life_predictions"]
        for key, entry in lp.items():
            if key == "caveat" or not isinstance(entry, dict):
                continue
            lines.append(f"\n{entry['title']}: {entry['text']}")

        lines.append("\n\n--- Karmic & Past Life: The Soul's Narrative ---")
        lines.append(r["karmic_and_past_life"]["soul_narrative"] or "(see the Karmic & Past Life tab)")

        self.text_view.set_text("\n".join(lines))
