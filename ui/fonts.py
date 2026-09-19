"""
fonts.py - which font the app draws with, per language.

Kivy's default font (Roboto) has no Devanagari or Bengali letters, so for Hindi
and Bengali the app re-points the default "Roboto" name at the matching Noto Sans
font bundled in fonts/ (SIL Open Font License, see fonts/OFL-NotoSans.txt).
Every Label and TextInput that does not name its own font then picks it up
automatically. Both Noto fonts include Latin letters and digits, so mixed text
("D9", "ASC", English names) still draws. Fully offline: the fonts ship inside the APK.
"""
import os

import kivy
from kivy.core.text import LabelBase

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(_APP_DIR, "fonts")

DEVANAGARI = {"fn_regular": os.path.join(FONT_DIR, "NotoSansDevanagari-Regular.ttf"),
              "fn_bold": os.path.join(FONT_DIR, "NotoSansDevanagari-Bold.ttf")}
BENGALI = {"fn_regular": os.path.join(FONT_DIR, "NotoSansBengali-Regular.ttf"),
           "fn_bold": os.path.join(FONT_DIR, "NotoSansBengali-Bold.ttf")}


def _roboto():
    d = os.path.join(kivy.kivy_data_dir, "fonts")
    return {"fn_regular": os.path.join(d, "Roboto-Regular.ttf"), "fn_italic": os.path.join(d, "Roboto-Italic.ttf"),
            "fn_bold": os.path.join(d, "Roboto-Bold.ttf"), "fn_bolditalic": os.path.join(d, "Roboto-BoldItalic.ttf")}


def font_for_language(code):
    """Path of the regular font that can draw this language's own name."""
    return {"hi": DEVANAGARI["fn_regular"], "bn": BENGALI["fn_regular"]}.get(code)


def apply(code):
    """Make `code` the language of the default font. Widgets created AFTER this use it."""
    files = {"hi": DEVANAGARI, "bn": BENGALI}.get(code)
    LabelBase.register("Roboto", **(files or _roboto()))
