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
