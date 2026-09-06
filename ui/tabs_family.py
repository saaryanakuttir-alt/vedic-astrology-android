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

from ui.widgets import SimpleTable, LongText
from ui.app_state import PROFILE_LABELS


class FamilyTab(BoxLayout):
    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store

        note = Label(
            text=("Generate a chart for Self at minimum; add Life Partner and/or Child "
                  "profiles for a fuller report. Self<->Life Partner uses Ashtakoot Guna "
                  "Milan; Self<->Child deliberately does NOT (see family_bonds.py)."),
            size_hint_y=None, height=dp(70), text_size=(None, None),
        )
        self.add_widget(note)

        compute_btn = Button(text="Compute Family Compatibility Report", size_hint_y=None, height=dp(48))
        compute_btn.bind(on_release=lambda *_: self.refresh())
        self.add_widget(compute_btn)

        self.summary_label = Label(text="", size_hint_y=None, height=dp(30), bold=True)
        self.add_widget(self.summary_label)

        self.table = SimpleTable(["Koota", "Points", "Max"], [0.5, 0.25, 0.25])
        self.table.size_hint_y = 0.35
        self.add_widget(self.table)

        self.report_text = LongText(size_hint_y=0.65)
        self.add_widget(self.report_text)

    def refresh(self):
        self_chart = self.store.profiles["self"]["chart"]
        self_reading = self.store.profiles["self"]["reading"]
        if self_chart is None or self_reading is None:
            self.summary_label.text = "Generate a chart for Self first."
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
            self.summary_label.text = (
                f"Self <-> Life Partner - Total: {result['total_points']:.1f} / "
                f"{result['max_points']} - {result['verdict']}"
            )
            rows = [(k["koota"], k["points"], k["max_points"]) for k in result["kootas"]]
            self.table.set_rows(rows)
        else:
            self.summary_label.text = "No Life Partner chart yet - showing Self's own disposition below."
            self.table.clear_rows()

        self.report_text.set_text(report["text"])
