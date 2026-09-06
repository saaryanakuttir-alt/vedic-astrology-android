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

## Why you're not getting a finished .apk file directly in this chat

Producing an actual Android `.apk` requires downloading and running the
Android SDK, the Android NDK (for cross-compiling native code), Buildozer,
and python-for-android — several gigabytes of tooling, none of which could
be installed in either of the two places this project has access to:

- **This cloud workspace** blocks essentially all package-registry and SDK
  traffic (verified directly: `pip install` to PyPI, `apt-get` to Ubuntu's
  own archives, and downloads from `dl.google.com` and `github.com` all
  come back `403 Forbidden` here).
- **Your PC**, reached through the file-bridge, runs its shell commands
  inside a small Linux VM whose own network egress is controlled by your
  organization's settings — it was also unreachable at the moment this was
  built, so it couldn't be tried either.

So instead of a same-session `.apk`, this project ships a **complete,
ready-to-build Kivy/Buildozer project** plus a **GitHub Actions workflow**
that does the actual build for you on GitHub's own runners — which have
full internet access and are free for a personal repo. That's genuinely
the most reliable way to get a real `.apk` out of this, more so than
fighting your own machine's SDK setup by hand.

## Option A — GitHub Actions (recommended, no local Android tooling needed)

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

If the build fails on the custom `pyswisseph` step (see the recipe's own
docstring in `recipes/pyswisseph/__init__.py` for why it exists and the
likely fixes), the failing step's log will say exactly what broke — that
recipe was written carefully but has not been build-tested end-to-end
anywhere with real Android SDK/NDK access, since neither sandbox available
during development had one.

## Option B — build it yourself on a Linux machine (or WSL)

Buildozer only runs on Linux (native Linux, or WSL2 on Windows, or macOS
with extra setup — **not** plain Windows). If you have access to one:

```bash
pip install buildozer cython==0.29.36
sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 \
    cmake libffi-dev libssl-dev
cd android_app
buildozer android debug
```

The first run downloads the Android SDK/NDK automatically (a few GB) and
will take a while. The finished `.apk` lands in `android_app/bin/`.

## What's in this folder

| Path | What it is |
|---|---|
| `main.py` | Kivy app entry point — builds one `TabbedPanel` mirroring the desktop app's tabs |
| `ui/` | The Kivy screens: profile/birth-data form, chart diagram (North/South Indian, all 12 vargas), the seven data tables, Karmic & Past Life, Life Predictions, Full Reading, Family Compatibility |
| `engine/` | Unmodified copy of the desktop app's chart-calculation + interpretation engine (`chart_engine/*.py`, `kb/`, `data/`) |
| `buildozer.spec` | Buildozer's build configuration — app name, permissions, Python/Kivy/pyswisseph requirements, target Android API levels |
| `recipes/pyswisseph/` | A custom python-for-android build recipe for the Swiss Ephemeris binding — it has no official recipe upstream, so this project supplies one |
| `.github/workflows/build-apk.yml` | The automated build described in Option A above |
| `icon.png` | Placeholder app icon — replace with your own before a real release |

## What's been verified vs. not

**Verified**: every screen's actual logic (parsing birth-detail input,
calling the chart engine, populating every table and long-form report,
computing Family Compatibility with a Life Partner and a Child profile,
drawing both chart-diagram styles at multiple vargas) was smoke-tested end
to end against a lightweight Kivy stub that runs the real chart engine
underneath while faking Kivy's widget mechanics — the same technique used
earlier in this project to validate the desktop tkinter app without a
display. All of that logic ran correctly.

**Not verified**: real Kivy's actual rendering, touch/click behavior, and
screen sizing on a real device or emulator — neither was available in
either sandbox. Visual polish (label sizing, spacing, the chart diagram's
exact proportions) will likely need a pass or two once you can actually
see it running on a phone or in an Android emulator.

## Known limitations carried over from the desktop app

Everything documented in `chart_engine/README.md`'s "Known limitations"
and "Design decisions" sections still applies unchanged — Ayanamsa,
house system, Ashtakoot sourcing-confidence notes, and so on — since the
underlying engine is identical.
