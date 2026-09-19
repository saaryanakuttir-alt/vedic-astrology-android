"""
tabs_entry.py — the design's "New Chart" screen: a profile-chip row, the
birth-data form (name, sex, date, known/unknown time, place with live city
suggestions, chart style), a Generate button, and the "Chart generated"
result card with the real Lagna / Moon / Sun signs.

Replaces the old Profile tab. The generate / example / profile-switching
logic is carried over from it unchanged in behaviour; only the presentation
follows the Classical design. Widgets stay stock-behaviour (see theme.py).
"""
import datetime

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior

from ui import theme
from ui.app_state import PROFILE_IDS, PROFILE_LABELS
from ui.theme import (ThemedButton, ThemedSpinner, ThemedTextInput, ThemedCheckBox,
                      SegmentedControl, Divider, OutlineBox)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

_EXAMPLE_BIRTHS = {
    "self":    ("Example Self",    "1990", "06", "15", "14", "30", "Mumbai",    "IN", "Male"),
    "partner": ("Example Partner", "1992", "11", "03", "09", "15", "Delhi",     "IN", "Female"),
    "child_1": ("Example Child 1", "2016", "04", "22", "07", "45", "Bengaluru", "IN", "Male"),
    "child_2": ("Example Child 2", "2019", "09", "10", "18", "05", "Chennai",   "IN", "Female"),
    "child_3": ("Example Child 3", "2021", "01", "27", "11", "20", "Pune",      "IN", "Male"),
    "child_4": ("Example Child 4", "2023", "07", "08", "22", "50", "Kolkata",   "IN", "Female"),
}


def show_message(title, text):
    content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
    msg = Label(text=text, valign="top")
    msg.bind(size=lambda inst, size: setattr(msg, "text_size", size))
    content.add_widget(msg)
    popup = Popup(title=title, content=content, size_hint=(0.88, 0.5))
    close = ThemedButton(text="OK", variant="primary", size_hint_y=None, height=dp(44))
    close.bind(on_release=popup.dismiss)
    content.add_widget(close)
    popup.open()


def _caption(text, icon=None):
    lbl = Label(text=text, size_hint_y=None, height=dp(20), halign="left", valign="bottom",
                font_size="12sp", color=theme.INK_SOFT)
    lbl.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
    return lbl


def _muted(text, height=dp(20), size="11.5sp"):
    lbl = Label(text=text, size_hint_y=None, height=height, halign="left", valign="middle",
                font_size=size, color=theme.MUTED)
    lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)),
             texture_size=lambda inst, ts: setattr(inst, "height", max(height, ts[1] + dp(4))))
    return lbl


class _Chip(ButtonBehavior, BoxLayout):
    """One avatar chip: 38dp ring with the initial, name label below."""

    def __init__(self, initial, name, selected, has_chart, **kwargs):
        kwargs.setdefault("size_hint", (None, 1))
        kwargs.setdefault("width", dp(60))
        super().__init__(orientation="vertical", spacing=dp(4), padding=(0, dp(2), 0, 0), **kwargs)
        ring_holder = BoxLayout(size_hint_y=None, height=dp(40))
        ring_holder.add_widget(BoxLayout())
        self.ring = Label(text=initial, bold=True, font_size="15sp", size_hint=(None, None), size=(dp(38), dp(38)),
                          color=theme.ACCENT if selected else theme.TEXT)
        from kivy.graphics import Color, Line
        with self.ring.canvas.after:
            Color(*(theme.ACCENT if selected else theme.DIVIDER))
            self._circle = Line(circle=(self.ring.center_x, self.ring.center_y, dp(19)), width=1.5)
            if has_chart:
                Color(*theme.ACCENT)
                self._dot = Line(circle=(self.ring.center_x + dp(14), self.ring.center_y + dp(14), dp(3)), width=2)
        self.ring.bind(pos=self._sync, size=self._sync)
        ring_holder.add_widget(self.ring)
        ring_holder.add_widget(BoxLayout())
        self.add_widget(ring_holder)
        self.name_label = Label(text=name, font_size="10.5sp", size_hint_y=None, height=dp(16),
                                shorten=True, shorten_from="right",
                                color=theme.ACCENT if selected else theme.TEXT)
        self.name_label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        self.add_widget(self.name_label)
        self._has_chart = has_chart

    def _sync(self, *_):
        self._circle.circle = (self.ring.center_x, self.ring.center_y, dp(19))
        if self._has_chart:
            self._dot.circle = (self.ring.center_x + dp(14), self.ring.center_y + dp(14), dp(3))


class EntryScreen(BoxLayout):
    def __init__(self, store, on_chart_generated, goto, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.on_chart_generated = on_chart_generated
        self.goto = goto
        self._place_meta = None      # {lat, lng, country} once a suggestion was picked
        self._suggest_ev = None
        self._loading = False
        self._form_pid = store.current_profile_id   # which profile the form currently shows

        # ---- profile chips ----
        chip_scroll = ScrollView(size_hint_y=None, height=dp(72), do_scroll_y=False, bar_width=0)
        self.chip_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_x=None,
                                  padding=(dp(18), dp(6), dp(18), 0))
        self.chip_row.bind(minimum_width=self.chip_row.setter("width"))
        chip_scroll.add_widget(self.chip_row)
        self.add_widget(chip_scroll)
        self.add_widget(Divider())

        # ---- scrolling form ----
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        form = GridLayout(cols=1, size_hint_y=None, spacing=dp(14), padding=(dp(18), dp(14), dp(18), dp(24)))
        form.bind(minimum_height=form.setter("height"))
        scroll.add_widget(form)
        self.add_widget(scroll)
        self.form = form

        self.editing_label = _muted("", height=dp(18))
        form.add_widget(self.editing_label)

        self.name_input = ThemedTextInput(multiline=False, hint_text="e.g. Asha Rao", size_hint_y=None, height=dp(46))
        form.add_widget(self._field("Name", self.name_input))

        self.sex_spinner = ThemedSpinner(text="(not set)", values=["(not set)", "Male", "Female", "Other"],
                                         size_hint_y=None, height=dp(46))
        form.add_widget(self._field("Sex (optional)", self.sex_spinner))

        # date of birth: day / month / year
        dob = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(46))
        self.day_spinner = ThemedSpinner(text="Day", values=[str(i) for i in range(1, 32)], size_hint_x=1)
        self.month_spinner = ThemedSpinner(text="Month", values=MONTHS, size_hint_x=1.7)
        self.year_input = ThemedTextInput(multiline=False, input_filter="int", hint_text="Year", size_hint_x=1.2)
        for w in (self.day_spinner, self.month_spinner, self.year_input):
            dob.add_widget(w)
        form.add_widget(self._field("Date of birth", dob, height=dp(72)))

        # time of birth: Known/Unknown + h/m/ampm
        time_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, height=dp(96))
        self.time_seg = SegmentedControl(["Known", "Unknown"], selected="Known", on_select=self._on_time_toggle)
        time_box.add_widget(self.time_seg)
        self.time_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(46))
        self.hour_spinner = ThemedSpinner(text="Hr", values=[str(i) for i in range(1, 13)])
        self.minute_spinner = ThemedSpinner(text="Min", values=[f"{i:02d}" for i in range(60)])
        self.ampm_spinner = ThemedSpinner(text="AM", values=["AM", "PM"])
        for w in (self.hour_spinner, self.minute_spinner, self.ampm_spinner):
            self.time_row.add_widget(w)
        self.time_note = _muted("A noon chart will be used until the exact time is confirmed. Ascendant and finer "
                                "dasha timing depend on precise time.", height=dp(46), size="12sp")
        time_box.add_widget(self.time_row)
        form.add_widget(self._field("Time of birth", time_box, height=dp(124)))
        self.time_box = time_box

        # place of birth + live suggestions
        self.place_input = ThemedTextInput(multiline=False, hint_text="Search city", size_hint_y=None, height=dp(46))
        self.place_input.bind(text=self._on_place_text)
        place_box = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None, height=dp(46))
        place_box.add_widget(self.place_input)
        self.suggest_box = BoxLayout(orientation="vertical", size_hint_y=None, height=0)
        place_box.add_widget(self.suggest_box)
        self.place_confirm = BoxLayout(orientation="horizontal", size_hint_y=None, height=0, opacity=0)
        self.place_confirm_label = _muted("", height=dp(28), size="12sp")
        self.place_confirm.add_widget(self.place_confirm_label)
        change = ThemedButton(text="Change", variant="ghost", size_hint=(None, None), size=(dp(80), dp(28)), font_size="12sp")
        change.bind(on_release=lambda *_: self._clear_place())
        self.place_confirm.add_widget(change)
        place_box.add_widget(self.place_confirm)
        self.place_box = place_box
        form.add_widget(self._field("Place of birth", place_box, height=dp(72)))
        self.place_field_row = form.children[0]

        # exact coordinates (advanced)
        manual_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(6))
        self.manual_check = ThemedCheckBox()
        self.manual_check.bind(active=self._on_manual_toggle)
        manual_row.add_widget(self.manual_check)
        ml = Label(text="Enter exact coordinates instead", halign="left", valign="middle", font_size="13sp",
                   color=theme.INK_SOFT)
        ml.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        manual_row.add_widget(ml)
        form.add_widget(manual_row)
        self.lat_input = ThemedTextInput(multiline=False, disabled=True, hint_text="28.6139", size_hint_y=None, height=dp(46))
        self.lon_input = ThemedTextInput(multiline=False, disabled=True, hint_text="77.2090", size_hint_y=None, height=dp(46))
        self.tz_input = ThemedTextInput(multiline=False, disabled=True, hint_text="Asia/Kolkata", size_hint_y=None, height=dp(46))
        for cap, w in (("Latitude", self.lat_input), ("Longitude", self.lon_input), ("Time zone", self.tz_input)):
            form.add_widget(self._field(cap, w))

        form.add_widget(Divider())

        self.style_seg = SegmentedControl(["North Indian", "South Indian"], selected=self.store.chart_style,
                                          on_select=self._on_style_select)
        form.add_widget(self._field("Chart style", self.style_seg, height=dp(70)))
        form.add_widget(_muted("Lahiri ayanamsa · sidereal (Vedic) positions", height=dp(18)))

        self.generate_btn = ThemedButton(text="Generate chart", variant="primary", size_hint_y=None, height=dp(50))
        self.generate_btn.bind(on_release=lambda *_: self._on_generate())
        form.add_widget(self.generate_btn)

        # result card (built on demand)
        self.result_holder = BoxLayout(orientation="vertical", size_hint_y=None, height=0)
        form.add_widget(self.result_holder)

        quick = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(88), spacing=dp(4))
        b1 = ThemedButton(text="Use example (this profile)", variant="ghost", font_size="12.5sp")
        b1.bind(on_release=lambda *_: self._fill_example(True))
        b2 = ThemedButton(text="Example family (fill + generate all)", variant="ghost", font_size="12.5sp")
        b2.bind(on_release=lambda *_: self._fill_example_all())
        quick.add_widget(b1)
        quick.add_widget(b2)
        form.add_widget(quick)

        self.status_label = _muted("Enter birth details and tap Generate chart.", height=dp(24), size="12.5sp")
        form.add_widget(self.status_label)

        self._on_time_toggle("Known")
        self._load_profile_into_form()
        self._render_chips()
        self._render_result()

    # ------------------------------------------------------------------ layout helpers
    def _field(self, caption, widget, height=None):
        h = height or dp(72)
        box = BoxLayout(orientation="vertical", spacing=dp(5), size_hint_y=None, height=h)
        box.add_widget(_caption(caption))
        box.add_widget(widget)
        return box

    def save_now(self):
        """Called by main when navigating away: keep whatever was typed."""
        self._save_form_into_profile(self._form_pid)

    def refresh(self):
        """Called by main whenever this screen is (re)shown. Always reloads
        the form from the store, since a Library tap or a Sample Charts load
        may have changed which profile is current or what it contains."""
        self._load_profile_into_form()
        self._render_chips()
        self._render_result()

    # ------------------------------------------------------------------ chips
    def _render_chips(self):
        self.chip_row.clear_widgets()
        for pid in PROFILE_IDS:
            data = self.store.profiles[pid]
            nm = (data["inputs"].get("name") or "").strip()
            label = nm.split()[0] if nm else PROFILE_LABELS[pid].replace("Life Partner", "Partner").replace(" (Native)", "")
            initial = (nm[:1] or PROFILE_LABELS[pid][:1]).upper()
            chip = _Chip(initial, label, pid == self.store.current_profile_id, data["chart"] is not None)
            chip.bind(on_release=lambda inst, p=pid: self._switch_profile(p))
            self.chip_row.add_widget(chip)
        self.editing_label.text = "Editing: " + PROFILE_LABELS[self.store.current_profile_id]

    def _switch_profile(self, pid):
        if pid == self.store.current_profile_id:
            return
        self._save_form_into_profile(self._form_pid)
        self.store.current_profile_id = pid
        self._load_profile_into_form()
        self._render_chips()
        self._render_result()
        self.on_chart_generated(profile_switch_only=True)

    # ------------------------------------------------------------------ toggles
    def _on_time_toggle(self, choice):
        known = choice == "Known"
        # swap the h/m/ampm row for the explanatory note (design behaviour)
        for w in (self.time_row, self.time_note):
            if w.parent is self.time_box:
                self.time_box.remove_widget(w)
        self.time_box.add_widget(self.time_row if known else self.time_note)

    def _on_manual_toggle(self, checkbox, active):
        for w in (self.lat_input, self.lon_input, self.tz_input):
            w.disabled = not active

    def _on_style_select(self, choice):
        self.store.chart_style = choice

    # ------------------------------------------------------------------ place search
    def _on_place_text(self, inst, text):
        if getattr(self, "_setting_place", False):
            return
        self._place_meta = None
        self._set_confirm(None)
        if self._suggest_ev:
            self._suggest_ev.cancel()
        q = (text or "").strip()
        if len(q) < 2:
            self._show_suggestions([])
            return
        self._suggest_ev = Clock.schedule_once(lambda dt: self._run_search(q), 0.2)

    def _run_search(self, q):
        try:
            import geocode
            results = geocode.search_places(q, limit=4)
        except Exception:  # noqa: BLE001 - suggestions are a convenience, never fatal
            results = []
        self._show_suggestions(results, q)

    def _show_suggestions(self, results, q=""):
        self.suggest_box.clear_widgets()
        rows = results if results else ([None] if q and len(q) >= 2 else [])
        for c in rows:
            if c is None:
                self.suggest_box.add_widget(_muted("No matches — try another city.", height=dp(30), size="12sp"))
                continue
            b = Button(text=f"{c['name']}   [size=11sp]{c['lat']:.2f}°, {c['lng']:.2f}° · {c['country']}[/size]",
                       markup=True, halign="left", valign="middle", background_normal="", background_down="",
                       background_color=theme.SURFACE, color=theme.TEXT, font_size="13sp",
                       size_hint_y=None, height=dp(40), padding=(dp(12), 0))
            b.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
            b.bind(on_release=lambda inst, city=c: self._pick_place(city))
            self.suggest_box.add_widget(b)
        h = dp(40) * len(results) if results else (dp(30) if rows else 0)
        self.suggest_box.height = h
        self.place_box.height = dp(46) + h + dp(4) * (1 if h else 0)
        self.place_field_row.height = dp(26) + self.place_box.height

    def _pick_place(self, c):
        self._setting_place = True
        self.place_input.text = c["name"]
        self._setting_place = False
        self._place_meta = {"lat": c["lat"], "lng": c["lng"], "country": c["country"]}
        self._country = c["country"]
        self._show_suggestions([])
        self._set_confirm(self._place_meta)

    def _set_confirm(self, meta):
        if meta:
            self.place_confirm_label.text = f"{meta['lat']:.2f}°, {meta['lng']:.2f}° · {meta['country']}"
            self.place_confirm.height = dp(28)
            self.place_confirm.opacity = 1
            extra = dp(32)
        else:
            self.place_confirm.height = 0
            self.place_confirm.opacity = 0
            extra = 0
        base = dp(46) + self.suggest_box.height
        self.place_box.height = base + extra
        self.place_field_row.height = dp(26) + self.place_box.height

    def _clear_place(self):
        self._place_meta = None
        self._country = ""
        self._set_confirm(None)
        self.place_input.focus = True

    # ------------------------------------------------------------------ profile <-> form
    def _hour24(self):
        if self.time_seg.selected == "Unknown":
            return "12", "0"
        h, m = self.hour_spinner.text, self.minute_spinner.text
        if h in ("Hr", "") or m in ("Min", ""):
            return "", ""
        hh = int(h) % 12
        if self.ampm_spinner.text == "PM":
            hh += 12
        return str(hh), str(int(m))

    def _save_form_into_profile(self, profile_id):
        hour, minute = self._hour24()
        month = str(MONTHS.index(self.month_spinner.text) + 1) if self.month_spinner.text in MONTHS else ""
        day = self.day_spinner.text if self.day_spinner.text.isdigit() else ""
        inputs = {
            "name": self.name_input.text.strip(),
            "sex": None if self.sex_spinner.text == "(not set)" else self.sex_spinner.text,
            "year": self.year_input.text.strip(), "month": month, "day": day,
            "hour": hour, "minute": minute, "second": "0",
            "place": self.place_input.text.strip(), "country": getattr(self, "_country", "") or "",
            "use_manual_coords": self.manual_check.active,
            "lat": self.lat_input.text.strip(), "lon": self.lon_input.text.strip(), "tz": self.tz_input.text.strip(),
            "time_known": "no" if self.time_seg.selected == "Unknown" else "yes",
            "place_meta": self._place_meta,
        }
        self.store.profiles[profile_id]["inputs"] = inputs

    def _load_profile_into_form(self):
        inp = self.store.current["inputs"]
        self.name_input.text = inp.get("name", "")
        self.sex_spinner.text = inp.get("sex") or "(not set)"
        self.year_input.text = str(inp.get("year", "") or "")
        m = inp.get("month", "")
        self.month_spinner.text = MONTHS[int(m) - 1] if str(m).isdigit() and 1 <= int(m) <= 12 else "Month"
        d = inp.get("day", "")
        self.day_spinner.text = str(int(d)) if str(d).isdigit() else "Day"
        known = inp.get("time_known", "yes") != "no"
        self.time_seg.select("Known" if known else "Unknown", notify=False)
        self._on_time_toggle("Known" if known else "Unknown")
        h = inp.get("hour", "")
        if str(h).isdigit():
            hi = int(h)
            self.hour_spinner.text = str(hi % 12 or 12)
            self.ampm_spinner.text = "PM" if hi >= 12 else "AM"
            self.minute_spinner.text = f"{int(inp.get('minute') or 0):02d}"
        else:
            self.hour_spinner.text, self.minute_spinner.text, self.ampm_spinner.text = "Hr", "Min", "AM"
        self._setting_place = True
        self.place_input.text = inp.get("place", "")
        self._setting_place = False
        self._country = inp.get("country", "") or ""
        self._place_meta = inp.get("place_meta")
        self._show_suggestions([])
        self._set_confirm(self._place_meta)
        self.manual_check.active = bool(inp.get("use_manual_coords"))
        self.lat_input.text = inp.get("lat", "")
        self.lon_input.text = inp.get("lon", "")
        self.tz_input.text = inp.get("tz", "")
        self._form_pid = self.store.current_profile_id
        chart = self.store.current["chart"]
        label = PROFILE_LABELS[self.store.current_profile_id]
        self._set_status(f"{label}: chart generated (Ascendant {chart['ascendant']['sign']})." if chart
                         else f"{label}: no chart generated yet.")

    def _set_status(self, text):
        self.status_label.text = text

    # ------------------------------------------------------------------ examples
    def _fill_example(self, save=False):
        ex = _EXAMPLE_BIRTHS.get(self.store.current_profile_id, _EXAMPLE_BIRTHS["self"])
        name, year, month, day, hour, minute, place, country, sex = ex
        inp = self.store.current["inputs"]
        inp.update({"name": name, "sex": sex, "year": year, "month": str(int(month)), "day": str(int(day)),
                    "hour": str(int(hour)), "minute": str(int(minute)), "second": "0", "place": place,
                    "country": country, "use_manual_coords": False, "time_known": "yes", "place_meta": None})
        self._load_profile_into_form()
        self._render_chips()

    def _fill_example_all(self):
        current = self.store.current_profile_id
        generated = []
        for pid in PROFILE_IDS:
            self._save_form_into_profile(self.store.current_profile_id)
            self.store.current_profile_id = pid
            self._fill_example()
            if self._generate_current_profile(quiet=True):
                generated.append(PROFILE_LABELS[pid])
        self.store.current_profile_id = current
        self._load_profile_into_form()
        self._render_chips()
        self._render_result()
        self.on_chart_generated(profile_switch_only=False)
        show_message("Example family generated", "Generated sample charts for:\n- " + "\n- ".join(generated))

    # ------------------------------------------------------------------ generate
    def _on_generate(self):
        if self._loading:
            return
        self._loading = True
        self.generate_btn.text = "Calculating…"
        self.generate_btn.disabled = True
        # one frame so the "Calculating..." state is actually painted first
        Clock.schedule_once(lambda dt: self._finish_generate(), 0.08)

    def _finish_generate(self):
        try:
            self._save_form_into_profile(self.store.current_profile_id)
            self._generate_current_profile()
        finally:
            self._loading = False
            self.generate_btn.text = "Generate chart"
            self.generate_btn.disabled = False

    @staticmethod
    def _parse_int(text, field_name):
        text = (text or "").strip()
        if not text:
            raise ValueError(f"{field_name} is required.")
        try:
            return int(text)
        except ValueError:
            raise ValueError(f"{field_name} must be a whole number, got '{text}'.")

    def _generate_current_profile(self, quiet=False):
        # Imported lazily: loading the chart engine pulls in every bundled KB file.
        from birth_chart import compute_birth_chart
        from rule_engine import generate_reading

        pid = self.store.current_profile_id
        inp = self.store.current["inputs"]
        try:
            name = (inp.get("name") or "").strip() or PROFILE_LABELS[pid]
            birth_date = (self._parse_int(inp.get("year"), "Birth year"),
                          self._parse_int(inp.get("month"), "Birth month"),
                          self._parse_int(inp.get("day"), "Birth day"))
            birth_time = (self._parse_int(inp.get("hour"), "Birth time (hour)"),
                          self._parse_int(inp.get("minute"), "Birth time (minute)"),
                          int(inp.get("second") or 0))
            place_name = (inp.get("place") or "").strip()
            country_hint = (inp.get("country") or "").strip() or None
            sex = inp.get("sex") or None
            kwargs = dict(name=name, birth_date=birth_date, birth_time=birth_time,
                          place_name=place_name, country_hint=country_hint, sex=sex)
            if inp.get("use_manual_coords"):
                if not (inp.get("lat") and inp.get("lon") and inp.get("tz")):
                    raise ValueError("Latitude, longitude, and time zone are all required for exact coordinates.")
                kwargs["latitude"] = float(inp["lat"])
                kwargs["longitude"] = float(inp["lon"])
                kwargs["tz_name"] = inp["tz"]
            elif not place_name:
                raise ValueError("Enter a place of birth, or tick 'Enter exact coordinates' and fill those in.")
            self._set_status(f"Computing chart for {PROFILE_LABELS[pid]}...")
            chart = compute_birth_chart(**kwargs)
            reading = generate_reading(chart)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            if not quiet:
                show_message("Could not generate chart", str(exc))
            self._set_status("Error - no chart was generated.")
            return False

        self.store.profiles[pid]["chart"] = chart
        self.store.profiles[pid]["reading"] = reading
        self._set_status(f"Chart generated for {PROFILE_LABELS[pid]} ({name}) - Ascendant "
                         f"{chart['ascendant']['sign']} {chart['ascendant']['degree_in_sign']:.2f} degrees.")
        if not quiet:
            self._render_chips()
            self._render_result()
            self.on_chart_generated(profile_switch_only=False)
        return True

    # ------------------------------------------------------------------ result card
    def _render_result(self):
        self.result_holder.clear_widgets()
        self.result_holder.height = 0
        data = self.store.current
        if data["reading"] is None or data["chart"] is None:
            return
        chart, reading = data["chart"], data["reading"]
        card = OutlineBox(orientation="vertical", padding=dp(14), spacing=dp(8), size_hint_y=None, height=dp(206))
        kicker = Label(text="CHART GENERATED", font_size="10sp", color=theme.ACCENT, halign="left",
                       size_hint_y=None, height=dp(16))
        kicker.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        title = Label(text=reading.get("name") or PROFILE_LABELS[self.store.current_profile_id], bold=True,
                      font_size="17sp", halign="left", valign="middle", size_hint_y=None, height=dp(26))
        title.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
        tags = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(26))
        for cap, val in (("Lagna", chart["ascendant"]["sign"]), ("Moon", chart["planets"]["Moon"]["sign"]),
                         ("Sun", chart["planets"]["Sun"]["sign"])):
            tag = OutlineBox(accent=True, size_hint_x=None, width=dp(104))
            tl = Label(text=f"{cap} · {val}", font_size="11sp", color=theme.ACCENT)
            tag.add_widget(tl)
            tags.add_widget(tag)
        tags.add_widget(BoxLayout())
        note = _muted("Full planetary placements, dashas and yogas are ready in the other screens.", height=dp(34), size="12.5sp")
        buttons = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
        open_btn = ThemedButton(text="Open chart", variant="secondary")
        open_btn.bind(on_release=lambda *_: self.goto("chart"))
        new_btn = ThemedButton(text="New chart", variant="ghost", size_hint_x=None, width=dp(104))
        new_btn.bind(on_release=lambda *_: self._new_chart())
        buttons.add_widget(open_btn)
        buttons.add_widget(new_btn)
        for w in (kicker, title, tags, note, buttons):
            card.add_widget(w)
        self.result_holder.add_widget(card)
        self.result_holder.height = dp(206)

    def _new_chart(self):
        self.store.current["inputs"] = {**{k: "" for k in ("name", "sex", "year", "month", "day", "hour", "minute",
                                                         "place", "country", "lat", "lon", "tz")},
                                         "second": "0", "use_manual_coords": False, "time_known": "yes"}
        self._load_profile_into_form()
        self._render_chips()
        self.result_holder.clear_widgets()
        self.result_holder.height = 0
        self.name_input.focus = True
