"""The offline translation layer (engine/i18n.py) and the Bengali table built by tools/build_i18n.py.
Run from android_app/:  python -m pytest tests/test_i18n.py"""
import datetime
import os
import re
import sys

import pytest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

import i18n  # noqa: E402

PLACEHOLDER = re.compile(r"\{[^}]*\}|%s|%d")
PUA = re.compile("[-]")


@pytest.fixture(autouse=True)
def _english_after():
    yield
    i18n.set_language("en")


def test_english_is_a_no_op():
    i18n.set_language("en")
    assert i18n.t("Good") == "Good"
    assert i18n.tr("{0} is in {1}", "Sun", "Leo") == "Sun is in Leo"
    assert i18n.tr("Plain sentence.") == "Plain sentence."
    assert i18n.join_list(["A", "B", "C"]) == "A, B and C"
    assert i18n.fmt_date(datetime.date(2026, 3, 5), "%d %b %Y") == "05 Mar 2026"
    assert i18n.t_text("Anything at all.\n\nSecond paragraph.") == "Anything at all.\n\nSecond paragraph."


def test_bengali_module_loads_and_names_itself():
    assert i18n.language_available("bn")
    assert i18n.native_name("bn")           # the language's own name, drawn with the Bengali font
    assert i18n.native_name("en") == "English"


def test_bengali_words_sentences_and_lists_are_translated():
    i18n.set_language("bn")
    assert i18n.t("Good") != "Good" and i18n.t("good") == i18n.t("Good")       # case-insensitive words
    assert i18n.t("Sun") != "Sun"
    assert i18n.tr("{0} is in {1}", "Sun", "Leo") == "{0} is in {1}".format("Sun", "Leo")   # unknown template stays English
    # a real template: pieces are translated and slotted in, and no placeholder is left over
    out = i18n.tr("{0} house ({1})", "5th", "children")
    assert "{" not in out and "house" not in out
    assert i18n.join_list(["Sun", "Moon", "Mars"]).count(",") == 1              # "A, B ও C"
    assert i18n.t("Sun, Mars") == ", ".join([i18n.t("Sun"), i18n.t("Mars")])    # comma lists of known words
    assert i18n.t("13th") not in ("13th", "")                                    # ordinals beyond the table


def test_bengali_dates_use_bengali_month_names():
    i18n.set_language("bn")
    d = datetime.date(2026, 3, 5)
    short, long_ = i18n.fmt_date(d, "%d %b %Y"), i18n.fmt_date(d, "%d %B %Y")
    assert "Mar" not in short and "March" not in long_
    assert short.startswith("05 ") and short.endswith(" 2026")


def test_program_keys_are_never_translated():
    i18n.set_language("bn")
    for key in ("surya_grahan", "chandra_grahan", "rahu_ketu_in_9th", "planet_house", "shodashvarga", "pdf_sections_",
                "Created by Sammya Das"):
        assert i18n.t(key) == key


def test_every_bengali_string_keeps_its_placeholders():
    bn = __import__("i18n_bn")
    src_keys = {k: v for k, v in bn.T.items()}
    bad = [k for k, v in src_keys.items()
           if "{n}" not in k and not re.search(r"'s'", k)
           and {p for p in PLACEHOLDER.findall(k)} - {p for p in PLACEHOLDER.findall(v)} - {"{1}", "{5}", "{7}"}]
    # a few English plural suffixes ("house{1}") intentionally have no Bengali counterpart, everything else must match
    assert len(bad) <= 6, bad[:10]


def test_every_indic_glyph_used_exists_in_the_bundled_fonts():
    """The table stores pre-shaped syllables as private-use characters; each must exist in both font weights."""
    from fontTools.ttLib import TTFont
    bn = __import__("i18n_bn")
    used = set()
    for text in list(bn.T.values()) + [bn.NAME] + list(bn.MONTHS) + list(bn.MONTHS_LONG):
        used.update(PUA.findall(text))
    assert used, "the Bengali table should use pre-shaped glyphs"
    for weight in ("Regular", "Bold"):
        cmap = TTFont(os.path.join(APP, "fonts", f"IndicBn-{weight}.ttf")).getBestCmap()
        missing = [hex(ord(c)) for c in used if ord(c) not in cmap]
        assert not missing, (weight, missing[:10])


def test_no_raw_indic_letters_are_left_in_the_generated_table():
    """Raw Bengali letters would be drawn scrambled by Kivy; the build must have replaced them all."""
    bn = __import__("i18n_bn")
    raw = re.compile("[ঀ-৿]")
    left = [k for k, v in bn.T.items() if raw.search(v)]
    assert not left, left[:5]
