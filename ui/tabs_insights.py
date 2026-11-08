"""
tabs_insights.py - three screens built from engine/extras.py: Doshas & Sade Sati, Planet Relations
(a plain verdict for each planet, friendships and aspects) and the Shodashvarga table (the sign of
every planet in all 15 divisional charts). Each is one scrolling page; long text follows the
Compact | Detailed switch, tables always show everything.
"""
import traceback

from kivy.app import App
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView

import extras
from astrology_tables import PLANET_ABBR, SIGN_ABBR
from ui import pdf_report, reading_mode, theme
from ui.app_state import PROFILE_LABELS
from ui.reading_mode import ReadingModeBar
from ui.widgets import CaptionLabel, FlowTable, FlowText


class _InsightPage(BoxLayout):
    """A scrolling page: caption, Compact/Detailed switch, then whatever `_build(chart, reading)` adds.
    An error is shown on the screen instead of leaving it blank."""
    caption = ""
    uses_mode = True

    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.page = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=(0, 0, 0, dp(20)))
        self.page.bind(minimum_height=self.page.setter("height"))
        scroll.add_widget(self.page)
        self.add_widget(scroll)
        self._scroll = scroll
        self.mode_bar = None

    def refresh(self):
        self.page.clear_widgets()
        self.page.add_widget(CaptionLabel(self.caption))
        if self.uses_mode:
            self.mode_bar = ReadingModeBar(self.store, self.refresh)
            self.page.add_widget(self.mode_bar)
        chart = self.store.current["chart"]
        if chart is None:
            self._text("No chart generated yet for this profile.")
            return
        try:
            self._build(chart, self.store.current["reading"])
        except Exception:  # noqa: BLE001 - show the problem on screen, never a blank page
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:{type(self).__name__}: failed:\n{tb}")
            self._text(tx("This screen hit an error while building - details below so it can be reported:\n\n") + tb)
        self._scroll.scroll_y = 1

    def _text(self, text, compactable=False):
        widget = FlowText()
        widget.set_text(reading_mode.apply(self.store, text) if compactable else text)
        self.page.add_widget(widget)

    def _card(self, widget):
        """A ready-made card (ui/knowledge_widgets.py), inset like the reading cards."""
        holder = BoxLayout(size_hint_y=None, padding=(dp(12), 0))
        widget.bind(height=lambda w, h: setattr(holder, "height", h))
        holder.height = widget.height
        holder.add_widget(widget)
        self.page.add_widget(holder)
        theme.animate_in(widget, delay=0.05)
        return widget

    def _table(self, columns, hints, rows, font_size="12sp"):
        table = FlowTable(columns, hints, font_size=font_size)
        table.set_rows(rows)
        self.page.add_widget(table)
        return table

    def _name(self, reading):
        return (reading or {}).get("name") or PROFILE_LABELS[self.store.current_profile_id]

    def _build(self, chart, reading):
        raise NotImplementedError


class DoshaTab(_InsightPage):
    caption = (
        "Doshas are classical 'watch points' in a chart. Each one below says whether it is present, "
        "what it may mean, and what can help. They describe tendencies, not fixed fate - many people "
        "with a dosha live very happily, and the rest of the chart matters more."
    )

    def _build(self, chart, reading):
        self._text(tr('=== Doshas & Sade Sati - {0} ===', self._name(reading)))
        self._text(extras.doshas_text(chart), compactable=True)
        self._text(extras.sade_sati_detail_text(chart), compactable=True)
        self._text(tx("--- Sade Sati and Dhaiya through your life (dates) ---"))
        self._text(tx("Sade Sati is Saturn's roughly 7.5-year walk over the sign before, the sign of and the sign after "
                   "your Moon. Dhaiya (Small Panoti) is its 2.5-year stay in the 4th or 8th sign from your Moon. "
                   "These are times that test patience and reward steady work - not fixed bad news. Saturn sometimes "
                   "steps back into the earlier sign for a few months, so a phase can appear twice. Dates are approximate."))
        rows = []
        for r in extras.sade_sati_table(chart):
            rows.append((r["kind"].split(" (")[0], r["phase"].replace("Saturn in the ", "Saturn "), r["sign"],
                         tr('{0:%d %b %Y}', r['start']), tr('{0:%d %b %Y}', r['end']),
                         pdf_report._age_span(r)))
        self._table(["Type", "Phase", "Saturn in", "From", "To", "Age"], [0.14, 0.24, 0.14, 0.17, 0.17, 0.14], rows, "11sp")


_FRIEND_CODE = {"Adhi Mitra": "++", "Mitra": "+", "Sama": "=", "Shatru": "-", "Adhi Shatru": "--",
                "friend": "+", "neutral": "=", "enemy": "-"}


class PlanetRelationsTab(_InsightPage):
    caption = (
        "For every planet: is it doing well in your chart (good, mixed or needs care?), what may happen "
        "because of it, and why. Below that, which planets get along with each other and which angles "
        "they make. All of this describes tendencies, never certainties."
    )

    def _build(self, chart, reading):
        self._text(tr('=== Planet by planet - {0} ===', self._name(reading)))
        period = extras.period_text(chart)
        if period:
            self._text(period, compactable=True)
        cons = extras.planet_considerations(chart)
        self._table(["Planet", "Verdict", "Sign / house", "Ruler of", "Looks at"], [0.15, 0.24, 0.26, 0.17, 0.18],
                    [(p, c["tone"], tr('{0} / {1}', c['sign'], c['house']), ", ".join(map(str, c["lord_of"])) or "-",
                      ", ".join(map(str, c["aspects_houses"]))) for p, c in cons.items()])
        self._text(extras.planet_considerations_text(chart), compactable=True)

        fr = extras.friendship_tables(chart)
        seven = list(fr["compound"])
        short = [PLANET_ABBR[p] for p in seven]
        self._text(tx("--- Which planets get along ---"))
        self._text(tx("Read each row as: how this planet feels about the planet in the column. Natural friendship is "
                   "permanent; temporary friendship depends on how close the planets sit in YOUR chart; the combined "
                   "table joins the two into one of five grades. Key: ++ great friend, + friend, = neutral, - enemy, "
                   "-- great enemy. [In simple terms: it shows which planets help each "
                   "other in your chart and which tend to work against each other.]"))
        for title, key in (("Natural friendship", "natural"), ("Temporary friendship (this chart)", "temporary"),
                           ("Combined (five-fold) friendship", "compound")):
            self._text(tr('--- {0} ---', title))
            rows = []
            for a in seven:
                row = [a]
                for b in seven:
                    row.append("." if a == b else _FRIEND_CODE[fr[key][a][b]])
                rows.append(tuple(row))
            self._table(["From"] + short, [0.15] + [0.12] * 7, rows, "10sp")

        self._text(tx("--- Angles between the planets (Western-style aspects) ---"))
        self._text(tx("Two planets at certain angles influence each other. Conjunction (together) blends them, sextile and "
                   "trine support each other, square and opposition pull against each other. Smaller 'orb' means a "
                   "stronger link. [In simple terms: 'easy' pairs tend to help you, 'tense' pairs push you to act.]"))
        rows = [(tr('{0} - {1}', a['a'], a['b']), a["aspect"], tr('{0:.1f}', a['orb']), a["flow"].capitalize()) for a in extras.western_aspects(chart)]
        self._table(["Planets", "Angle", "Orb (deg)", "Feels"], [0.34, 0.26, 0.2, 0.2], rows or [("None found", "", "", "")])


class ShodashvargaTab(_InsightPage):
    caption = (
        "The sign each planet occupies in all 15 divisional charts (each zoom-in looks at one life area). "
        "Use it to spot planets that keep landing in comfortable or uncomfortable signs across charts."
    )
    uses_mode = False

    def _build(self, chart, reading):
        self._text(tr('=== Shodashvarga table - {0} ===', self._name(reading)))
        head = ["Chart", "Asc"] + [PLANET_ABBR[p] for p in extras.BODIES]
        rows = []
        for r in extras.shodashvarga_table(chart):
            s = r["signs"]
            rows.append((r["key"], SIGN_ABBR[s["Lagna"]]) + tuple(SIGN_ABBR[s[p]] for p in extras.BODIES))
        self._table(head, [0.11, 0.09] + [0.088] * 9, rows, "10sp")
        self._text(tx("--- What each chart looks at ---"))
        self._text("\n\n".join(tr('{0} {1}: {2}.', r['key'], r['name'], r['purpose']) for r in extras.shodashvarga_table(chart)))


# ---------------------------------------------------------------- planet-by-planet effect sections
from kivy.graphics import Color, Rectangle, RoundedRectangle  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from ui import theme  # noqa: E402
from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)


class PlanetBanner(Label):
    """A tinted bar that starts each planet's section, so the planets are easy to tell apart."""

    def __init__(self, text, **kwargs):
        super().__init__(text=text, bold=True, font_size="14sp", color=theme.ACCENT_800, halign="left", valign="middle",
                         size_hint_y=None, height=dp(42), **kwargs)
        with self.canvas.before:
            Color(*theme.ACCENT_TINT)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size
        self.text_size = (self.width - dp(20), self.height)
        self.padding = (dp(10), 0)


class SectionLabel(Label):
    """The small bold label above one block of a planet's explanation (e.g. 'Sun in the 12th house')."""

    def __init__(self, text, **kwargs):
        super().__init__(text=text, bold=True, font_size="13sp", color=theme.ACCENT_700, halign="left", valign="bottom",
                         size_hint_y=None, **kwargs)
        self.bind(width=self._fit, texture_size=self._fit)

    def _fit(self, *_):
        self.text_size = (self.width - dp(8), None)
        self.height = max(dp(30), self.texture_size[1] + dp(12))


def planet_effect_widgets(store, chart, reading, focus=None):
    """A banner and labelled sections for every planet (Compact keeps 'At a glance' and 'In simple terms')."""
    import planet_effects
    compact = reading_mode.current(store) == "compact"
    widgets = []
    for e in planet_effects.planet_effects(chart, reading, focus):
        widgets.append(PlanetBanner(e["banner"]))
        for label, text in e["sections"]:
            if compact and label not in (planet_effects.GLANCE, planet_effects.SIMPLE):
                continue
            widgets.append(SectionLabel(label))
            body = FlowText()
            body.set_text(text)
            widgets.append(body)
    return widgets


# ---------------------------------------------------------------- Yogini, Char dasha and Jaimini
class MoreDashaTab(_InsightPage):
    caption = (
        "Two more ways of dividing life into periods (Yogini Dasha and Jaimini's Char Dasha), what each Vimshottari "
        "period may feel like, and your Jaimini soul-planet (Atmakaraka) with its Karakamsa chart. All are tendencies to "
        "reflect on, not fixed events; dates are approximate."
    )

    def _build(self, chart, reading):
        import datetime
        import more_dashas as md
        from ui.tabs_chart import ChartCanvas
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        fmt = lambda d: tr('{0:%d %b %Y}', d)
        self._text(tr('=== More dashas and Jaimini - {0} ===', self._name(reading)))
        self._text(md.mahadasha_text(chart), compactable=True)

        self._text(tx("--- Yogini Dasha (a 36-year cycle of eight periods) ---"))
        self._text(tx("[In simple terms: each 'yogini' colours a stretch of life - Mangala for good fortune, Pingala for effort, "
                   "Dhanya for money and comfort, Bhramari for change, Bhadrika for steady gains, Ulka for pressure, Siddha for "
                   "achievement and Sankata for obstacles that ask for patience.]"))
        yog = md.yogini_dasha(chart)
        self._table(["Yogini", "From", "To", "Years", "Feels like"], [0.17, 0.2, 0.2, 0.1, 0.33],
                    [(y["name"] + (" (now)" if y["start"] <= now < y["end"] else ""), fmt(y["start"]), fmt(y["end"]),
                      y["years"], md._YOGINI_MEANING[y["name"]]) for y in yog], "11sp")
        run = next((y for y in yog if y["start"] <= now < y["end"]), None)
        if run:
            self._text(tr('--- Sub-periods inside the running {0} period ---', run['name']))
            self._table(["Sub-period", "From", "To"], [0.4, 0.3, 0.3],
                        [(a["name"], fmt(a["start"]), fmt(a["end"])) for a in run["antardashas"]], "11sp")

        self._text(tx("--- Char Dasha (Jaimini, counted by signs from your Lagna) ---"))
        self._text(tx("[In simple terms: instead of planets, each period belongs to a zodiac sign, starting with your rising sign. "
                   "The sign's house in your chart shows which area of life is in focus during that period.]"))
        chd = md.char_dasha(chart)
        self._table(["Sign", "Years", "From", "To"], [0.3, 0.14, 0.28, 0.28],
                    [(c["sign"] + (" (now)" if c["start"] <= now < c["end"] else ""), c["years"], fmt(c["start"]), fmt(c["end"]))
                     for c in chd], "11sp")
        crun = next((c for c in chd if c["start"] <= now < c["end"]), None)
        if crun:
            self._text(tr('--- Sub-periods inside the running {0} period ---', crun['sign']))
            self._table(["Sub-period", "From", "To"], [0.4, 0.3, 0.3],
                        [(a["sign"], fmt(a["start"]), fmt(a["end"])) for a in crun["antardashas"]], "11sp")

        self._text(tx("--- Jaimini significators (Chara Karakas) ---"))
        self._table(["Role", "Planet", "Stands for"], [0.3, 0.2, 0.5],
                    [(k["role"], k["chara"], k["meaning"]) for k in md.karakas(chart)], "11sp")
        self._text(tx("--- Karakamsa ---"))
        self._text(md.karakamsa_text(chart), compactable=True)
        view = md.with_karakamsa(chart)
        canvas = ChartCanvas(size_hint_y=None, height=dp(340))
        canvas.set_chart(view, "KM", self.store.chart_style)
        self.page.add_widget(canvas)


# ---------------------------------------------------------------- Your Nature, Varshaphal, KP, Planet Strength, Ashtakvarga detail
class NatureTab(_InsightPage):
    caption = ("Your character, mind, career leanings, learning style and hobbies, in plain words, drawn from your rising sign, "
               "Moon, nakshatra and the planets that rule those areas. These are tendencies, not rules.")

    def _build(self, chart, reading):
        import life_profile
        self._text(tr('=== Your nature - {0} ===', self._name(reading)))
        self._text(life_profile.profile_text(chart), compactable=True)


class StrengthTab(_InsightPage):
    caption = ("How strong each planet is in your chart, from the classical sources of strength (exaltation, divisional charts, house and "
               "direction, time of birth, Moon phase and natural strength). Scores compare the planets of YOUR chart with each other.")

    def _build(self, chart, reading):
        import shadbala
        sb = shadbala.compute_shadbala(chart)
        order = sorted(shadbala.SEVEN, key=lambda p: sb[p]["rank"])
        self._text(tr('=== Planet strength - {0} ===', self._name(reading)))
        from ui.knowledge_widgets import StrengthBars
        self._card(StrengthBars(sb))
        self._table(["Planet", "Rank", "Strength", "Points"], [0.3, 0.15, 0.3, 0.25],
                    [(p, sb[p]["rank"], sb[p]["tone"], tr('{0:.0f}', sb[p]['total'])) for p in order])
        self._text(shadbala.shadbala_text(chart), compactable=True)
        self._text(tx("--- Points from each source ---"))
        head = ["Source"] + [p[:3] for p in shadbala.SEVEN]
        rows = [(label.split(" (")[0],) + tuple(tr('{0:.0f}', sb[p][key]) for p in shadbala.SEVEN) for key, label in shadbala.COMPONENTS]
        rows.append(("Total",) + tuple(tr('{0:.0f}', sb[p]['total']) for p in shadbala.SEVEN))
        rows.append(("Drik *",) + tuple(tr('{0:+.0f}', sb[p]['drik']) for p in shadbala.SEVEN))
        self._table(head, [0.28] + [0.103] * 7, rows, "10sp")
        self._text(tx("* Drik Bala (aspect strength) is now calculated from the classical rules (BPHS chapter 27) and shown "
                   "for reference, but it is not added to the total until it has been checked against a reference chart.") +
                   "\n\n" +
                   tx("Not counted: the year and month lords, planetary speed, aspect strength and planetary war, which need extra tables. "
                   "So read these as comparisons between your own planets, not as the traditional 'rupa' totals."))


class PrastaraTab(_InsightPage):
    caption = ("Prastharashtakvarga shows WHO gives each point in a planet's Ashtakvarga row. For each planet, every helper "
               "(the other planets and the Lagna) gives a point (1) to some signs and none (.) to others; the last row is the "
               "planet's usual Ashtakvarga row. A sign with more points is friendlier for that planet. Above that: the "
               "classical reductions of each row, the Shodhya Pinda, and the Kakshya each planet is passing through now.")
    uses_mode = False

    def _build(self, chart, reading):
        import datetime

        import ashtakvarga_reductions as red
        import prastara
        from panchanga import SIGNS
        self._text(tr('=== Ashtakvarga detail - {0} ===', self._name(reading)))
        r = red.reductions(chart)
        self._text(tx("--- Reduced points (Trikona and Ekadhipatya Shodhana) ---") + "\n" +
                   tx("Classical texts first 'reduce' each planet's row: points shared by a group of trine signs are taken "
                      "out (Trikona), then points doubled up between the two signs one planet rules (Ekadhipatya). What "
                      "is left shows where each planet's support is really concentrated, and is what the timing rules use.") +
                   "\n" + tx("[In simple terms: a higher reduced number means that sign is a genuinely strong place for "
                              "that planet in your chart; 0 means no special support.]"))
        rows = [(p,) + tuple(str(r[p]["ekadhipatya"][s]) for s in SIGNS) for p in red.PLANET_ORDER]
        rows.append(("Sarva",) + tuple(str(r["sarva_reduced"][s]) for s in SIGNS))
        self._table(["Planet"] + [s[:3] for s in SIGNS], [0.16] + [0.07] * 12, rows, "10sp")
        self._text(tx("--- Shodhya Pinda ---") + "\n" +
                   tx("Each reduced sign figure multiplied by the sign's classical multiplier (Rasi Pinda), plus the "
                      "figures of the signs the planets occupy multiplied by each planet's multiplier (Graha Pinda). "
                      "Classical texts use the total in their timing arithmetic; it is shown here as a figure only."))
        self._table(["Planet", "Rasi Pinda", "Graha Pinda", "Shodhya Pinda"], [0.28, 0.24, 0.24, 0.24],
                    [(p, r[p]["rasi_pinda"], r[p]["graha_pinda"], r[p]["shodhya_pinda"]) for p in red.PLANET_ORDER])
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        k = red.kakshya_now(chart, now)
        self._text(tx("--- Kakshya: where each planet is passing now ---") + "\n" +
                   tr('Each sign is split into eight parts of 3 deg 45 min (Kakshyas), ruled in turn by Saturn, Jupiter, '
                      'Mars, the Sun, Venus, Mercury, the Moon and the Lagna. When a planet passes through a part whose '
                      'ruler gave that sign a point in the planet\'s own row, the stretch is traditionally favourable. '
                      'As of {0:%d %b %Y}:', now))
        self._table(["Planet", "In", "Kakshya", "Ruler gives point?", "Points"], [0.17, 0.22, 0.25, 0.22, 0.14],
                    [(p, tr('{0} {1}°', tx(t["sign"]), int(t["degree"])), tr('{0} ({1})', t["kakshya"], t["lord"]),
                      tx("Yes") if t["lord_gives_point"] else tx("No"), t["bindus"]) for p, t in k.items()])
        self._text(tx("--- Who gives each point ---"))
        for planet, grid in prastara.all_prastara(chart).items():
            self._text(tr('--- {0} ---', planet))
            rows = [(c,) + tuple("1" if v else "." for v in r_) for c, r_ in grid["rows"].items()]
            rows.append(("Total",) + tuple(str(t) for t in grid["totals"]))
            self._table(["From"] + [s[:3] for s in SIGNS], [0.16] + [0.07] * 12, rows, "10sp")


class KPTab(_InsightPage):
    caption = ("Krishnamurti Paddhati (KP): every point of the zodiac has a sign lord, a star (nakshatra) lord and a sub lord. KP "
               "reads a house by the star and sub lord of its cusp. Uses Placidus houses and the KP ayanamsa. Positions differ from the "
               "main chart by a few arc-minutes, which can change the sub lord.")

    def _build(self, chart, reading):
        import kp
        t = kp.kp_tables(chart)
        ab = lambda p: p[:3]
        self._text(tr('=== KP system - {0} ===', self._name(reading)))
        self._text(tr('KP ayanamsa: {0}.\n\n[In simple terms: the star lord shows the kind of result a house or planet '
                      'is linked to, and the sub lord decides whether that result is likely to come through. It is a '
                      'table for astrologers who use KP; treat it as extra detail, not a verdict.]', t['ayanamsa_dms']), compactable=True)
        self._text(tx("--- Cusps (house starting points) ---"))
        self._table(["House", "Degree", "Sign lord", "Star", "Sub", "Sub-sub"], [0.11, 0.25, 0.16, 0.16, 0.16, 0.16],
                    [(c["cusp"], c["dms"], ab(c["sign_lord"]), ab(c["star_lord"]), ab(c["sub_lord"]), ab(c["subsub_lord"])) for c in t["cusps"]], "11sp")
        self._text(tx("--- Planets ---"))
        self._table(["Planet", "Degree", "House", "Sign lord", "Star", "Sub", "Sub-sub"], [0.14, 0.23, 0.1, 0.14, 0.13, 0.13, 0.13],
                    [(p["planet"][:3] + ("R" if p["retrograde"] else ""), p["dms"], p["house"], ab(p["sign_lord"]), ab(p["star_lord"]),
                      ab(p["sub_lord"]), ab(p["subsub_lord"])) for p in t["planets"]], "10sp")
        r = t["ruling"]
        self._text(tx("--- Ruling planets ---\nLagna (sign, star, sub lord): ") + ", ".join(tx(x) for x in r["Lagna"]) + tx(". Moon (sign, star, sub lord): ") +
                   ", ".join(tx(x) for x in r["Moon"]) + tr('. Weekday lord: {0}.\n\n[In simple terms: these are the planets KP astrologers treat as most '
                                             'active at the time and place of your birth.]', r['Day lord']), compactable=True)
        self._text(tx("--- Planets linked with each house (significators, strongest first) ---"))
        self._table(["House", "Signified by"], [0.2, 0.8], [(h, ", ".join(x[:3] for x in pl)) for h, pl in t["significators"].items()], "11sp")
        _kp_cusp_readings(self, t)
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        fmt = lambda d: tr('{0:%d %b %Y}', d)
        dasha = kp.kp_dasha(chart)
        self._text(tx("--- KP Vimshottari periods (KP Moon) ---\nSame planetary periods as the main Dasha but counted from the KP Moon, so "
                   "dates can differ from the main chart by a few days. [In simple terms: the running period shows which planet's KP themes are "
                   "active now.]"), compactable=True)
        self._table(["Main period", "From", "To"], [0.34, 0.33, 0.33],
                    [(m["lord"] + (" (now)" if m["start"] <= now < m["end"] else ""), fmt(m["start"]), fmt(m["end"])) for m in dasha[:9]], "11sp")
        run = next((m for m in dasha if m["start"] <= now < m["end"]), None)
        if run:
            ant = next((a for a in run["antardashas"] if a["start"] <= now < a["end"]), None)
            self._text(tr('--- Sub-periods inside the running {0} period ---', run['lord']))
            self._table(["Sub-period", "From", "To"], [0.34, 0.33, 0.33],
                        [(a["lord"] + (" (now)" if a is ant else ""), fmt(a["start"]), fmt(a["end"])) for a in run["antardashas"]], "11sp")
            if ant:
                self._text(tr('--- Smallest periods inside {0} / {1} ---', run['lord'], ant['lord']))
                self._table(["Pratyantar", "From", "To"], [0.34, 0.33, 0.33],
                            [(x["lord"], fmt(x["start"]), fmt(x["end"])) for x in ant["pratyantars"]], "11sp")


def _houses(hs):
    return ", ".join(str(h) for h in hs) if hs else tx("none")


def kp_verdict_text(j):
    """One plain paragraph for a KP judgement (kp_judgement.judge)."""
    m = j["matter"]
    head = {"promised": tx("Promised"), "mixed": tx("Promised, with obstacles"), "weak": tx("Weak support"),
            "not_shown": tx("Not clearly shown")}[j["verdict"]]
    if j["verdict"] == "promised":
        body = tr('The sub lord {0} links to houses {1} through its star lord {2}, and to nothing that works against it.',
                  j["sub_lord"], _houses(j["for"]), j["star_lord"])
    elif j["verdict"] == "mixed":
        body = tr('The sub lord {0} links to houses {1}, but also to {2}, which work against it. Expect delays or extra effort.',
                  j["sub_lord"], _houses(j["for"]), _houses(j["against"]))
    elif j["verdict"] == "weak":
        body = tr('Only the sub lord {0} itself links to houses {1}; its star lord {2} does not, so this needs the right period to show.',
                  j["sub_lord"], _houses(j["for"]), j["star_lord"])
    else:
        body = tr('The sub lord {0} does not link to houses {1}, the houses this matter needs.', j["sub_lord"], _houses(m["houses"]))
    retro = {"retro_self": tx(" The sub lord is retrograde, which KP reads as delay."),
             "retro_star": tx(" The sub lord is in the star of a retrograde planet, which KP reads as delay.")}.get(j["retro"], "")
    return f"[{head}: {tx(m['title'])} - {tr('houses {0}', _houses(m['houses']))}. {body}{retro}]"


def _kp_cusp_readings(page, t):
    import kp_judgement as kj
    page._text(tx("--- What each cusp's sub lord says ---\nIn KP the sub lord of a cusp decides whether that house's matters "
                  "come through. It is judged by the houses its star lord sits in and owns (the main level) and by the houses "
                  "it sits in and owns itself (a weaker level). Houses that are 12th from the needed ones work against the matter.\n\n"
                  "[In simple terms: \"Promised\" means the chart supports it; it still comes in the right period. \"Not clearly "
                  "shown\" means KP does not see it from this cusp alone. It is a tendency, not a verdict.]"), compactable=True)
    readings = kj.cusp_readings(t)
    page._table(["Cusp", "Sub lord", "Via star lord", "Own houses"], [0.13, 0.2, 0.35, 0.32],
                [(r["cusp"], r["sub_lord"][:3], tr('{0}: {1}', r["star_lord"][:3], _houses(r["star"])), _houses(r["own"]))
                 for r in readings], "11sp")
    for r in readings:
        lines = [tr('--- Cusp {0}: {1} ---', r["cusp"], tx(r["theme"]))]
        for j in r["judgements"]:
            lines.append(kp_verdict_text(j))
            who = kj.timing_planets(t, j["matter"]["id"])
            if who:
                lines.append(tr('Periods that can bring it: {0}.', ", ".join(tx(p) for p in who)))
        if not r["judgements"]:
            lines.append(tr('The sub lord {0} gives houses {1} through its star lord {2}.', r["sub_lord"], _houses(r["star"]), r["star_lord"]))
        page._text("\n".join(lines), compactable=True)


class KPHoraryTab(_InsightPage):
    caption = ("KP horary (prashna): hold one clear question in mind, think of a number from 1 to 249 and pick the matter it is "
               "about. The number fixes the rising point of a chart cast for this moment, and the sub lord of the matter's cusp "
               "answers. No birth details are needed. One sincere question at a time; a tendency, not a certainty.")
    number = None
    matter_id = "career"
    show_table = False

    def _build(self, chart, reading):
        import datetime
        import kp_judgement as kj
        from ui.theme import ThemedButton, ThemedSpinner, ThemedTextInput
        loc = chart["resolved_location"]
        titles = {tx(m["title"]): m["id"] for m in kj.matters()}
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8), padding=(dp(12), 0))
        field = ThemedTextInput(multiline=False, input_filter="int", kb_layout="number", hint_text=tx("1 to 249"),
                                text=str(self.number or ""), size_hint_x=0.32)
        pick = ThemedSpinner(text=tx(kj.matter(self.matter_id)["title"]), values=list(titles), size_hint_x=0.68)
        row.add_widget(field)
        row.add_widget(pick)
        self.page.add_widget(row)
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8), padding=(dp(12), 0))
        ask = ThemedButton(text=tx("Judge the question"), variant="primary")
        table_btn = ThemedButton(text=tx("Hide the 1-249 table") if self.show_table else tx("Show the 1-249 table"))
        buttons.add_widget(ask)
        buttons.add_widget(table_btn)
        self.page.add_widget(buttons)

        def judge(*_):
            try:
                n = int(field.text or 0)
            except ValueError:
                n = 0
            self.number = n if 1 <= n <= 249 else None
            self.matter_id = titles.get(pick.text, self.matter_id)
            self.refresh()

        def toggle(*_):
            self.show_table = not self.show_table
            self.refresh()

        ask.bind(on_release=judge)
        table_btn.bind(on_release=toggle)
        if self.number is None:
            self._text(tx("Enter a number from 1 to 249, choose the matter and tap \"Judge the question\"."))
        else:
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            h = kj.horary_judgement(self.number, self.matter_id, now, loc["latitude"], loc["longitude"], loc.get("tz_name"))
            t, j = h["tables"], h["judgement"]
            r = t["row"]
            self._text(tr('=== KP horary number {0} ===', self.number))
            self._text(tr('Rising point: {0} (sign lord {1}, star lord {2}, sub lord {3}). Judged at {4:%d %b %Y %H:%M} for {5}.\n\n'
                          '[Place: The chart uses the place saved in this profile. KP casts the horary chart for where the question '
                          'is judged, so use a profile for your current town if you are elsewhere.]',
                          "{0} {1} - {2}".format(tx(kj.horary_row_parts(r)[0]), *kj.horary_row_parts(r)[1:]), r["sign_lord"], r["star_lord"], r["sub_lord"], t["local"],
                          loc.get("matched_name") or loc.get("place_name_as_entered") or ""), compactable=True)
            self._text(tr('--- The answer: {0} (cusp {1}) ---', tx(j["matter"]["title"]), j["cusp"]) + "\n" + kp_verdict_text(j))
            rp = t["ruling"]
            names = ", ".join(tx(x) for x in sorted(kj.ruling_set(t)))
            self._text(tr('Ruling planets now: {0}.', names) + " " +
                       (tx("The deciding planet is among them, which KP takes as confirmation.") if h["in_ruling"] else
                        tx("The deciding planet is not among them, so KP would treat the answer with less confidence.")) +
                       ("\n" + tr('Periods or days ruled by these planets can bring it: {0}.', ", ".join(tx(p) for p in h["timing"]))
                        if h["timing"] and j["verdict"] in ("promised", "mixed") else ""), compactable=True)
            ab = lambda p: p[:3]
            self._text(tx("--- Horary cusps ---"))
            self._table(["House", "Degree", "Sign lord", "Star", "Sub"], [0.13, 0.27, 0.2, 0.2, 0.2],
                        [(c["cusp"], c["dms"], ab(c["sign_lord"]), ab(c["star_lord"]), ab(c["sub_lord"])) for c in t["cusps"]], "11sp")
            self._text(tx("--- Planets now ---"))
            self._table(["Planet", "Degree", "House", "Star", "Sub"], [0.17, 0.27, 0.14, 0.21, 0.21],
                        [(p["planet"][:3] + ("R" if p["retrograde"] and p["planet"] not in ("Rahu", "Ketu") else ""), p["dms"],
                          p["house"], ab(p["star_lord"]), ab(p["sub_lord"])) for p in t["planets"]], "11sp")
        if self.show_table:
            self._text(tx("--- The 1-249 table ---\nEach number is one KP sub. The six subs that cross from one sign into the next "
                          "are counted once on each side, which is why there are 249 and not 243."))
            self._table(["No.", "From - to", "Sign", "Star", "Sub"], [0.1, 0.42, 0.16, 0.16, 0.16],
                        [(x["number"], "{1} - {2}".format(*kj.horary_row_parts(x)), x["sign"][:3], x["star_lord"][:3], x["sub_lord"][:3])
                         for x in kj.HORARY], "10sp")


class LalKitabTab(_InsightPage):
    caption = ("Lal Kitab is a separate system of astrology with its own rules. Its chart keeps every planet in the same house as "
               "your birth chart, but reads the houses as fixed (house 1 is always Aries). It judges each planet by its house, finds "
               "family debts (rin), runs a 35-year planetary cycle and a yearly chart from a fixed 120-year table. Its remedies are "
               "traditional and optional, never a cure or a guarantee.")
    year_no = None

    _STANDING = {"pakka": "Own house (pakka ghar)", "exalted": "Exalted", "debilitated": "Debilitated", "good": "Good house",
                 "weak": "Weak house", "neutral": "Neutral"}

    def _build(self, chart, reading):
        import datetime
        import lal_kitab as lk
        from ui.theme import ThemedSpinner
        today = datetime.date.today()
        x = lk.lal_kitab(chart, today)
        self._text(tr('=== Lal Kitab - {0} ===', self._name(reading)))
        self._text(tx("--- How each planet stands ---\nA planet in its own permanent house (pakka ghar) or its house of exaltation "
                      "gives good results; in its house of debilitation or a weak house it needs support. Planets sharing a house "
                      "affect each other: friends help, enemies spoil each other's results."), compactable=True)
        self._table(["Planet", "House", "Standing", "Shares with"], [0.18, 0.14, 0.38, 0.3],
                    [(p["planet"], p["house"], tx(self._STANDING[p["status"]]), ", ".join(q[:3] for q in p["with"]) or "-")
                     for p in x["placements"]], "11sp")
        for p in x["placements"]:
            r = lk.reading(p["planet"], p["house"], p["with"])
            lines = [tr('--- {0} in house {1} ---', p["planet"], p["house"]),
                     tr('{0} stands for {1}. House {2} covers {3}.', p["planet"], tx(r["stands_for"]), p["house"], tx(r["house_area"])),
                     tx(r["status_text"]).replace("{p}", tx(p["planet"]))]
            if r["friends_with"]:
                lines.append(tr('It shares the house with its friend(s) {0}, which helps.', ", ".join(tx(q) for q in r["friends_with"])))
            if r["enemies_with"]:
                lines.append(tr('It shares the house with its enemy(ies) {0}, which can spoil some of its results.',
                                ", ".join(tx(q) for q in r["enemies_with"])))
            if r["remedy"]:
                lines.append(tr('[Remedy: {0}]', tx(r["remedy"])))
            self._text("\n".join(lines), compactable=True)
        self._text(tx("--- Family debts (rin) ---\nLal Kitab says some placements show a debt carried by the family line. Each "
                      "debt follows one rule: a planet's own houses are disturbed by that planet's enemies. The traditional remedy is a "
                      "shared act: every family member gives an equal share, and it is given away together on one day."), compactable=True)
        if x["debts"]:
            for d in x["debts"]:
                self._text(tr('--- {0} ({1}) ---\nShown by {2} in house {3}. {4}\n[Remedy: {5}]', tx(d["name"]), tx(d["meaning"]),
                              ", ".join(tx(b) for b in d["by"]), ", ".join(str(x["houses"][b]) for b in d["by"]), tx(d["why"]),
                              tx(d["remedy"])), compactable=True)
        else:
            self._text(tx("No Lal Kitab debt (rin) is shown in this chart."))
        cyc = x["cycle"]
        self._text(tr('--- The 35-year cycle (cycle {0}) ---\nLal Kitab gives each planet a fixed stretch of years, the same order for '
                      'everyone, repeating every 35 years. The planet running now colours the period through the house it sits in.',
                      cyc["cycle_no"]), compactable=True)
        fmt = lambda d: tr('{0:%d %b %Y}', datetime.datetime(d.year, d.month, d.day))
        self._table(["Planet", "Years", "From", "To"], [0.28, 0.14, 0.29, 0.29],
                    [(tx(p["planet"]) + tx(" (now)") if p["now"] else tx(p["planet"]), p["years"], fmt(p["start"]), fmt(p["end"]))
                     for p in cyc["periods"]], "11sp")
        now = next((p for p in cyc["periods"] if p["now"]), None)
        if now:
            st, tone = lk.status(now["planet"], x["houses"][now["planet"]])
            self._text(tr('[Now: The {0} period. {0} sits in house {1} ({2}), so this stretch is felt through {3}.]', now["planet"],
                          x["houses"][now["planet"]], tx(self._STANDING[st]).lower(), tx(lk.data()["houses"][str(x["houses"][now["planet"]])])))
        # Varshphal
        birth_year = int(chart["birth_input"]["birth_date"][:4])
        if self.year_no is None:
            self.year_no = min(max(x["running_year"], 1), 120)
        labels = {n: tr('Year {0} of life (age {1}-{2})', n, n - 1, n) for n in range(1, 121)}
        self._text(tx("--- Lal Kitab Varshphal (yearly chart) ---\nEach year of life the planets move to new houses by a fixed "
                      "120-year table; the year runs from one birthday to the next. Pick the year below."), compactable=True)
        spinner = ThemedSpinner(text=labels[self.year_no], values=list(labels.values()), size_hint_y=None, height=dp(44))
        by_label = {v: k for k, v in labels.items()}
        spinner.bind(text=lambda inst, text: self._pick(by_label.get(text)))
        self.page.add_widget(spinner)
        vp = lk.varshphal(chart, self.year_no)
        self._text(tr('Year {0} of life: {1} to {2}.', self.year_no, fmt(vp["start"]), fmt(vp["end"])))
        self._table(["Planet", "Birth house", "This year", "Standing"], [0.2, 0.2, 0.2, 0.4],
                    [(m["planet"], m["birth_house"], m["year_house"], tx(self._STANDING[pl["status"]]))
                     for m, pl in zip(vp["moves"], vp["placements"])], "11sp")
        good = [pl["planet"] for pl in vp["placements"] if pl["tone"] == "good"]
        care = [pl["planet"] for pl in vp["placements"] if pl["tone"] == "care"]
        line = []
        if good:
            line.append(tr('Well placed this year: {0}.', ", ".join(tx(p) for p in good)))
        if care:
            line.append(tr('Needs support this year: {0}; their remedies above help.', ", ".join(tx(p) for p in care)))
        self._text(" ".join(line) or tx("No planet is especially strong or weak this year."))

    def _pick(self, year_no):
        if year_no and year_no != self.year_no:
            self.year_no = year_no
            self.refresh()


class PracticesTab(_InsightPage):
    caption = ("Meditation, breath and yoga practices matched to your chart: for the planets that need support right now, for your "
               "running periods, for your Moon's temperament, and sized for your stage of life. The practices come from classical "
               "yoga texts; matching them to planets is a modern Jyotish-Ayurveda approach. Traditional guidance, not medical "
               "treatment.")
    show_advanced = False

    def _practice_text(self, pr, heading=None):
        import practices
        body = [tx(pr["why"]),
                tr('{0} · {1} · about {2} minutes a day', tx(pr["kind"]), tx(practices.data()["levels"][pr["level"]]), pr["minutes_now"])]
        body += [tr('{0}. {1}', n, tx(step)) for n, step in enumerate(pr["steps"], start=1)]
        tail = ([tr('[Caution: {0}]', " ".join(tx(c) for c in pr["caution_text"]))] if pr["caution_text"] else []) + \
            [tr('[Source: {0}]', tx(pr["source"]))]
        return (heading or tr('--- {0} ---', tx(pr["name"]))) + "\n" + "\n\n".join(body) + "\n" + "\n".join(tail)

    def _build(self, chart, reading):
        import practices
        from ui.theme import ThemedButton
        plan = practices.practice_plan(chart, reading)
        band = plan["band"]
        self._text(tr('=== Meditation & practice - {0} ===', self._name(reading)))
        self._text(tr('--- Your stage of life: {0} (age {1}) ---\n{2}', tx(band["label"]), plan["age"], tx(band["advice"])) +
                   "\n" + tr('[Safety: {0}]', tx(plan["safety"])))
        r = plan["routine"]
        self._text(tr('--- A simple daily routine (about {0} minutes) ---', r["total_minutes"]) + "\n" +
                   tr('Morning: {0}.', ", ".join(tr('{0} ({1} min)', tx(x["name"]), x["minutes_now"]) for x in r["morning"])) + "\n" +
                   tr('Evening: {0}.', ", ".join(tr('{0} ({1} min)', tx(x["name"]), x["minutes_now"]) for x in r["evening"])) + "\n" +
                   tx("[In simple terms: a short practice done every day helps more than a long one done now and then. Start small and "
                      "add time only when it feels easy.]"))
        base = plan["base"]
        self._text(self._practice_text(base["practice"], tr('--- Your base practice: {0} ---', tx(base["practice"]["name"]))) +
                   "\n" + tr('[Why this one: {0}]', tx(base["why"])), compactable=True)
        if plan["focus"]:
            self._text(tx("--- Planets that need support now ---\nThese planets are weak or troubled in your chart and active in "
                          "your life right now (the same planets the Remedies screen lists). Their practices work on the qualities "
                          "the planet stands for."))
            for f in plan["focus"]:
                head = tr('--- For {0}: {1} ---', tx(f["planet"]), tx(f["theme"]))
                intro = tr('Why now: {0}. Its traditional day is {1}.', f["why"], tx(f["day"])) + (
                    "\n" + tr('[Mantra: {0}]', f["mantra"]) if f["mantra"] else "")
                self._text(head + "\n" + intro, compactable=True)
                for pr in f["practices"]:
                    self._text(self._practice_text(pr), compactable=True)
        else:
            self._text(tx("--- Planets that need support now ---\nNo planet is both troubled and active for you right now, so the "
                          "practices below follow your running periods instead."))
        for per in plan["periods"]:
            head = tr('--- For your {0}: {1} ---', tx(per["label"]), tx(per["planet"]))
            intro = tr('{0} runs until {1:%b %Y}. Working with it supports {2}. Its traditional day is {3}.', tx(per["planet"]),
                       per["until"], tx(per["theme"]), tx(per["day"])) + ("\n" + tr('[Mantra: {0}]', per["mantra"]) if per["mantra"] else "")
            self._text(head + "\n" + intro, compactable=True)
            for pr in per["practices"]:
                self._text(self._practice_text(pr), compactable=True)
        k = plan["kundalini"]
        self._text(tx("--- The Kundalini path ---\nKundalini yoga works with energy said to rest at the base of the spine. The classical "
                      "texts teach it in stages: first steady breath awareness and attention to the energy centres, and only later "
                      "the locks (bandhas) and breath holding, under a teacher. Begin with the two gentle practices below and keep "
                      "them up for several months before going further."))
        for pr in k["gentle"]:
            self._text(self._practice_text(pr), compactable=True)
        if not k["advanced_allowed"]:
            self._text(tr('[Advanced practices: {0}]', tx("The locks and breath holding are not shown for your stage of life; the "
                                                         "gentle practices above are the safe way to work with this path.")))
            return
        btn = ThemedButton(text=tx("Hide advanced Kundalini practices") if self.show_advanced else tx("Show advanced Kundalini practices"),
                           size_hint_y=None, height=dp(44))

        def toggle(*_):
            self.show_advanced = not self.show_advanced
            self.refresh()

        btn.bind(on_release=toggle)
        holder = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(12), 0))
        holder.add_widget(btn)
        self.page.add_widget(holder)
        if self.show_advanced:
            self._text(tx("--- Before you start the advanced practices ---\n[Warning: These are powerful classical techniques. Learn "
                          "them from a qualified teacher in person. Do not practise them if you are pregnant, have high or low blood "
                          "pressure, heart disease, glaucoma, epilepsy, a hernia, recent surgery, or a history of panic attacks, "
                          "psychosis or bipolar disorder. Stop at once if you notice headaches, a racing heart, sleeplessness, strong "
                          "anxiety, shaking or heat that does not settle.]\nPractise them in this order, each only once the one "
                          "before is easy: the root lock, the chin lock, the abdominal lock, gentle breath holding, then the three "
                          "locks together."))
            for pr in k["advanced"]:
                self._text(self._practice_text(pr))


class VarshaphalTab(_InsightPage):
    caption = ("Varshaphal is your yearly chart (Tajika system), cast for the moment the Sun returns to its birth position each year "
               "(near your birthday). It shows the year's rising sign, the lord of the year, the Muntha (the life area in the spotlight), "
               "the Tajika yogas and Sahams, and how the year's mood changes period by period. Pick the year below. Tendencies only, "
               "not fixed events.")
    year = None

    def _default_year(self, chart):
        import datetime
        import varshaphal
        today = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        y = today.year
        return y if varshaphal.return_moment(chart, y) <= today else y - 1

    def _build(self, chart, reading):
        import datetime
        import varshaphal
        from ui.tabs_chart import ChartCanvas
        from ui.theme import ThemedSpinner
        birth_year = int(chart["birth_input"]["birth_date"][:4])
        if self.year is None or self.year <= birth_year:
            self.year = max(self._default_year(chart), birth_year + 1)
        labels = {y: tr('Age {0}  ({1}-{2})', y - birth_year, y, str(y + 1)[2:]) for y in range(birth_year + 1, birth_year + 101)}
        spinner = ThemedSpinner(text=labels[self.year], values=list(labels.values()), size_hint_y=None, height=dp(44))
        by_label = {v: k for k, v in labels.items()}
        spinner.bind(text=lambda inst, text: self._pick(by_label.get(text)))
        self.page.add_widget(spinner)
        vp = varshaphal.varshaphal(chart, self.year)
        self._text(tr('=== Your year - {0}, age {1} ===', self._name(reading), vp['age']))
        self._text(varshaphal.varshaphal_text(vp), compactable=True)
        self._table(["Period", "From", "To", "House", "Feels"], [0.2, 0.22, 0.22, 0.12, 0.24],
                    [(p["lord"], tr('{0:%d %b %y}', p['start']), tr('{0:%d %b %y}', p['end']), p["house"], p["tone"]) for p in vp["mudda"]], "11sp")
        x = vp["tajika_extras"]
        self._text(tx("--- The five office-bearers ---"))
        self._table(["Office", "Planet", "Points", "Looks at rising sign"], [0.36, 0.2, 0.16, 0.28],
                    [(tx(r["office"]), tx(r["planet"]) + (" *" if r["planet"] == x["varshesh"]["lord"] else ""), tr('{0:.1f}', r["bala"]["total"]),
                      tx("Yes") if r["aspects_lagna"] else tx("No")) for r in x["varshesh"]["bearers"]], "11sp")
        self._text(tx("--- Planet strength in the year (Pancha-vargiya bala, out of 20) ---\nFive Tajika dignities: sign, exaltation, "
                      "hadda (terms), drekkana and navamsa. Over 10 is strong, under 5 weak. Kuttha marks a planet that gives its results "
                      "in full; Durupha one that gives weak results this year."), compactable=True)
        cond = {"kuttha": tx("Kuttha (full results)"), "durupha": tx("Durupha (weak results)")}
        self._table(["Planet", "Sign", "Exalt.", "Hadda", "Total", "Condition"], [0.14, 0.13, 0.13, 0.13, 0.13, 0.34],
                    [(p[:3], tr('{0:g}', b["kshetra"]), tr('{0:.1f}', b["uchcha"]), tr('{0:g}', b["hadda"]), tr('{0:.1f}', b["total"]),
                      cond.get(x["conditions"][p][0], "-")) for p, b in x["bala"].items()], "11sp")
        verdict = {"supported": tx("Supported"), "mixed": tx("Mixed"), "care": tx("Needs care")}
        self._text(tx("--- Sahams of the year ---"))
        self._table(["Saham", "Point", "House", "Ruler", "Reading"], [0.26, 0.24, 0.12, 0.16, 0.22],
                    [(tx(s["name"]), tr('{0} {1}°', tx(s["sign"][:3]), int(s["degree"])), s["house"], s["lord"][:3],
                      (tx("Active") if s["malefic"] and s["verdict"] == "supported" else verdict[s["verdict"]])) for s in x["sahams"]], "11sp")
        self._text(tx("--- The yearly chart ---"))
        canvas = ChartCanvas(size_hint_y=None, height=dp(340))
        canvas.set_chart(vp["varsha"], "D1", self.store.chart_style)
        self.page.add_widget(canvas)

    def _pick(self, year):
        if year and year != self.year:
            self.year = year
            self.refresh()


class RemediesTab(_InsightPage):
    caption = ("What may help right now: only planets that are both weak or troubled in your chart AND active in your current periods are "
               "listed, with a gemstone only where it is traditionally safe and a stone-free alternative (mantra, charity, fast). Plus "
               "everyday habits for everyone. Traditional guidance - optional, and never a cure or a guarantee.")

    def _build(self, chart, reading):
        import remedy_plan
        self._text(tr('=== Remedies - {0} ===', self._name(reading)))
        from ui.knowledge_widgets import FunctionalNatureCard
        self._card(FunctionalNatureCard(chart))
        self._text(remedy_plan.remedy_text(chart, reading), compactable=True)
        from ui.theme import ThemedButton
        go = ThemedButton(text=tx("Meditation & practice for your chart"), variant="primary", size_hint_y=None, height=dp(46))
        go.bind(on_release=lambda *_: App.get_running_app().goto("practices"))
        holder = BoxLayout(size_hint_y=None, height=dp(46), padding=(dp(12), 0))
        holder.add_widget(go)
        self.page.add_widget(holder)


class LearnTab(_InsightPage):
    """Learn Astrology: short lessons on the basics, a step-by-step reading of the user's own chart, and a searchable
    glossary. Lessons and the glossary work without a chart; the walkthrough uses the current profile's chart."""
    caption = ("Learn how Vedic astrology works and how to read a chart. The lessons and the glossary work without a chart; "
               "'Read your chart' walks through the chart of the current profile, one step at a time.")
    uses_mode = False
    PARTS = (("lessons", "Lessons"), ("chart", "Read your chart"), ("glossary", "Glossary"))

    def __init__(self, store, **kwargs):
        super().__init__(store, **kwargs)
        self.part = "lessons"
        self.lesson_id = None
        self.query = ""

    # ---------------------------------------------------------------- navigation
    def show(self, part, lesson_id=None):
        self.part, self.lesson_id = part, lesson_id
        self.refresh()

    def _button(self, text, on_press, height=48):
        from ui.theme import ThemedButton
        btn = ThemedButton(text=text, size_hint_y=None, height=dp(height), halign="center")
        btn.bind(width=lambda b, w: setattr(b, "text_size", (w - dp(20), None)))
        btn.bind(on_release=lambda *_: on_press())
        holder = BoxLayout(size_hint_y=None, height=dp(height), padding=(dp(12), 0))
        holder.add_widget(btn)
        self.page.add_widget(holder)
        return btn

    def refresh(self):
        from ui.theme import SegmentedControl
        self.page.clear_widgets()
        self.page.add_widget(CaptionLabel(self.caption))
        labels = {key: tx(label) for key, label in self.PARTS}
        back = {v: k for k, v in labels.items()}
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), padding=(dp(10), dp(3)))
        row.add_widget(SegmentedControl([labels[k] for k, _l in self.PARTS], selected=labels[self.part],
                                        on_select=lambda opt: self.show(back[opt])))
        row.add_widget(BoxLayout())
        self.page.add_widget(row)
        try:
            {"lessons": self._lessons, "chart": self._walkthrough, "glossary": self._glossary}[self.part]()
        except Exception:  # noqa: BLE001 - show the problem on screen, never a blank page
            tb = traceback.format_exc()
            Logger.error(f"VedicAstro:LearnTab: failed:\n{tb}")
            self._text(tx("This screen hit an error while building - details below so it can be reported:\n\n") + tb)
        self._scroll.scroll_y = 1

    # ---------------------------------------------------------------- lessons
    def _lessons(self):
        import learn
        all_lessons = learn.lessons()
        if self.lesson_id is None:
            self._text(tx("=== Learn Astrology ===\nStart with lesson 1 and go in order; each lesson is a few minutes' reading and "
                          "builds on the one before. Where a lesson says so, you can see the idea in your own chart."))
            for n, les in enumerate(all_lessons, start=1):
                self._button(tr('{0}. {1}', n, tx(les["title"])), lambda lid=les["id"]: self.show("lessons", lid))
            return
        idx = next(i for i, les in enumerate(all_lessons) if les["id"] == self.lesson_id)
        les = all_lessons[idx]
        self._button(tx("Back to all lessons"), lambda: self.show("lessons"), height=44)
        self._text(tr('=== Lesson {0}: {1} ===', idx + 1, tx(les["title"])))
        for heading, text in les["sections"]:
            self._text(tr('--- {0} ---', tx(heading)) + "\n" + tx(text))
        chart = self.store.current["chart"]
        if les.get("try"):
            if chart is None:
                self._text(tx("[In your chart: generate a chart on the Birth Chart screen to see this lesson in your own chart.]"))
            else:
                self._text(tx("--- See it in your chart ---") + "\n" +
                           tr('[In your chart: {0}]', learn.try_in_chart(les["try"], chart, self.store.current["reading"])))
        if idx + 1 < len(all_lessons):
            nxt = all_lessons[idx + 1]
            self._button(tr('Next: {0}', tx(nxt["title"])), lambda: self.show("lessons", nxt["id"]))

    # ---------------------------------------------------------------- walkthrough
    def _walkthrough(self):
        import learn
        chart = self.store.current["chart"]
        if chart is None:
            self._text(tx("No chart generated yet for this profile. Make one on the Birth Chart screen, then come back here to "
                          "read it step by step."))
            return
        reading = self.store.current["reading"]
        titles = {les["id"]: les["title"] for les in learn.lessons()}
        self._text(tr('=== Read your chart - {0} ===', self._name(reading)) + "\n" +
                   tx("Astrologers read a chart in a fixed order: the rising sign, the Moon, the houses and their lords, the "
                      "strength of each planet, aspects, yogas, and then timing. Follow the same steps here; each one names "
                      "the lesson that explains it."))
        for n, step in enumerate(learn.walkthrough(chart, reading), start=1):
            self._text(tr('--- Step {0}: {1} ---', n, tx(step["title"])) + "\n" + step["text"] + "\n" +
                       tr('[Lesson: {0}]', tx(titles[step["lesson"]])))
        self._text(tx("[Remember: These steps teach the method. For the full reading of each part, open the matching screen from "
                      "Home.]"))

    # ---------------------------------------------------------------- glossary
    def _glossary(self):
        from ui.theme import ThemedTextInput
        field = ThemedTextInput(multiline=False, text=self.query, hint_text=tx("Search a term, e.g. 'dasha' or 'lord'"),
                                size_hint_y=None, height=dp(46), padding=(dp(12), dp(12)))
        holder = BoxLayout(size_hint_y=None, height=dp(46), padding=(dp(12), 0))
        holder.add_widget(field)
        self.page.add_widget(holder)
        self._gloss_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        self._gloss_grid.bind(minimum_height=self._gloss_grid.setter("height"))
        self.page.add_widget(self._gloss_grid)
        field.bind(text=lambda _w, t: self._fill_glossary(t))
        self._fill_glossary(self.query)

    def _fill_glossary(self, query):
        import learn
        self.query = query
        titles = {les["id"]: les["title"] for les in learn.lessons()}
        self._gloss_grid.clear_widgets()
        q = (query or "").strip().lower()
        rows = [g for g in learn.glossary() if not q or q in g["term"].lower() or q in tx(g["term"]).lower()
                or q in g["meaning"].lower() or q in tx(g["meaning"]).lower()]
        if not rows:
            widget = FlowText()
            widget.set_text(tx("No term matches that search."))
            self._gloss_grid.add_widget(widget)
            return
        for g in rows:
            widget = FlowText()
            widget.set_text(tr('--- {0} ---', tx(g["term"])) + "\n" + tx(g["meaning"]) + "\n" +
                            tr('[Lesson: {0}]', tx(titles[g["lesson"]])))
            self._gloss_grid.add_widget(widget)
