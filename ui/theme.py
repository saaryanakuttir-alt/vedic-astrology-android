"""
theme.py — the "Classical" design system for the Android/Kivy app (from the
Birth Chart App design handoff, same tokens the web app now uses): a warm
parchment ground, ink text, ONE gold accent, hairline dividers, 4dp radii,
and colour used as STROKE - outlined buttons/cards/tags/inputs, never solid
fills. Everything is plain kivy.graphics primitives (no bundled images), so
it stays fully offline and adds nothing to the APK.

Fonts: the handoff names Cormorant Garamond / Lora, but this app bundles no
font files (and never downloads any), so it uses Kivy's built-in Roboto -
the layout, spacing and colour system carry the design.

IMPORTANT DESIGN NOTE - keep widgets BEHAVIORALLY stock. Every widget below
is a stock Kivy widget plus canvas drawing and a few property defaults; none
overrides on_touch_*/collide logic. (Debugging an earlier "typing and taps do
nothing on device" report, the previous themed widgets were desktop-tested
with synthetic touches and behaved correctly, so touch dispatch is left
entirely to Kivy here.)

The old module-level palette names (BG, PANEL, INK, GOLD, ...) are kept as
aliases mapped onto the new tokens, so tab modules that still reference them
pick up the new look without edits.
"""
import os

import kivy
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty
from kivy.utils import get_color_from_hex as hex_color

# ---- Classical tokens (design-system/styles.css) ----
BG = hex_color("#f3f2f2")
SURFACE = hex_color("#eae9e9")
TEXT = hex_color("#201f1d")
ACCENT = hex_color("#b68235")
ACCENT_100 = hex_color("#fff3e4")
ACCENT_600 = hex_color("#a06f24")
ACCENT_700 = hex_color("#7d5411")
ACCENT_800 = hex_color("#5a3b0a")
NEUTRAL_100 = hex_color("#f8f4f4")
NEUTRAL_500 = hex_color("#9b9797")
NEUTRAL_600 = hex_color("#7d7979")
NEUTRAL_800 = hex_color("#444141")


def _alpha(rgba, a):
    return (rgba[0], rgba[1], rgba[2], a)


DIVIDER = _alpha(TEXT, 0.16)          # color-mix(text 16%, transparent)
DIVIDER_SOLID = (0.855, 0.851, 0.847, 1)  # the same hairline pre-blended onto BG, for opaque table gaps
DIVIDER_HOVER = _alpha(TEXT, 0.45)
MUTED = _alpha(TEXT, 0.55)
INK = TEXT
INK_SOFT = _alpha(TEXT, 0.78)
PRESS_TINT = _alpha(ACCENT, 0.22)     # accent 22% while a primary button is held
HOVER_TINT = _alpha(ACCENT, 0.12)
PRESS_TINT_NEUTRAL = _alpha(TEXT, 0.14)

# ---- legacy aliases (kept so older modules keep working, now on-brand) ----
PANEL = SURFACE
PANEL_SOFT = SURFACE
INDIGO = ACCENT
INDIGO_2 = ACCENT
INDIGO_DEEP = ACCENT_700
INDIGO_PRESS = PRESS_TINT
GOLD = ACCENT
GOLD_PRESS = ACCENT_600
GOLD_SOFT = ACCENT_700                # text colour on parchment - dark enough to read
GOLD_TEXT = TEXT

R = dp(4)                             # --radius-md

# Kivy's default font (Roboto) has no arrows, check marks or backspace glyphs -
# they draw as empty boxes. DejaVu Sans ships with Kivy and has them all, so
# any label that shows such a symbol uses this font.
SYMBOL_FONT = os.path.join(kivy.kivy_data_dir, "fonts", "DejaVuSans.ttf")

# Default text colours: Kivy's Label/TextInput default to WHITE, which would
# vanish on parchment. One global rule fixes every Label in the app that
# doesn't pass its own colour; widgets that DO pass color= are unaffected.
# Popups get the parchment surface instead of Kivy's dark atlas image.
Builder.load_string(f"""
<Label>:
    color: {TEXT[0]}, {TEXT[1]}, {TEXT[2]}, 1
<Popup>:
    background: ''
    background_color: {SURFACE[0]}, {SURFACE[1]}, {SURFACE[2]}, 1
    title_color: {TEXT[0]}, {TEXT[1]}, {TEXT[2]}, 1
    separator_color: {ACCENT[0]}, {ACCENT[1]}, {ACCENT[2]}, 1
""")


# ---------------------------------------------------------------------------
# Backgrounds / structure
# ---------------------------------------------------------------------------
class GradientBackground(FloatLayout):
    """Name kept for compatibility. The Classical system is FLAT parchment -
    no gradient - so this now just paints the ground colour."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*BG)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class Divider(Widget):
    """A 1dp hairline (the design's .hr)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(1))
        super().__init__(**kwargs)
        with self.canvas:
            Color(*DIVIDER)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._r.pos = self.pos
        self._r.size = self.size


class SectionHeader(BoxLayout):
    """A compact in-tab title row: small accent kicker text over a hairline.
    (The big screen title now lives in the app header, so tabs that add a
    SectionHeader get a light, non-duplicating label rather than a banner.)"""

    def __init__(self, icon, title, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(30))
        kwargs.setdefault("padding", (dp(4), 0))
        super().__init__(orientation="vertical", **kwargs)
        lbl = Label(text=str(title).upper(), color=ACCENT, font_size="11sp", halign="left", valign="middle")
        lbl.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        self.add_widget(lbl)
        self.add_widget(Divider())


class OutlineBox(BoxLayout):
    """A transparent box with a hairline rounded outline - the design's
    .card. `accent=True` strokes it in gold instead of the divider colour."""

    def __init__(self, accent=False, **kwargs):
        super().__init__(**kwargs)
        self._accent = accent
        with self.canvas.after:
            self._c = Color(*(ACCENT if accent else DIVIDER))
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, R), width=1)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, R)

    def set_accent(self, on):
        self._c.rgba = ACCENT if on else DIVIDER


# ---------------------------------------------------------------------------
# Line icons (24x24 design grid, drawn with stroke only)
# ---------------------------------------------------------------------------
def _star_pts():
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = 9 if i % 2 == 0 else 4
        pts.append((12 + r * math.cos(ang), 12 + r * math.sin(ang)))
    return pts


def _icon_shapes():
    """name -> list of ('poly'|'open'|'circle', data) in 24x24 space."""
    return {
        "diamond": [("poly", [(12, 2), (22, 12), (12, 22), (2, 12)])],
        "grid": [("poly", [(3, 3), (21, 3), (21, 21), (3, 21)]), ("open", [(12, 3), (12, 21)]), ("open", [(3, 12), (21, 12)])],
        "house": [("open", [(3, 11), (12, 4), (21, 11)]), ("open", [(5, 10), (5, 20), (19, 20), (19, 10)])],
        "sign": [("circle", (12, 12, 9)), ("open", [(12, 3), (12, 6)]), ("open", [(12, 18), (12, 21)]),
                 ("open", [(3, 12), (6, 12)]), ("open", [(18, 12), (21, 12)])],
        "key": [("circle", (8, 15, 3.5)), ("open", [(10.5, 12.5), (19, 4)]), ("open", [(19, 4), (19, 8)]), ("open", [(19, 4), (15, 4)])],
        "rings": [("circle", (9, 12, 5.5)), ("circle", (15, 12, 5.5))],
        "clock": [("circle", (12, 12, 9)), ("open", [(12, 7), (12, 12), (15.5, 14)])],
        "book": [("poly", [(4, 4), (12, 4), (12, 20), (4, 20)]), ("poly", [(12, 4), (20, 4), (20, 20), (12, 20)])],
        "card": [("poly", [(3, 5), (21, 5), (21, 19), (3, 19)]), ("open", [(7, 10), (13, 10)]), ("open", [(7, 14), (17, 14)])],
        "calendar": [("poly", [(3, 5), (21, 5), (21, 21), (3, 21)]), ("open", [(3, 9), (21, 9)]), ("open", [(8, 3), (8, 7)]), ("open", [(16, 3), (16, 7)])],
        "infinity": [("circle", (8, 12, 3.8)), ("circle", (16, 12, 3.8))],
        "hourglass": [("open", [(6, 3), (18, 3)]), ("open", [(6, 21), (18, 21)]), ("open", [(7, 3), (12, 12), (7, 21)]), ("open", [(17, 3), (12, 12), (17, 21)])],
        "cross": [("circle", (12, 12, 9)), ("open", [(12, 8), (12, 16)]), ("open", [(8, 12), (16, 12)])],
        "heart": [("poly", [(12, 20), (4, 11), (5, 6), (9, 5), (12, 9), (15, 5), (19, 6), (20, 11)])],
        "warn": [("poly", [(12, 3), (22, 20), (2, 20)]), ("open", [(12, 10), (12, 14)])],
        "people": [("circle", (9, 8, 3)), ("open", [(3, 20), (4, 16), (9, 14.5), (14, 16), (15, 20)]), ("circle", (17, 9, 2.4))],
        "gem": [("poly", [(7, 4), (17, 4), (21, 9), (12, 20), (3, 9)]), ("open", [(3, 9), (21, 9)])],
        "star": [("poly", _star_pts())],
        "doc": [("poly", [(6, 3), (15, 3), (19, 7), (19, 21), (6, 21)]), ("open", [(9, 12), (16, 12)]), ("open", [(9, 16), (16, 16)])],
        "help": [("circle", (12, 12, 9)), ("open", [(9.5, 9.5), (10.5, 7.5), (13.5, 7.5), (14.5, 9.5), (12, 12), (12, 14)])],
    }


_ICONS = _icon_shapes()


class LineIcon(Widget):
    """A stroke-only icon from the design's 24x24 line-icon set, drawn with
    kivy.graphics Lines (no image assets). Colour is changeable via
    set_color() so nav items can tint active/inactive."""

    def __init__(self, name="diamond", color=None, size_dp=22, stroke=1.5, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(size_dp), dp(size_dp)))
        super().__init__(**kwargs)
        self.icon_name = name if name in _ICONS else "diamond"
        self.icon_color = color or ACCENT
        self._stroke = stroke
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def set_color(self, rgba):
        self.icon_color = rgba
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s <= 0:
            return
        ox = self.x + (self.width - s) / 2
        oy = self.y + (self.height - s) / 2
        k = s / 24.0

        def P(x, y):
            return ox + x * k, oy + (24 - y) * k

        w = max(1.0, self._stroke * k * 1.05)
        with self.canvas:
            Color(*self.icon_color)
            for kind, data in _ICONS[self.icon_name]:
                if kind == "circle":
                    cx, cy, r = data
                    Line(circle=(*P(cx, cy), r * k), width=w)
                else:
                    pts = []
                    for x, y in data:
                        pts.extend(P(x, y))
                    Line(points=pts, width=w, close=(kind == "poly"))


# ---------------------------------------------------------------------------
# Buttons - outlined, colour as stroke
# ---------------------------------------------------------------------------
class _OutlineMixin:
    """Shared stroke + press-tint drawing for every button-like widget. Pure
    canvas work bound to pos/size/state: touch handling is untouched."""

    def _init_outline(self, stroke, tint, radius=R):
        self._stroke_rgba = stroke
        self._tint_rgba = tint
        self._r = radius
        with self.canvas.before:
            self._tint_color = Color(0, 0, 0, 0)
            self._tint_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        with self.canvas.after:
            self._stroke_color = Color(*stroke)
            self._stroke_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, radius), width=1)
        self.bind(pos=self._sync_outline, size=self._sync_outline, state=self._sync_state,
                  disabled=self._sync_state)

    def _sync_outline(self, *_):
        self._tint_rect.pos = self.pos
        self._tint_rect.size = self.size
        self._stroke_line.rounded_rectangle = (self.x, self.y, self.width, self.height, self._r)

    def _sync_state(self, *_):
        down = self.state == "down" and not self.disabled
        self._tint_color.rgba = self._tint_rgba if down else (0, 0, 0, 0)
        self.opacity = 0.45 if self.disabled else 1


class ThemedButton(_OutlineMixin, Button):
    """variant: 'primary' (gold stroke + gold label), 'secondary' (hairline
    stroke, ink label), 'ghost' (no stroke, gold label). The old `gold=True`
    argument still works and means 'primary'; a plain ThemedButton(text=...)
    is 'secondary'."""

    def __init__(self, variant=None, gold=False, **kwargs):
        variant = variant or ("primary" if gold else "secondary")
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", "14sp")
        if variant == "primary":
            kwargs.setdefault("color", ACCENT)
            stroke, tint = ACCENT, PRESS_TINT
        elif variant == "ghost":
            kwargs.setdefault("color", ACCENT)
            stroke, tint = (0, 0, 0, 0), PRESS_TINT
        else:
            kwargs.setdefault("color", TEXT)
            stroke, tint = DIVIDER, PRESS_TINT_NEUTRAL
        super().__init__(**kwargs)
        self.variant = variant
        self._init_outline(stroke, tint)


class ThemedSpinnerOption(SpinnerOption):
    """Dropdown row: parchment surface, ink text, hairline separator."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", SURFACE)
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("bold", False)
        kwargs.setdefault("font_size", "14sp")
        super().__init__(**kwargs)
        with self.canvas.after:
            Color(*DIVIDER)
            self._sep = Rectangle(pos=(self.x, self.y), size=(self.width, dp(1)))
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._sep.pos = (self.x, self.y)
        self._sep.size = (self.width, dp(1))


class ThemedSpinner(_OutlineMixin, Spinner):
    """Dropdown styled as an outlined input (hairline stroke, ink text)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("bold", False)
        kwargs.setdefault("font_size", "14sp")
        kwargs.setdefault("option_cls", ThemedSpinnerOption)
        super().__init__(**kwargs)
        self._init_outline(DIVIDER, PRESS_TINT_NEUTRAL)


class ThemedTextInput(TextInput):
    """Transparent field with a hairline outline that turns gold on focus
    (the design's .input). Plain TextInput behaviour otherwise, plus two
    options for the built-in keyboard (ui/keyboard.py): kb_layout ("text",
    "number" = digits only, "decimal" = digits . -) and kb_autocap (capitalise
    the first letter of each word)."""

    def __init__(self, **kwargs):
        self.kb_layout = kwargs.pop("kb_layout", "text")
        self.kb_autocap = kwargs.pop("kb_autocap", True)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_disabled_normal", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("foreground_color", TEXT)
        kwargs.setdefault("disabled_foreground_color", MUTED)
        kwargs.setdefault("hint_text_color", MUTED)
        kwargs.setdefault("cursor_color", ACCENT)
        kwargs.setdefault("selection_color", _alpha(ACCENT, 0.30))
        kwargs.setdefault("font_size", "14sp")
        kwargs.setdefault("padding", (dp(10), dp(11), dp(10), dp(9)))
        super().__init__(**kwargs)
        with self.canvas.after:
            self._c = Color(*DIVIDER)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, R), width=1)
        self.bind(pos=self._sync, size=self._sync, focus=self._on_focus, disabled=self._on_focus)
        from ui import keyboard   # late import: keyboard.py itself imports this module
        keyboard.SERVICE.register(self)

    def _sync(self, *_):
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, R)

    def _on_focus(self, *_):
        self._c.rgba = _alpha(TEXT, 0.08) if self.disabled else (ACCENT if self.focus else DIVIDER)


class ThemedCheckBox(Button):
    """Outlined square toggle with a gold check when active. Same `active`
    BooleanProperty / bind(active=...) API as the stock CheckBox."""

    active = BooleanProperty(False)

    def __init__(self, active=False, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(36), dp(36)))
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("text", "")
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", "18sp")
        kwargs.setdefault("color", ACCENT)
        kwargs.setdefault("font_name", SYMBOL_FONT)     # the check mark is not in Roboto
        super().__init__(**kwargs)
        with self.canvas.after:
            self._c = Color(*DIVIDER)
            self._line = Line(rounded_rectangle=(self.x + dp(4), self.y + dp(4), self.width - dp(8), self.height - dp(8), R), width=1.2)
        self.bind(pos=self._sync, size=self._sync, on_release=self._toggle, active=self._apply, state=self._apply)
        self.active = active
        self._apply()

    def _sync(self, *_):
        self._line.rounded_rectangle = (self.x + dp(4), self.y + dp(4), self.width - dp(8), self.height - dp(8), R)

    def _toggle(self, *_):
        self.active = not self.active

    def _apply(self, *_):
        self._c.rgba = ACCENT if (self.active or self.state == "down") else DIVIDER
        self.text = "✓" if self.active else ""


class SegmentedControl(BoxLayout):
    """The design's .seg: a bordered row of options, the selected one gold.
    SegmentedControl(["Known","Unknown"], selected="Known", on_select=fn)"""

    def __init__(self, options, selected=None, on_select=None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("height", dp(38))
        super().__init__(orientation="horizontal", **kwargs)
        self.options = list(options)
        self.on_select = on_select
        self.selected = selected or self.options[0]
        self._buttons = {}
        for opt in self.options:
            b = Button(text=opt, background_normal="", background_down="", background_color=(0, 0, 0, 0),
                       font_size="13sp", size_hint_x=None, width=dp(104))
            b.bind(on_release=lambda inst, o=opt: self.select(o))
            self._buttons[opt] = b
            self.add_widget(b)
        self.width = dp(104) * len(self.options)
        with self.canvas.after:
            Color(*DIVIDER)
            self._frame = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, R), width=1)
            self._sel_color = Color(*ACCENT)
            self._sel_line = Line(rounded_rectangle=(self.x, self.y, dp(104), self.height, R), width=1.2)
        self.bind(pos=self._sync, size=self._sync)
        self._apply()

    def _sync(self, *_):
        self._frame.rounded_rectangle = (self.x, self.y, self.width, self.height, R)
        self._apply()

    def select(self, opt, notify=True):
        if opt == self.selected and notify is False:
            return
        self.selected = opt
        self._apply()
        if notify and self.on_select:
            self.on_select(opt)

    def _apply(self):
        for opt, b in self._buttons.items():
            b.color = ACCENT if opt == self.selected else TEXT
        if self.selected in self.options:
            i = self.options.index(self.selected)
            w = self.width / max(1, len(self.options))
            self._sel_line.rounded_rectangle = (self.x + i * w, self.y, w, self.height, R)


# ---------------------------------------------------------------------------
# Home cards, header and bottom navigation
# ---------------------------------------------------------------------------
class HomeCard(ButtonBehavior, OutlineBox):
    """One tappable Home menu card: line icon, title, one-line description,
    hairline outline (never filled). Turns gold-stroked while pressed."""

    def __init__(self, icon, title, desc, on_press_cb=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(108))
        kwargs.setdefault("padding", dp(12))
        kwargs.setdefault("spacing", dp(4))
        super().__init__(orientation="vertical", **kwargs)
        self.add_widget(LineIcon(icon, size_dp=20))
        t = Label(text=title, bold=True, font_size="14sp", halign="left", valign="middle", size_hint_y=None, height=dp(34))
        t.bind(size=lambda inst, sz: setattr(inst, "text_size", (sz[0], sz[1])))
        d = Label(text=desc, font_size="11.5sp", color=_alpha(TEXT, 0.72), halign="left", valign="top")
        d.bind(size=lambda inst, sz: setattr(inst, "text_size", (sz[0], sz[1])))
        self.add_widget(t)
        self.add_widget(d)
        if on_press_cb:
            self.bind(on_release=lambda *_: on_press_cb())
        self.bind(state=lambda inst, st: inst.set_accent(st == "down"))


class _NavItem(ButtonBehavior, BoxLayout):
    def __init__(self, icon, label, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(7), 0, dp(6)), spacing=dp(2), **kwargs)
        self.icon = LineIcon(icon, color=NEUTRAL_600, size_dp=21, stroke=1.5)
        holder = BoxLayout()
        holder.add_widget(Widget())
        holder.add_widget(self.icon)
        holder.add_widget(Widget())
        self.label = Label(text=label, font_size="10.5sp", color=NEUTRAL_600, size_hint_y=None, height=dp(14))
        self.add_widget(holder)
        self.add_widget(self.label)

    def set_active(self, on):
        c = ACCENT if on else NEUTRAL_600
        self.icon.set_color(c)
        self.label.color = c


class BottomNav(BoxLayout):
    """The design's 4-tab bar (Chart / Dasha / Yogas / Library), 21dp line
    icons, active tab gold, inactive neutral gray, hairline on top."""

    def __init__(self, items, on_select, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(58))
        super().__init__(orientation="horizontal", **kwargs)
        self._items = {}
        for key, label, icon in items:
            it = _NavItem(icon, label)
            it.bind(on_release=lambda inst, k=key: on_select(k))
            self._items[key] = it
            self.add_widget(it)
        with self.canvas.after:
            Color(*DIVIDER)
            self._top = Rectangle(pos=(self.x, self.top - dp(1)), size=(self.width, dp(1)))
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._top.pos = (self.x, self.top - dp(1))
        self._top.size = (self.width, dp(1))

    def set_active(self, key):
        for k, it in self._items.items():
            it.set_active(k == key)


class AppHeader(BoxLayout):
    """The design's .nav: the gold diamond mark (always returns Home) and the
    current screen title."""

    def __init__(self, on_home, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(54))
        kwargs.setdefault("padding", (dp(16), dp(8), dp(16), dp(6)))
        kwargs.setdefault("spacing", dp(12))
        super().__init__(orientation="horizontal", **kwargs)
        mark = ButtonBehaviorBox(on_home)
        self.add_widget(mark)
        self.title_label = Label(text="Home", bold=True, font_size="19sp", halign="left", valign="middle")
        self.title_label.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        self.add_widget(self.title_label)

    def set_title(self, text):
        self.title_label.text = text


class ButtonBehaviorBox(ButtonBehavior, BoxLayout):
    """A generous 40dp tap target around the header's 18dp diamond mark."""

    def __init__(self, cb, **kwargs):
        kwargs.setdefault("size_hint", (None, 1))
        kwargs.setdefault("width", dp(40))
        super().__init__(orientation="vertical", **kwargs)
        row = BoxLayout()
        row.add_widget(Widget())
        row.add_widget(LineIcon("diamond", size_dp=20, stroke=1.6))
        row.add_widget(Widget())
        self.add_widget(row)
        self.bind(on_release=lambda *_: cb())
