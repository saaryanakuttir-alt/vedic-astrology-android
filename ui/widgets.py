"""
widgets.py — small reusable Kivy building blocks used across every tab, so
each tab module only has to describe ITS data, not re-solve "how do I show
a scrollable table" / "how do I show a scrollable block of text" every time.

Kivy has no built-in ttk.Treeview equivalent, so SimpleTable below is a
plain scrollable GridLayout: a bold header row, then one row per data row.
It's intentionally simple (no sorting/column-resize) — this app's tables
are for reading, not manipulating.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock

# Border color shows through the 1dp gaps GridLayout leaves between cells
# (see _make_cell_background below) - a plain medium gray reads as a grid
# line against either the header or data cell fill color.
_BORDER_COLOR = (0.4, 0.4, 0.45, 1)
_HEADER_BG = (0.16, 0.16, 0.2, 1)
_DATA_BG = (0.09, 0.09, 0.12, 1)


class SimpleTable(ScrollView):
    """SimpleTable(columns=["A","B"], col_hints=[0.3,0.7]) then
    .set_rows([("a1","b1"), ("a2","b2"), ...]). Pass font_size to shrink
    text for tables with many columns (e.g. Ashtakvarga's 13) - the
    default suits most of this app's tables (up to ~9 columns)."""

    def __init__(self, columns, col_hints=None, font_size="13sp", **kwargs):
        super().__init__(**kwargs)
        self.columns = columns
        self.col_hints = col_hints or [1.0 / len(columns)] * len(columns)
        self.font_size = font_size
        # spacing=dp(1) is the actual GAP between cells - it's what lets
        # the grid's own border-colored background (below) show through
        # as thin lines around every cell, so it must stay non-zero.
        self.grid = GridLayout(cols=len(columns), size_hint_y=None, spacing=dp(1))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        with self.grid.canvas.before:
            Color(*_BORDER_COLOR)
            self._grid_bg = Rectangle(pos=self.grid.pos, size=self.grid.size)
        self.grid.bind(pos=self._update_grid_bg, size=self._update_grid_bg)
        self.add_widget(self.grid)
        self._add_row(self.columns, header=True)

    def _update_grid_bg(self, instance, value):
        self._grid_bg.pos = instance.pos
        self._grid_bg.size = instance.size

    def _make_cell_background(self, label, color):
        # A filled Rectangle tracking the label's own pos/size, INSET by
        # nothing (the visible border comes from the dp(1) gap between
        # sibling cells showing the grid's own background behind them,
        # not from insetting this rectangle) - each cell just needs to be
        # opaque so it doesn't show the tab's own background through it.
        # The rect is stashed on the label itself and both pos/size bind
        # to the SAME method (_sync_cell_bg) rather than two fresh lambda
        # closures per cell - tables like Dasha can have 100+ rows (450+
        # cells), and allocating 2 new closures + 2 bind() calls for each
        # one measurably added up (~150ms for a 450-cell table even on a
        # desktop GPU; far worse on the emulator's software SwiftShader
        # renderer, where it contributed to an ANR during rapid tab-
        # switching). One shared bound method avoids that per-cell
        # closure-allocation overhead.
        with label.canvas.before:
            Color(*color)
            label._bg_rect = Rectangle(pos=label.pos, size=label.size)
        label.bind(pos=self._sync_cell_bg, size=self._sync_cell_bg)

    @staticmethod
    def _sync_cell_bg(label, value):
        label._bg_rect.pos = label.pos
        label._bg_rect.size = label.size

    def _add_row(self, values, header=False):
        for value, hint in zip(values, self.col_hints):
            # height can't be None here even though _resize_label (bound
            # below) immediately recomputes it once the label's texture is
            # ready - Kivy's height is a NumericProperty that rejects a
            # literal None at construction (raises "None is not allowed
            # for Label.height", confirmed via adb logcat on a real
            # device/emulator the moment any table got real data rows -
            # this affects every data tab, not just profile-switching).
            # dp(28) matches _resize_label's own floor value below, so it's
            # a sensible placeholder for the instant before that binding
            # fires.
            lbl = Label(
                text=str(value), size_hint_x=hint, size_hint_y=None,
                height=dp(36) if header else dp(28), text_size=(None, None),
                halign="left", valign="middle", bold=header,
                font_size=self.font_size,
                color=(1, 0.85, 0.3, 1) if header else (1, 1, 1, 1),
                shorten=False,
            )
            self._make_cell_background(lbl, _HEADER_BG if header else _DATA_BG)
            lbl.bind(texture_size=self._resize_label, width=self._update_text_size)
            self.grid.add_widget(lbl)

    def _update_text_size(self, label, width):
        # Must be a live binding, not a one-time read of label.width inside
        # _resize_label: GridLayout assigns each child's real (column-
        # fraction) width on its own later layout pass, not synchronously
        # when the Label is first constructed and parented. Reading
        # label.width once at that point sees a stale/default width (not
        # yet the real column width), constraining text_size to it and
        # wrapping the text after almost every character - confirmed via
        # screenshot on the emulator (every table column rendered as a
        # single letter per line). Binding width itself re-applies
        # text_size whenever GridLayout later assigns the real width.
        label.text_size = (width, None)

    def _resize_label(self, label, texture_size):
        label.height = max(dp(28), texture_size[1] + dp(10))

    def clear_rows(self):
        self.grid.clear_widgets()
        self._add_row(self.columns, header=True)

    def set_rows(self, rows):
        self.clear_rows()
        for row in rows:
            self._add_row(row, header=False)


class LongText(ScrollView):
    """A big scrollable block of read-only wrapped text — the mobile
    equivalent of the desktop app's tk.Text widgets used for the Karmic,
    Life Predictions, Full Reading, and Family Compatibility tabs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label = Label(
            text="", size_hint_y=None, height=dp(28), halign="left", valign="top",
            padding=(dp(10), dp(10)),
        )
        self.label.bind(texture_size=self._on_texture_size)
        self.bind(width=self._on_width)
        self.add_widget(self.label)

    def _on_width(self, instance, width):
        self.label.text_size = (width - dp(20), None)

    def _on_texture_size(self, instance, texture_size):
        self.label.height = max(dp(28), texture_size[1] + dp(20))

    def set_text(self, text):
        self.label.text = text or ""
        # Belt-and-suspenders, not just the width binding above: confirmed
        # via adb logcat + screenshot that the Karmic & Past Life and Life
        # Predictions tabs (both LongText) rendered completely blank after
        # a real, exception-free chart generation (no traceback anywhere
        # in the log) - and stayed blank even after navigating away and
        # back, which rules out a "tab not laid out yet" one-time timing
        # fluke. This tab's content is set once, immediately after
        # construction, while the TabbedPanelItem holding it may not be
        # the active tab yet - if self.width happened to already equal
        # whatever it was at bind time with no further change, _on_width
        # never fires again and text_size is left at its unset default,
        # producing a degenerate (often invisible) render. Reapplying
        # text_size here against whatever width is currently known
        # removes the dependency on that binding having already fired
        # with a valid value by the time text changes.
        if self.width:
            self.label.text_size = (self.width - dp(20), None)
        # A synchronous texture_update() here (tried first) still left the
        # ScrollView completely blank on-device (re-confirmed on the
        # emulator with a real generated chart) - EXCEPT the scrollbar
        # thumb DID show a real, scrollable content height and moved when
        # swiped, proving the label's own height/texture_size are correct
        # and non-zero; nothing simply fails to render. Only the actual
        # glyph texture never made it on screen. This is the same
        # "two GL updates land in the same frame" quirk already found and
        # fixed for the Chart tab's label ghosting (see tabs_chart.py's
        # ChartCanvas._schedule_redraw): every tab using LongText also
        # constructs a CaptionLabel immediately above it, and that
        # CaptionLabel does its OWN synchronous texture rebuild at
        # construction time, in the same frame as this set_text() call -
        # never reproducible on desktop's SDL2/GL backend despite direct
        # attempts. Deferring this label's texture rebuild to the next
        # frame via Clock, rather than forcing it synchronously in the
        # same frame as CaptionLabel's own update, resolved it.
        Clock.schedule_once(self._rebuild_texture, 0)

    def _rebuild_texture(self, dt):
        self.label.texture_update()
        self.label.height = max(dp(28), self.label.texture_size[1] + dp(20))


class CaptionLabel(Label):
    """A short, plain-English one-to-three-line explainer shown at the top
    of a tab, above its table/report content - e.g. "Your planetary time-
    periods (Dasha) - a traditional system for timing when each planet's
    themes are most active in your life." Astrology has a lot of jargon
    (Ashtakvarga, Chalit, Nakshatra, Atmakaraka...); this doesn't remove
    the technical names (they stay precise and searchable for anyone who
    wants to look them up) but gives everyone a plain-language anchor
    before diving into a table full of abbreviations.

    Auto-sizes its own height to fit wrapped text, the same texture_update
    pattern LongText above uses (needed even for a caption this short -
    see LongText.set_text's own comment for why relying on Kivy's default
    post-property-change scheduling alone isn't reliable on Android)."""

    def __init__(self, text, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "top")
        kwargs.setdefault("padding", (dp(10), dp(8)))
        kwargs.setdefault("color", (0.75, 0.78, 0.85, 1))
        kwargs.setdefault("font_size", "12sp")
        kwargs.setdefault("italic", True)
        super().__init__(text=text, height=dp(28), **kwargs)
        self.bind(width=self._on_width, texture_size=self._on_texture_size)

    def _on_width(self, instance, width):
        self.text_size = (width - dp(20), None)
        self.texture_update()
        self.height = max(dp(28), self.texture_size[1] + dp(16))

    def _on_texture_size(self, instance, texture_size):
        self.height = max(dp(28), texture_size[1] + dp(16))


def _bind_label_text_size(label, *_):
    # halign/valign are no-ops in Kivy until text_size constrains the
    # label's layout box (see _add_label's docstring in tabs_chart.py for
    # the fuller explanation) - this Label's width isn't known until the
    # parent BoxLayout's own later layout pass assigns it, so text_size
    # must be set from a live width binding, not a one-time read here.
    label.text_size = (label.width, label.height)


def field_row(label_text, widget, height=dp(40)):
    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=height, spacing=dp(6))
    label = Label(text=label_text, size_hint_x=0.38, halign="right", valign="middle")
    label.bind(size=_bind_label_text_size)
    row.add_widget(label)
    row.add_widget(widget)
    return row
