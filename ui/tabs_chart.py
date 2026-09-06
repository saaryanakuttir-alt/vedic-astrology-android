"""
tabs_chart.py — the Chart Diagram tab: North Indian (diamond) or South
Indian (4x4 grid) chart, any of the 12 vargas, for whichever profile is
currently selected. All the actual layout math is chart_geometry.py (pure,
already unit-tested, GUI-independent) — this file just draws it with Kivy
graphics instructions instead of gui_app.py's tkinter Canvas calls.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp

import chart_geometry as cg
from astrology_tables import SIGN_ABBR
from panchanga import SIGNS

VARGA_CHOICES = [
    ("Rasi (D1)", "D1"), ("Hora (D2)", "D2"), ("Drekkana (D3)", "D3"),
    ("Chaturthamsa (D4)", "D4"), ("Saptamsa (D7)", "D7"), ("Navamsa (D9)", "D9"),
    ("Dasamsa (D10)", "D10"), ("Dwadasamsa (D12)", "D12"), ("Shodasamsa (D16)", "D16"),
    ("Vimsamsa (D20)", "D20"), ("Chaturvimsamsa (D24)", "D24"),
    ("Trimsamsa (D30)", "D30"), ("Shashtiamsa (D60)", "D60"),
]


def _sign_number(sign_name):
    return SIGNS.index(sign_name) + 1


def _abbr_sign(sign_name):
    return SIGN_ABBR.get(sign_name, sign_name[:3])


class ChartCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chart = None
        self.varga_key = "D1"
        self.style = "North Indian"
        self._sign_labels = []
        self._planet_labels = []
        self.bind(size=self._redraw, pos=self._redraw)

    def set_chart(self, chart, varga_key, style):
        self.chart = chart
        self.varga_key = varga_key
        self.style = style
        self._redraw()

    def _clear_labels(self):
        # clear_widgets() rather than looping over the tracked lists below
        # and remove_widget()-ing each one individually: on-device testing
        # (both a real OnePlus 7T Pro and the x86_64 emulator) showed
        # switching styles via the spinner leaves the PREVIOUS style's
        # labels still rendered underneath the new ones - confirmed via
        # screenshot, e.g. South Indian's sign abbreviations ("Ari",
        # "Tau", ...) still visible after switching to North Indian.
        # The remove_widget-per-tracked-label loop is logically correct
        # and was verified, via four separate from-scratch desktop Kivy
        # reproductions of this exact add/remove/redraw pattern (including
        # driving the real ChartTab/TabbedPanel with genuine touch-
        # dispatched spinner selections, matching the on-device sequence
        # step for step), to behave perfectly on desktop's SDL2 backend -
        # the ghosting never reproduced there. That points to an Android-
        # specific GL/instruction-invalidation quirk rather than the
        # tracked lists ever actually losing sync with self.children.
        # clear_widgets() removes every widget ChartCanvas ACTUALLY has as
        # a child right now, unconditionally, rather than only the ones
        # the tracked lists remember adding - a strictly safer clear that
        # can't be fooled by however this class of issue is occurring.
        self.clear_widgets()
        self._sign_labels = []
        self._planet_labels = []

    def _add_label(self, text, cx, cy, bold=False, small=False, color=(1, 1, 1, 1)):
        """cx, cy is the point the label should be CENTERED on (not a
        corner) - callers previously had to pre-offset by half the label
        size themselves, which only worked for cells on the left/top of
        the diagram; cells on the right edge had their label's default
        left-aligned text extend straight off the visible canvas (and
        past the screen edge entirely), confirmed via screenshot on the
        emulator. halign="center" alone does nothing in Kivy without
        text_size also being set to constrain it - it was silently a
        no-op here before."""
        size = (dp(60), dp(28) if small else dp(40))
        lbl = Label(
            text=text, pos=(cx - size[0] / 2, cy - size[1] / 2), size=size,
            text_size=size, color=color, bold=bold,
            font_size="11sp" if small else "13sp",
            halign="center", valign="middle",
        )
        self.add_widget(lbl)
        (self._sign_labels if small else self._planet_labels).append(lbl)
        return lbl

    def _redraw(self, *args):
        self.canvas.before.clear()
        self._clear_labels()
        if self.chart is None or self.width < 10 or self.height < 10:
            return

        size = min(self.width, self.height) - dp(20)
        ox = self.x + (self.width - size) / 2
        oy = self.y + (self.height - size) / 2

        def to_canvas(pt):
            # Kivy's y axis grows upward; chart_geometry's normalized
            # coordinates assume a downward-growing y like a screen bitmap,
            # so flip y here to match.
            return ox + pt[0] * size, oy + (1 - pt[1]) * size

        with self.canvas.before:
            Color(0.05, 0.05, 0.15, 1)
            Rectangle(pos=(ox, oy), size=(size, size))
            Color(1, 1, 1, 1)
            if self.style == "North Indian":
                self._draw_north_indian(to_canvas)
            else:
                self._draw_south_indian(ox, oy, size)

    def _draw_north_indian(self, to_canvas):
        for p1, p2 in cg.NORTH_INDIAN_FRAME_LINES:
            a, b = to_canvas(p1), to_canvas(p2)
            Line(points=[a[0], a[1], b[0], b[1]], width=1.3)

        asc_sign = cg.ascendant_sign_for_varga(self.chart, self.varga_key)
        sign_map = cg.north_indian_sign_map(asc_sign)
        house_planets = cg.build_house_planet_map(self.chart, self.varga_key)

        for house_num, house_def in cg.NORTH_INDIAN_HOUSES.items():
            centroid = cg.polygon_centroid(house_def["polygon"])
            cx, cy = to_canvas(centroid)
            ov = house_def["outer_vertex"]
            lx = ov[0] + (centroid[0] - ov[0]) * 0.35
            ly = ov[1] + (centroid[1] - ov[1]) * 0.35
            lx, ly = to_canvas((lx, ly))

            sign = sign_map[house_num]
            self._add_label(str(_sign_number(sign)), lx, ly,
                             small=True, color=(0.7, 0.7, 0.7, 1))

            planets_here = house_planets[house_num]
            label = "\n".join(planets_here) if planets_here else ""
            if house_num == 1:
                label = ("ASC\n" + label) if label else "ASC"
            self._add_label(label, cx, cy, bold=True,
                             color=(0.6, 0.75, 1, 1))

    def _draw_south_indian(self, ox, oy, size):
        cell = size / 4.0
        sign_planets = cg.build_sign_planet_map(self.chart, self.varga_key)
        asc_sign = cg.ascendant_sign_for_varga(self.chart, self.varga_key)

        for i in range(5):
            Line(points=[ox, oy + i * cell, ox + size, oy + i * cell], width=1)
            Line(points=[ox + i * cell, oy, ox + i * cell, oy + size], width=1)

        for sign, (row, col) in cg.SOUTH_INDIAN_GRID.items():
            # South Indian grids are conventionally drawn top-to-bottom by
            # row 0..3; Kivy's y grows upward, so invert the row here.
            x0 = ox + col * cell
            y0 = oy + (3 - row) * cell
            cx, cy = x0 + cell / 2, y0 + cell / 2
            if sign == asc_sign:
                with self.canvas.before:
                    Color(0.75, 0.2, 0.15, 1)
                    Line(rectangle=(x0 + 3, y0 + 3, cell - 6, cell - 6), width=2)
                    Color(1, 1, 1, 1)
            # Sign abbreviation sits in the cell's top-left corner
            # (classical South Indian style, not centered) - _add_label
            # now takes a CENTER point, so offset by half its own (small)
            # label size to land the same corner as before.
            self._add_label(_abbr_sign(sign), x0 + dp(4) + dp(30), y0 + cell - dp(20) + dp(14),
                             small=True, color=(0.7, 0.7, 0.7, 1))
            label = "\n".join(sign_planets[sign])
            self._add_label(label, cx, cy, bold=True,
                             color=(0.6, 0.75, 1, 1))


class ChartTab(BoxLayout):
    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store

        controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(6))
        self.style_spinner = Spinner(text="North Indian", values=["North Indian", "South Indian"])
        self.style_spinner.bind(text=self._on_control_change)
        self.varga_spinner = Spinner(text=VARGA_CHOICES[0][0], values=[lbl for lbl, _ in VARGA_CHOICES])
        self.varga_spinner.bind(text=self._on_control_change)
        controls.add_widget(self.style_spinner)
        controls.add_widget(self.varga_spinner)
        self.add_widget(controls)

        self.info_label = Label(text="No chart generated yet.", size_hint_y=None, height=dp(28))
        self.add_widget(self.info_label)

        self.canvas_widget = ChartCanvas()
        self.add_widget(self.canvas_widget)

    def _varga_key(self):
        label = self.varga_spinner.text
        for lbl, key in VARGA_CHOICES:
            if lbl == label:
                return key
        return "D1"

    def _on_control_change(self, spinner, value):
        self.refresh()

    def refresh(self):
        chart = self.store.current["chart"]
        if chart is None:
            self.info_label.text = "No chart generated yet for this profile."
            self.canvas_widget.set_chart(None, self._varga_key(), self.style_spinner.text)
            return
        varga_key = self._varga_key()
        asc_sign = cg.ascendant_sign_for_varga(chart, varga_key)
        self.info_label.text = f"Ascendant ({varga_key}): {asc_sign}"
        self.canvas_widget.set_chart(chart, varga_key, self.style_spinner.text)
