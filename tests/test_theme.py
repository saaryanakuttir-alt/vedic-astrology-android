"""The Light/Dark design system (ui/theme.py): both palettes must define the same tokens, and switching must really
change the colours every screen reads."""
import os
import sys

os.environ.setdefault("KIVY_NO_ARGS", "1")
sys.path[:0] = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"),
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]

from ui import theme  # noqa: E402


def test_palettes_define_the_same_tokens():
    keys = [set(p) for p in theme.PALETTES.values()]
    assert all(k == keys[0] for k in keys), "a token is missing from one palette - that theme would crash on switch"


def test_switching_changes_the_colours():
    theme.apply("dark", window=False)
    dark = (theme.BG, theme.SURFACE, theme.TEXT, theme.ACCENT, theme.MUTED, theme.GOLD)
    assert theme.IS_DARK and theme.other() == "light"
    theme.apply("light", window=False)
    light = (theme.BG, theme.SURFACE, theme.TEXT, theme.ACCENT, theme.MUTED, theme.GOLD)
    assert not theme.IS_DARK and theme.other() == "dark"
    assert all(a != b for a, b in zip(dark, light))
    theme.apply(theme.DEFAULT_THEME, window=False)


def test_unknown_theme_falls_back_to_default():
    assert theme.apply("neon", window=False) == theme.DEFAULT_THEME


def test_text_is_readable_on_surfaces():
    """Rough contrast guard: body text and the card surface must differ strongly in brightness in both themes."""
    def lum(c):
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    for name in theme.THEMES:
        theme.apply(name, window=False)
        assert abs(lum(theme.TEXT) - lum(theme.SURFACE)) > 0.6, name
        assert abs(lum(theme.ON_ACCENT) - lum(theme.ACCENT)) > 0.35, name
    theme.apply(theme.DEFAULT_THEME, window=False)
