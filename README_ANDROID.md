# Vedic Astrology — Android port

This is the Android version of the Windows desktop app in `chart_engine/`
one folder up. Same chart math, same knowledge base, same Chara Karakas /
Karmic & Past Life / Life Predictions / Family Compatibility logic —
`engine/` in this folder is an unmodified copy of `chart_engine/*.py` +
`kb/` + `data/`. Only the UI toolkit changed: tkinter doesn't exist on
Android at all, so the UI layer was rebuilt from scratch on
[Kivy](https://kivy.org), a pure-Python, touch-first UI framework that
does run on Android and packages straight to an `.apk` via
[Buildozer](https://buildozer.readthedocs.io/).

## Status: verified working on a real Android device (2026-09-06)

This project now has a **working, real-device-tested build**:
`vedicastrology-1.0-arm64-v8a_armeabi-v7a_x86_64-debug.apk` (built via
GitHub Actions, all three architectures). It was installed on a real
phone (OnePlus 7T Pro, Android, arm64-v8a) via `adb`, launched, and
confirmed running past Kivy's full startup sequence (Python init, OpenGL
context creation on the device's real Adreno 640 GPU, "Start application
main loop") with the Profile & Birth Data / Chart / Kundli Details /
Planets tabs all visible and interactive - not just installed, actually
used.

Getting there took two rounds of real, since-fixed bugs:

**Build-time (toolchain) bugs** — all now captured as comments in
`buildozer.spec`, `Dockerfile.build`, and `.github/workflows/build-apk.yml`
for anyone building this again later: python-for-android's own `master`
branch had a multi-year release gap and jumped straight to targeting
bleeding-edge Python 3.14 (pinning to the last pre-jump release,
`v2024.01.21`, sidesteps that entirely); Ubuntu's `libtool` package splits
a macro libffi needs into `libltdl-dev`; Cython 3.x removed the `long`
builtin that pyjnius 1.6.1 still uses (hence the classic `0.29.36` pin,
not a modern one); CPython's `grp` module needs API 26+ (hence
`android.minapi = 26`); and GitHub's runner image defaults to the wrong
pre-installed JDK for Gradle (hence pinning `JAVA_HOME` explicitly in the
workflow). Through all of this, **`pyswisseph`'s native Swiss Ephemeris C
extension - the thing everyone expected to be hardest - needed no
compile-level fixes at all**, only a one-line setup.py patch (see
`recipes/pyswisseph/__init__.py`) for a missing `setuptools` in
python-for-android's own build-time interpreter.

**A real runtime bug**, only found by actually installing and running the
built APK: it crashed immediately on launch every time (splash icon for
~1 second, then exit). Captured via `adb logcat` on the real device:
`ModuleNotFoundError: No module named 'filetype'`, raised from
`kivy/core/image/__init__.py` during Kivy's own startup, before any of
this project's own code ever ran. Kivy 2.3.1 imports `filetype`
unconditionally for image-type sniffing; python-for-android's
auto-detection of Kivy's own extra pure-Python runtime dependencies
silently missed it. Now listed explicitly in `requirements` in
`buildozer.spec`.

This is the general lesson worth keeping in mind for any future changes:
**a build that completes without error is not the same as an app that
runs.** A clean Buildozer/Gradle build only proves everything compiled
and linked - it says nothing about whether the app's Python code actually
imports and runs successfully on-device. `filetype` was never a compile-
time dependency (nothing fails to *build* without it), only a runtime
one, so no build log ever flagged it. Whenever `requirements` in
`buildozer.spec` changes, or after bumping Kivy/pyswisseph/any dependency
version, re-verify by actually installing and launching the APK — on a
real device via `adb install` + `adb logcat` (fastest, and tests the real
target architecture), or failing that, an x86_64 emulator AVD if you add
`x86_64` to `android.archs` (already done here) so it doesn't need ARM
translation, which recent emulator images no longer support.

## Option A — GitHub Actions (no local Android tooling needed)

1. Create a new GitHub repository (public or private, either works).
2. Push the **contents of this `android_app/` folder** as the repo root
   (so `buildozer.spec` sits at the top level of the repo, not one folder
   down) — for example:
   ```bash
   cd android_app
   git init
   git add .
   git commit -m "Vedic Astrology Android app"
   git remote add origin <your-new-repo-url>
   git push -u origin main
   ```
3. Open the repo's **Actions** tab on GitHub. The push triggers
   `.github/workflows/build-apk.yml` automatically; it takes roughly
   15-30 minutes the first time (later runs are faster once GitHub's
   caches warm up).
4. When it finishes, open the completed run and download the
   **`vedic-astrology-debug-apk`** artifact — that zip contains the
   installable `.apk`.
5. Copy the `.apk` to your phone (email it to yourself, a cloud-drive
   link, a USB cable, anything) and tap it to install. Android will warn
   about installing from an unknown source the first time — that's normal
   for an app not published on the Play Store; allow it for this file.

This workflow's dependency versions were updated to match the verified
local Docker build above; it has not itself been re-run on GitHub's
runners since that update, so if it still fails somewhere, compare its log
against `buildozer.spec` / `Dockerfile.build`'s comments first — the
underlying toolchain-version issues those explain apply equally to CI.

## Option B — build it yourself locally with Docker (the verified path)

This is exactly how the working APK above was produced, and it sidesteps
Buildozer's Linux-only requirement without needing a full WSL setup —
Docker Desktop's own Linux VM is enough. From this `android_app/` folder:

```bash
docker build -f Dockerfile.build -t vedic-buildozer:py311 .
docker volume create vedic_src
docker run -d --name seed -v vedic_src:/work busybox sleep 60
docker cp . seed:/work
docker rm -f seed
docker run --rm -v vedic_src:/work -v vedic_buildozer_home:/root/.buildozer \
    vedic-buildozer:py311 bash -lc 'cd /work && yes | buildozer android debug'
docker run -d --name extract -v vedic_src:/work busybox sleep 30
docker cp extract:/work/bin/. ./bin/
docker rm -f extract
```

The first run downloads the Android SDK/NDK inside the container (a few
GB, cached in the `vedic_buildozer_home` volume across runs) and compiles
everything from scratch — expect 20-40 minutes depending on your machine.
The finished `.apk` lands in `android_app/bin/`. If you change the source
(`engine/`, `ui/`, `main.py`) and rebuild, the SDK/NDK/recipe cache in the
named volumes is reused, so later builds are much faster.

## Option C — build it yourself on a native Linux machine (or WSL)

Same idea without Docker, if you already have a suitable environment
(Buildozer only runs on Linux/WSL2/macOS, not plain Windows) — mirror
`Dockerfile.build`'s package list exactly, since several of those packages
(`libltdl-dev` especially) are easy to miss and cause real, previously-hit
build failures:

```bash
pip install "buildozer==1.5.0" "cython==0.29.36"
sudo apt-get install -y git zip unzip openjdk-17-jdk \
    autoconf automake libtool libtool-bin libltdl-dev pkg-config \
    zlib1g-dev libncurses-dev libncursesw5-dev libtinfo5 cmake \
    libffi-dev libssl-dev liblzma-dev uuid-dev libbz2-dev \
    libsqlite3-dev libreadline-dev libgdbm-dev libgdbm-compat-dev
cd android_app
buildozer android debug
```

## What's in this folder

| Path | What it is |
|---|---|
| `main.py` | Kivy app entry point — builds one `TabbedPanel` mirroring the desktop app's tabs |
| `ui/` | The Kivy screens: profile/birth-data form, chart diagram (North/South Indian, all 12 vargas), the seven data tables, Karmic & Past Life, Life Predictions, Full Reading, Family Compatibility |
| `engine/` | Unmodified copy of the desktop app's chart-calculation + interpretation engine (`chart_engine/*.py`, `kb/`, `data/`) |
| `buildozer.spec` | Buildozer's build configuration — app name, permissions, Python/Kivy/pyswisseph requirements, target Android API levels |
| `recipes/pyswisseph/` | A custom python-for-android build recipe for the Swiss Ephemeris binding — it has no official recipe upstream, so this project supplies one. Build-verified end to end (2026-09-06). |
| `Dockerfile.build` | The pinned Ubuntu 22.04 / Python 3.11 build environment used to produce the verified APK — see Option B |
| `.github/workflows/build-apk.yml` | The automated GitHub Actions build described in Option A above |
| `icon.png` | Placeholder app icon — replace with your own before a real release |

## What's been verified vs. not

**Verified**: the full Buildozer/python-for-android build pipeline runs
end to end and produces a real, installable `.apk` — every recipe
(CPython, Kivy, pyjnius, and `pyswisseph`'s native Swiss Ephemeris
extension) compiles and links successfully for all three architectures
(`arm64-v8a`, `armeabi-v7a`, `x86_64`), and Gradle successfully assembles
and signs the debug APK. **The APK has been installed and run on a real
device** (OnePlus 7T Pro): it launches, Kivy fully initializes (Python,
OpenGL context on the device's real GPU), and the app reaches its main
loop with the Profile & Birth Data tab visible and its fields accepting
real input. Separately, every screen's actual *logic* (parsing
birth-detail input, calling the chart engine, populating every table and
long-form report, computing Family Compatibility with a Life Partner and
a Child profile, drawing both chart-diagram styles at multiple vargas) was
smoke-tested end to end against a lightweight Kivy stub that runs the real
chart engine underneath while faking Kivy's widget mechanics — the same
technique used earlier in this project to validate the desktop tkinter app
without a display. All of that logic ran correctly.

**Not yet verified**: only the Profile & Birth Data tab has been
confirmed on-device so far (basic navigation and field entry). The other
tabs (Chart diagram rendering, Kundli Details, Planets, Houses, Yogas,
Dasha, Ashtakvarga, Chalit, Karmic & Past Life, Life Predictions, Full
Reading, Family Compatibility) haven't yet been exercised on a real
device — a full end-to-end chart generation (fill in a real birth, tap
Generate, click through every tab) is the natural next verification step.
Visual polish (label sizing, spacing, the chart diagram's exact
proportions) will likely need a pass or two once that's done. There's
also one confirmed-harmless cosmetic issue in the log: a "Permission
denied" error copying Kivy's default window-icon files into the app's
`.kivy/icon/` cache directory on first launch - Kivy catches this itself
and continues normally (doesn't affect any of this app's own logic), but
it's worth a look if a custom app icon ever needs to go through that same
path.

## Known limitations carried over from the desktop app

Everything documented in `chart_engine/README.md`'s "Known limitations"
and "Design decisions" sections still applies unchanged — Ayanamsa,
house system, Ashtakoot sourcing-confidence notes, and so on — since the
underlying engine is identical.


## v1.1 - Classical redesign (Created by Sammya Das)

The UI now follows the "Birth Chart App" design handoff (the same Classical
system the web app uses): parchment ground, ink text, one gold accent,
hairline outlines instead of filled buttons, a Home card menu, a gold diamond
header mark that always returns Home, and a 4-tab bottom bar (Chart / Dasha /
Yogas / Library). `main.py` no longer uses a TabbedPanel; screens are built
lazily on first visit. New screens: Predictions (any date), Medical Astrology,
Relationship Themes; the Chart Diagram screen shows a plain-language
explanation of the selected chart. The credit "Created by Sammya Das" is on
Home and Help & About.

`tests/desktop_smoke.py` drives the real widget tree with synthetic touches on
desktop Kivy (it is excluded from the APK). It found that the previous
themed widgets responded correctly to touches on desktop, so the earlier
"typing and buttons do nothing on device" report was not caused by the widget
classes; the new widgets deliberately stay behaviorally stock, and
`scroll_timeout` is raised to 250ms in main.py so a slow or slightly jittery
tap inside a ScrollView still reaches the widget under it.

## Version 1.2 changes (2026-09-19)

* **Typing works without the phone's keyboard.** The New Chart form now has a
  built-in on-screen keyboard (`ui/keyboard.py`), the default, because tapping
  a field never produced a working phone keyboard on the OnePlus 7T Pro (cause
  never confirmed; it does not reproduce on desktop). A Built-in / Phone switch
  at the top of the form chooses between the two and is remembered.
* **Chart numbers no longer overlap** after choosing a different person or
  style. Root cause (a real bug, reproducible on desktop, not an Android quirk):
  the old chart created its `Label` widgets inside a `with self.canvas.before:`
  block, which made Kivy register their canvases twice; the next
  `canvas.before.clear()` orphaned them, so every redraw left the previous
  chart's labels on screen. The chart is now drawn as text textures in one
  canvas that is cleared on each redraw (`ui/tabs_chart.py`).
* **Saved birth details** (`ui/persist.py`): every successful Generate saves the
  details in the app's private folder; Saved Charts lists them for one-tap
  recall (load into any profile slot and regenerate) with Delete.
* **Sample charts removed** (the public-figure list and the "example family"
  buttons), including `engine/sample_charts.py` and `sample_profiles.json`.
* **No lifespan/longevity or children predictions.** The Longevity & Lifespan
  and Children sections, the Saptamsa (D7) chart and its text, and the
  "vulnerable period" output are gone from `engine/rule_engine.py`, and
  `tools/scrub_kb.py` removes the same themes from `engine/kb/*.json`
  (re-run it after re-copying the KB from chart_engine). **This Android
  engine copy now intentionally differs from `chart_engine/`**; the PC and web
  apps still have those sections. `tests/test_engine_content.py` guards this.
* Other overlaps fixed: Classical Yogas summary printed over its caption; table
  rows had uneven cell heights (grey bars, text spilling); the Place of birth
  caption was overlapped; Help/FAQ and check marks used symbols Roboto lacks
  (drawn as empty boxes).

Tests (desktop, not shipped): `python -m pytest tests/test_engine_content.py`
and `python tests/desktop_smoke.py` (needs kivy 2.3.1, pyswisseph, tzdata,
filetype, pytest).

## Version 1.3 changes (2026-09-19)

* **Medical Astrology body-map chart** (`BodyMapCanvas` in `ui/tabs_chart.py`): the
  birth chart with each house labelled by its body area (1 Head ... 12 Feet) and
  shaded where a Sun/Mars/Saturn/Rahu/Ketu sits; North or South Indian.
* **Plain-words explanations**: every Medical paragraph, the Predictions year note
  and transit outlooks now end with an "[In simple terms: ...]" sentence written
  as you would tell a friend. The duplicated constitution paragraph is gone.
* **Chart Diagram style switch works**: the North/South spinner used to be reset by
  `refresh()` because it never updated `store.chart_style`.
* **Predictions date**: day / month pickers plus a year box (number pad) replace
  typing "YYYY-MM-DD".
* **Freeze fixed**: tapping a text field that is not inside a ScrollView (Predictions,
  Help search) hung the app - the keyboard's scroll-into-view search looped forever
  at the top of the widget tree. Now bounded; covered by `tests/desktop_smoke.py`.

## Version 1.4 changes (2026-09-19)

* **(Removed again in 1.5 at the user's request - it was too much.) Relationship Themes: year-by-year outlook from age 6 to 80**
  (`relationship_themes.yearly_relationship_outlook`). Each year gets a level
  (Low / Moderate / High / Very high) from the Mahadasha/Antardasha/Pratyantardasha
  lords (Venus, the 7th, 5th and 11th lords, the Moon), the Muntha in the
  5th/7th/11th house, and Jupiter's transit that year over the 7th/5th house. The
  levels compare the years of one chart with each other; they are NOT
  probabilities. Ages 6-17 describe friendships and emotional bonds only, with
  no romance/partnership/physical wording (enforced by a test); adult years
  say "romance or partnership (emotional or physical)". Thresholds were
  calibrated on 40 random charts (about 34% Low, 36% Moderate, 24% High, 5% Very high).
* **Stable signing key** (`ci/debug.keystore`, used by the workflow): from 1.4 on,
  a new build installs over the previous one and keeps its saved data. The step
  from a build made before 1.4 needs one uninstall.

## Version 1.5 changes (2026-09-19)

* **Year-by-year relationship outlook removed** (see 1.4 above).
* **Language switch was built and then SHELVED** (see version 1.5.2): everything is in `shelved_language_switch/` (not shipped).
* Signing: CI now exports ANDROID_PREFS_ROOT/USER_HOME/SDK_HOME so Gradle really uses
  `ci/debug.keystore` (verified: the APK's certificate SHA-256 matches). Updates from
  1.4.1 on install over the previous build and keep saved data.

## Version 1.5.2 changes (2026-09-19)

* **Hindi/Bengali buttons removed** and the whole language feature moved to `shelved_language_switch/`
  (README inside explains it). The owner wanted ALL text, including the long classical readings,
  in the chosen language; that needs a very large translation run plus proofreading, and a
  half-translated app was not wanted. Confirmed on the OnePlus: Kivy's text engine cannot shape
  Devanagari/Bengali; the shelved `tools/build_i18n.py` shows a workable pre-joining approach.
* **Chart Diagram is one scrolling page** (`ui/tabs_chart.py`): caption, the chart at a square size,
  then the explanation, instead of a stretched chart above a small text box.
* **Planets (Planet in House / Planet in Sign) and Family Compatibility** are one scrolling page too,
  using the new `FlowTable` / `FlowText` widgets (`ui/widgets.py`): the table is as tall as its rows
  instead of a small self-scrolling box.
* **Compact | Detailed reading** switch on every long reading (Life Predictions, Karmic, Full Reading,
  Relationship, Medical, Predictions), remembered in settings (`ui/reading_mode.py`, `ui/compact.py`).
  Compact keeps each section's heading and its "[In simple terms ...]" explanation.
* **PDF report** (Full Reading > "Save PDF report"): `ui/pdf_writer.py` (dependency-free PDF writer),
  `ui/pdf_report.py` (cover page, chart diagram as vector lines, planet table, readings; follows the
  Compact/Detailed choice; credit and page numbers in the footer), `ui/export.py` (Android: saved to
  Downloads/VedicAstrology through MediaStore, no permission needed, with an Open button; desktop:
  <data folder>/reports). Tests: `tests/test_pdf.py` and the desktop smoke test.


## Version 1.6.0 changes (2026-09-20) - AstroSage-report parity, phase 1

Checked against an AstroSage report for the same birth (29 May 1992, 07:06, Howrah): planets, nakshatras,
panchang, avakahada, Ashtakvarga totals, Manglik, Sade Sati dates (to the day) and 159/160 divisional-chart
placements agree. Known differences: Moon in D7 (D7 is not shown in this app), Paya, and AstroSage lists
Rahu/Ketu aspects on the 5th/7th/9th while this engine gives them only the 7th.

* **`engine/extras.py`** (new): plain "Good / Mostly good / Mixed / Needs some care / Challenging" verdicts
  with "what may happen" for every planet and each of the 12 houses, the running Mahadasha/Antardasha
  outlook, doshas (Manglik, Kalsarpa with type, Pitra, Guru Chandal, Grahan, Shrapit, Sade Sati/Dhaiya now),
  a lifetime Sade Sati / Dhaiya table (Saturn ingress scan), planetary friendships (natural, temporary,
  five-fold), Western-style aspects, and the Shodashvarga table. Wording is deliberately non-definite.
* **Divisional charts**: D27, D40 and D45 added (`engine/divisional.py`); the chart picker now offers 14
  divisional charts (D7 stays out on purpose).
* **New screens** (Home cards): Doshas & Sade Sati, Planet by Planet, Shodashvarga Table
  (`ui/tabs_insights.py`). Life Predictions now opens with "Where you are right now" and "Your 12 houses at
  a glance".
* **Detailed PDF** now also carries: panchang/avakahada, period + houses verdicts, planet-by-planet,
  doshas and the lifetime Sade Sati table, friendships, aspects, all 14 divisional charts + the
  Shodashvarga table, Chalit, Ashtakvarga, the full Vimshottari table with sub-periods, and the Medical
  body-map chart. Compact PDF stays short (doshas at a glance + plain-words lines).
* Tests: `tests/test_extras.py` (new), `tests/test_pdf.py`, desktop smoke test (23 Home cards).
* Not done yet (later phases): Varshaphal, Yogini/Char dasha, Jaimini Karakamsa/Swamsa, KP tables,
  Shadbala/Bhavabala, Prastharashtakvarga, Lal Kitab, and the long life-prediction prose in the
  AstroSage style.

## Version 1.6.1 (2026-09-20)

* Doshas that are NOT present now say "What this means" instead of "What may happen", and the two
  plain-words lines for Guru Chandal / Shrapit read "This does not apply to you ...".

## Version 1.6.1 (2026-09-21)

* Doshas that are not present now say "What this means" instead of "What may happen", and their plain-words lines say why the worry does not apply.

## Version 1.6.2 (2026-09-21)

* **Planet effects**: Planet in House / Planet in Sign now show one banner per planet with labelled sections (house, sign, ruler relationship, special conditions, what it rules and looks at, verdict, what may happen, in simple terms) - `engine/planet_effects.py`; also in the Detailed PDF.
* **More Dashas** screen (Yogini Dasha, Jaimini Char Dasha, Chara Karakas + Karakamsa chart, plain-words verdict for every Mahadasha) - `engine/more_dashas.py`. Char Dasha and Karakas match the AstroSage reference exactly; Yogini dates are within 2 days (AstroSage also shifts the first sub-periods).
* **Compact | Detailed switch** now also on Yogas, Dasha, Chart Diagram, Family Compatibility, Planets and the new screens.
* The profile row on New Chart shows two child slots (was four).
* The app version is shown on Home and in Help (`ui/version.py`, kept equal to buildozer.spec by a test) so a bug report can say which build it came from.
* Doshas that are not present now say "What this means".

## Version 1.7.0 (2026-09-21)

Checked against the AstroSage reference report (same birth data); AstroSage was used only to compare numbers, all wording is original.

* **Varshaphal** (`engine/varshaphal.py`, screen "Varshaphal"): Sun-return moment (matches to 31 s), yearly chart, Muntha, Mudda Dasha (all 8 periods within a day), good/mixed/care outlook. Pick any year.
* **KP system** (`engine/kp.py`): Placidus cusps, star/sub/sub-sub lords, ruling planets, significators. All 12 cusp sign/star/sub lords match; sub lords of planets can differ by an arc-minute.
* **Planet strength** (`engine/shadbala.py`): the parts of Shadbala that can be computed from the chart - 9 of 13 match AstroSage; Saptavargaja differs for 3 planets (a different friendship convention), Hora uses the classical sunrise count. NOT included: Abda, Masa, Cheshta, Drik, Yuddha and Bhavabala (need tables/formulas not implemented), so it is shown as comparative "strength points", not rupas.
* **Your Nature** (`engine/life_profile.py`): character, mind, career, education, hobbies in plain words (original text).
* **Ashtakvarga detail** (`engine/prastara.py`): Prastharashtakvarga for all seven planets (columns equal the Bhinnashtakvarga rows).
* **Sade Sati in detail** (`extras.sade_sati_detail_text`): personal reading - Saturn and Moon in your chart, where you are now, how each phase may go, per-stay Ashtakvarga points, all cycles.
* Not done: Lal Kitab (not enough reliable knowledge to write it), KP Pratyantar pages, Bhavabala.
* PDF (Detailed) now also has Your Nature, personal Sade Sati, Varshaphal, Planet strength, KP and Ashtakvarga detail; Compact has Your Nature and a short Sade Sati.

## Version 1.7.1 (2026-09-21)

* **Planet in House** and **Planet in Sign** are now two separate screens (before, both cards opened the same page). House: the house table (house, Chalit house, houses ruled, houses looked at) and the house-side sections. Sign: the sign table (sign, degree, nakshatra, dignity) and the sign-side sections (sign, ruler relationship, combust/retrograde/vargottama). The verdict, what may happen and the plain-words summary appear on both. The full combined view is still in the PDF.

## Version 1.8.0 (2026-09-21)

Everything that could not be done reliably is listed in `KNOWLEDGE_GAPS.md` (what is missing and what a source must provide).

* **Remedies** screen (`engine/remedy_plan.py`): only what is needed NOW - a planet is considered only if it is weak or troubled AND active
  (running Mahadasha/Antardasha, or Saturn during Sade Sati/Dhaiya). Levels: Highly recommended (gemstone traditionally safe: the planet rules a trine
  and no difficult house), Recommended with care, Helpful without a gemstone, Optional. Every stone comes with a stone-free alternative (mantra,
  donation, fast, colour) and milder substitute stones; troubled-but-inactive planets are listed with the date their period begins; a "What everyone
  can do" section gives everyday habits; combinations of stones to avoid are flagged.
* **KP**: Vimshottari maha / antar / pratyantar tables from the KP Moon (within 3-4 days of AstroSage), on the KP screen and in the PDF.
* **Varshaphal**: Tajika yogas (Ithasala and Ishrafa) in plain words.
* **PDF section chooser**: "Save PDF report" now asks which sections to include (15 in Detailed, 6 in Compact); the choice is remembered.
* **Home** is grouped under headings (Charts & tables, Readings, Timing & years, Strength doshas & remedies, People & help).
* **Your Nature** is deeper: purpose, speaking and thinking, money habits, strengths and growth areas were added.
* Not done (see KNOWLEDGE_GAPS.md): Drik, Cheshta, Abda, Masa, Bhavabala, year lord, Sahams, Lal Kitab.

## Version 1.9.0 (2026-09-22) - Bengali (বাংলা), step 1

A language bar on Home switches the whole app between English and Bengali; the choice is remembered. Fully offline.

* **How it works** (`engine/i18n.py`): every piece of text the program builds goes through `t()` / `tr()` / `tbl()` / `join_list()` /
  `fmt_date()`; sentences built from pieces are translated as whole templates so Bengali word order is right. `ui/i18n_hook.py` translates
  what Kivy draws, so widget `.text` stays English for program logic. English mode returns exactly the old text (tests prove it).
* **Fonts**: Kivy cannot join Bengali letters, so `tools/build_i18n.py` pre-shapes every syllable with HarfBuzz into private-use glyphs of
  `fonts/IndicBn-*.ttf` (Noto Sans Bengali, SIL OFL; `fonts/OFL-NotoSans.txt`) and writes `engine/i18n_bn.py`.
* **Sources**: `i18n_todo/keys.json` (1405 texts extracted by `tools/i18n_tool.py`), the translations `i18n_todo/bn_NN.txt` plus
  `bn_vocab_kb.txt` (remedy stones, mantras, donations, colours); `tools/merge_bn.py` merges them into `i18n_src/bn.py` and checks that
  every placeholder survived; `tools/build_i18n.py` bakes the fonts and the table. None of these folders ship in the APK.
* **What is Bengali in this step**: the whole interface and everything the app composes itself - Home, menus, captions, doshas, Sade Sati,
  planet verdicts, houses, periods, remedies, Your Nature, Varshaphal, KP text, strength, help/FAQ questions.
* **Still English on purpose**: the long classical knowledge-base paragraphs (planet in house / sign readings, Kundli notes, Life,
  Karmic, Medical, Relationship and Family body text - about 155,000 words) and the PDF report. Text without a translation simply shows in
  English. Step 2 will translate the classical paragraphs; Hindi follows the same route (`tools/build_i18n.py` already supports it).
* Bengali wording needs a native reader's proofreading pass: edit `i18n_todo/bn_NN.txt`, then run `python tools/merge_bn.py` and
  `python tools/build_i18n.py`.

## 2.0.0 - Bengali (complete)
Step 2 of the Bengali language: the classical knowledge-base paragraphs (planet in sign/house, houses, yogas, doshas,
dashas, divisional charts, remedies ...) and every sentence the engine composes are now shown in Bengali as well
(4,800+ texts, translated in parallel batches and checked with `tools/validate_wf.py`). Switching language re-writes the
kept readings. The PDF report stays English for now. The app remains fully offline. Sources: `i18n_todo/` (translation
files: `wf/out_NNN.txt`, `bn_vocab_*.txt`, `bn_fix_*.txt`), `tools/merge_bn.py` -> `i18n_src/bn.py` ->
`tools/build_i18n.py` -> `engine/i18n_bn.py` + `fonts/IndicBn-*.ttf`.

## 2.1.0 - Compact (free) edition
This same source now builds two separate Android apps, controlled by `engine/edition.py`:

* **Vedic Astrology** (`org.vedicastro.vedicastrology`, `EDITION = "full"`) - every screen, as before.
* **Vedic Astrology Compact** (`org.vedicastro.vedicastrologycompact`, `EDITION = "lite"`) - a free edition with only
  Birth Chart, Chart Diagram (every divisional chart), Kundli Details, Planet in House, Planet in Sign, House Lord
  Placements, Saved Charts and Help. Everything else (Classical Yogas, Mahadasha/Antardasha, the Ashtakvarga/KP/
  Shodashvarga tables, Chalit, the readings - Your Nature, Life Predictions, Karmic & Past Life, Medical Astrology,
  Relationship Themes, Full Reading, More Dashas, Varshaphal, Predictions, Planet Strength, Doshas & Sade Sati,
  Remedies, Family Compatibility - is held back for a future paid **Premium** edition) is left out of Home and the
  bottom bar entirely; it is not shown locked, it simply isn't built. Both editions install side by side on one
  device (different package ids), read/write their own separate app data, and are fully offline like the full app.

CI (`.github/workflows/build-apk.yml`) builds both as separate jobs/artifacts from independent checkouts: the "lite"
job flips `engine/edition.py`'s default to `"lite"` with a `sed` replace before running
`buildozer --profile lite android debug` (buildozer.spec's `[app@lite]` profile supplies the different title/package
id); a normal working copy - and the "full" job - are never touched and stay `"full"`. To test the lite edition
locally without touching the source: `VEDIC_EDITION=lite python main.py` (desktop) or set the same env var before
`tests/desktop_smoke.py`-style scripts. See `tests/test_edition.py` for the consistency checks (every
`edition.FREE_SCREENS` key is a real screen main.py can build and has a Home card; the lite bottom bar only points at
free screens; the CI `sed` target string exists exactly once; the two package ids differ).

Not done in this pass: no in-app upsell/teaser for the Premium screens (Home's subtitle text mentions them, that's
all), no separate app icon for Compact (both editions currently share `icon.png`), and there is no Premium edition
itself yet - `EDITION` only has "full" and "lite" today.
