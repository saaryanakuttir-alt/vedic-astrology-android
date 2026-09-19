"""
reading_mode.py - the Compact / Detailed switch for every long reading.

DETAILED (default) shows everything: the classical wording followed by its plain-words
explanation in [brackets]. COMPACT keeps each section's heading and only its plain-words
explanation, or, for a section that has none, just its first sentence. The choice is
remembered (settings "reading_mode") and applies to the reading screens and the PDF report.
"""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout

from ui.compact import compact_text, first_sentence  # noqa: F401 - re-exported
from ui.theme import SegmentedControl

MODES = ("Compact", "Detailed")


def current(store):
    return "compact" if store.settings.get("reading_mode", "detailed") == "compact" else "detailed"


def apply(store, text):
    """The text as the current mode wants it."""
    return compact_text(text) if current(store) == "compact" else text


class ReadingModeBar(BoxLayout):
    """A Compact | Detailed switch. `on_change()` is called after the choice is stored."""

    def __init__(self, store, on_change, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(46))
        kwargs.setdefault("padding", (dp(10), dp(4)))
        super().__init__(orientation="horizontal", **kwargs)
        self.store = store
        self.seg = SegmentedControl(list(MODES), selected=current(store).capitalize(),
                                    on_select=lambda choice: self._pick(choice, on_change))
        self.add_widget(self.seg)
        self.add_widget(BoxLayout())

    def sync(self):
        """Show the stored choice (it may have been changed on another screen)."""
        self.seg.select(current(self.store).capitalize(), notify=False)

    def _pick(self, choice, on_change):
        self.store.settings.set("reading_mode", choice.lower())
        on_change()
