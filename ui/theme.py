"""
theme.py - the design system of the Android/Kivy app (v2.3 "Dusk & Ivory" redesign; v2.2 introduced Light/Dark).

Two palettes share one set of widgets:
  * "dark"  - Midnight Dusk: a deep blue-black sky with two soft aurora glows and faint stars, a saffron accent
              and a teal second accent, filled rounded cards.
  * "light" - Ivory: a warm manuscript-ivory ground with a faint mandala, white cards, deep ink text and a
              vermilion-saffron accent.
English headings use a serif display face (fonts/DMSerifDisplay-Regular.ttf, SIL OFL); other languages keep
their own bundled font, which has their pre-shaped letters (see display_font()).

Motion (v2.3): animate_in() fades a widget in while sliding it up a few dp (screens, cards), stagger() does it to
a row of widgets one after another, and the bottom bar's highlight glides between tabs. All of it is canvas-only
(a temporary PushMatrix/Translate pair, removed when the animation ends) and is switched off by set_motion(False)
(Home > Motion, remembered in settings.json as "motion").

apply(name) swaps the palette. Colours are plain module attributes (theme.ACCENT, theme.SURFACE ...) that every
screen reads while it builds its widgets, so switching the theme = apply() + rebuild the widget tree (main.py
set_theme does that, exactly like a language switch). Nothing keeps a colour from an earlier palette.

Everything is drawn with kivy.graphics primitives - gradients are tiny textures filled in code - so the app stays
fully offline and ships no image files.

IMPORTANT DESIGN NOTE - keep widgets BEHAVIORALLY stock. Every widget below is a stock Kivy widget plus canvas
drawing and a few property defaults; none overrides on_touch_*/collide logic. (An earlier "typing and taps do
nothing on device" report was traced away from the themed widgets; touch dispatch is left entirely to Kivy.)

The old palette names (BG, PANEL, INK, GOLD, ...) are kept as aliases, so every screen picks up the new look.
"""
import math
import os

import kivy
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, InstructionGroup, Line, PopMatrix, PushMatrix, Rectangle, RoundedRectangle, Translate
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.utils import get_color_from_hex as hex_color


def _alpha(rgba, a):
    return (rgba[0], rgba[1], rgba[2], a)


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
PALETTES = {
    "dark": {
        "BG": "#070b17", "BG_TOP": "#111a3c", "SURFACE": "#121a33", "SURFACE_2": "#1c2649",
        "TEXT": "#eef0fa", "ACCENT": "#f6a04d", "ACCENT_100": "#2a2338", "ACCENT_600": "#e08a36",
        "ACCENT_700": "#f8b56f", "ACCENT_800": "#fbd2a6", "ON_ACCENT": "#1a1206", "SECOND": "#5fd3c6",
        "NEUTRAL_100": "#151d3a", "NEUTRAL_500": "#6f7899", "NEUTRAL_600": "#949cba", "NEUTRAL_800": "#c6cbe0",
        "DIVIDER_SOLID": "#26305a", "HERO_A": "#e0773a", "HERO_B": "#34237a", "HERO_TEXT": "#ffffff",
        "SHADOW": (0, 0, 0, 0.50), "STARS": True, "GOLD_SOFT": "#f3d9b8",
        "GLOW_A": "#3d5bdb", "GLOW_B": "#14b8a6", "GLOW_ALPHA": (0.26, 0.14), "MANDALA": False,
        "GOOD": "#4ade80", "WARN": "#fbbf24", "BAD": "#f87171", "INFO": "#7dd3fc",
    },
    "light": {
        "BG": "#f7f3ea", "BG_TOP": "#fcefdc", "SURFACE": "#ffffff", "SURFACE_2": "#f4ede1",
        "TEXT": "#1c2033", "ACCENT": "#c2552a", "ACCENT_100": "#fbe7da", "ACCENT_600": "#a94820",
        "ACCENT_700": "#a8461f", "ACCENT_800": "#7d3417", "ON_ACCENT": "#ffffff", "SECOND": "#3a4aa8",
        "NEUTRAL_100": "#f5f0e6", "NEUTRAL_500": "#a39d90", "NEUTRAL_600": "#6d6878", "NEUTRAL_800": "#3b3a4a",
        "DIVIDER_SOLID": "#e9e1d3", "HERO_A": "#e0773a", "HERO_B": "#7a3b8f", "HERO_TEXT": "#ffffff",
        "SHADOW": (0.35, 0.22, 0.10, 0.10), "STARS": False, "GOLD_SOFT": "#7a5a2e",
        "GLOW_A": "#f5b97a", "GLOW_B": "#d9a1c7", "GLOW_ALPHA": (0.40, 0.28), "MANDALA": True,
        "GOOD": "#15803d", "WARN": "#b45309", "BAD": "#b91c1c", "INFO": "#1d4ed8",
    },
}
THEMES = ("dark", "light")
DEFAULT_THEME = "dark"
NAME = DEFAULT_THEME

R = dp(12)            # inputs, buttons with text inside a card
R_CARD = dp(20)       # cards
DISPLAY_FONT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts",
                                 "DMSerifDisplay-Regular.ttf")
MOTION = True         # set_motion(); Home > Motion
SYMBOL_FONT = os.path.join(kivy.kivy_data_dir, "fonts", "DejaVuSans.ttf")   # Roboto lacks arrows / check marks
_RULES_FILE = "vedic_theme_rules.kv"
_texture_cache = {}


def apply(name, window=True):
    """Make `name` ("dark"/"light") the current palette. Widgets built afterwards use it. window=False skips
    Window.clearcolor (the import-time call must not create the Window before main.py has set its Config)."""
    global NAME, IS_DARK, DIVIDER, DIVIDER_HOVER, MUTED, INK, INK_SOFT, PRESS_TINT, HOVER_TINT, PRESS_TINT_NEUTRAL
    global ACCENT_TINT, PANEL, PANEL_SOFT, INDIGO, INDIGO_2, INDIGO_DEEP, INDIGO_PRESS, GOLD, GOLD_PRESS, GOLD_TEXT
    global SECOND_TINT
    name = name if name in PALETTES else DEFAULT_THEME
    NAME = name
    IS_DARK = name == "dark"
    g = globals()
    for key, value in PALETTES[name].items():
        g[key] = hex_color(value) if isinstance(value, str) else value
    text = g["TEXT"]
    DIVIDER = _alpha(text, 0.12)
    DIVIDER_HOVER = _alpha(text, 0.40)
    MUTED = _alpha(text, 0.60)
    INK = text
    INK_SOFT = _alpha(text, 0.80)
    PRESS_TINT = _alpha(g["ACCENT"], 0.24)
    HOVER_TINT = _alpha(g["ACCENT"], 0.12)
    PRESS_TINT_NEUTRAL = _alpha(text, 0.10)
    ACCENT_TINT = _alpha(g["ACCENT"], 0.16)
    SECOND_TINT = _alpha(g["SECOND"], 0.14)
    # legacy aliases
    PANEL = PANEL_SOFT = g["SURFACE"]
    INDIGO = INDIGO_2 = GOLD = g["ACCENT"]
    INDIGO_DEEP = g["ACCENT_700"]
    INDIGO_PRESS = PRESS_TINT
    GOLD_PRESS = g["ACCENT_600"]
    GOLD_TEXT = text
    _load_rules()
    if not window:
        return name
    try:
        from kivy.core.window import Window
        Window.clearcolor = g["BG"]
    except Exception:            # no window (tests that only import the palette)
        pass
    return name


def other(name=None):
    """The theme a toggle switches to."""
    return "light" if (name or NAME) == "dark" else "dark"


def _load_rules():
    """Defaults for stock widgets: label ink, popup surface, scroll bar."""
    Builder.unload_file(_RULES_FILE)
    t, s, a = TEXT, SURFACE, ACCENT
    Builder.load_string(f"""
<Label>:
    color: {t[0]}, {t[1]}, {t[2]}, 1
<Popup>:
    background: ''
    background_color: {s[0]}, {s[1]}, {s[2]}, 1
    title_color: {t[0]}, {t[1]}, {t[2]}, 1
    title_size: '16sp'
    separator_color: {a[0]}, {a[1]}, {a[2]}, 1
<ScrollView>:
    bar_color: {a[0]}, {a[1]}, {a[2]}, 0.55
    bar_inactive_color: {t[0]}, {t[1]}, {t[2]}, 0.15
""", filename=_RULES_FILE)


def display_font():
    """The heading font: the serif display face in English, else the language's own default font (Bengali and
    Hindi need their pre-shaped glyph fonts, which the display face does not have)."""
    try:
        import i18n
        english = i18n.is_english()
    except Exception:          # engine/ not on the path (palette-only tests)
        english = True
    return DISPLAY_FONT_FILE if english and os.path.exists(DISPLAY_FONT_FILE) else "Roboto"


def radial_texture(n=64):
    """An n x n white texture whose alpha falls from 1 at the centre to 0 at the edge (soft glows)."""
    key = ("radial", n)
    tex = _texture_cache.get(key)
    if tex is None:
        tex = Texture.create(size=(n, n), colorfmt="rgba")
        buf = bytearray()
        c = (n - 1) / 2.0
        for y in range(n):
            for x in range(n):
                d = min(1.0, math.hypot(x - c, y - c) / c)
                a = (1.0 - d) ** 2
                buf += bytes((255, 255, 255, int(255 * a)))
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.wrap = "clamp_to_edge"
        _texture_cache[key] = tex
    return tex


def gradient_texture(c_from, c_to, horizontal=False, n=64):
    """A 1 x n (or n x 1) texture fading from c_from (bottom / left) to c_to (top / right)."""
    key = (tuple(c_from), tuple(c_to), horizontal, n)
    tex = _texture_cache.get(key)
    if tex is None:
        tex = Texture.create(size=(n, 1) if horizontal else (1, n), colorfmt="rgba")
        buf = bytearray()
        for i in range(n):
            f = i / (n - 1)
            buf += bytes(int(255 * max(0.0, min(1.0, a + (b - a) * f))) for a, b in zip(c_from, c_to))
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.wrap = "clamp_to_edge"
        _texture_cache[key] = tex
    return tex


apply(DEFAULT_THEME, window=False)


# ---------------------------------------------------------------------------
# Backgrounds / structure
# ---------------------------------------------------------------------------
def _stars(count=70, seed=7):
    """Deterministic star field: (x, y, radius_dp, alpha) with x, y as fractions of the area."""
    out, s = [], seed
    for _ in range(count):
        vals = []
        for _k in range(4):
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            vals.append(s / 0x7FFFFFFF)
        out.append((vals[0], vals[1], 0.6 + vals[2] * 1.2, 0.18 + vals[3] * 0.55))
    return out


class GradientBackground(FloatLayout):
    """The app ground: a vertical gradient (BG at the bottom -> BG_TOP at the top) with two soft colour glows; a
    faint star field in the dark theme and a faint mandala in the light one."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._star_items = []
        self._mandala = []
        a1, a2 = GLOW_ALPHA
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size, texture=gradient_texture(BG, BG_TOP))
            Color(*_alpha(GLOW_A, a1))
            self._glow_a = Rectangle(texture=radial_texture())
            Color(*_alpha(GLOW_B, a2))
            self._glow_b = Rectangle(texture=radial_texture())
            if STARS:
                for x, y, r, a in _stars():
                    Color(1, 1, 1, a)
                    self._star_items.append((x, y, dp(r), Ellipse(size=(dp(r) * 2, dp(r) * 2))))
            if MANDALA:
                Color(*_alpha(ACCENT, 0.07))
                self._mandala = [Line(width=1) for _ in range(4)]
                self._spokes = [Line(width=1) for _ in range(24)]
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        w, h = self.width, self.height
        ga = max(w, h) * 0.95
        gb = max(w, h) * 0.75
        if IS_DARK:
            self._glow_a.pos, self._glow_a.size = (self.x - ga * 0.45, self.y + h - ga * 0.55), (ga, ga)
            self._glow_b.pos, self._glow_b.size = (self.x + w - gb * 0.45, self.y + h * 0.35 - gb / 2), (gb, gb)
        else:
            self._glow_a.pos, self._glow_a.size = (self.x + w - ga * 0.55, self.y + h - ga * 0.50), (ga, ga)
            self._glow_b.pos, self._glow_b.size = (self.x - gb * 0.50, self.y - gb * 0.35), (gb, gb)
        for x, y, r, e in self._star_items:
            e.pos = (self.x + x * self.width - r, self.y + y * self.height - r)
        if self._mandala:
            cx, cy = self.x + w - dp(40), self.y + h - dp(60)
            for i, ring in enumerate(self._mandala):
                ring.circle = (cx, cy, dp(70) + i * dp(46))
            for k, spoke in enumerate(self._spokes):
                ang = k * math.pi / 12
                inner, outer = (dp(70), dp(208)) if k % 2 == 0 else (dp(116), dp(208))
                spoke.points = [cx + inner * math.cos(ang), cy + inner * math.sin(ang),
                                cx + outer * math.cos(ang), cy + outer * math.sin(ang)]


class Divider(Widget):
    """A 1dp hairline."""

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
    """A compact in-tab title: a short accent bar and small bold caps."""

    def __init__(self, icon, title, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(32))
        kwargs.setdefault("padding", (dp(4), dp(6), 0, dp(2)))
        kwargs.setdefault("spacing", dp(8))
        super().__init__(orientation="horizontal", **kwargs)
        bar = Widget(size_hint_x=None, width=dp(4))
        with bar.canvas:
            Color(*ACCENT)
            rr = RoundedRectangle(radius=[dp(2)])
        bar.bind(pos=lambda w, _v: setattr(rr, "pos", (w.x, w.y + dp(4))),
                 size=lambda w, _v: setattr(rr, "size", (w.width, max(0, w.height - dp(8)))))
        self.add_widget(bar)
        lbl = Label(text=str(title).upper(), color=ACCENT_700, bold=True, font_size="11.5sp", halign="left", valign="middle")
        lbl.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        self.add_widget(lbl)


class _CardDraw:
    """Filled rounded card drawing (soft shadow + fill + optional stroke) bound to pos/size. Canvas only."""

    def _init_card(self, fill, stroke=None, radius=R_CARD, shadow=True):
        self._card_radius = radius
        self._card_shadow = shadow
        with self.canvas.before:
            self._shadow_color = Color(*(SHADOW if shadow else (0, 0, 0, 0)))
            self._shadow_rect = RoundedRectangle(radius=[radius])
            self._fill_color = Color(*fill)
            self._fill_rect = RoundedRectangle(radius=[radius])
        with self.canvas.after:
            self._stroke_color = Color(*(stroke or (0, 0, 0, 0)))
            self._stroke_line = Line(width=1.1)
        self.bind(pos=self._sync_card, size=self._sync_card)
        self._sync_card()

    def _sync_card(self, *_):
        r = min(self._card_radius, self.height / 2, self.width / 2) if self.height and self.width else self._card_radius
        self._shadow_rect.pos = (self.x, self.y - dp(2))
        self._shadow_rect.size = self.size
        self._shadow_rect.radius = [r]
        self._fill_rect.pos = self.pos
        self._fill_rect.size = self.size
        self._fill_rect.radius = [r]
        self._stroke_line.rounded_rectangle = (self.x, self.y, self.width, self.height, r)


class OutlineBox(_CardDraw, BoxLayout):
    """A card. Default: filled surface with a soft shadow and a faint edge. accent=True: a small accent-tinted pill
    (used for tags). set_accent(True) shows the pressed state."""

    def __init__(self, accent=False, **kwargs):
        super().__init__(**kwargs)
        self._accent = accent
        if accent:
            self._init_card(ACCENT_TINT, None, radius=dp(14), shadow=False)
        else:
            self._init_card(SURFACE, _alpha(TEXT, 0.06), radius=R_CARD, shadow=True)

    def set_accent(self, on):
        if self._accent:
            self._fill_color.rgba = PRESS_TINT if on else ACCENT_TINT
        else:
            self._fill_color.rgba = SURFACE_2 if on else SURFACE
            self._stroke_color.rgba = _alpha(ACCENT, 0.7) if on else _alpha(TEXT, 0.06)


class HeroCard(BoxLayout):
    """A dusk-gradient card (HERO_B -> HERO_A) with a soft sun glow, two orbit rings and a faint constellation at
    its right edge."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*SHADOW)
            self._sh = RoundedRectangle(radius=[dp(22)])
            Color(1, 1, 1, 1)
            self._bg = RoundedRectangle(radius=[dp(22)], texture=gradient_texture(HERO_B, HERO_A, horizontal=True))
            Color(1, 0.92, 0.75, 0.30)
            self._sun = Rectangle(texture=radial_texture())
            Color(1, 1, 1, 0.20)
            self._orbit = Line(width=1.1)
            self._orbit2 = Line(width=1)
            Color(1, 1, 1, 0.55)
            self._dots = [Ellipse(size=(dp(4), dp(4))) for _ in range(5)]
            self._lines = Line(width=1)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._sh.pos, self._sh.size = (self.x, self.y - dp(3)), self.size
        self._bg.pos, self._bg.size = self.pos, self.size
        # x/y/width/height, not right/top: those cached aliases can still be stale inside a size callback
        cx, cy = self.x + self.width - dp(46), self.y + self.height - dp(40)
        g = dp(190)
        self._sun.pos, self._sun.size = (cx - g / 2, cy - g / 2), (g, g)
        self._orbit.circle = (cx, cy, dp(58))
        self._orbit2.circle = (cx, cy, dp(30))
        pts = [(cx - dp(40), cy - dp(4)), (cx - dp(16), cy + dp(18)), (cx + dp(8), cy + dp(6)),
               (cx + dp(24), cy + dp(24)), (cx + dp(14), cy - dp(22))]
        for e, (x, y) in zip(self._dots, pts):
            e.pos = (x - dp(2), y - dp(2))
        self._lines.points = [v for p in pts for v in p]


# ---------------------------------------------------------------------------
# Line icons (24x24 design grid, drawn with stroke only)
# ---------------------------------------------------------------------------
def _star_pts():
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = 9 if i % 2 == 0 else 4
        pts.append((12 + r * math.cos(ang), 12 + r * math.sin(ang)))
    return pts


def _crescent_pts():
    """A crescent moon: the part of one circle outside a second, offset circle."""
    cx, cy, rr = 12, 12, 8.5
    ix, iy, ir = 16.5, 8.5, 7.5
    ring = [(cx + rr * math.cos(math.radians(d)), cy + rr * math.sin(math.radians(d))) for d in range(0, 360, 6)]
    keep = [math.hypot(x - ix, y - iy) > ir for x, y in ring]
    n = len(ring)
    start = next(i for i in range(n) if keep[i] and not keep[i - 1])
    arc, i = [], start
    while keep[i % n] and len(arc) < n:
        arc.append(ring[i % n])
        i += 1
    # back along the inner circle, from the end of the outer arc to its start
    a0 = math.atan2(arc[-1][1] - iy, arc[-1][0] - ix)
    a1 = math.atan2(arc[0][1] - iy, arc[0][0] - ix)
    best = None
    for direction in (1, -1):
        span = (a1 - a0) % (2 * math.pi) if direction == 1 else -((a0 - a1) % (2 * math.pi))
        pts = [(ix + ir * math.cos(a0 + span * k / 12), iy + ir * math.sin(a0 + span * k / 12)) for k in range(1, 12)]
        inside = sum(math.hypot(x - cx, y - cy) < rr for x, y in pts)
        if best is None or inside > best[0]:
            best = (inside, pts)
    return arc + best[1]


def _sun_shapes():
    shapes = [("circle", (12, 12, 4.2))]
    for k in range(8):
        a = k * math.pi / 4
        shapes.append(("open", [(12 + 6.8 * math.cos(a), 12 + 6.8 * math.sin(a)),
                                (12 + 9.4 * math.cos(a), 12 + 9.4 * math.sin(a))]))
    return shapes


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
        "sun": _sun_shapes(),
        "moon": [("poly", _crescent_pts())],
        "chevron": [("open", [(9, 5), (16, 12), (9, 19)])],
        "chevron_down": [("open", [(6, 9), (12, 15), (18, 9)])],
    }


_ICONS = _icon_shapes()


class LineIcon(Widget):
    """A stroke-only icon from the 24x24 line-icon set, drawn with kivy.graphics Lines (no image assets).
    set_color() retints it (nav items, pressed states)."""

    def __init__(self, name="diamond", color=None, size_dp=22, stroke=1.6, **kwargs):
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

    def set_icon(self, name):
        self.icon_name = name if name in _ICONS else "diamond"
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
                    Line(points=pts, width=w, close=(kind == "poly"), joint="round", cap="round")


class IconChip(Widget):
    """A round tinted chip with a line icon centred in it (Home cards, header buttons)."""

    def __init__(self, icon, size_dp=40, icon_dp=20, fill=None, color=None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(size_dp), dp(size_dp)))
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fill_color = Color(*(fill or ACCENT_TINT))
            self._disc = Ellipse()
        self.icon = LineIcon(icon, color=color or ACCENT_700, size_dp=icon_dp)
        self.add_widget(self.icon)
        self.bind(pos=self._sync, size=self._sync)
        self._sync()

    def _sync(self, *_):
        self._disc.pos, self._disc.size = self.pos, self.size
        self.icon.pos = (self.x + (self.width - self.icon.width) / 2, self.y + (self.height - self.icon.height) / 2)

    def set_fill(self, rgba):
        self._fill_color.rgba = rgba


# ---------------------------------------------------------------------------
# Buttons - filled pills
# ---------------------------------------------------------------------------
class _OutlineMixin:
    """Shared fill + stroke + pressed-state drawing for every button-like widget (the name is historical).
    Pure canvas work bound to pos/size/state: touch handling is untouched."""

    def _init_outline(self, stroke, tint, radius=R, fill=(0, 0, 0, 0), fill_down=None):
        self._stroke_rgba = stroke
        self._tint_rgba = tint
        self._fill_rgba = fill
        self._fill_down_rgba = fill_down
        self._r = radius
        with self.canvas.before:
            self._fill_color = Color(*fill)
            self._fill_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            self._tint_color = Color(0, 0, 0, 0)
            self._tint_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        with self.canvas.after:
            self._stroke_color = Color(*stroke)
            self._stroke_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, radius), width=1.1)
        self.bind(pos=self._sync_outline, size=self._sync_outline, state=self._sync_state,
                  disabled=self._sync_state)

    def _radius(self):
        return min(self._r, self.height / 2) if self.height > 0 else self._r

    def _sync_outline(self, *_):
        r = self._radius()
        for rect in (self._fill_rect, self._tint_rect):
            rect.pos = self.pos
            rect.size = self.size
            rect.radius = [r]
        self._stroke_line.rounded_rectangle = (self.x, self.y, self.width, self.height, r)

    def _sync_state(self, *_):
        down = self.state == "down" and not self.disabled
        if self._fill_down_rgba is not None:
            self._fill_color.rgba = self._fill_down_rgba if down else self._fill_rgba
        else:
            self._tint_color.rgba = self._tint_rgba if down else (0, 0, 0, 0)
        self.opacity = 0.45 if self.disabled else 1


class ThemedButton(_OutlineMixin, Button):
    """variant: 'primary' (filled accent pill), 'secondary' (tonal pill), 'ghost' (text only). The old `gold=True`
    argument still works and means 'primary'; a plain ThemedButton(text=...) is 'secondary'."""

    def __init__(self, variant=None, gold=False, **kwargs):
        variant = variant or ("primary" if gold else "secondary")
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", "14sp")
        if variant == "primary":
            kwargs.setdefault("color", ON_ACCENT)
            fill, fill_down, stroke = ACCENT, ACCENT_600, (0, 0, 0, 0)
        elif variant == "ghost":
            kwargs.setdefault("color", ACCENT_700)
            fill, fill_down, stroke = (0, 0, 0, 0), None, (0, 0, 0, 0)
        else:
            kwargs.setdefault("color", TEXT)
            fill, fill_down, stroke = SURFACE_2, None, _alpha(TEXT, 0.06)
        super().__init__(**kwargs)
        self.variant = variant
        self._init_outline(stroke, PRESS_TINT if variant != "secondary" else PRESS_TINT_NEUTRAL,
                           radius=dp(24), fill=fill, fill_down=fill_down)


class ThemedSpinnerOption(SpinnerOption):
    """Dropdown row: surface, ink text, hairline separator."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", SURFACE_2 if IS_DARK else SURFACE)
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("bold", False)
        kwargs.setdefault("font_size", "14sp")
        kwargs.setdefault("height", dp(46))
        super().__init__(**kwargs)
        with self.canvas.after:
            Color(*DIVIDER)
            self._sep = Rectangle(pos=(self.x, self.y), size=(self.width, dp(1)))
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._sep.pos = (self.x, self.y)
        self._sep.size = (self.width, dp(1))


class ThemedSpinner(_OutlineMixin, Spinner):
    """Dropdown styled as a filled input with a chevron at its right edge."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("bold", False)
        kwargs.setdefault("font_size", "14sp")
        kwargs.setdefault("option_cls", ThemedSpinnerOption)
        super().__init__(**kwargs)
        self._init_outline(DIVIDER, PRESS_TINT_NEUTRAL, radius=R, fill=SURFACE)
        with self.canvas.after:
            Color(*MUTED)
            self._chev = Line(width=1.3, cap="round", joint="round")
        self.bind(pos=self._sync_chev, size=self._sync_chev)

    def _sync_chev(self, *_):
        if self.width < dp(70):
            self._chev.points = []
            return
        x, y = self.x + self.width - dp(16), self.y + self.height / 2
        self._chev.points = [x - dp(4), y + dp(2), x, y - dp(2), x + dp(4), y + dp(2)]


class ThemedTextInput(TextInput):
    """Filled rounded field whose edge turns accent on focus. Plain TextInput behaviour otherwise, plus two options
    for the built-in keyboard (ui/keyboard.py): kb_layout ("text", "number" = digits only, "decimal" = digits . -)
    and kb_autocap (capitalise the first letter of each word)."""

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
        kwargs.setdefault("padding", (dp(14), dp(12), dp(14), dp(10)))
        super().__init__(**kwargs)
        # TextInput draws its own text in canvas.before, so the fill must go FIRST in that list (appending it
        # would paint over the typed text)
        fill = InstructionGroup()
        self._fill = Color(*SURFACE)
        self._box = RoundedRectangle(pos=self.pos, size=self.size, radius=[R])
        fill.add(self._fill)
        fill.add(self._box)
        self.canvas.before.insert(0, fill)
        with self.canvas.after:
            self._c = Color(*DIVIDER)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, R), width=1.1)
        self.bind(pos=self._sync, size=self._sync, focus=self._on_focus, disabled=self._on_focus)
        from ui import keyboard   # late import: keyboard.py itself imports this module
        keyboard.SERVICE.register(self)

    def _sync(self, *_):
        self._box.pos, self._box.size = self.pos, self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, R)

    def _on_focus(self, *_):
        self._c.rgba = _alpha(TEXT, 0.05) if self.disabled else (ACCENT if self.focus else DIVIDER)
        self._line.width = 1.5 if self.focus else 1.1


class ThemedCheckBox(Button):
    """Rounded square toggle: filled accent with a check when active. Same `active` BooleanProperty /
    bind(active=...) API as the stock CheckBox."""

    active = BooleanProperty(False)

    def __init__(self, active=False, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(36), dp(36)))
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("text", "")
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", "16sp")
        kwargs.setdefault("color", ON_ACCENT)
        kwargs.setdefault("font_name", SYMBOL_FONT)     # the check mark is not in Roboto
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fc = Color(0, 0, 0, 0)
            self._box = RoundedRectangle(radius=[dp(7)])
        with self.canvas.after:
            self._c = Color(*NEUTRAL_500)
            self._line = Line(width=1.4)
        self.bind(pos=self._sync, size=self._sync, on_release=self._toggle, active=self._apply, state=self._apply)
        self.active = active
        self._sync()
        self._apply()

    def _sync(self, *_):
        x, y, w, h = self.x + dp(6), self.y + dp(6), self.width - dp(12), self.height - dp(12)
        self._box.pos, self._box.size = (x, y), (w, h)
        self._line.rounded_rectangle = (x, y, w, h, dp(7))

    def _toggle(self, *_):
        self.active = not self.active

    def _apply(self, *_):
        on = self.active
        self._fc.rgba = ACCENT if on else ((0, 0, 0, 0) if self.state != "down" else PRESS_TINT)
        self._c.rgba = ACCENT if (on or self.state == "down") else NEUTRAL_500
        self.text = "✓" if on else ""


class SegmentedControl(BoxLayout):
    """A pill-shaped switch: a tonal track with the selected option on a filled accent thumb.
    SegmentedControl(["Known","Unknown"], selected="Known", on_select=fn)"""

    def __init__(self, options, selected=None, on_select=None, item_width=None, **kwargs):
        item_width = item_width or dp(104)
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("height", dp(40))
        super().__init__(orientation="horizontal", **kwargs)
        self.options = list(options)
        self.on_select = on_select
        self.selected = selected or self.options[0]
        self._buttons = {}
        with self.canvas.before:
            Color(*SURFACE_2)
            self._track = RoundedRectangle(radius=[dp(20)])
            Color(*ACCENT)
            self._thumb = RoundedRectangle(radius=[dp(17)])
        for opt in self.options:
            b = Button(text=opt, background_normal="", background_down="", background_color=(0, 0, 0, 0),
                       font_size="13sp", size_hint_x=None, width=item_width)
            b.bind(on_release=lambda inst, o=opt: self.select(o))
            self._buttons[opt] = b
            self.add_widget(b)
        self.width = item_width * len(self.options)
        self.bind(pos=self._sync, size=self._sync)
        self._apply()

    def _sync(self, *_):
        r = self.height / 2
        self._track.pos, self._track.size, self._track.radius = self.pos, self.size, [r]
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
            on = opt == self.selected
            b.color = ON_ACCENT if on else INK_SOFT
            b.bold = on
        if self.selected in self.options:
            i = self.options.index(self.selected)
            w = self.width / max(1, len(self.options))
            inset = dp(3)
            h = max(0, self.height - 2 * inset)
            self._thumb.pos = (self.x + i * w + inset, self.y + inset)
            self._thumb.size = (w - 2 * inset, h)
            self._thumb.radius = [h / 2]


# ---------------------------------------------------------------------------
# Home cards, header and bottom navigation
# ---------------------------------------------------------------------------
class HomeCard(ButtonBehavior, OutlineBox):
    """One tappable Home menu card: an icon chip, title and one-line description on a filled rounded card."""

    def __init__(self, icon, title, desc, on_press_cb=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(118))
        kwargs.setdefault("padding", (dp(14), dp(14), dp(12), dp(10)))
        kwargs.setdefault("spacing", dp(2))
        super().__init__(orientation="vertical", **kwargs)
        top = BoxLayout(size_hint_y=None, height=dp(38))
        top.add_widget(IconChip(icon, size_dp=36, icon_dp=19))
        top.add_widget(Widget())
        self.add_widget(top)
        t = Label(text=title, bold=True, font_size="14sp", halign="left", valign="middle", size_hint_y=None, height=dp(30))
        t.bind(size=lambda inst, sz: setattr(inst, "text_size", (sz[0], sz[1])))
        d = Label(text=desc, font_size="11.5sp", color=MUTED, halign="left", valign="top")
        d.bind(size=lambda inst, sz: setattr(inst, "text_size", (sz[0], sz[1])))
        self.add_widget(t)
        self.add_widget(d)
        if on_press_cb:
            self.bind(on_release=lambda *_: on_press_cb())
        self.bind(state=lambda inst, st: inst.set_accent(st == "down"))


class _NavItem(ButtonBehavior, BoxLayout):
    def __init__(self, icon, label, **kwargs):
        super().__init__(orientation="vertical", padding=(0, dp(6), 0, dp(6)), spacing=dp(2), **kwargs)
        self.icon = LineIcon(icon, color=NEUTRAL_600, size_dp=21, stroke=1.6)
        self.holder = BoxLayout(size_hint_y=None, height=dp(28))
        self.holder.add_widget(Widget())
        self.holder.add_widget(self.icon)
        self.holder.add_widget(Widget())
        self.label = Label(text=label, font_size="10.5sp", color=NEUTRAL_600, size_hint_y=None, height=dp(14))
        self.add_widget(self.holder)
        self.add_widget(self.label)

    def set_active(self, on):
        c = ACCENT_700 if on else NEUTRAL_600
        self.icon.set_color(c)
        self.label.color = c
        self.label.bold = on


class BottomNav(BoxLayout):
    """A floating rounded tab bar; one accent pill sits behind the active tab's icon and glides to the next tab
    when the tab changes (instantly when motion is off or no tab is active)."""

    pill_x = NumericProperty(0)
    pill_alpha = NumericProperty(0)

    def __init__(self, items, on_select, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(76))
        kwargs.setdefault("padding", (dp(20), dp(10), dp(20), dp(14)))
        super().__init__(orientation="horizontal", **kwargs)
        with self.canvas.before:
            Color(*SHADOW)
            self._sh = RoundedRectangle(radius=[dp(26)])
            Color(*(SURFACE_2 if IS_DARK else SURFACE))
            self._bar = RoundedRectangle(radius=[dp(26)])
            self._pill_color = Color(*_alpha(ACCENT, 0))
            self._pill = RoundedRectangle(radius=[dp(14)])
            self._dot_color = Color(*_alpha(ACCENT, 0))
            self._dot = Ellipse(size=(dp(5), dp(5)))
        self._active_key = None
        self.bind(pill_x=self._place_pill, pill_alpha=self._place_pill)
        with self.canvas.after:
            Color(*_alpha(TEXT, 0.07))
            self._edge = Line(width=1)
        self._items = {}
        for key, label, icon in items:
            it = _NavItem(icon, label)
            it.bind(on_release=lambda inst, k=key: on_select(k))
            self._items[key] = it
            self.add_widget(it)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        x, y, w, h = self.x + dp(12), self.y + dp(8), self.width - dp(24), self.height - dp(12)
        self._sh.pos, self._sh.size = (x, y - dp(3)), (w, h)
        self._bar.pos, self._bar.size = (x, y), (w, h)
        self._edge.rounded_rectangle = (x, y, w, h, dp(26))
        Clock.schedule_once(lambda _dt: self._jump_to_active(), 0)     # children are laid out after this

    def _target_x(self, key):
        it = self._items.get(key)
        return None if it is None else it.x + it.width / 2

    def _jump_to_active(self):
        x = self._target_x(self._active_key)
        if x is not None:
            Animation.cancel_all(self, "pill_x")
            self.pill_x = x

    def _place_pill(self, *_):
        w, h = dp(56), dp(28)
        it = next(iter(self._items.values()), None)
        y = (it.holder.y if it is not None else self.y + dp(14))
        self._pill.pos, self._pill.size = (self.pill_x - w / 2, y), (w, h)
        self._pill_color.rgba = _alpha(ACCENT, 0.18 * self.pill_alpha)
        self._dot.pos = (self.pill_x - dp(2.5), self.y + dp(9))
        self._dot_color.rgba = _alpha(ACCENT, 0.9 * self.pill_alpha)

    def set_active(self, key):
        for k, it in self._items.items():
            it.set_active(k == key)
        previous, self._active_key = self._active_key, key
        x = self._target_x(key)
        if x is None:                                   # a screen that is not on the bar: fade the pill out
            Animation.cancel_all(self, "pill_alpha")
            if MOTION:
                Animation(pill_alpha=0, d=0.15).start(self)
            else:
                self.pill_alpha = 0
            return
        moving = previous in self._items and self.pill_alpha > 0
        Animation.cancel_all(self, "pill_x", "pill_alpha")
        if MOTION and moving:
            Animation(pill_x=x, d=0.30, t="out_back").start(self)
        else:
            self.pill_x = x
        if MOTION:
            Animation(pill_alpha=1, d=0.18).start(self)
        else:
            self.pill_alpha = 1


class _ChipButton(ButtonBehavior, IconChip):
    def __init__(self, icon, **kwargs):
        super().__init__(icon=icon, **kwargs)      # ButtonBehavior.__init__ takes keyword arguments only


class AppHeader(BoxLayout):
    """The top bar: a Home button (diamond chip), the screen title, and a light/dark switch."""

    def __init__(self, on_home, on_theme=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(64))
        kwargs.setdefault("padding", (dp(16), dp(10), dp(16), dp(8)))
        kwargs.setdefault("spacing", dp(12))
        super().__init__(orientation="horizontal", **kwargs)
        mark = _ChipButton("diamond", size_dp=42, icon_dp=20, fill=SURFACE_2 if IS_DARK else ACCENT_100,
                           pos_hint={"center_y": 0.5})
        mark.bind(on_release=lambda *_: on_home())
        mark.bind(state=lambda inst, st: inst.set_fill(PRESS_TINT if st == "down" else (SURFACE_2 if IS_DARK else ACCENT_100)))
        self.add_widget(mark)
        font = display_font()
        self.title_label = Label(text="Home", bold=font == "Roboto", font_size="23sp" if font != "Roboto" else "20sp",
                                 font_name=font, halign="left", valign="middle", shorten=True, shorten_from="right")
        self.title_label.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        self.add_widget(self.title_label)
        if on_theme is not None:
            # the icon shows the theme you switch TO: a moon in the light theme, a sun in the dark one
            toggle = _ChipButton("sun" if IS_DARK else "moon", size_dp=42, icon_dp=20,
                                 fill=SURFACE_2 if IS_DARK else ACCENT_100, pos_hint={"center_y": 0.5})
            toggle.bind(on_release=lambda *_: on_theme(other()))
            toggle.bind(state=lambda inst, st: inst.set_fill(PRESS_TINT if st == "down" else (SURFACE_2 if IS_DARK else ACCENT_100)))
            self.theme_toggle = toggle
            self.add_widget(toggle)

    def set_title(self, text):
        if self.title_label.text != text:
            self.title_label.text = text
            fade_in(self.title_label, d=0.22)


class ButtonBehaviorBox(ButtonBehavior, BoxLayout):
    """Kept for compatibility: a 40dp tap target around the diamond mark."""

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


# ---------------------------------------------------------------------------
# Motion (v2.3)
# ---------------------------------------------------------------------------
class _Shift(EventDispatcher):
    dy = NumericProperty(0)


def set_motion(on):
    """Turn every animation on or off (Home > Motion)."""
    global MOTION
    MOTION = bool(on)


def animate_in(widget, delay=0.0, dy=None, d=0.30):
    """Fade `widget` in while it slides up `dy` (default 16dp) into place. Canvas-only: a PushMatrix/Translate pair
    is put in front of the widget's drawing and removed again when the animation ends, so layout and touch are
    never changed. No-op when motion is off."""
    if not MOTION or widget is None:
        return
    dy = dp(16) if dy is None else dy
    push, shift_t, pop = PushMatrix(), Translate(0, -dy), PopMatrix()
    widget.canvas.before.insert(0, shift_t)
    widget.canvas.before.insert(0, push)
    widget.canvas.after.add(pop)
    widget.opacity = 0
    shift = _Shift(dy=-dy)
    shift.bind(dy=lambda _o, v: setattr(shift_t, "y", v))
    widget._motion_shift = shift                    # keep the dispatcher alive while it animates

    def _done(*_):
        for group, inst in ((widget.canvas.before, push), (widget.canvas.before, shift_t), (widget.canvas.after, pop)):
            try:
                group.remove(inst)
            except Exception:                         # already removed (a second animation finished first)
                pass
        widget.opacity = 1
        widget._motion_shift = None

    def _start(*_):
        Animation(opacity=1, d=d * 0.85, t="out_quad").start(widget)
        anim = Animation(dy=0, d=d, t="out_cubic")
        anim.bind(on_complete=_done)
        anim.start(shift)

    if delay:
        Clock.schedule_once(_start, delay)
    else:
        _start()


def fade_in(widget, d=0.25):
    """Opacity-only entrance (for things that must not move, such as the header title)."""
    if not MOTION or widget is None:
        return
    widget.opacity = 0
    Animation(opacity=1, d=d, t="out_quad").start(widget)


def stagger(widgets, step=0.035, max_n=12, start=0.0):
    """animate_in() a sequence of widgets one after another; only the first `max_n` move (the rest just appear),
    which keeps long pages cheap on slow phones."""
    if not MOTION:
        return
    for i, w in enumerate(widgets):
        if i >= max_n:
            break
        animate_in(w, delay=start + i * step)
