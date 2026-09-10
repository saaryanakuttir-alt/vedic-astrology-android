"""
tabs_tables.py — the seven data tabs that were tkinter Treeviews on the
desktop (Kundli Details, Planets, Houses, Yogas, Dasha, Ashtakvarga,
Chalit), rebuilt on the shared SimpleTable widget. Each tab's `refresh()`
pulls the exact same fields gui_app.py's corresponding `_populate_*_tab`
method did, from the currently selected profile's chart/reading.
"""
import datetime

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp

from ui.widgets import SimpleTable, CaptionLabel, LongText
from ui.theme import ThemedCheckBox as CheckBox
from ui import theme
from panchanga import SIGNS
from astrology_tables import ordinal


class _BaseTableTab(BoxLayout):
    columns = []
    col_hints = None
    # Most tables (up to ~6 columns) read fine at SimpleTable's default
    # font_size - subclasses with many columns or long cell text (Planets,
    # Ashtakvarga) override this to fit more content without wrapping as
    # aggressively, confirmed via emulator screenshot.
    font_size = "13sp"
    # A one-to-three-line plain-English explainer shown above the table -
    # every subclass below sets this, since every one of these tabs names
    # at least one classical Sanskrit/astrology term (Chalit, Ashtakvarga,
    # Nakshatra, Yoga, Dasha...) with no explanation otherwise.
    caption = ""

    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        if self.caption:
            self.add_widget(CaptionLabel(self.caption))
        self.table = SimpleTable(self.columns, self.col_hints, font_size=self.font_size)
        self.add_widget(self.table)

    def refresh(self):
        raise NotImplementedError


class KundliDetailsTab(_BaseTableTab):
    columns = ["Field", "Value"]
    col_hints = [0.4, 0.6]
    caption = (
        "A summary of your birth chart's key facts, plus traditional classifications "
        "(the 'Avkahada Chakra') used for things like matching horoscopes."
    )

    def refresh(self):
        chart = self.store.current["chart"]
        reading = self.store.current["reading"]
        if chart is None:
            self.table.set_rows([("Status", "No chart generated yet for this profile.")])
            return

        c = chart
        loc = c["resolved_location"]
        rows = [
            ("--- Basic Details ---", ""),
            ("Name", c["name"]),
            ("Sex", c["birth_input"]["sex"] or "(not entered)"),
            ("Date of Birth", str(c["birth_input"]["birth_date"])),
            ("Time of Birth", str(c["birth_input"]["birth_time_local"])),
            ("Day of Birth", c["day_of_week"]),
            ("Place of Birth", c["birth_input"]["place_name"] or "(exact coordinates entered)"),
            ("Latitude", f"{loc['latitude']:.4f}"),
            ("Longitude", f"{loc['longitude']:.4f}"),
            ("Time Zone", loc["tz_name"]),
            ("Ayanamsa (Lahiri)", f"{c['resolved_datetime']['ayanamsa_value_deg']:.6f} deg"),
            ("Sunrise", c["day_details"]["sunrise_local"] or "n/a"),
            ("Sunset", c["day_details"]["sunset_local"] or "n/a"),
            ("Day Duration", c["day_details"]["day_duration"] or "n/a"),
            ("Sidereal Time at Birth", c["day_details"]["local_sidereal_time_at_birth"]),
            ("SunSign (Indian/sidereal)", c["planets"]["Sun"]["sign"]),
            ("SunSign (Western/tropical)", c["western_sun_sign"]),
            ("Midheaven (MC) sign", c["ascendant"]["mc_sign"]),
            ("--- Avkahada Chakra ---", ""),
        ]
        a = c["avkahada_chakra"]
        rows += [
            ("Lagna (Ascendant)", c["ascendant"]["sign"]),
            ("Rasi (Moon sign)", c["planets"]["Moon"]["sign"]),
            ("Nakshatra - Pada", f"{c['planets']['Moon']['nakshatra']} - {c['planets']['Moon']['nakshatra_pada']}"),
            ("Nakshatra Lord", c["planets"]["Moon"]["nakshatra_lord"]),
            ("Varna", a["varna"]), ("Vasya", a["vasya"]), ("Yoni", a["yoni"]),
            ("Gana", a["gana"]), ("Nadi", a["nadi"]),
            ("Paya", "(not computed - disputed formula)"),
        ]
        for note in a["notes"]:
            rows.append(("Note", note))

        p = c["panchang"]
        rows += [
            ("--- Panchang ---", ""),
            ("Tithi", f"{p['tithi']['name']} ({p['tithi']['paksha']} Paksha)"),
            ("Yoga", p["yoga"]["name"]),
            ("Karana", p["karana"]["name"]),
        ]

        bal = c["dasha"]["balance_at_birth"]
        rows.append(("--- Dasha Balance at Birth ---", ""))
        rows.append(("Balance", f"{bal['lord']} {bal['years']}Y {bal['months']}M {bal['days']}D"))

        m = c["mangal_dosha"]
        rows += [
            ("--- Mangal Dosha (Manglik) ---", ""),
            ("Mars sign", m["mars_sign"]),
            ("From Lagna", f"House {m['from_lagna']['house']} - " +
             ("Dosha present" if m["from_lagna"]["dosha_present"] else "No dosha")),
            ("From Moon", f"House {m['from_moon']['house']} - " +
             ("Dosha present" if m["from_moon"]["dosha_present"] else "No dosha")),
        ]
        if m["from_venus"]:
            rows.append(("From Venus", f"House {m['from_venus']['house']} - " +
                         ("Dosha present" if m["from_venus"]["dosha_present"] else "No dosha")))
        rows.append(("Overall", "At least one reference point shows the dosha" if m["any_present"]
                     else "No dosha from any checked reference point"))
        rows.append(("Note", m["note"]))
        self.table.set_rows(rows)


class PlanetsTab(_BaseTableTab):
    columns = ["Planet", "Sign", "Deg", "Rx", "House", "Chalit Hs", "Nakshatra", "Pada", "Dignity"]
    col_hints = [0.13, 0.13, 0.09, 0.06, 0.09, 0.11, 0.17, 0.07, 0.15]
    # 9 columns including long values (nakshatra names, the "undetermined
    # (classical texts disagree)" dignity string) wrap heavily at the
    # default size - confirmed via emulator screenshot.
    font_size = "12sp"
    caption = (
        "Where each planet sat in the sky at your birth. Deg = position within its "
        "sign (0-30). Rx = retrograde (appears to move backward). House = the life-area "
        "it falls in; Chalit Hs is a more precise recalculation of that. Nakshatra/Pada = "
        "the lunar 'constellation' and its quarter-division. Dignity = how strong or "
        "comfortable the planet is in that sign."
    )

    def __init__(self, store, **kwargs):
        super().__init__(store, **kwargs)
        # "What this means" - table above is raw placement data; this is
        # the plain-language "so what does that actually affect" reading
        # for each planet, pulled from reading["planets"][p]["plain_gloss"]
        # (rule_engine.py's _plain_planet_gloss) rather than the chart's
        # own raw dict the table above reads, which has no interpretive
        # text at all. LongText (not a table) since this is prose, one
        # paragraph per planet - already chunk-safe, see widgets.py.
        self.add_widget(CaptionLabel("What this means for you, planet by planet:"))
        self.gloss_text = LongText(size_hint_y=0.55)
        self.add_widget(self.gloss_text)

    def refresh(self):
        from astrology_tables import get_dignity
        chart = self.store.current["chart"]
        if chart is None:
            self.table.set_rows([("No chart generated yet.", "", "", "", "", "", "", "", "")])
            self.gloss_text.set_text("")
            return
        rows = []
        for planet, detail in chart["planets"].items():
            dignity = get_dignity(planet, detail["sign"])
            rows.append((
                planet, detail["sign"], f"{detail['degree_in_sign']:.2f}",
                "Yes" if detail["retrograde"] else "",
                detail["house"], detail.get("chalit_house", ""),
                detail["nakshatra"], detail["nakshatra_pada"], dignity,
            ))
        self.table.set_rows(rows)

        reading = self.store.current["reading"]
        if reading is None:
            self.gloss_text.set_text("")
            return
        glosses = [
            reading["planets"][p]["plain_gloss"]
            for p in chart["planets"]
            if reading["planets"].get(p, {}).get("plain_gloss")
        ]
        self.gloss_text.set_text("\n\n".join(glosses))


class HousesTab(_BaseTableTab):
    columns = ["House", "Sign", "Lord", "Lord placed in house", "Relation"]
    col_hints = [0.12, 0.2, 0.15, 0.25, 0.28]
    caption = (
        "The 12 houses represent 12 areas of life (career, home, relationships...). "
        "'Lord' is the planet that rules each house's sign; where that planet itself "
        "sits shapes how that life-area actually plays out for you."
    )

    def refresh(self):
        reading = self.store.current["reading"]
        if reading is None:
            self.table.set_rows([("No chart generated yet.", "", "", "", "")])
            return
        rows = []
        for house_num, detail in reading["house_lords"].items():
            relation = detail["reading"]["relation_of_placed_house_from_lord_house"] if detail["reading"] else None
            relation_text = f"{ordinal(relation)} from its own house" if relation is not None else "?"
            rows.append((house_num, detail["house_sign"], detail["lord"], detail["placed_in_house"],
                         relation_text))
        self.table.set_rows(rows)


class YogasTab(BoxLayout):
    def __init__(self, store, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.add_widget(CaptionLabel(
            "'Yogas' are specific planetary combinations that classical texts link to "
            "particular life themes (e.g. leadership, wealth, obstacles) when present."
        ))
        # Rebuilt fresh each refresh() rather than mutated - same "never
        # mutate .text on an already-rendered Label" pattern as widgets.py's
        # LongText/SimpleTable (see LongText's own comment for why this
        # project specifically avoids that).
        self.summary_area = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(28))
        self.add_widget(self.summary_area)

        toggle_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40))
        self.only_present_check = CheckBox(active=True)
        self.only_present_check.bind(active=lambda *_: self.refresh())
        toggle_row.add_widget(Label(text="Show only present yogas", size_hint_x=0.8))
        toggle_row.add_widget(self.only_present_check)
        self.add_widget(toggle_row)
        self.table = SimpleTable(["ID", "Name", "Present", "Details"], [0.08, 0.22, 0.1, 0.6])
        self.add_widget(self.table)

    def _set_summary(self, text):
        self.summary_area.clear_widgets()
        label = Label(text=text, size_hint_y=None, halign="left", valign="middle", bold=True,
                      color=theme.GOLD_SOFT, text_size=(None, None))
        label.bind(texture_size=lambda inst, ts: setattr(label, "height", max(dp(28), ts[1] + dp(8))))
        label.bind(width=lambda inst, w: setattr(label, "text_size", (w, None)))
        self.summary_area.add_widget(label)
        self.summary_area.height = label.height

    def refresh(self):
        reading = self.store.current["reading"]
        if reading is None:
            self._set_summary("")
            self.table.set_rows([("", "No chart generated yet.", "", "")])
            return
        self._set_summary(reading.get("yogas_plain_summary", ""))
        only_present = self.only_present_check.active
        rows = []
        for y in reading["yogas"]:
            if only_present and not y["present"]:
                continue
            rows.append((y["id"], y["name"], "Yes" if y["present"] else "No", y["details"]))
        self.table.set_rows(rows)


class DashaTab(_BaseTableTab):
    columns = ["Level", "Lord", "Start", "End", "At Birth?"]
    col_hints = [0.14, 0.16, 0.22, 0.22, 0.26]
    caption = (
        "'Dasha' is a timeline system: your life is divided into periods ruled by "
        "each planet in turn ('Maha' = main period, 'Antar' = a sub-period within it), "
        "used to time when a planet's themes are most active for you."
    )

    def refresh(self):
        reading = self.store.current["reading"]
        if reading is None:
            self.table.set_rows([("No chart generated yet.", "", "", "", "")])
            return

        def fmt(dt):
            if isinstance(dt, str):
                dt = datetime.datetime.fromisoformat(dt)
            return dt.strftime("%Y-%m-%d")

        running = reading["dasha"]["running_at_birth"]
        rows = []
        for maha in reading["dasha"]["timeline"]:
            is_running_maha = maha["lord"] == running["mahadasha_lord"] and maha["is_partial_at_birth"]
            rows.append(("Maha", f"{maha['lord']}", fmt(maha["start"]), fmt(maha["end"]),
                         "<-- at birth" if is_running_maha else ""))
            for antar in maha["antardashas"]:
                is_running_antar = is_running_maha and antar["lord"] == running["antardasha_lord"]
                rows.append(("  Antar", f"{maha['lord']}/{antar['lord']}", fmt(antar["start"]), fmt(antar["end"]),
                             "<-- at birth" if is_running_antar else ""))
        self.table.set_rows(rows)


class AshtakvargaTab(_BaseTableTab):
    columns = ["Planet"] + [s[:3] for s in SIGNS]
    col_hints = [0.16] + [0.07] * 12
    # 13 columns total (Planet + all 12 signs) - each sign column is only
    # ~7% of the table's width, so the default font_size clips/wraps even
    # the single- or double-digit point values it holds.
    font_size = "11sp"
    caption = (
        "'Ashtakvarga' scores each zodiac sign (0-8 points) for how supportive it "
        "tends to be for each planet - higher numbers mean more support. 'Sarva "
        "(Total)' adds every planet's score together per sign."
    )

    def refresh(self):
        import ashtakvarga as av
        chart = self.store.current["chart"]
        if chart is None:
            self.table.set_rows([("No chart generated yet.",) + ("",) * 12])
            return
        avk = chart["ashtakavarga"]
        rows = []
        for planet in av.PLANET_ORDER:
            bhinna = avk["bhinnashtakavarga"][planet]
            rows.append(tuple([planet] + [bhinna[s] for s in SIGNS]))
        sarva = avk["sarvashtakavarga"]
        rows.append(tuple(["Sarva (Total)"] + [sarva[s] for s in SIGNS]))
        self.table.set_rows(rows)


class ChalitTab(_BaseTableTab):
    columns = ["Bhava", "Begin Sign", "Begin Deg", "Madhya Sign", "Madhya Deg", "Planets"]
    col_hints = [0.08, 0.17, 0.11, 0.17, 0.11, 0.36]
    caption = (
        "'Chalit' is a more precise recalculation of your house boundaries (each "
        "'Bhava' = house). 'Begin' is where the house starts, 'Madhya' is its exact "
        "midpoint - used to double-check which house a planet near a boundary truly falls in."
    )

    def refresh(self):
        chart = self.store.current["chart"]
        if chart is None:
            self.table.set_rows([("No chart generated yet.", "", "", "", "", "")])
            return
        planets_by_chalit_house = {i: [] for i in range(1, 13)}
        for planet, detail in chart["planets"].items():
            house = detail.get("chalit_house")
            if house:
                planets_by_chalit_house[house].append(planet)
        rows = []
        for row in chart["chalit"]:
            bhava = row["bhava"]
            rows.append((bhava, row["begin_sign"], f"{row['begin_degree_in_sign']:.2f}",
                        row["madhya_sign"], f"{row['madhya_degree_in_sign']:.2f}",
                        ", ".join(planets_by_chalit_house[bhava]) or ""))
        self.table.set_rows(rows)
