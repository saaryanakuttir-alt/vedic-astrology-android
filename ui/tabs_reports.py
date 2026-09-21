"""
tabs_reports.py — the three long-form text tabs: Karmic & Past Life, Life
Predictions, and Full Reading. The text-assembly logic here is a direct
port of gui_app.py's _populate_karmic_tab / _populate_life_predictions_tab
/ _populate_reading_tab (pure string building, nothing tkinter-specific
about it) onto the LongText widget instead of a tk.Text.
"""
import traceback

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.logger import Logger

from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.label import Label

from ui import export, pdf_report, reading_mode, theme
from ui.reading_mode import ReadingModeBar
from ui.theme import ThemedButton, ThemedCheckBox
from ui.widgets import LongText, CaptionLabel, ItalicSummaryLabel
from ui.app_state import PROFILE_LABELS
from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)


class _BaseReportTab(BoxLayout):
    # Plain-English explainer shown above the report text - every subclass
    # below sets this.
    caption = ""

    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        if self.caption:
            self.add_widget(CaptionLabel(self.caption))
        # Compact / Detailed switch (see ui/reading_mode.py); changing it redraws this report
        self.mode_bar = ReadingModeBar(store, lambda: self.refresh())
        self.add_widget(self.mode_bar)
        self.add_extra_controls()
        self.text_view = LongText()
        self.add_widget(self.text_view)

    def add_extra_controls(self):
        """Hook for a subclass that wants more controls under the Compact/Detailed switch."""

    def _build_text(self, reading):
        """Subclasses implement this: return the report's full text for a
        non-None reading, or raise on any bad assumption about its shape.
        NOT wrapped in try/except here on purpose - refresh() below does
        that, so a mistaken KeyError/AttributeError renders as visible
        on-screen text instead of leaving the tab silently blank. This
        exists specifically because this project's report tabs have a
        history of going blank on Android with no way to tell WHY short of
        pulling adb logcat, which isn't always available - a wrong
        assumption here is now readable directly on the phone screen."""
        raise NotImplementedError

    def refresh(self):
        self.mode_bar.sync()
        reading = self.store.current["reading"]
        if reading is None:
            self.text_view.set_text("No chart generated yet for this profile.")
            return
        try:
            text = reading_mode.apply(self.store, self._build_text(reading))
        except Exception:  # noqa: BLE001 - deliberately broad, see _build_text's docstring
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:{type(self).__name__}: _build_text failed:\n{tb}")
            self.text_view.set_text(
                tx("This tab hit an error while building its text - showing the "
                "details below instead of a blank screen so it can be reported:\n\n")
                + tb
            )
            return
        self.text_view.set_text(text)


class KarmicTab(_BaseReportTab):
    caption = (
        "A symbolic, reflective look at past-life themes and this life's karmic "
        "direction - not literal history, just a traditional lens for thinking about "
        "old patterns (Ketu) versus where you're being pulled to grow (Rahu)."
    )

    def __init__(self, store, **kwargs):
        super().__init__(store, **kwargs)
        # The section's own closing "in simple words" line (rule_engine.py's
        # plain_section_summary) rendered in italics, separate from the
        # main report text - see ItalicSummaryLabel's own docstring for
        # why this needs its own widget rather than markup on LongText.
        self.summary_label = ItalicSummaryLabel()
        self.add_widget(self.summary_label)

    def _build_text(self, reading):
        k = reading["karmic_and_past_life"]
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        lines = [tr('=== Karmic & Past Life Perspective - {0} ===\n', name), k["caveat"] + "\n"]

        ak, dk, pk = k["atmakaraka"], k["darakaraka"], k["putrakaraka"]
        lines.append(
            tr('\n--- Chara Karakas (Jaimini significators) ---\nAtmakaraka (soul): {0} in {1}, house {2} '
               '({3})\nDarakaraka (spouse): {4} in {5}, house {6} ({7})\nPutrakaraka (intellect & creativity): '
               '{8} in {9}, house {10} ({11})', ak['planet'], ak['sign'], ak['house'], ak['nakshatra'], dk['planet'], dk['sign'], dk['house'], dk['nakshatra'], pk['planet'], pk['sign'], pk['house'], pk['nakshatra'])
        )
        lines.append(tx("\n\n--- The Soul's Narrative ---\n"))
        # soul_narrative ends with plain_section_summary (see
        # rule_engine.py's _build_karmic_and_past_life) - stripped here
        # since it's shown separately, in italics, via self.summary_label
        # below rather than twice.
        narrative = k["soul_narrative"]
        summary = k.get("plain_section_summary")
        if summary and narrative.endswith(summary):
            narrative = narrative[: -len(summary)].rstrip("\n")
        lines.append(narrative)

        for key, title in (("purva_punya_house_5", "5th House - Purva Punya (past-life merit)"),
                            ("dharma_house_9", "9th House - Dharma (fortune / higher purpose)"),
                            ("moksha_house_12", "12th House - Moksha (endings / past attachments)")):
            h = k[key]
            lines.append(tr('\n\n--- {0} (reference) ---', title))
            lines.append(tr('Lord: {0} in {1}, placed in house {2}', h['lord'], h['lord_sign'], h['placed_in_house']))
            if h.get("effects") or h.get("summary"):
                lines.append(h.get("effects") or h.get("summary"))

        return "\n".join(lines)

    def refresh(self):
        super().refresh()
        reading = self.store.current["reading"]
        summary = reading["karmic_and_past_life"].get("plain_section_summary") if reading else None
        self.summary_label.set_text(summary or "")


class LifePredictionsTab(_BaseReportTab):
    caption = (
        "General traditional tendencies for different areas of life (career, health, "
        "relationships...), based on your houses, planets, and current Dasha period - "
        "broad themes to consider, not guaranteed events."
    )

    def _build_text(self, reading):
        lp = reading["life_predictions"]
        name = reading.get("name") or PROFILE_LABELS[self.store.current_profile_id]
        lines = [tr('=== Life Predictions - {0} ===\n', name), lp["caveat"] + "\n"]
        chart = self.store.current["chart"]
        if chart is not None:
            import extras
            lines.append("\n" + extras.period_text(chart) + "\n\n" + extras.houses_text(chart) + "\n")
        for key, entry in lp.items():
            if key == "caveat" or not isinstance(entry, dict):
                continue
            lines.append(tr('\n--- {0} ---', entry['title']))
            # `text` already ends with the plain-language gist in
            # [brackets] (see rule_engine.py's area()) - the professional
            # classical writing stays intact and first; the gist is an
            # addition at the end, not a replacement or a lead-in
            # (explicit user feedback after an earlier pass led with it).
            text = entry["text"] or tx("(not enough KB data to synthesize this area for this chart)")
            lines.append(text)
        return "\n".join(lines)


class FullReadingTab(_BaseReportTab):
    caption = ("Everything from the other tabs combined into one complete, readable report. "
               "Use 'Save PDF report' to keep it as a file you can open, print or share.")

    def add_extra_controls(self):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52), padding=(dp(10), dp(4)))
        self.pdf_button = ThemedButton(text="Save PDF report", variant="primary")
        self.pdf_button.bind(on_release=lambda *_: self._save_pdf())
        row.add_widget(self.pdf_button)
        self.add_widget(row)

    def _save_pdf(self):
        data = self.store.current
        if data["chart"] is None or data["reading"] is None:
            self._popup("No chart yet", tx("Generate a chart for this profile first, then save its PDF report."))
            return
        self._choose_sections(data)

    def _choose_sections(self, data):
        """Ask which sections go into the report (the last choice for this mode is remembered)."""
        mode = reading_mode.current(self.store)
        avail = pdf_report.available_sections(mode)
        saved = self.store.settings.get("pdf_sections_" + mode)
        chosen = {k for k, _ in avail} if not isinstance(saved, list) else set(saved)
        self._chooser_checks = {}
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        hint = Label(text=tr('Choose what to include in your {0} report.', mode), size_hint_y=None, height=dp(28), halign="left", valign="middle")
        hint.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        content.add_widget(hint)
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        box = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        box.bind(minimum_height=box.setter("height"))
        for key, label in avail:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(42))
            check = ThemedCheckBox(active=key in chosen, size_hint_x=None, width=dp(44))
            self._chooser_checks[key] = check
            text = Label(text=label, halign="left", valign="middle", font_size="14sp")
            text.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
            row.add_widget(check)
            row.add_widget(text)
            box.add_widget(row)
        scroll.add_widget(box)
        content.add_widget(scroll)
        quick = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))
        all_btn = ThemedButton(text="Select all", variant="secondary")
        none_btn = ThemedButton(text="Clear", variant="secondary")
        all_btn.bind(on_release=lambda *_: [setattr(c, "active", True) for c in self._chooser_checks.values()])
        none_btn.bind(on_release=lambda *_: [setattr(c, "active", False) for c in self._chooser_checks.values()])
        quick.add_widget(all_btn)
        quick.add_widget(none_btn)
        content.add_widget(quick)
        buttons = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(46))
        popup = self._chooser = Popup(title="Choose report sections", content=content, size_hint=(0.94, 0.86))
        cancel = ThemedButton(text="Cancel", variant="secondary")
        cancel.bind(on_release=popup.dismiss)
        create = self._chooser_create = ThemedButton(text="Create PDF", variant="primary")

        def _create(*_):
            picked = [k for k, _l in avail if self._chooser_checks[k].active]
            if not picked:
                create.text = "Pick at least one"
                return
            self.store.settings.set("pdf_sections_" + mode, picked)
            popup.dismiss()
            self._start_pdf(data, picked)

        create.bind(on_release=_create)
        buttons.add_widget(cancel)
        buttons.add_widget(create)
        content.add_widget(buttons)
        popup.open()

    def _start_pdf(self, data, sections):
        self.pdf_button.text = "Creating PDF..."
        self.pdf_button.disabled = True
        Clock.schedule_once(lambda dt: self._finish_pdf(data, sections), 0.08)      # let the button repaint first

    def _finish_pdf(self, data, sections=None):
        try:
            pdf = pdf_report.build_pdf(data["chart"], data["reading"], style=self.store.chart_style,
                                       mode=reading_mode.current(self.store), sections=set(sections) if sections else None)
            saved = export.save_pdf(pdf, pdf_report.safe_filename(data["chart"].get("name")), self.store.data_dir)
            self._popup("PDF saved", tr('{0}\n\nOpen it from your Files / Downloads app, or tap Open.', saved.where),
                        open_fn=saved.open_fn)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            Logger.error(f"VedicAstro:FullReadingTab: PDF failed:\n{traceback.format_exc()}")
            self._popup("Could not create the PDF", str(exc))
        finally:
            self.pdf_button.text = "Save PDF report"
            self.pdf_button.disabled = False

    def _popup(self, title, message, open_fn=None):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        label = Label(text=message, halign="left", valign="top")
        label.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        content.add_widget(label)
        buttons = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(46))
        popup = Popup(title=title, content=content, size_hint=(0.9, None), height=dp(300))
        if open_fn is not None:
            def _open(*_):
                popup.dismiss()
                try:
                    open_fn()
                except Exception as exc:  # noqa: BLE001 - e.g. no PDF viewer installed
                    self._popup("Could not open it", tr('{0}\n\nThe file is saved; open it from your Files app.', exc))
            open_btn = ThemedButton(text="Open", variant="primary")
            open_btn.bind(on_release=_open)
            buttons.add_widget(open_btn)
        ok = ThemedButton(text="OK", variant="secondary")
        ok.bind(on_release=popup.dismiss)
        buttons.add_widget(ok)
        content.add_widget(buttons)
        popup.open()

    def _build_text(self, reading):
        r = reading
        profile_label = PROFILE_LABELS[self.store.current_profile_id]
        lines = [tr('=== {0} ({1}) ===\n', r['name'] or 'Birth Chart', profile_label)]
        lines.append(tr('Ascendant: {0} ({1:.2f} degrees)\n', r['ascendant']['sign'], r['ascendant']['degree_in_sign']))

        lines.append(tx("\n--- Planets ---"))
        for planet, detail in r["planets"].items():
            lines.append(tr('\n{0}: {1}, house {2} ({3} pada {4})', planet, detail['sign'], detail['house'], detail['nakshatra'], detail['nakshatra_pada']))
            if detail["in_sign"]:
                lines.append(tr('   {0}', detail['in_sign'].get('effects') or detail['in_sign']['summary']))
            if detail["in_house"]:
                lines.append(tr('   {0}', detail['in_house'].get('effects') or detail['in_house']['summary']))

        lines.append(tx("\n\n--- Yogas present ---"))
        if r.get("yogas_plain_summary"):
            lines.append(r["yogas_plain_summary"])
        present = [y for y in r["yogas"] if y["present"]]
        if present:
            for y in present:
                lines.append(tr('\n{0} {1}: {2}', y['id'], y['name'], y['details']))
        else:
            lines.append(tx("\n(none of the 24 checked yogas are formed in this chart)"))

        running = r["dasha"]["running_at_birth"]
        lines.append(tr('\n\n--- Dasha running at birth: {0} Mahadasha / {1} Antardasha ---', running['mahadasha_lord'], running['antardasha_lord']))
        if running["mahadasha_reading"]:
            lines.append(tr('\n{0}', running['mahadasha_reading']['general_effects']))
        if running["antardasha_reading"]:
            lines.append(tr('\n{0}', running['antardasha_reading']['summary']))

        lines.append(tx("\n\n--- Life Predictions ---"))
        lp = r["life_predictions"]
        for key, entry in lp.items():
            if key == "caveat" or not isinstance(entry, dict):
                continue
            lines.append(tr('\n{0}: {1}', entry['title'], entry['text']))

        lines.append(tx("\n\n--- Karmic & Past Life: The Soul's Narrative ---"))
        lines.append(r["karmic_and_past_life"]["soul_narrative"] or "(see the Karmic & Past Life tab)")

        return "\n".join(lines)
