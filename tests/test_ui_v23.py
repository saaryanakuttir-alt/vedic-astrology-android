"""v2.3 UI: the reading layout (ui/widgets.build_reading), motion (ui/theme.animate_in / BottomNav pill) and the
knowledge cards (ui/knowledge_widgets.py). Widgets are built without showing a window.
Run from android_app/:  python -m pytest tests/test_ui_v23.py"""
import datetime
import os
import sys
import time

import pytest

os.environ.setdefault("KIVY_NO_ARGS", "1")
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(APP, "engine"), APP):
    if p not in sys.path:
        sys.path.insert(0, p)

pytest.importorskip("kivy")
from kivy.clock import Clock  # noqa: E402
from kivy.graphics import PopMatrix, PushMatrix, Translate  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402

from ui import theme  # noqa: E402
from ui import widgets  # noqa: E402


@pytest.fixture(scope="module")
def chart():
    from birth_chart import compute_birth_chart
    return compute_birth_chart(name="Sammya Das", birth_date=(1992, 5, 29), birth_time=(7, 6, 0), place_name="Howrah",
                               country_hint="IN", sex="Male")


def _texts(widget):
    out = []

    def walk(w):
        if isinstance(w, Label):
            out.append(w.text)
        for c in reversed(w.children):
            walk(c)
    walk(widget)
    return out


# ---------------------------------------------------------------- reading layout
def test_markers_become_title_cards_and_callouts():
    text = ("=== Remedies - Asha ===\n\n--- For right now ---\nOnly what is needed.\n\n"
            "[In simple terms: start with the mantra.]\n\n--- Points from each source ---")
    blocks = widgets.build_reading(text)
    assert isinstance(blocks[0], Label) and blocks[0].text == "Remedies - Asha"
    card = blocks[1]
    assert isinstance(card, widgets.ReadingCard) and card.has_body
    texts = _texts(card)
    assert texts[0] == "For right now" and "Only what is needed." in texts
    assert any(isinstance(c, widgets.Callout) for c in card.children)
    assert "IN SIMPLE TERMS" in texts and "start with the mantra." in texts
    # a heading with nothing under it (e.g. just above a table) is a plain heading, not an empty card
    assert isinstance(blocks[2], Label) and blocks[2].text == "Points from each source"
    assert len(blocks) == 3


def test_note_on_its_own_line_or_after_a_sentence_becomes_a_callout():
    card = widgets.build_reading("--- Strength ---\nEach planet is scored.\n[In simple terms: stronger is easier.]")[0]
    assert sum(isinstance(c, widgets.Callout) for c in card.children) == 1
    card = widgets.build_reading("--- Strength ---\nRank 1 of 7. [In simple terms: it helps you most.]")[0]
    assert sum(isinstance(c, widgets.Callout) for c in card.children) == 1
    assert "Rank 1 of 7." in _texts(card)


def test_layout_reads_markers_not_words():
    """Bengali (or any language) keeps the same --- / === / [x: y] markers, so the same structure appears."""
    blocks = widgets.build_reading("=== প্রতিকার ===\n\n--- আপনার জন্য ---\nএকটি বাক্য।\n\n[সহজ কথায়: শান্ত থাকুন।]")
    assert isinstance(blocks[0], Label) and isinstance(blocks[1], widgets.ReadingCard)
    assert any(isinstance(c, widgets.Callout) for c in blocks[1].children)


def test_plain_text_without_markers_still_shows():
    blocks = widgets.build_reading("No chart generated yet for this profile.")
    assert len(blocks) == 1 and "No chart generated yet for this profile." in _texts(blocks[0])


def test_long_paragraphs_stay_split_into_small_labels():
    """The Android blank-text fix (see LongText): no single label holds a huge paragraph."""
    long_para = " ".join(["This is one sentence of a very long run-on report paragraph."] * 60)
    card = widgets.build_reading("--- Long ---\n" + long_para)[0]
    body = [t for t in _texts(card) if t != "Long"]
    assert len(body) > 3 and max(len(t) for t in body) <= 420


# ---------------------------------------------------------------- motion
def _tick(seconds):
    end = time.time() + seconds
    while time.time() < end:
        Clock.tick()
        time.sleep(0.01)


def test_animate_in_cleans_up_its_canvas_instructions():
    theme.set_motion(True)
    w = Widget()
    before = len(w.canvas.before.children)
    theme.animate_in(w, d=0.05)
    assert any(isinstance(i, PushMatrix) for i in w.canvas.before.children)
    assert w.opacity == 0
    _tick(0.4)
    kinds = [type(i) for i in w.canvas.before.children + w.canvas.after.children]
    assert PushMatrix not in kinds and PopMatrix not in kinds and Translate not in kinds
    assert len(w.canvas.before.children) == before and w.opacity == 1


def test_motion_off_changes_nothing():
    theme.set_motion(False)
    try:
        w = Widget()
        theme.animate_in(w)
        theme.fade_in(w)
        assert w.opacity == 1 and not any(isinstance(i, PushMatrix) for i in w.canvas.before.children)
    finally:
        theme.set_motion(True)


def test_bottom_nav_pill_follows_the_active_tab():
    theme.set_motion(False)
    try:
        nav = theme.BottomNav([("a", "A", "diamond"), ("b", "B", "clock")], on_select=lambda k: None)
        nav.size = (400, 76)
        nav.do_layout()
        nav.set_active("b")
        assert nav.pill_alpha == 1 and nav.pill_x == nav._target_x("b")
        nav.set_active("home")                       # not on the bar: the pill hides
        assert nav.pill_alpha == 0
    finally:
        theme.set_motion(True)


def test_palettes_have_the_new_status_colours_and_display_font():
    for name in theme.THEMES:
        theme.apply(name, window=False)
        for key in ("GOOD", "WARN", "BAD", "INFO", "SECOND", "GLOW_A", "GLOW_B"):
            assert len(getattr(theme, key)) == 4, (name, key)
    theme.apply(theme.DEFAULT_THEME, window=False)
    assert os.path.exists(theme.DISPLAY_FONT_FILE)


# ---------------------------------------------------------------- knowledge cards
def test_functional_nature_card_matches_bphs(chart):
    from ui.knowledge_widgets import FunctionalNatureCard
    import remedy_plan
    card = FunctionalNatureCard(chart)
    assert card.nature == remedy_plan.functional_nature(chart["ascendant"]["sign"])
    texts = _texts(card)
    assert "Jupiter" in texts and "Difficult" in texts and "Helper" in texts      # Gemini rising: Jupiter difficult, Venus helper


def test_gochara_card_shows_vedha(chart):
    import transits
    from ui.knowledge_widgets import GocharaCard
    forecast = transits.compute_transit_forecast(chart, datetime.datetime(2026, 11, 7, 12))
    card = GocharaCard(forecast)
    assert card.rows["Jupiter"] == ("blocked", ["Mars"])
    assert "Held back" in _texts(card)
    assert set(card.rows) == set(forecast["planet_transits"])


def test_strength_bars_show_drik_but_rank_by_total(chart):
    import shadbala
    from ui.knowledge_widgets import StrengthBars
    sb = shadbala.compute_shadbala(chart)
    texts = _texts(StrengthBars(sb))
    best = min(sb, key=lambda p: sb[p]["rank"])
    assert any(t.startswith(f"{sb[best]['total']:.0f} (") for t in texts)
