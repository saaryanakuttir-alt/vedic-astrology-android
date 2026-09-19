"""
tabs_chart.py — the Chart Diagram tab: North Indian (diamond) or South
Indian (4x4 grid) chart, any of the 12 vargas, for whichever profile is
currently selected. All the actual layout math is chart_geometry.py (pure,
already unit-tested, GUI-independent) — this file just draws it with Kivy
graphics instructions instead of gui_app.py's tkinter Canvas calls.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock

import chart_geometry as cg
from astrology_tables import SIGN_ABBR
from panchanga import SIGNS
from ui import theme
from ui.widgets import CaptionLabel, LongText
from ui.theme import ThemedSpinner as Spinner

VARGA_CHOICES = [
    ("Rasi (D1)", "D1"), ("Hora (D2)", "D2"), ("Drekkana (D3)", "D3"),
    ("Chaturthamsa (D4)", "D4"), ("Navamsa (D9)", "D9"),
    ("Dasamsa (D10)", "D10"), ("Dwadasamsa (D12)", "D12"), ("Shodasamsa (D16)", "D16"),
    ("Vimsamsa (D20)", "D20"), ("Chaturvimsamsa (D24)", "D24"),
    ("Trimsamsa (D30)", "D30"), ("Shashtiamsa (D60)", "D60"),
]


def _sign_number(sign_name):
    return SIGNS.index(sign_name) + 1


def _abbr_sign(sign_name):
    return SIGN_ABBR.get(sign_name, sign_name[:3])


class ChartCanvas(Widget):
    """Draws one chart (North or South Indian) using ONLY canvas instructions:
    lines, fills and text textures inside a single canvas that is cleared and
    rebuilt on every redraw.

    Earlier versions put every sign number and planet name in a Label WIDGET
    created inside a `with self.canvas.before:` block. Kivy quietly registers
    anything created inside a `with canvas:` block into that canvas, so each
    Label's own canvas was added to `canvas.before` as well as to the widget's
    canvas; the next `canvas.before.clear()` then detached those canvases from
    their real parent, `remove_widget()` could no longer find them, and every
    redraw left the previous chart's 24 labels on screen forever. Redrawing the
    SAME chart hid it (old and new sat exactly on top of each other); choosing
    a different person or style showed two charts overlapped. With no child
    widgets there is nothing to leak: `canvas.clear()` removes it all.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chart = None
        self.varga_key = "D1"
        self.style = "North Indian"
        self._redraw_scheduled = False
        self._textures = {}
        # size and pos are separate properties that a layout pass often changes
        # together; routing both through the Clock collapses them (and a
        # set_chart() in the same frame) into a single redraw.
        self.bind(size=self._schedule_redraw, pos=self._schedule_redraw)

    def _schedule_redraw(self, *args):
        if not self._redraw_scheduled:
            self._redraw_scheduled = True
            Clock.schedule_once(self._run_scheduled_redraw, 0)

    def _run_scheduled_redraw(self, dt):
        self._redraw_scheduled = False
        self._redraw()

    def set_chart(self, chart, varga_key, style):
        self.chart = chart
        self.varga_key = varga_key
        self.style = style
        self._schedule_redraw()

    # ------------------------------------------------------------------ text
    def _texture(self, text, size_sp, bold):
        key = (text, size_sp, bold)
        tex = self._textures.get(key)
        if tex is None:
            label = CoreLabel(text=text, font_size=sp(size_sp), bold=bold, halign="center")
            label.refresh()
            tex = self._textures[key] = label.texture
        return tex

    def _text_at(self, text, cx, cy, size_sp, bold, color):
        """Draw `text` centred on (cx, cy). Must be called inside `with self.canvas:`."""
        if not text:
            return
        tex = self._texture(text, size_sp, bold)
        Color(*color)
        Rectangle(texture=tex, size=tex.size, pos=(cx - tex.width / 2, cy - tex.height / 2))

    @staticmethod
    def _planet_block(names, extra_first=None):
        """Planet abbreviations as centred text: one per line for up to two,
        otherwise two per line so a crowded house stays inside its cell."""
        items = ([extra_first] if extra_first else []) + list(names)
        if len(items) <= 2:
            return "\n".join(items)
        return "\n".join(" ".join(items[i:i + 2]) for i in range(0, len(items), 2))

    # ------------------------------------------------------------------ draw
    def _redraw(self, *args):
        self.canvas.clear()
        if len(self._textures) > 300:
            self._textures.clear()
        if self.chart is None or self.width < 10 or self.height < 10:
            return

        size = min(self.width, self.height) - dp(20)
        ox = self.x + (self.width - size) / 2
        oy = self.y + (self.height - size) / 2

        with self.canvas:
            Color(*theme.SURFACE)
            Rectangle(pos=(ox, oy), size=(size, size))
            Color(*theme.ACCENT)
            if self.style == "North Indian":
                self._draw_north_indian(ox, oy, size)
            else:
                self._draw_south_indian(ox, oy, size)

    def _draw_north_indian(self, ox, oy, size):
        def to_canvas(pt):
            # Kivy's y axis grows upward; chart_geometry's normalized
            # coordinates assume a downward-growing y like a screen bitmap,
            # so flip y here to match.
            return ox + pt[0] * size, oy + (1 - pt[1]) * size

        for p1, p2 in cg.NORTH_INDIAN_FRAME_LINES:
            a, b = to_canvas(p1), to_canvas(p2)
            Line(points=[a[0], a[1], b[0], b[1]], width=1.3)

        asc_sign = cg.ascendant_sign_for_varga(self.chart, self.varga_key)
        sign_map = cg.north_indian_sign_map(asc_sign)
        house_planets = cg.build_house_planet_map(self.chart, self.varga_key)

        for house_num, house_def in cg.NORTH_INDIAN_HOUSES.items():
            centroid = cg.polygon_centroid(house_def["polygon"])
            ov = house_def["outer_vertex"]
            # sign number: a little way in from the house's outer corner/edge
            lx = ov[0] + (centroid[0] - ov[0]) * 0.35
            ly = ov[1] + (centroid[1] - ov[1]) * 0.35
            self._text_at(str(_sign_number(sign_map[house_num])), *to_canvas((lx, ly)), 10.5, False,
                          theme.NEUTRAL_600)
            block = self._planet_block(house_planets[house_num], "ASC" if house_num == 1 else None)
            self._text_at(block, *to_canvas(centroid), 12.5, True, theme.TEXT)

    def _draw_south_indian(self, ox, oy, size):
        cell = size / 4.0
        sign_planets = cg.build_sign_planet_map(self.chart, self.varga_key)
        asc_sign = cg.ascendant_sign_for_varga(self.chart, self.varga_key)

        for i in range(5):
            Line(points=[ox, oy + i * cell, ox + size, oy + i * cell], width=1)
            Line(points=[ox + i * cell, oy, ox + i * cell, oy + size], width=1)

        for sign, (row, col) in cg.SOUTH_INDIAN_GRID.items():
            # South Indian grids are drawn top-to-bottom by row 0..3; Kivy's y
            # grows upward, so invert the row here.
            x0 = ox + col * cell
            y0 = oy + (3 - row) * cell
            if sign == asc_sign:
                Color(*theme.ACCENT_700)
                Line(rectangle=(x0 + 3, y0 + 3, cell - 6, cell - 6), width=2)
            # Sign abbreviation in the cell's top-left corner (classical
            # South Indian style); planets centred, nudged down a little so
            # they never touch it.
            self._text_at(_abbr_sign(sign), x0 + dp(17), y0 + cell - dp(10), 10.5, False, theme.NEUTRAL_600)
            self._text_at(self._planet_block(sign_planets[sign], "ASC" if sign == asc_sign else None),
                          x0 + cell / 2, y0 + cell / 2 - dp(5), 12.5, True, theme.TEXT)


class ChartTab(BoxLayout):
    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store

        controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(8),
                             padding=(dp(12), dp(4), dp(12), dp(6)))
        self.style_spinner = Spinner(text="North Indian", values=["North Indian", "South Indian"])
        self.style_spinner.bind(text=self._on_control_change)
        self.varga_spinner = Spinner(text=VARGA_CHOICES[0][0], values=[lbl for lbl, _ in VARGA_CHOICES])
        self.varga_spinner.bind(text=self._on_control_change)
        controls.add_widget(self.style_spinner)
        controls.add_widget(self.varga_spinner)
        self.add_widget(controls)

        self.add_widget(CaptionLabel(
            "A visual diagram of your chart, showing which sign/house each planet falls "
            "in. 'D1' (Rasi) is your main birth chart; the other 'D' options are "
            "specialized zoom-ins classical texts use for specific life areas (e.g. D9 for "
            "marriage)."
        ))

        self.info_label = Label(text="No chart generated yet.", size_hint_y=None, height=dp(28))
        self.add_widget(self.info_label)

        self.canvas_widget = ChartCanvas()
        self.add_widget(self.canvas_widget)

        # This person's own placements in the selected chart, in plain
        # language first and the denser classical wording after it.
        self.explain = LongText(size_hint_y=None, height=dp(170))
        self.add_widget(self.explain)

    def _varga_key(self):
        label = self.varga_spinner.text
        for lbl, key in VARGA_CHOICES:
            if lbl == label:
                return key
        return "D1"

    def _on_control_change(self, spinner, value):
        self.refresh()

    def preset_varga(self, key):
        """Home's 'Divisional Charts' card opens this screen already on D9."""
        for lbl, k in VARGA_CHOICES:
            if k == key:
                self.varga_spinner.text = lbl

    def _explanation_text(self, varga_key):
        reading = self.store.current["reading"]
        cd = ((reading or {}).get("chart_descriptions") or {}).get(varga_key)
        if not cd:
            return ""
        return "\n\n".join([cd.get("plain_explanation", ""), "In classical terms:", cd.get("text", "")]).strip()

    def refresh(self):
        chart = self.store.current["chart"]
        style = getattr(self.store, "chart_style", None)
        if style and self.style_spinner.text != style:
            self.style_spinner.text = style
        if chart is None:
            self.info_label.text = "No chart generated yet for this profile."
            self.canvas_widget.set_chart(None, self._varga_key(), self.style_spinner.text)
            self.explain.set_text("")
            return
        self.explain.set_text(self._explanation_text(self._varga_key()))
        varga_key = self._varga_key()
        asc_sign = cg.ascendant_sign_for_varga(chart, varga_key)
        self.info_label.text = f"Ascendant ({varga_key}): {asc_sign}"
        self.canvas_widget.set_chart(chart, varga_key, self.style_spinner.text)
