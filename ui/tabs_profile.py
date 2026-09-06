"""
tabs_profile.py — the Profile & Birth Data tab: pick which profile you're
editing (Self / Life Partner / Child 1-4), enter birth details, and
Generate Chart. Direct port of gui_app.py's profile switcher + on_generate,
minus tkinter StringVars (plain widget .text access instead).
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.metrics import dp

from ui.app_state import PROFILE_IDS, PROFILE_LABELS
from ui.widgets import field_row


def _show_message(title, text):
    content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
    # text_size must be bound to the label's own width, not left unset -
    # without it a long error message (a real possibility here: geocoding
    # failures, missing-field validation text, etc.) renders as one long
    # unwrapped line that can overflow the popup instead of wrapping to
    # fit it - the same class of bug documented at length elsewhere in
    # this file's sibling widgets (see widgets.py's SimpleTable/LongText).
    msg_label = Label(text=text, valign="top")
    msg_label.bind(size=lambda inst, size: setattr(msg_label, "text_size", size))
    content.add_widget(msg_label)
    popup = Popup(title=title, content=content, size_hint=(0.85, 0.5))
    close_btn = Button(text="OK", size_hint_y=None, height=dp(44))
    close_btn.bind(on_release=popup.dismiss)
    content.add_widget(close_btn)
    popup.open()


class ProfileTab(BoxLayout):
    def __init__(self, store, on_chart_generated, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.store = store
        self.on_chart_generated = on_chart_generated

        self.profile_spinner = Spinner(
            text=PROFILE_LABELS[self.store.current_profile_id],
            values=[PROFILE_LABELS[pid] for pid in PROFILE_IDS],
            size_hint_y=None, height=dp(44),
        )
        self.profile_spinner.bind(text=self._on_profile_change)
        self.add_widget(self.profile_spinner)

        form_scroll = ScrollView()
        form = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=dp(8))
        form.bind(minimum_height=form.setter("height"))
        form_scroll.add_widget(form)
        self.add_widget(form_scroll)

        self.name_input = TextInput(multiline=False)
        self.sex_spinner = Spinner(text="(not set)", values=["(not set)", "Male", "Female"])
        self.year_input = TextInput(multiline=False, input_filter="int")
        self.month_input = TextInput(multiline=False, input_filter="int")
        self.day_input = TextInput(multiline=False, input_filter="int")
        self.hour_input = TextInput(multiline=False, input_filter="int")
        self.minute_input = TextInput(multiline=False, input_filter="int")
        self.second_input = TextInput(multiline=False, input_filter="int", text="0")
        self.place_input = TextInput(multiline=False)
        self.country_input = TextInput(multiline=False, hint_text="optional, e.g. India")

        self.manual_coords_check = CheckBox()
        self.manual_coords_check.bind(active=self._on_manual_toggle)
        self.lat_input = TextInput(multiline=False, disabled=True)
        self.lon_input = TextInput(multiline=False, disabled=True)
        self.tz_input = TextInput(multiline=False, disabled=True, hint_text="e.g. Asia/Kolkata")

        for label_text, widget in [
            ("Name", self.name_input),
            ("Sex", self.sex_spinner),
            ("Birth Year", self.year_input),
            ("Birth Month", self.month_input),
            ("Birth Day", self.day_input),
            ("Birth Hour (0-23)", self.hour_input),
            ("Birth Minute", self.minute_input),
            ("Birth Second", self.second_input),
            ("Place of Birth", self.place_input),
            ("Country (hint)", self.country_input),
            ("Enter exact coordinates", self.manual_coords_check),
            ("Latitude", self.lat_input),
            ("Longitude", self.lon_input),
            ("Time Zone", self.tz_input),
        ]:
            form.add_widget(field_row(label_text, widget))

        generate_btn = Button(text="Generate Chart", size_hint_y=None, height=dp(50))
        generate_btn.bind(on_release=self._on_generate)
        self.add_widget(generate_btn)

        # text_size bound to width (not left unset) + height synced from
        # texture_size: without this, a long status string (the actual
        # generated-chart summary below routinely runs 70-90+ characters)
        # renders as one unwrapped line and, since Kivy centers a Label's
        # texture within its own box when text_size is unset, the START
        # of the text ends up pushed off the left edge of the screen -
        # confirmed repeatedly via emulator/device screenshot this session
        # ("...nerated for Self..." with "Chart ge" missing off-screen).
        self.status_label = Label(text="Enter birth details and tap Generate Chart.",
                                   size_hint_y=None, height=dp(40), halign="left", valign="middle")
        self.status_label.bind(width=self._update_status_text_size,
                                texture_size=self._resize_status_label)
        self.add_widget(self.status_label)

        self._load_profile_into_form()

    def _update_status_text_size(self, label, width):
        label.text_size = (width, None)

    def _resize_status_label(self, label, texture_size):
        label.height = max(dp(40), texture_size[1] + dp(10))

    def _set_status(self, text):
        # Routed through here (not `self.status_label.text = ...` directly)
        # for the same reason LongText.set_text() forces texture_update():
        # a property-change-triggered re-layout isn't reliably observed on
        # Android (see widgets.py's LongText for the fuller writeup) - so
        # force the text_size/height recompute synchronously every time,
        # rather than depending solely on the width/texture_size bindings
        # above having already fired with a valid value.
        self.status_label.text = text
        if self.status_label.width:
            self.status_label.text_size = (self.status_label.width, None)
        self.status_label.texture_update()
        self.status_label.height = max(dp(40), self.status_label.texture_size[1] + dp(10))

    # ------------------------------------------------------------------
    def _on_manual_toggle(self, checkbox, active):
        self.lat_input.disabled = not active
        self.lon_input.disabled = not active
        self.tz_input.disabled = not active

    def _save_form_into_profile(self, profile_id):
        inputs = {
            "name": self.name_input.text.strip(),
            "sex": None if self.sex_spinner.text == "(not set)" else self.sex_spinner.text,
            "year": self.year_input.text.strip(), "month": self.month_input.text.strip(),
            "day": self.day_input.text.strip(), "hour": self.hour_input.text.strip(),
            "minute": self.minute_input.text.strip(), "second": self.second_input.text.strip() or "0",
            "place": self.place_input.text.strip(), "country": self.country_input.text.strip(),
            "use_manual_coords": self.manual_coords_check.active,
            "lat": self.lat_input.text.strip(), "lon": self.lon_input.text.strip(),
            "tz": self.tz_input.text.strip(),
        }
        self.store.profiles[profile_id]["inputs"] = inputs

    def _load_profile_into_form(self):
        inputs = self.store.current["inputs"]
        self.name_input.text = inputs["name"]
        self.sex_spinner.text = inputs["sex"] or "(not set)"
        self.year_input.text = inputs["year"]
        self.month_input.text = inputs["month"]
        self.day_input.text = inputs["day"]
        self.hour_input.text = inputs["hour"]
        self.minute_input.text = inputs["minute"]
        self.second_input.text = inputs["second"] or "0"
        self.place_input.text = inputs["place"]
        self.country_input.text = inputs["country"]
        self.manual_coords_check.active = inputs["use_manual_coords"]
        self.lat_input.text = inputs["lat"]
        self.lon_input.text = inputs["lon"]
        self.tz_input.text = inputs["tz"]
        chart = self.store.current["chart"]
        label = PROFILE_LABELS[self.store.current_profile_id]
        if chart is not None:
            self._set_status(f"{label}: chart generated (Ascendant {chart['ascendant']['sign']}).")
        else:
            self._set_status(f"{label}: no chart generated yet.")

    def _on_profile_change(self, spinner, label_text):
        new_id = next(pid for pid in PROFILE_IDS if PROFILE_LABELS[pid] == label_text)
        if new_id == self.store.current_profile_id:
            return
        self._save_form_into_profile(self.store.current_profile_id)
        self.store.current_profile_id = new_id
        self._load_profile_into_form()
        self.on_chart_generated(profile_switch_only=True)

    def _parse_int(self, text, field_name):
        text = (text or "").strip()
        if not text:
            raise ValueError(f"{field_name} is required.")
        try:
            return int(text)
        except ValueError:
            raise ValueError(f"{field_name} must be a whole number, got '{text}'.")

    def _on_generate(self, button):
        # Imported lazily: importing the chart engine triggers loading all
        # bundled kb/*.json files, which is somewhat expensive and not
        # needed until the very first Generate tap.
        from birth_chart import compute_birth_chart
        from rule_engine import generate_reading

        profile_id = self.store.current_profile_id
        inputs_snapshot = None
        try:
            name = self.name_input.text.strip() or PROFILE_LABELS[profile_id]
            birth_date = (
                self._parse_int(self.year_input.text, "Birth year"),
                self._parse_int(self.month_input.text, "Birth month"),
                self._parse_int(self.day_input.text, "Birth day"),
            )
            birth_time = (
                self._parse_int(self.hour_input.text, "Birth hour"),
                self._parse_int(self.minute_input.text, "Birth minute"),
                int(self.second_input.text.strip() or 0),
            )
            place_name = self.place_input.text.strip()
            country_hint = self.country_input.text.strip() or None
            sex = None if self.sex_spinner.text == "(not set)" else self.sex_spinner.text

            kwargs = dict(name=name, birth_date=birth_date, birth_time=birth_time,
                          place_name=place_name, country_hint=country_hint, sex=sex)
            if self.manual_coords_check.active:
                if not (self.lat_input.text.strip() and self.lon_input.text.strip() and self.tz_input.text.strip()):
                    raise ValueError("Latitude, longitude, and timezone are all required when using manual coordinates.")
                kwargs["latitude"] = float(self.lat_input.text.strip())
                kwargs["longitude"] = float(self.lon_input.text.strip())
                kwargs["tz_name"] = self.tz_input.text.strip()
            elif not place_name:
                raise ValueError("Enter a place of birth, or check 'Enter exact coordinates' and fill those in instead.")

            self._set_status(f"Computing chart for {PROFILE_LABELS[profile_id]}...")
            chart = compute_birth_chart(**kwargs)
            reading = generate_reading(chart)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
            _show_message("Could not generate chart", str(exc))
            self._set_status("Error - see the message above. No chart was generated.")
            return

        self._save_form_into_profile(profile_id)
        self.store.profiles[profile_id]["chart"] = chart
        self.store.profiles[profile_id]["reading"] = reading
        warn_note = f" ({len(reading['warnings'])} KB lookup warning(s))" if reading["warnings"] else ""
        self._set_status(
            f"Chart generated for {PROFILE_LABELS[profile_id]} ({name}) - Ascendant "
            f"{chart['ascendant']['sign']} {chart['ascendant']['degree_in_sign']:.2f} degrees.{warn_note}"
        )
        self.on_chart_generated(profile_switch_only=False)
