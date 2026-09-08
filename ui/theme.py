"""
theme.py — shared visual theme for the Android/Kivy app: the same
indigo/gold "celestial" palette already used by the desktop and web apps
(see chart_engine/webapp/static/style.css's :root custom properties),
plus a handful of reusable, canvas-drawn widgets so every tab can share
one more graphical look without bundling any image assets - everything
here is either a plain kivy.graphics primitive or a tiny procedurally
generated gradient texture, so it stays fully offline and adds no extra
dependency or file size to the APK.

Usage: put a GradientBackground as the very first child of the app's
root layout (so it paints behind everything else), swap a plain
kivy.uix.button.Button for ThemedButton where you want the gold/indigo
pill look, and drop a SectionHeader at the top of a tab's content for a
colored "hero" banner instead of a plain Label.
"""
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.utils import get_color_from_hex as hex_color

# ---- Palette (mirrors webapp/static/style.css's :root variables) ----
BG = hex_color("#0e1230")           # deep night
BG2 = hex_color("#151a44")
PANEL = hex_color("#1a2050")        # card / content background - dark, since a
PANEL_SOFT = hex_color("#242a5e")   # phone screen reads better dark throughout
INK = hex_color("#eef0ff")          # primary text, for the dark panels above
INK_SOFT = hex_color("#b9c0e0")
MUTED = hex_color("#8890b8")
INDIGO = hex_color("#3d5a8a")
INDIGO_2 = hex_color("#4c6fb0")
INDIGO_DEEP = hex_color("#232c58")
GOLD = hex_color("#c9a24a")
GOLD_SOFT = hex_color("#e7d5a3")
GOLD_TEXT = hex_color("#20264a")    # dark ink used ON TOP of a gold fill


def _make_gradient_texture(top_hex, bottom_hex, size=256):
    """A 1px-wide, `size`-tall vertical gradient texture (Kivy textures
    are bottom-up, so row 0 = bottom_hex, row size-1 = top_hex). Stretched
    to fill any Rectangle - avoids needing a bundled image or a GLSL
    shader just for a smooth background gradient."""
    top = [int(round(c * 255)) for c in hex_color(top_hex)]
    bottom = [int(round(c * 255)) for c in hex_color(bottom_hex)]
    buf = bytearray(size * 4)
    for y in range(size):
        t = y / (size - 1)
        for ch in range(4):
            buf[y * 4 + ch] = int(round(bottom[ch] + (top[ch] - bottom[ch]) * t))
    tex = Texture.create(size=(1, size), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    return tex


_gradient_texture_cache = {}


def _gradient_texture(top_hex, bottom_hex):
    key = (top_hex, bottom_hex)
    if key not in _gradient_texture_cache:
        _gradient_texture_cache[key] = _make_gradient_texture(top_hex, bottom_hex)
    return _gradient_texture_cache[key]


class GradientBackground(FloatLayout):
    """Fills itself with a deep indigo-to-navy vertical gradient - drop
    this as the FIRST child of the app's root layout, with everything
    else added on top of it, to replace Kivy's flat default gray/black
    with the same "celestial night sky" feel the desktop/web apps have."""

    def __init__(self, top="#1c2560", bottom="#0a0d24", **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=_gradient_texture(top, bottom),
                                    pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class SectionHeader(BoxLayout):
    """A colored banner with an icon + title for the top of a tab's
    content - a more "hero card" look than a plain Label, e.g.
    SectionHeader("\U0001F52E", "Karmic & Past Life")."""

    def __init__(self, icon, title, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(48))
        kwargs.setdefault("padding", (dp(14), dp(4)))
        super().__init__(orientation="horizontal", **kwargs)
        with self.canvas.before:
            Color(*INDIGO_DEEP)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._sync_bg, size=self._sync_bg)
        self.add_widget(Label(text=f"{icon}  {title}", color=GOLD_SOFT,
                               font_size="17sp", bold=True, halign="left", valign="middle"))

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


class ThemedButton(Button):
    """A Button re-skinned with a rounded, bordered fill instead of
    Kivy's default gray atlas image - same text/on_release API as a
    plain Button, so it drops in anywhere. gold=True gives the solid
    gold-filled variant used for primary calls to action (e.g. Generate
    Chart); the default is an indigo fill with a soft-gold border."""

    def __init__(self, gold=False, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("color", GOLD_TEXT if gold else INK)
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)
        fill = GOLD if gold else INDIGO
        border = GOLD_SOFT if gold else INDIGO_2
        with self.canvas.before:
            Color(*border)
            self._border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(*fill)
            self._fill_rect = RoundedRectangle(pos=self._inset_pos(), size=self._inset_size(),
                                                radius=[dp(9)])
        self.bind(pos=self._sync, size=self._sync)

    def _inset_pos(self, inset=dp(1.5)):
        return self.pos[0] + inset, self.pos[1] + inset

    def _inset_size(self, inset=dp(1.5)):
        return self.size[0] - inset * 2, self.size[1] - inset * 2

    def _sync(self, *_):
        self._border_rect.pos = self.pos
        self._border_rect.size = self.size
        self._fill_rect.pos = self._inset_pos()
        self._fill_rect.size = self._inset_size()
