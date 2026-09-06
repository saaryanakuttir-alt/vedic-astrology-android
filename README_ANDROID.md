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

## Status: a real debug APK has been built and verified (2026-09-06)

This project now has a **working, tested build**: `vedicastrology-1.0-
arm64-v8a_armeabi-v7a-debug.apk`, built end to end from this exact source
via Docker (Ubuntu 22.04, pinned Buildozer 1.5.0 / python-for-android
v2024.01.21 / Cython 0.29.36 — see `Dockerfile.build`), including
`pyswisseph`'s native Swiss Ephemeris C extension cross-compiling and
linking successfully for both architectures. That was genuinely the
biggest open question going in, and it's resolved: pyswisseph needed no
compile-level fixes at all, only a one-line setup.py patch (see
`recipes/pyswisseph/__init__.py`) for a missing `setuptools` in
python-for-android's own build-time interpreter.

Getting there took several real, since-fixed toolchain bugs — all now
captured as comments in `buildozer.spec`, `Dockerfile.build`, and
`.github/workflows/build-apk.yml` for anyone building this again later:
python-for-android's own `master` branch had a multi-year release gap and
jumped straight to targeting bleeding-edge Python 3.14 (pinning to the
last pre-jump release, `v2024.01.21`, sidesteps that entirely); Ubuntu's
`libtool` package splits a macro libffi needs into `libltdl-dev`; and
Cython 3.x removed the `long` builtin that pyjnius 1.6.1 still uses (hence
the classic `0.29.36` pin, not a modern one).

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

**Verified**: the full Buildozer/python-for-android build pipeline now
runs end to end and produces a real, installable `.apk` — every recipe
(CPython, Kivy, pyjnius, and `pyswisseph`'s native Swiss Ephemeris
extension) compiles and links successfully for both `arm64-v8a` and
`armeabi-v7a`, and Gradle successfully assembles and signs the debug APK.
Separately, every screen's actual *logic* (parsing birth-detail input,
calling the chart engine, populating every table and long-form report,
computing Family Compatibility with a Life Partner and a Child profile,
drawing both chart-diagram styles at multiple vargas) was smoke-tested end
to end against a lightweight Kivy stub that runs the real chart engine
underneath while faking Kivy's widget mechanics — the same technique used
earlier in this project to validate the desktop tkinter app without a
display. All of that logic ran correctly.

**Not yet verified**: the built APK has not yet been installed and run on
a real device or emulator, so real Kivy's actual rendering, touch/click
behavior, and screen sizing are still unconfirmed. Visual polish (label
sizing, spacing, the chart diagram's exact proportions) will likely need a
pass or two once you've installed it and can see it running on a phone.

## Known limitations carried over from the desktop app

Everything documented in `chart_engine/README.md`'s "Known limitations"
and "Design decisions" sections still applies unchanged — Ayanamsa,
house system, Ashtakoot sourcing-confidence notes, and so on — since the
underlying engine is identical.
