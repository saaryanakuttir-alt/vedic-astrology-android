"""
keyboard.py — a built-in on-screen keyboard, and the switch between it and
the phone's own keyboard.

Why it exists: on the real device (OnePlus 7T Pro) tapping a text field never
produced a working phone keyboard, so no new birth details could be typed.
The cause on the device was never pinned down (it did not reproduce on
desktop), so instead of depending on Android's input method at all, the
default is this keyboard: a docked panel made of ordinary buttons - the same
kind of widget that already works reliably on the device - that types into the
focused field with the public TextInput API (insert_text / do_backspace).
"Phone keyboard" stays available as a setting.

How the pieces fit:
  * ThemedTextInput (theme.py) registers every field with SERVICE.
  * In built-in mode a field is put in keyboard_mode="managed" (Kivy then never
    asks Android for its keyboard) and focusing it shows the panel.
  * BuiltinKeyboard is docked in main.py's layout above the bottom bar, so the
    screen content simply gets shorter; the focused field is scrolled into view.
"""
import weakref

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from ui import theme

KEY_H = dp(44)
GAP = dp(5)
PAD_V = dp(6)

_ALPHA_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
_SYMBOL_ROW2 = "-/_.,'()&:"
_SYMBOL_ROW3 = "+=*#@%!?;"

# (label, kind) layouts for the number pad: 4 columns x 4 rows
_NUMBER_ROWS = [
    [("1", "char"), ("2", "char"), ("3", "char"), ("⌫", "back")],
    [("4", "char"), ("5", "char"), ("6", "char"), ("Done", "done")],
    [("7", "char"), ("8", "char"), ("9", "char"), ("-", "char")],
    [(".", "char"), ("0", "char"), ("", "blank"), ("", "blank")],
]


class _Key(theme.ThemedButton):
    def __init__(self, label, kind, weight=1.0, **kwargs):
        kwargs.setdefault("size_hint", (weight, 1))
        kwargs.setdefault("font_size", "17sp")
        kwargs.setdefault("bold", kind not in ("char", "space"))
        if kind in ("back", "shift"):
            kwargs.setdefault("font_name", theme.SYMBOL_FONT)   # arrows/backspace are not in Roboto
        super().__init__(text=label, variant="primary" if kind == "done" else "secondary", **kwargs)
        self.kind = kind


class BuiltinKeyboard(BoxLayout):
    def __init__(self, service, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(orientation="vertical", height=0, opacity=0, disabled=True,
                         padding=(dp(4), PAD_V, dp(4), PAD_V), spacing=GAP, **kwargs)
        self._service = service
        self.target = None
        self.mode = "alpha"          # alpha | symbols | number
        self.shift = "off"           # off | once | lock
        self._repeat = None
        with self.canvas.before:
            Color(*theme.SURFACE)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*theme.DIVIDER)
            self._top = Rectangle(pos=self.pos, size=(self.width, dp(1)))
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._top.pos, self._top.size = (self.x, self.top - dp(1)), (self.width, dp(1))

    # ------------------------------------------------------------- show / hide
    @property
    def visible(self):
        return self.target is not None and self.height > 0

    def attach(self, field):
        self.target = field
        if field.kb_layout in ("number", "decimal"):
            mode = "number"
        else:
            mode = "alpha"
        self.shift = "once" if (mode == "alpha" and field.kb_autocap and self._at_word_start(field)) else "off"
        self._build(mode)
        self.disabled = False
        self.opacity = 1
        Clock.schedule_once(self._scroll_to_target, 0.15)

    def detach(self):
        self._stop_repeat()
        self.target = None
        self.clear_widgets()
        self.height = 0
        self.opacity = 0
        self.disabled = True

    def _scroll_to_target(self, *_):
        field = self.target
        if field is None:
            return
        node = field.parent
        while node is not None and not (isinstance(node, ScrollView) and node.do_scroll_y):
            node = node.parent
        if node is not None:
            try:
                node.scroll_to(field, padding=dp(28), animate=False)
            except Exception:  # noqa: BLE001 - scrolling is a nicety, never fatal
                pass

    @staticmethod
    def _at_word_start(field):
        text, idx = field.text, field.cursor_index()
        return idx == 0 or text[idx - 1:idx] in (" ", "-", "/")

    # ------------------------------------------------------------- layout
    def _build(self, mode):
        """Rebuild the key rows from scratch (fresh widgets every time - this
        project avoids mutating .text on already-drawn widgets)."""
        self.mode = mode
        self.clear_widgets()
        if mode == "number":
            rows = [self._row(spec) for spec in _NUMBER_ROWS]
        elif mode == "symbols":
            rows = [self._row([(c, "char") for c in "1234567890"]),
                    self._row([(c, "char") for c in _SYMBOL_ROW2]),
                    self._row([(c, "char") for c in _SYMBOL_ROW3] + [("⌫", "back", 1.4)]),
                    self._bottom_row("ABC")]
        else:
            up = self.shift != "off"
            r1 = [(c.upper() if up else c, "char") for c in _ALPHA_ROWS[0]]
            r2 = [("", "blank", 0.5)] + [(c.upper() if up else c, "char") for c in _ALPHA_ROWS[1]] + [("", "blank", 0.5)]
            shift_label = {"off": "⇧", "once": "⇧", "lock": "⇪"}[self.shift]
            r3 = [(shift_label, "shift", 1.4)] + [(c.upper() if up else c, "char") for c in _ALPHA_ROWS[2]] + [("⌫", "back", 1.4)]
            rows = [self._row(r1), self._row(r2), self._row(r3), self._bottom_row("?123")]
        for r in rows:
            self.add_widget(r)
        n = len(rows)
        self.height = n * KEY_H + (n - 1) * GAP + 2 * PAD_V

    def _bottom_row(self, switch_label):
        return self._row([(switch_label, "mode", 1.5), (",", "char"), ("space", "space", 4.0), (".", "char"),
                          ("Done", "done", 1.6)])

    def _row(self, spec):
        row = BoxLayout(orientation="horizontal", spacing=GAP, size_hint_y=None, height=KEY_H)
        for item in spec:
            label, kind = item[0], item[1]
            weight = item[2] if len(item) > 2 else 1.0
            if kind == "blank":
                row.add_widget(Widget(size_hint_x=weight))
                continue
            key = _Key(label, kind, weight)
            if kind == "back":
                key.bind(on_press=self._back_down, on_release=self._back_up)
            else:
                key.bind(on_press=lambda inst, k=kind, t=label: self._on_key(k, t))
            row.add_widget(key)
        return row

    # ------------------------------------------------------------- typing
    def _on_key(self, kind, text):
        field = self.target
        if kind == "done":
            self._service.hide()
            return
        if kind == "mode":
            self._build("symbols" if self.mode == "alpha" else "alpha")
            return
        if kind == "shift":
            self.shift = {"off": "once", "once": "lock", "lock": "off"}[self.shift]
            self._build(self.mode)
            return
        if field is None:
            return
        ch = " " if kind == "space" else text
        field.insert_text(ch)
        if self.mode != "alpha":
            return
        was = self.shift
        if ch.isalpha() and self.shift == "once":
            self.shift = "off"
        elif ch in (" ", "-", "/") and field.kb_autocap and self.shift == "off":
            self.shift = "once"
        if self.shift != was:
            self._build("alpha")

    def _back_down(self, *_):
        self._backspace()
        self._stop_repeat()
        self._repeat = Clock.schedule_once(self._begin_repeat, 0.45)

    def _begin_repeat(self, *_):
        self._repeat = Clock.schedule_interval(lambda dt: self._backspace(), 0.07)

    def _back_up(self, *_):
        self._stop_repeat()

    def _stop_repeat(self):
        if self._repeat is not None:
            self._repeat.cancel()
            self._repeat = None

    def _backspace(self):
        field = self.target
        if field is None:
            return
        field.do_backspace()
        if self.mode == "alpha" and field.kb_autocap and self.shift == "off" and self._at_word_start(field):
            self.shift = "once"
            self._build("alpha")


class KeyboardService:
    """One per app (SERVICE below). Decides, per text field, whether the
    built-in keyboard or the phone's keyboard is used."""

    def __init__(self):
        self.builtin = True
        self.panel = None
        self.on_visibility = None        # callback(bool), set by main.py
        self._fields = weakref.WeakSet()

    @property
    def visible(self):
        return bool(self.panel and self.panel.visible)

    def make_panel(self):
        self.panel = BuiltinKeyboard(self)
        return self.panel

    # ---- fields
    def register(self, field):
        self._fields.add(field)
        self._configure(field)
        field.bind(focus=self._on_focus)

    def _configure(self, field):
        field.keyboard_mode = "managed" if self.builtin else "auto"
        field.keyboard_suggestions = False      # no autocorrect/composing for names and places
        field.input_type = "number" if (not self.builtin and field.kb_layout == "number") else "text"

    def set_builtin(self, on):
        on = bool(on)
        if on == self.builtin:
            return
        self.builtin = on
        for f in list(self._fields):
            self._configure(f)
        if not on:
            self.hide()

    # ---- focus -> panel
    def _on_focus(self, field, focused):
        if not self.builtin or self.panel is None:
            return
        if focused:
            self.show(field)
        elif field is self.panel.target:
            Clock.schedule_once(self._hide_if_idle, 0.12)

    def _hide_if_idle(self, *_):
        if not any(f.focus for f in list(self._fields)):
            self.hide()

    def show(self, field):
        prev = self.panel.target
        if prev is not None and prev is not field and prev.focus:
            prev.focus = False
        was_visible = self.visible
        self.panel.attach(field)
        if not was_visible and self.on_visibility:
            self.on_visibility(True)

    def hide(self):
        if self.panel is None:
            return
        was_visible = self.visible
        for f in list(self._fields):
            if f.focus:
                f.focus = False
        self.panel.detach()
        if was_visible and self.on_visibility:
            self.on_visibility(False)


SERVICE = KeyboardService()
