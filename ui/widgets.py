"""
widgets.py — small reusable Kivy building blocks used across every tab, so
each tab module only has to describe ITS data, not re-solve "how do I show
a scrollable table" / "how do I show a scrollable block of text" every time.

Kivy has no built-in ttk.Treeview equivalent, so SimpleTable below is a
plain scrollable GridLayout: a bold header row, then one row per data row.
It's intentionally simple (no sorting/column-resize) — this app's tables
are for reading, not manipulating.
"""
import re

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.core.window import Window

from ui import theme

# Border color shows through the 1dp gaps GridLayout leaves between cells
# (see _make_cell_background below) - a plain medium gray reads as a grid
# line against either the header or data cell fill color.
_BORDER_COLOR = (0.4, 0.4, 0.45, 1)
_HEADER_BG = (0.16, 0.16, 0.2, 1)
_DATA_BG = (0.09, 0.09, 0.12, 1)


class SimpleTable(ScrollView):
    """SimpleTable(columns=["A","B"], col_hints=[0.3,0.7]) then
    .set_rows([("a1","b1"), ("a2","b2"), ...]). Pass font_size to shrink
    text for tables with many columns (e.g. Ashtakvarga's 13) - the
    default suits most of this app's tables (up to ~9 columns)."""

    def __init__(self, columns, col_hints=None, font_size="13sp", **kwargs):
        super().__init__(**kwargs)
        self.columns = columns
        self.col_hints = col_hints or [1.0 / len(columns)] * len(columns)
        self.font_size = font_size
        # spacing=dp(1) is the actual GAP between cells - it's what lets
        # the grid's own border-colored background (below) show through
        # as thin lines around every cell, so it must stay non-zero.
        self.grid = GridLayout(cols=len(columns), size_hint_y=None, spacing=dp(1))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        with self.grid.canvas.before:
            Color(*_BORDER_COLOR)
            self._grid_bg = Rectangle(pos=self.grid.pos, size=self.grid.size)
        self.grid.bind(pos=self._update_grid_bg, size=self._update_grid_bg)
        self.add_widget(self.grid)
        self._add_row(self.columns, header=True)

    def _update_grid_bg(self, instance, value):
        self._grid_bg.pos = instance.pos
        self._grid_bg.size = instance.size

    def _make_cell_background(self, label, color):
        # A filled Rectangle tracking the label's own pos/size, INSET by
        # nothing (the visible border comes from the dp(1) gap between
        # sibling cells showing the grid's own background behind them,
        # not from insetting this rectangle) - each cell just needs to be
        # opaque so it doesn't show the tab's own background through it.
        # The rect is stashed on the label itself and both pos/size bind
        # to the SAME method (_sync_cell_bg) rather than two fresh lambda
        # closures per cell - tables like Dasha can have 100+ rows (450+
        # cells), and allocating 2 new closures + 2 bind() calls for each
        # one measurably added up (~150ms for a 450-cell table even on a
        # desktop GPU; far worse on the emulator's software SwiftShader
        # renderer, where it contributed to an ANR during rapid tab-
        # switching). One shared bound method avoids that per-cell
        # closure-allocation overhead.
        with label.canvas.before:
            Color(*color)
            label._bg_rect = Rectangle(pos=label.pos, size=label.size)
        label.bind(pos=self._sync_cell_bg, size=self._sync_cell_bg)

    @staticmethod
    def _sync_cell_bg(label, value):
        label._bg_rect.pos = label.pos
        label._bg_rect.size = label.size

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
                font_size=self.font_size,
                color=(1, 0.85, 0.3, 1) if header else (1, 1, 1, 1),
                shorten=False,
            )
            self._make_cell_background(lbl, _HEADER_BG if header else _DATA_BG)
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


def _split_into_chunks(text, max_chars=400):
    """Splits text into pieces no longer than max_chars, breaking first on
    blank lines (paragraph boundaries), then, for any paragraph still over
    the limit, on sentence boundaries, packing consecutive sentences up to
    the limit. Needed because some of this project's own report sections
    (rule_engine.py's life_predictions "area" text, in particular) are one
    continuous run-on paragraph joined with plain spaces - NO newlines
    anywhere inside them - so a "\\n\\n"-only split still leaves single
    chunks of 3000-5500+ characters. See LongText.set_text's docstring for
    why keeping every chunk small is the actual point here."""
    chunks = []
    for para in (text or "").split("\n\n"):
        para = para.strip("\n")
        if not para.strip():
            continue
        if len(para) <= max_chars:
            chunks.append(para)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", para)
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) > max_chars and current:
                chunks.append(current)
                current = sentence
            else:
                current = candidate
        if current:
            chunks.append(current)
    return chunks or [""]


class LongText(ScrollView):
    """A big scrollable block of read-only wrapped text — the mobile
    equivalent of the desktop app's tk.Text widgets used for the Karmic,
    Life Predictions, Full Reading, and Family Compatibility tabs.

    Renders as MANY SMALL per-paragraph Labels in a GridLayout, not one
    single giant Label holding the whole report - see set_text's own
    comment for why: this was the actual fix, after two prior full-APK-
    build-and-device-test rounds (mutate .text in place with various
    texture-rebuild-timing fixes; then rebuild one fresh Label per
    set_text() call) both still rendered completely blank."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2), padding=(0, dp(4)))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.add_widget(self.grid)

    def set_text(self, text):
        # Splits the report into per-paragraph Labels (blank-line
        # boundaries - this project's own report-building code already
        # joins its sections with "\n\n", so this recovers exactly the
        # section/paragraph structure the text was assembled from) laid
        # out one-per-row in a GridLayout, the SAME structure SimpleTable
        # (above in this file) already uses successfully for every table
        # in this app - many small Labels, never one huge one.
        #
        # Root-caused by elimination, not by ever seeing a device log:
        # SimpleTable (many small per-cell textures) has never been
        # reported blank on this project. LongText as ONE giant Label
        # holding an entire multi-paragraph report (Life Predictions
        # alone easily wraps to 100+ lines) was blank even after being
        # rebuilt fresh every time with correct, non-zero texture_size and
        # height (confirmed via this file's OWN prior diagnostic logging
        # and a real on-device re-test) - the one thing that setup asked
        # of the GPU that SimpleTable's cells never do is one enormous
        # single glyph texture. Most Android GPUs cap a single texture's
        # dimension (2048/4096/8192px depending on hardware), and a report
        # this long, on a high-density display where Kivy's dp() scaling
        # inflates the actual pixel height further, is a real candidate
        # for quietly exceeding it - texture creation past that limit can
        # silently produce nothing to draw rather than raising a Python
        # exception, which matches every symptom seen: correct computed
        # height/texture_size, a working scrollbar, zero glyphs, and no
        # traceback anywhere. Capping each Label to one paragraph keeps
        # every individual texture small regardless of how long the
        # overall report is.
        self.grid.clear_widgets()
        paragraphs = _split_into_chunks(text)
        for para in paragraphs:
            label = Label(
                text=para, size_hint_y=None, height=dp(28), text_size=(None, None),
                halign="left", valign="top", padding=(dp(10), dp(6)),
            )
            label.bind(texture_size=self._make_resize_handler(label), width=self._on_label_width)
            self.grid.add_widget(label)
        self.scroll_y = 1  # start scrolled to the top of the new content
        Logger.info(f"VedicAstro:LongText: set_text len={len(text or '')} paragraphs={len(paragraphs)}")

    def _on_label_width(self, label, width):
        label.text_size = (width, None)

    def _make_resize_handler(self, label):
        def _resize(instance, texture_size):
            label.height = max(dp(28), texture_size[1] + dp(12))
        return _resize


class ItalicSummaryLabel(BoxLayout):
    """A single short paragraph rendered in italics - the mobile
    equivalent of a section's closing "in simple words, here's what this
    means" line (e.g. Karmic & Past Life's plain_section_summary). A thin
    BoxLayout wrapper (not a Label subclass) so set_text() can rebuild a
    fresh inner Label every call rather than mutate .text on an already-
    rendered one - see LongText's own docstring for why this project
    specifically avoids that pattern now.

    markup=True on the inner Label ONLY (never turned on for LongText's
    paragraph labels) because this project's own report text is now full
    of literal [bracketed asides] (the plain-language gists this same
    feedback round added elsewhere) - markup=True would make Kivy try to
    parse every one of those brackets as BBCode. This widget only ever
    shows one fully-controlled string (rule_engine.py's own composed
    text, never user input, never containing a literal bracket), so
    enabling markup here to get real italics is safe."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(28))
        super().__init__(**kwargs)
        self.label = None

    def set_text(self, text):
        self.clear_widgets()
        if not text:
            self.height = dp(0)
            return
        self.label = Label(
            text=f"[i]{text}[/i]", markup=True, halign="left", valign="top",
            padding=(dp(10), dp(10)), color=theme.GOLD_SOFT,
            size_hint_y=None, height=dp(28), text_size=(None, None),
        )
        self.label.bind(texture_size=self._on_texture_size, width=self._on_label_width)
        self.add_widget(self.label)

    def _on_label_width(self, label, width):
        label.text_size = (width, None)

    def _on_texture_size(self, instance, texture_size):
        self.label.height = max(dp(28), texture_size[1] + dp(20))
        self.height = self.label.height


class CaptionLabel(Label):
    """A short, plain-English one-to-three-line explainer shown at the top
    of a tab, above its table/report content - e.g. "Your planetary time-
    periods (Dasha) - a traditional system for timing when each planet's
    themes are most active in your life." Astrology has a lot of jargon
    (Ashtakvarga, Chalit, Nakshatra, Atmakaraka...); this doesn't remove
    the technical names (they stay precise and searchable for anyone who
    wants to look them up) but gives everyone a plain-language anchor
    before diving into a table full of abbreviations.

    Auto-sizes its own height to fit wrapped text, the same texture_update
    pattern LongText above uses (needed even for a caption this short -
    see LongText.set_text's own comment for why relying on Kivy's default
    post-property-change scheduling alone isn't reliable on Android)."""

    def __init__(self, text, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "top")
        kwargs.setdefault("padding", (dp(10), dp(8)))
        kwargs.setdefault("color", (0.75, 0.78, 0.85, 1))
        kwargs.setdefault("font_size", "12sp")
        kwargs.setdefault("italic", True)
        super().__init__(text=text, height=dp(28), **kwargs)
        self.bind(width=self._on_width, texture_size=self._on_texture_size)

    def _on_width(self, instance, width):
        self.text_size = (width - dp(20), None)
        # Deferred via Clock rather than calling texture_update()
        # synchronously right here, same fix and same reasoning as
        # LongText.set_text() (see its comment) - CaptionLabel's width is
        # first set the moment its tab becomes the TabbedPanel's visible
        # content, which is exactly when the TabbedPanel's OWN header
        # strip is also redrawing for the tab switch. A synchronous
        # texture_update() here lands in that same rendered frame; on
        # Android this reportedly left the header strip itself blank
        # (tab labels invisible) after sliding through several tabs -
        # never reproducible on desktop. Scheduling this for the next
        # frame keeps it out of that collision.
        Clock.schedule_once(self._rebuild_texture, 0)

    def _rebuild_texture(self, dt):
        self.texture_update()
        self.height = max(dp(28), self.texture_size[1] + dp(16))
        Logger.info(
            f"VedicAstro:CaptionLabel: rebuilt text_size={self.text_size} "
            f"texture_size={self.texture_size} texture={self.texture} height={self.height}"
        )
        # Forces a full window canvas redraw in case a texture rebuild's
        # new data isn't otherwise re-flushed to the GPU promptly - cheap,
        # harmless if unnecessary. (LongText above no longer needs this:
        # it now rebuilds a fresh Label per set_text() call rather than
        # mutating one in place - see its own _make_label docstring.)
        Window.canvas.ask_update()

    def _on_texture_size(self, instance, texture_size):
        self.height = max(dp(28), texture_size[1] + dp(16))


def _bind_label_text_size(label, *_):
    # halign/valign are no-ops in Kivy until text_size constrains the
    # label's layout box (see _add_label's docstring in tabs_chart.py for
    # the fuller explanation) - this Label's width isn't known until the
    # parent BoxLayout's own later layout pass assigns it, so text_size
    # must be set from a live width binding, not a one-time read here.
    label.text_size = (label.width, label.height)


def field_row(label_text, widget, height=dp(68)):
    """One form field: a small caption ABOVE a full-width input, not a
    cramped two-column "label | field" split (the original layout gave
    the caption ~38% of the row and squeezed every TextInput into the
    rest - fine on a desktop window, but on a phone-width column that
    left barely enough room to see what you'd typed, and every field's
    actual tap target was narrower than it needed to be). Stacking label-
    over-input is the standard modern mobile form pattern (Material/iOS
    settings-style) and, just as importantly here, it gives every input
    the FULL row width to be tapped in rather than ~60% of it - a
    concrete fix for "the buttons/fields don't work" reports that were
    really "I tried to tap the field and missed."

    CheckBox-like widgets (anything exposing a boolean `.active`, e.g.
    ThemedCheckBox) are the one exception: those render as a normal
    horizontal [box] then label row instead, since a caption stacked
    above a tiny checkbox reads oddly and every other checkbox pattern
    in mobile UI puts the label beside it, not above it.
    """
    if hasattr(widget, "active"):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        row.add_widget(widget)
        label = Label(text=label_text, halign="left", valign="middle", color=theme.INK_SOFT)
        label.bind(size=_bind_label_text_size)
        row.add_widget(label)
        return row

    row = BoxLayout(orientation="vertical", size_hint_y=None, height=height, spacing=dp(4))
    caption = Label(text=label_text, size_hint_y=None, height=dp(18), halign="left", valign="bottom",
                     font_size="12.5sp", color=theme.MUTED)
    caption.bind(size=_bind_label_text_size)
    row.add_widget(caption)
    # The input itself gets a fixed, comfortable touch height regardless
    # of what size_hint_y it arrived with (Spinner/TextInput both default
    # to size_hint_y=1, which would otherwise stretch to fill whatever's
    # left in `row` after the caption - fine today since row's height is
    # fixed, but pinning it explicitly makes every field the same
    # thumb-friendly height without depending on that).
    widget.size_hint_y = None
    widget.height = dp(46)
    row.add_widget(widget)
    return row


class ChipButton(Button):
    """A small rounded "filter chip" toggle - used for the Help & FAQ
    tab's category filter row. Not a real ToggleButton (Kivy's default
    toggle group styling is the same flat gray atlas as Button) - this
    just tracks its own `active` flag and redraws its own canvas rounded-
    rect so the selected chip visibly stands out in gold."""

    def __init__(self, text, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("height", dp(36))
        kwargs.setdefault("padding", (dp(14), 0))
        super().__init__(text=text, **kwargs)
        self.active = False
        self.font_size = "12.5sp"
        self.bold = True
        # Width follows the label's own text, plus side padding - a fixed
        # width would either clip long category names or waste space on
        # short ones.
        self.bind(texture_size=lambda *_: setattr(self, "width", self.texture_size[0] + dp(28)))
        with self.canvas.before:
            self._bg_color = Color(*theme.PANEL_SOFT)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
        self.bind(pos=self._sync, size=self._sync)
        self._apply_active()

    def _sync(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_active(self, active):
        self.active = active
        self._apply_active()

    def _apply_active(self):
        self._bg_color.rgba = theme.GOLD if self.active else theme.PANEL_SOFT
        self.color = theme.GOLD_TEXT if self.active else theme.INK_SOFT


class ExpandableCard(BoxLayout):
    """One collapsible question/answer card for the Help & FAQ tab: a
    tappable header (question + a caret) that shows/hides a wrapped
    answer label beneath it - the mobile equivalent of the desktop app's
    tk.Button-header FAQ card and the web app's .faq-card accordion."""

    def __init__(self, question, answer, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("padding", (0, 0))
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)
        self._open = False

        with self.canvas.before:
            Color(*theme.PANEL_SOFT)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.header = Button(
            text="▸  " + question, background_normal="", background_down="",
            background_color=(0, 0, 0, 0), color=theme.INK, bold=True,
            font_size="14sp", halign="left", valign="middle",
            size_hint_y=None, height=dp(52), padding=(dp(14), dp(6)),
        )
        # A fixed dp(52) height clips any question long enough to wrap to
        # two lines on a narrow phone (several of these questions run
        # 60-80+ characters - see faq_data.py) - the same class of bug
        # documented at length elsewhere in this file (CaptionLabel/
        # LongText), so this uses the same fix: bind width -> text_size,
        # then grow height to the real rendered texture_size, with the
        # texture rebuild itself deferred a frame via Clock.
        self.header.bind(width=self._on_header_width, texture_size=self._on_header_texture_size)
        self.header.bind(on_release=lambda *_: self.toggle())
        self.add_widget(self.header)

        self.answer_label = Label(
            text=answer, color=theme.INK_SOFT, font_size="13sp",
            halign="left", valign="top", size_hint_y=None, height=0,
            padding=(dp(14), dp(4)), opacity=0,
        )
        self.answer_label.bind(texture_size=self._resize_answer, width=self._update_answer_text_size)
        self.add_widget(self.answer_label)

        self.bind(minimum_height=self.setter("height"))

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _on_header_width(self, header, width):
        header.text_size = (width - dp(20), None)
        Clock.schedule_once(self._rebuild_header_texture, 0)

    def _on_header_texture_size(self, header, texture_size):
        header.height = max(dp(52), texture_size[1] + dp(20))

    def _rebuild_header_texture(self, dt):
        self.header.texture_update()
        self.header.height = max(dp(52), self.header.texture_size[1] + dp(20))

    def _update_answer_text_size(self, label, width):
        label.text_size = (width - dp(20), None)

    def _resize_answer(self, label, texture_size):
        if self._open:
            label.height = texture_size[1] + dp(16)

    def toggle(self):
        self._open = not self._open
        self.header.text = ("▾  " if self._open else "▸  ") + self.header.text[3:]
        if self._open:
            self.answer_label.opacity = 1
            self.answer_label.height = max(dp(1), self.answer_label.texture_size[1] + dp(16))
        else:
            self.answer_label.opacity = 0
            self.answer_label.height = 0
