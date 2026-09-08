"""
tabs_help.py — the Help & FAQ tab. There's no AI and no internet access in
this app (see engine/faq_data.py's module docstring), so this isn't a
chatbot - it's the same curated, searchable Q&A guide the desktop and web
apps show, presented as expandable cards with a search box and category
filter chips rather than a flat wall of text.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.metrics import dp

from ui import theme
from ui.widgets import ChipButton, ExpandableCard
from faq_data import FAQ_CATEGORIES


class HelpTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), **kwargs)
        self._active_category = "all"

        self.add_widget(theme.SectionHeader("❓", "Help & FAQ"))

        caption = Label(
            text="Answers to the questions people ask most when they first open a "
                 "chart - no AI, no internet, just a searchable guide.",
            color=theme.MUTED, italic=True, font_size="12sp",
            size_hint_y=None, halign="left", valign="top", padding=(dp(4), dp(4)),
        )
        caption.bind(width=lambda l, w: setattr(l, "text_size", (w - dp(8), None)),
                     texture_size=lambda l, ts: setattr(l, "height", ts[1] + dp(8)))
        self.add_widget(caption)

        self.search_input = TextInput(
            hint_text="Search a question, e.g. 'dasha' or 'time zone'...",
            multiline=False, size_hint_y=None, height=dp(46),
            background_color=theme.PANEL_SOFT, foreground_color=theme.INK,
            hint_text_color=theme.MUTED, cursor_color=theme.GOLD,
            padding=(dp(12), dp(12)),
        )
        self.search_input.bind(text=lambda *_: self._refresh())
        self.add_widget(self.search_input)

        chip_scroll = ScrollView(size_hint_y=None, height=dp(44), do_scroll_y=False)
        self.chip_row = BoxLayout(orientation="horizontal", spacing=dp(8),
                                   size_hint_x=None, padding=(dp(2), dp(4)))
        self.chip_row.bind(minimum_width=self.chip_row.setter("width"))
        chip_scroll.add_widget(self.chip_row)
        self.add_widget(chip_scroll)

        self._chips = {}
        self._add_chip("all", "\U0001F5C2", "All topics")
        for cat in FAQ_CATEGORIES:
            if cat["items"]:
                self._add_chip(cat["id"], cat["icon"], cat["title"])

        list_scroll = ScrollView()
        self.list_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=(0, dp(4)))
        self.list_grid.bind(minimum_height=self.list_grid.setter("height"))
        list_scroll.add_widget(self.list_grid)
        self.add_widget(list_scroll)

        self._refresh()

    def _add_chip(self, cat_id, icon, title):
        chip = ChipButton(f"{icon} {title}")
        chip.bind(on_release=lambda *_a, cid=cat_id: self._select_category(cid))
        self.chip_row.add_widget(chip)
        self._chips[cat_id] = chip
        chip.set_active(cat_id == self._active_category)

    def _select_category(self, cat_id):
        self._active_category = cat_id
        for cid, chip in self._chips.items():
            chip.set_active(cid == cat_id)
        self._refresh()

    def _refresh(self):
        self.list_grid.clear_widgets()
        query = self.search_input.text.strip().lower()
        any_shown = False
        for cat in FAQ_CATEGORIES:
            if not cat["items"]:
                continue
            if self._active_category != "all" and cat["id"] != self._active_category:
                continue
            items = [(q, a) for q, a in cat["items"]
                     if not query or query in q.lower() or query in a.lower()]
            if not items:
                continue
            any_shown = True
            head = Label(
                text=f"{cat['icon']}  {cat['title'].upper()}", color=theme.GOLD,
                bold=True, font_size="12sp", size_hint_y=None, height=dp(30),
                halign="left", valign="middle",
            )
            head.bind(size=lambda l, s: setattr(l, "text_size", s))
            self.list_grid.add_widget(head)
            for question, answer in items:
                self.list_grid.add_widget(ExpandableCard(question, answer))
        if not any_shown:
            msg = Label(
                text=f"No questions match \"{self.search_input.text}\" - try a different word.",
                color=theme.MUTED, italic=True, font_size="13sp",
                size_hint_y=None, height=dp(60), halign="left", valign="top",
            )
            msg.bind(size=lambda l, s: setattr(l, "text_size", s))
            self.list_grid.add_widget(msg)
