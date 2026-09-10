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
root layout (so it paints behind everything else), drop a SectionHeader
at the top of a tab's content for a colored "hero" banner instead of a
plain Label, and swap Kivy's stock form controls for their Themed*
equivalents below - ThemedButton, ThemedTextInput, ThemedSpinner (+ its
own ThemedSpinnerOption dropdown-list rows), ThemedCheckBox - each a
drop-in replacement with the same API as the widget it replaces, just
re-skinned with this file's rounded indigo/gold pill look instead of
Kivy's default flat gray atlas images (which is where this app's "looks
like an old Windows toolbar" impression came from - those defaults never
matched the celestial palette everything else here uses).
"""
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import BooleanProperty
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
INDIGO_PRESS = hex_color("#2c3d68")  # ThemedButton/Spinner fill while pressed -
                                      # a touch darker than INDIGO, so tapping
                                      # one visibly reacts (see _PillMixin)
# Brighter than the original #c9a24a - this project's one color-contrast
# complaint was the gold CTA button (Generate Chart, etc): #c9a24a fill with
# the old #20264a text measured ~3.4:1, under WCAG AA's 4.5:1 floor for
# normal-size text. Brightening the gold AND darkening its text (below) both
# widen that gap - the combined change measures ~7.7:1 (AAA), while still
# reading as "gold" rather than "yellow warning."
GOLD = hex_color("#e0b654")
GOLD_PRESS = hex_color("#caa049")    # gold fill while pressed - one step back
                                      # toward the old, less saturated gold
GOLD_SOFT = hex_color("#e7d5a3")
GOLD_TEXT = hex_color("#14172c")    # near-black ink used ON TOP of a gold
                                      # fill - see the contrast note above


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
    SectionHeader("\U0001F52E", "Karmic & Past Life"). Filled with the
    same indigo gradient texture GradientBackground uses (instead of one
    flat color) so every tab opens on a small echo of the app's own
    "celestial" background rather than a plain solid bar - a cheap way to
    make the UI read as more considered/modern without adding any image
    asset."""

    def __init__(self, icon, title, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(52))
        kwargs.setdefault("padding", (dp(16), dp(4)))
        super().__init__(orientation="horizontal", **kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)],
                                         texture=_gradient_texture("#343f78", "#1c2352"))
        self.bind(pos=self._sync_bg, size=self._sync_bg)
        self.add_widget(Label(text=f"{icon}  {title}", color=GOLD_SOFT,
                               font_size="18sp", bold=True, halign="left", valign="middle"))

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


class _PillMixin:
    """Shared rounded border+fill canvas drawing, used by every "pill"-
    style themed widget below (ThemedButton, ThemedSpinner/
    ThemedSpinnerOption) - they're all Button subclasses in Kivy (Spinner
    IS a Button), so they all share the same pos/size box model this
    draws against. Pulled out once rather than copy-pasted per widget,
    the same "one implementation, several call sites" approach this
    project already uses elsewhere (e.g. engine/dasha.py's
    _build_sub_periods) rather than letting near-identical drawing code
    drift out of sync across widgets.

    Also owns the fill-darkens-on-press feedback every pill widget got as
    part of this pass: originally _sync_pill only ever repainted the SAME
    fill color at a new pos/size, so tapping a button changed nothing
    visible until whatever its on_release callback did (a status label
    updating, a new tab appearing, etc.) - on a slower device, or for a
    button whose effect isn't immediately obvious, that reads as "nothing
    happened, is this even working," which is the most literal possible
    reading of this app's reported "the buttons donot work." Binding
    `state` here and swapping to `press_fill` while held (any Kivy Button
    subclass already flips its own `state` between 'normal'/'down' on
    touch down/up - this just reacts to it) gives every button an
    instant, correct-on-first-frame press cue."""

    def _init_pill(self, fill, border, radius=dp(12), press_fill=None):
        self._pill_fill = fill
        self._pill_press_fill = press_fill or fill
        self._pill_border = border
        with self.canvas.before:
            self._border_color = Color(*border)
            self._border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            self._fill_color = Color(*fill)
            self._fill_rect = RoundedRectangle(pos=self._inset_pos(), size=self._inset_size(),
                                                radius=[radius - dp(1)])
        self.bind(pos=self._sync_pill, size=self._sync_pill, state=self._sync_pill_state)

    def _inset_pos(self, inset=dp(1.5)):
        return self.pos[0] + inset, self.pos[1] + inset

    def _inset_size(self, inset=dp(1.5)):
        return self.size[0] - inset * 2, self.size[1] - inset * 2

    def _sync_pill(self, *_):
        self._border_rect.pos = self.pos
        self._border_rect.size = self.size
        self._fill_rect.pos = self._inset_pos()
        self._fill_rect.size = self._inset_size()

    def _sync_pill_state(self, instance, state):
        self._fill_color.rgba = self._pill_press_fill if state == "down" else self._pill_fill


class ThemedButton(_PillMixin, Button):
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
        self._init_pill(GOLD if gold else INDIGO, GOLD_SOFT if gold else INDIGO_2,
                         press_fill=GOLD_PRESS if gold else INDIGO_PRESS)


class ThemedSpinnerOption(_PillMixin, SpinnerOption):
    """The themed look for each row in a ThemedSpinner's dropdown list -
    set as ThemedSpinner's own option_cls below, so opening any dropdown
    in this app shows this instead of Kivy's default flat gray atlas
    button list."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("color", INK)
        kwargs.setdefault("bold", False)
        super().__init__(**kwargs)
        self._init_pill(PANEL_SOFT, INDIGO_2, radius=dp(8), press_fill=INDIGO_PRESS)


class ThemedSpinner(_PillMixin, Spinner):
    """A Spinner (dropdown) re-skinned to match ThemedButton - same
    rounded indigo pill, with its own dropdown list re-skinned via
    ThemedSpinnerOption rather than Kivy's default gray atlas."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("color", INK)
        kwargs.setdefault("bold", True)
        kwargs.setdefault("option_cls", ThemedSpinnerOption)
        super().__init__(**kwargs)
        self._init_pill(INDIGO, INDIGO_2, press_fill=INDIGO_PRESS)


class ThemedTextInput(TextInput):
    """A TextInput re-skinned with a rounded dark fill instead of Kivy's
    default white input box (the single most "old Windows toolbar"-
    looking stock widget in this app against a dark theme) - same
    .text/hint_text/input_filter API as a plain TextInput. Border turns
    gold while focused, for a lightweight "this field is active" cue."""

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("foreground_color", INK)
        kwargs.setdefault("hint_text_color", MUTED)
        kwargs.setdefault("cursor_color", GOLD)
        kwargs.setdefault("selection_color", (GOLD[0], GOLD[1], GOLD[2], 0.35))
        kwargs.setdefault("padding", (dp(10), dp(10), dp(10), dp(10)))
        super().__init__(**kwargs)
        with self.canvas.before:
            self._border_color = Color(*PANEL_SOFT)
            self._border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(*PANEL)
            self._fill_rect = RoundedRectangle(pos=self._inset_pos(), size=self._inset_size(),
                                                radius=[dp(9)])
        self.bind(pos=self._sync, size=self._sync, focus=self._on_focus, disabled=self._on_focus)

    def _inset_pos(self, inset=dp(1.5)):
        return self.pos[0] + inset, self.pos[1] + inset

    def _inset_size(self, inset=dp(1.5)):
        return self.size[0] - inset * 2, self.size[1] - inset * 2

    def _sync(self, *_):
        self._border_rect.pos = self.pos
        self._border_rect.size = self.size
        self._fill_rect.pos = self._inset_pos()
        self._fill_rect.size = self._inset_size()

    def _on_focus(self, *_):
        self._border_color.rgba = MUTED if self.disabled else (GOLD if self.focus else PANEL_SOFT)


class ThemedCheckBox(Button):
    """A checkbox re-skinned as a small square toggle (border normally,
    gold-filled with a check mark when active) instead of Kivy's default
    tiny checkbox atlas image, which doesn't restyle to a dark theme at
    all. Exposes the same `active` BooleanProperty + change-event API as
    the real kivy.uix.checkbox.CheckBox (bind(active=...), read/set
    .active directly), so it's a drop-in replacement everywhere this app
    used the stock one."""

    active = BooleanProperty(False)

    def __init__(self, active=False, **kwargs):
        # dp(36), not the original dp(30): still small (it's an inline
        # checkbox, not a primary button), but 30dp sat noticeably under
        # Android's own 48dp/44dp-ish recommended minimum touch target -
        # on a real device that made it genuinely easy to miss-tap, which
        # is functionally indistinguishable from "the button doesn't
        # work." 36dp keeps the row compact while closing most of that gap.
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(36), dp(36)))
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("text", "")
        super().__init__(**kwargs)
        with self.canvas.before:
            self._border_color = Color(*INK_SOFT)
            self._border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(7)])
            self._fill_color = Color(0, 0, 0, 0)
            self._fill_rect = RoundedRectangle(pos=self._inset_pos(), size=self._inset_size(),
                                                radius=[dp(6)])
        self.bind(pos=self._sync, size=self._sync, on_release=self._toggle,
                  active=self._apply, state=self._apply)
        self.active = active
        self._apply()

    def _inset_pos(self, inset=dp(2)):
        return self.pos[0] + inset, self.pos[1] + inset

    def _inset_size(self, inset=dp(2)):
        return self.size[0] - inset * 2, self.size[1] - inset * 2

    def _sync(self, *_):
        self._border_rect.pos = self.pos
        self._border_rect.size = self.size
        self._fill_rect.pos = self._inset_pos()
        self._fill_rect.size = self._inset_size()

    def _toggle(self, *_):
        self.active = not self.active

    def _apply(self, *_):
        pressed = self.state == "down"
        if self.active:
            self._fill_color.rgba = GOLD_PRESS if pressed else GOLD
        else:
            # A held-but-not-yet-released tap still gets a visible fill
            # (a soft translucent gold, not the empty/transparent normal
            # state) so pressing an UNCHECKED box gives the same instant
            # "yes, that registered" cue toggling ON already gave a
            # checked one - see _PillMixin's docstring for why this
            # press-feedback pass exists at all.
            self._fill_color.rgba = (GOLD[0], GOLD[1], GOLD[2], 0.35) if pressed else (0, 0, 0, 0)
        self._border_color.rgba = GOLD if (self.active or pressed) else INK_SOFT
        self.text = "✓" if self.active else ""
        self.color = GOLD_TEXT
        self.bold = True
        self.font_size = "16sp"
