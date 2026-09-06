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
from kivy.metrics import dp


class SimpleTable(ScrollView):
    """SimpleTable(columns=["A","B"], col_hints=[0.3,0.7]) then
    .set_rows([("a1","b1"), ("a2","b2"), ...])."""

    def __init__(self, columns, col_hints=None, **kwargs):
        super().__init__(**kwargs)
        self.columns = columns
        self.col_hints = col_hints or [1.0 / len(columns)] * len(columns)
        self.grid = GridLayout(cols=len(columns), size_hint_y=None, spacing=dp(1))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.add_widget(self.grid)
        self._add_row(self.columns, header=True)

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
                color=(1, 0.85, 0.3, 1) if header else (1, 1, 1, 1),
                shorten=False,
            )
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


def field_row(label_text, widget, height=dp(40)):
    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=height, spacing=dp(6))
    row.add_widget(Label(text=label_text, size_hint_x=0.38, halign="right", valign="middle"))
    row.add_widget(widget)
    return row
