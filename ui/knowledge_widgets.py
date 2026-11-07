"""
knowledge_widgets.py - v2.3 cards that show the knowledge-base tables wired into the engine in Nov 2026:

  FunctionalNatureCard   Remedies screen: the BPHS ch.34 functional benefics, yogakarakas and difficult planets
                         for the person's ascendant (kb/functional_nature.json via remedy_plan.functional_nature)
  GocharaCard            Predictions screen: each planet's transit house from the natal Moon with its Gochara
                         verdict, including Vedha (held back) and Vipareeta Vedha (eased) (kb/gochara_vedha.json)
  StrengthBars           Planet Strength screen: each planet's comparative strength points as a bar, with its Drik
                         Bala (aspect strength) shown beside it but not counted (kb/shadbala_rules.json)

All three are plain Kivy widgets drawn with the v2.3 theme; every visible string goes through tx/tr.
"""
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)
from ui import theme

FN_STYLE = {   # functional nature -> (label, palette key)
    "yogakaraka": ("Yogakaraka", "ACCENT"),
    "benefic": ("Helper", "GOOD"),
    "neutral": ("Neutral", "NEUTRAL_600"),
    "malefic": ("Difficult", "BAD"),
    None: ("Not labelled", "NEUTRAL_500"),
}
GOCHARA_STYLE = {   # transits.gochara_verdict()["effective"] -> (label, palette key)
    "good": ("Favourable", "GOOD"),
    "blocked": ("Held back", "WARN"),
    "eased": ("Eased", "INFO"),
    "difficult": ("Effortful", "NEUTRAL_600"),
}
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _col(key):
    return getattr(theme, key)


def _label(text, size="13sp", color=None, bold=False, halign="left", height=dp(20), font_name=None):
    kw = {"font_name": font_name} if font_name else {}
    lbl = Label(text=text, font_size=size, color=color or theme.TEXT, bold=bold, halign=halign, valign="middle",
                size_hint_y=None, height=height, **kw)
    lbl.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
    return lbl


def _wrap(text, size="12.5sp", color=None):
    lbl = Label(text=text, font_size=size, color=color or theme.MUTED, halign="left", valign="top", size_hint_y=None,
                height=dp(18))
    lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)),
             texture_size=lambda inst, ts: setattr(inst, "height", max(dp(18), ts[1])))
    return lbl


class Pill(Label):
    """A small tinted status pill: coloured text on a 16% tint of the same colour."""

    def __init__(self, text, rgba, **kwargs):
        kwargs.setdefault("font_size", "11.5sp")
        kwargs.setdefault("bold", True)
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("height", dp(24))
        kwargs.setdefault("color", rgba)
        super().__init__(text=text, **kwargs)
        with self.canvas.before:
            Color(*theme._alpha(rgba, 0.16))
            self._bg = RoundedRectangle(radius=[dp(12)])
        self.bind(texture_size=lambda inst, ts: setattr(inst, "width", ts[0] + dp(18)),
                  pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size


class _Card(theme.OutlineBox):
    def __init__(self, title, note=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("padding", (dp(14), dp(12), dp(14), dp(14)))
        kwargs.setdefault("spacing", dp(8))
        super().__init__(orientation="vertical", **kwargs)
        self.bind(minimum_height=self.setter("height"))
        font = theme.display_font()
        self.add_widget(_label(title, size="18sp" if font != "Roboto" else "15sp", color=theme.ACCENT_700,
                               bold=font == "Roboto", height=dp(28), font_name=font))
        if note:
            self.add_widget(_wrap(note))


class FunctionalNatureCard(_Card):
    """The nine planets as chips coloured by their BPHS functional nature for this ascendant."""

    def __init__(self, chart, **kwargs):
        import remedy_plan
        asc = chart["ascendant"]["sign"]
        nature = remedy_plan.functional_nature(asc)
        super().__init__(tr('Helpers and difficult planets for {0} rising', asc),
                         tx("From BPHS chapter 34. Helpers and yogakarakas may be strengthened (a gemstone can be "
                            "considered); a difficult planet is eased with mantra, charity and fasting instead."),
                         **kwargs)
        grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for p in PLANETS:
            label, key = FN_STYLE.get(nature.get(p), FN_STYLE[None])
            cell = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(56), spacing=dp(2))
            with cell.canvas.before:
                Color(*theme._alpha(_col(key), 0.10))
                bg = RoundedRectangle(radius=[dp(12)])
            cell.bind(pos=lambda w, _v, r=bg: setattr(r, "pos", w.pos), size=lambda w, _v, r=bg: setattr(r, "size", w.size))
            cell.add_widget(_label(tx(p), size="13.5sp", bold=True, halign="center", height=dp(28)))
            cell.add_widget(_label(tx(label), size="11.5sp", color=_col(key), bold=True, halign="center", height=dp(20)))
            grid.add_widget(cell)
        self.add_widget(grid)
        self.nature = nature


class GocharaCard(_Card):
    """One row per planet: its sign, its house counted from the natal Moon, and the Gochara verdict."""

    def __init__(self, forecast, **kwargs):
        super().__init__(tr('Transits from your Moon ({0})', forecast["moon_sign"]),
                         tx("Classical Gochara: each planet's house counted from your birth Moon. A good transit is "
                            "held back when another planet sits in its Vedha (obstruction) house; a hard one is eased "
                            "the same way (Vipareeta Vedha)."), **kwargs)
        pt = forecast["planet_transits"]
        self.rows = {}
        for p in PLANETS:
            t = pt.get(p)
            if not t:
                continue
            status = t.get("vedha") or ("good" if t.get("favourable") else "difficult")
            label, key = GOCHARA_STYLE[status]
            by = t.get("vedha_by") or []
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8))
            col = BoxLayout(orientation="vertical", size_hint_y=None, padding=(0, dp(4)))
            col.bind(minimum_height=col.setter("height"))
            col.bind(height=lambda w, h, r=row: setattr(r, "height", max(dp(46), h)))
            col.add_widget(_label(tx(p), size="13.5sp", bold=True, height=dp(22)))
            detail = tr('{0} · {1} from Moon', tx(t["sign"]), _ordinal(t["house_from_moon"]))
            if by:
                detail += " · " + tr('{0} from {1}', tx("Vedha" if status == "blocked" else "Vipareeta Vedha"),
                                       ", ".join(tx(b) for b in by))
            col.add_widget(_wrap(detail, size="11.5sp"))
            row.add_widget(col)
            holder = BoxLayout(size_hint_x=None, width=dp(104))
            holder.add_widget(Widget())
            holder.add_widget(Pill(tx(label), _col(key), pos_hint={"center_y": 0.5}))
            row.add_widget(holder)
            self.add_widget(row)
            self.rows[p] = (status, by)


def _ordinal(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


class StrengthBars(_Card):
    """Comparative strength points as horizontal bars (longest = strongest), with Drik Bala noted but not counted."""

    def __init__(self, sb, **kwargs):
        super().__init__(tx("Strength at a glance"),
                         tx("Bars compare your seven planets with each other. Drik Bala (aspect strength) is "
                            "calculated from the BPHS rules and shown in brackets, but it is not counted in the "
                            "points until it has been checked against a reference chart."), **kwargs)
        order = sorted(sb, key=lambda p: sb[p]["rank"])
        top = max(sb[p]["total"] for p in order) or 1
        tone_key = {"Strong": "GOOD", "Average": "ACCENT", "Weaker": "WARN"}
        for p in order:
            c = sb[p]
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=dp(8))
            row.add_widget(_label(tx(p), size="13sp", bold=True, height=dp(30), halign="left"))
            track = Widget()
            colour = _col(tone_key.get(c["tone"], "ACCENT"))
            frac = max(0.04, c["total"] / top)
            with track.canvas:
                Color(*theme._alpha(theme.TEXT, 0.07))
                bg = RoundedRectangle(radius=[dp(5)])
                Color(*colour)
                fg = RoundedRectangle(radius=[dp(5)])

            def _sync(w, _v, bg=bg, fg=fg, frac=frac):
                h = dp(10)
                y = w.y + (w.height - h) / 2
                bg.pos, bg.size = (w.x, y), (w.width, h)
                fg.pos, fg.size = (w.x, y), (w.width * frac, h)

            track.bind(pos=_sync, size=_sync)
            row.add_widget(track)
            drik = c.get("drik")
            value = tr('{0:.0f}', c["total"]) + (tr(' ({0:+.0f})', drik) if drik is not None else "")
            row.add_widget(_label(value, size="12sp", color=theme.INK_SOFT, halign="right", height=dp(30)))
            row.children[2].size_hint_x = 0.28      # name
            track.size_hint_x = 0.5
            row.children[0].size_hint_x = 0.22      # value
            self.add_widget(row)
