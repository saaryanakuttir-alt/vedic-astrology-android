"""
tabs_family.py — Family Compatibility tab: Self's/Life Partner's own
relational disposition, Ashtakoot Guna Milan (Self <-> Life Partner), and
a Parent-Child Thematic Connection for Self and every generated Child
profile. Port of gui_app.py's _compute_family_compatibility, built on
family_bonds.build_family_compatibility_report exactly as the desktop app
uses it.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.clock import Clock

from ui.widgets import SimpleTable, LongText, CaptionLabel
from ui.app_state import PROFILE_LABELS


class FamilyTab(BoxLayout):
    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store

        note = CaptionLabel(
            "Generate a chart for Self at minimum; add Life Partner and/or Child profiles "
            "for a fuller report. Self <-> Life Partner uses 'Ashtakoot Guna Milan' (a "
            "classical 36-point marriage-matching score); Self <-> Child deliberately does "
            "NOT, since that scoring system is only meant for spouses - children instead "
            "get a separate, appropriately-scoped comparison. Both also get a karmic layer: "
            "past-life themes and how each of you can support the other's growth."
        )
        self.add_widget(note)

        compute_btn = Button(text="Compute Family Compatibility Report", size_hint_y=None, height=dp(48))
        compute_btn.bind(on_release=lambda *_: self.refresh())
        self.add_widget(compute_btn)

        # text_size bound to width + a texture_update-forced height sync in
        # _set_summary below - same fix, same reasoning, as ProfileTab's
        # status_label (see tabs_profile.py): without it, a moderately
        # long summary string ("Self <-> Life Partner - Total: X / Y -
        # <verdict text>") renders unwrapped and can overflow the screen.
        self.summary_label = Label(
            text="", size_hint_y=None, height=dp(30), bold=True, halign="left", valign="middle",
        )
        self.summary_label.bind(width=self._update_summary_text_size,
                                 texture_size=self._resize_summary_label)
        self.add_widget(self.summary_label)

        self.table = SimpleTable(["Koota", "Points", "Max"], [0.5, 0.25, 0.25])
        self.table.size_hint_y = 0.35
        self.add_widget(self.table)

        self.report_text = LongText(size_hint_y=0.65)
        self.add_widget(self.report_text)

    def _update_summary_text_size(self, label, width):
        label.text_size = (width, None)

    def _resize_summary_label(self, label, texture_size):
        label.height = max(dp(30), texture_size[1] + dp(10))

    def _set_summary(self, text):
        self.summary_label.text = text
        if self.summary_label.width:
            self.summary_label.text_size = (self.summary_label.width, None)
        # Deferred a frame via Clock rather than calling texture_update()
        # synchronously right here - same Android same-frame-collision fix
        # as CaptionLabel/LongText/ProfileTab's status_label (see
        # widgets.py's CaptionLabel for the fuller writeup).
        Clock.schedule_once(self._rebuild_summary_texture, 0)

    def _rebuild_summary_texture(self, dt):
        self.summary_label.texture_update()
        self.summary_label.height = max(dp(30), self.summary_label.texture_size[1] + dp(10))

    def refresh(self):
        self_chart = self.store.profiles["self"]["chart"]
        self_reading = self.store.profiles["self"]["reading"]
        if self_chart is None or self_reading is None:
            self._set_summary("Generate a chart for Self first.")
            self.table.clear_rows()
            self.report_text.set_text("")
            return

        import family_bonds as fb

        partner_chart = self.store.profiles["partner"]["chart"]
        partner_reading = self.store.profiles["partner"]["reading"]
        children = self.store.generated_children()

        report = fb.build_family_compatibility_report(
            self_reading, self_chart, partner_reading, partner_chart, children=children,
        )

        result = report["ashtakoot"]
        if result:
            self._set_summary(
                f"Self <-> Life Partner - Total: {result['total_points']:.1f} / "
                f"{result['max_points']} - {result['verdict']}"
            )
            rows = [(k["koota"], k["points"], k["max_points"]) for k in result["kootas"]]
            self.table.set_rows(rows)
        else:
            self._set_summary("No Life Partner chart yet - showing Self's own disposition below.")
            self.table.clear_rows()

        self.report_text.set_text(report["text"])
