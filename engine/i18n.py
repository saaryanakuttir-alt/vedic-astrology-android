"""i18n.py - the app's tiny, fully OFFLINE translation layer.

Everything the app can show in Hindi or Bengali is a plain Python dict bundled
in the APK (i18n_hi.py, i18n_bn.py): no network, no translation service, no
model. English text is its own key, so a missing translation simply shows the
English original instead of failing.

    from i18n import t
    t("Home")                         -> "होम" when the language is Hindi
    t("Age {age}", age=24)            -> slots are filled after translating

Names of planets, signs and the like go through name(): name("Sun") -> "सूर्य".
"""
import importlib

LANGUAGES = [("en", "English"), ("hi", "हिन्दी"), ("bn", "বাংলা")]

_code = "en"
_tables = {}


def set_language(code):
    global _code
    _code = code if code in dict(LANGUAGES) else "en"


def get_language():
    return _code


def _table(code):
    if code not in _tables:
        try:
            _tables[code] = importlib.import_module(f"i18n_{code}").T
        except ImportError:
            _tables[code] = {}
    return _tables[code]


def t(text, **slots):
    """Translate an English string (or template with {slots}); English if there is no translation."""
    if _code != "en":
        text = _table(_code).get(text) or text
    if slots:
        try:
            return text.format(**slots)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def name(word):
    """Translate a single name (planet, sign, house word...); same lookup as t()."""
    return t(word)


def has_translation(text):
    return _code == "en" or bool(_table(_code).get(text))
