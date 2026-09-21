"""i18n_hook.py - makes every piece of text Kivy DRAWS go through the translation table.

Kivy draws all text with kivy.core.text.LabelBase. Patching its refresh() translates the text at the very last
moment, so a widget's own `.text` stays the English string the program logic reads and compares (button names,
spinner values, keys) while the screen shows the translation. Text with no translation is drawn as it is.

    install()          once, before the first screen is built
"""
import i18n

_installed = False


def install():
    global _installed
    if _installed:
        return
    from kivy.core.text import LabelBase
    original = LabelBase.refresh

    def refresh(self):
        if not i18n.is_english():
            text = getattr(self, "_text", None)
            if text:
                shown = i18n.t(text)
                if shown is not text and shown != text:
                    self._text = shown
        return original(self)

    LabelBase.refresh = refresh
    _installed = True
