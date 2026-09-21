"""
tabs_insights.py - three screens built from engine/extras.py: Doshas & Sade Sati, Planet Relations
(a plain verdict for each planet, friendships and aspects) and the Shodashvarga table (the sign of
every planet in all 15 divisional charts). Each is one scrolling page; long text follows the
Compact | Detailed switch, tables always show everything.
"""
import traceback

from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView

import extras
from astrology_tables import PLANET_ABBR, SIGN_ABBR
from ui import pdf_report, reading_mode
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
        self.page = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
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
from kivy.graphics import Color, Rectangle  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from ui import theme  # noqa: E402
from i18n import tr, tx  # noqa: E402 - translation helpers (engine/i18n.py)


class PlanetBanner(Label):
    """A tinted bar that starts each planet's section, so the planets are easy to tell apart."""

    def __init__(self, text, **kwargs):
        super().__init__(text=text, bold=True, font_size="14sp", color=theme.ACCENT_800, halign="left", valign="middle",
                         size_hint_y=None, height=dp(42), **kwargs)
        with self.canvas.before:
            Color(theme.ACCENT[0], theme.ACCENT[1], theme.ACCENT[2], 0.16)
            self._bg = Rectangle(pos=self.pos, size=self.size)
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
        self._table(["Planet", "Rank", "Strength", "Points"], [0.3, 0.15, 0.3, 0.25],
                    [(p, sb[p]["rank"], sb[p]["tone"], tr('{0:.0f}', sb[p]['total'])) for p in order])
        self._text(shadbala.shadbala_text(chart), compactable=True)
        self._text(tx("--- Points from each source ---"))
        head = ["Source"] + [p[:3] for p in shadbala.SEVEN]
        rows = [(label.split(" (")[0],) + tuple(tr('{0:.0f}', sb[p][key]) for p in shadbala.SEVEN) for key, label in shadbala.COMPONENTS]
        rows.append(("Total",) + tuple(tr('{0:.0f}', sb[p]['total']) for p in shadbala.SEVEN))
        self._table(head, [0.28] + [0.103] * 7, rows, "10sp")
        self._text(tx("Not counted: the year and month lords, planetary speed, aspect strength and planetary war, which need extra tables. "
                   "So read these as comparisons between your own planets, not as the traditional 'rupa' totals."))


class PrastaraTab(_InsightPage):
    caption = ("Prastharashtakvarga shows WHO gives each point in a planet's Ashtakvarga row. For each planet, every helper "
               "(the other planets and the Lagna) gives a point (1) to some signs and none (.) to others; the last row is the "
               "planet's usual Ashtakvarga row. A sign with more points is friendlier for that planet.")
    uses_mode = False

    def _build(self, chart, reading):
        import prastara
        from panchanga import SIGNS
        self._text(tr('=== Ashtakvarga detail - {0} ===', self._name(reading)))
        for planet, grid in prastara.all_prastara(chart).items():
            self._text(tr('--- {0} ---', planet))
            rows = [(c,) + tuple("1" if v else "." for v in r) for c, r in grid["rows"].items()]
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


class VarshaphalTab(_InsightPage):
    caption = ("Varshaphal is your yearly chart, cast for the moment the Sun returns to its birth position each year (near your "
               "birthday). It shows the year's rising sign, the Muntha (the life area in the spotlight) and how the year's mood changes "
               "period by period. Pick the year below. Tendencies only, not fixed events.")
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
        self._text(remedy_plan.remedy_text(chart, reading), compactable=True)
