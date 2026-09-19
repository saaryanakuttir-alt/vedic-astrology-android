"""build_i18n.py - turn the human-readable translations in i18n_src/ into what the app loads.

WHY THIS EXISTS. Kivy's text engine (SDL2_ttf as built for Kivy, on desktop AND on
Android) does not do the "shaping" Hindi and Bengali need: vowel signs must move to
the other side of a consonant, consonants fuse into conjuncts, marks must sit above or
below their base. Without shaping the letters come out scrambled ("তরৈ কিরুন" for
"তৈরি করুন"). Rather than depend on the phone's text stack, this tool does the shaping
AHEAD OF TIME, on this PC, with HarfBuzz:

  1. every Hindi/Bengali word in i18n_src/<lang>.py is shaped;
  2. each syllable (HarfBuzz "cluster") becomes ONE new glyph in a copy of the Noto font
     (a composite of the shaped glyphs at their shaped positions), reachable through a
     private-use code point U+E000...;
  3. the strings the app loads (engine/i18n_<lang>.py) use those code points instead of
     the raw letters, so a plain, non-shaping renderer draws them correctly.

Latin letters, digits, spaces and {placeholders} are left alone, so runtime values
(names, numbers) can still be slotted in. Nothing here needs a network or a runtime library.

Usage (from android_app/, needs `pip install uharfbuzz fonttools`):
    python tools/build_i18n.py
"""
import importlib.util
import os
import re
import sys

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(APP, "fonts")                      # output: what the APK ships
FONTS_SRC = os.path.join(APP, "tools", "fonts_src")    # input: the original Noto fonts (not shipped)
SRC = os.path.join(APP, "i18n_src")
ENGINE = os.path.join(APP, "engine")

# language -> (source Noto font stem, output font stem)
LANGS = {"hi": ("NotoSansDevanagari", "IndicHi"), "bn": ("NotoSansBengali", "IndicBn")}
PUA_START = 0xE000
PUA_END = 0xF8FF

INDIC = re.compile("[ऀ-ॿঀ-৿‌‍]+")


def load_src(code):
    spec = importlib.util.spec_from_file_location(f"src_{code}", os.path.join(SRC, f"{code}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _shape(hbfont, text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True, "ccmp": True, "locl": True})
    return buf


def split_clusters(hbfont, run):
    """Split one Indic run into its syllable (cluster) strings, in reading order."""
    buf = _shape(hbfont, run)
    starts = sorted({info.cluster for info in buf.glyph_infos})
    ends = starts[1:] + [len(run)]
    return [run[s:e] for s, e in zip(starts, ends)]


class Face:
    """One font file, opened for shaping (HarfBuzz) and for editing (fontTools)."""

    def __init__(self, path):
        self.path = path
        self.tt = TTFont(path)
        self.order = list(self.tt.getGlyphOrder())
        data = open(path, "rb").read()
        self.hbfont = hb.Font(hb.Face(hb.Blob(data)))
        self.cmap = self.tt.getBestCmap()
        self.added = {}

    def add_unit(self, pua, text):
        buf = _shape(self.hbfont, text)
        comps, pen = [], 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            comps.append((self.order[info.codepoint], pen + pos.x_offset, pos.y_offset))
            pen += pos.x_advance
        g = Glyph()
        g.numberOfContours = -1
        g.components = []
        for name, dx, dy in comps:
            c = GlyphComponent()
            c.glyphName, c.x, c.y, c.flags = name, dx, dy, 0x0002    # ARGS_ARE_XY_VALUES
            g.components.append(c)
        name = f"u{pua:04X}"
        glyf = self.tt["glyf"]
        glyf.glyphs[name] = g
        self.order.append(name)
        glyf.glyphOrder = self.order
        g.recalcBounds(glyf)
        lsb = getattr(g, "xMin", 0)
        self.tt["hmtx"].metrics[name] = (pen, lsb)
        self.added[pua] = name

    def save(self, out_path, family):
        self.tt.setGlyphOrder(self.order)
        for table in self.tt["cmap"].tables:
            if table.isUnicode() and table.format in (4, 12):
                for pua, name in self.added.items():
                    table.cmap[pua] = name
        for rec in self.tt["name"].names:
            if rec.nameID in (1, 16):
                rec.string = family
            elif rec.nameID in (4, 6):
                rec.string = family + ("-Bold" if "Bold" in out_path else "-Regular") if rec.nameID == 6 else family
        self.tt.save(out_path)


def build_language(code):
    src_stem, out_stem = LANGS[code]
    src = load_src(code)
    table = src.T
    faces = {w: Face(os.path.join(FONTS_SRC, f"{src_stem}-{w}.ttf")) for w in ("Regular", "Bold")}
    reg = faces["Regular"]

    # 1. every syllable used anywhere in the translations
    values = list(table.values()) + [getattr(src, "NAME", "")]
    units = []                                   # unique syllable strings, first-seen order
    seen = set()
    for value in values:
        for run in INDIC.findall(value):
            for cl in split_clusters(reg.hbfont, run):
                if cl not in seen:
                    seen.add(cl)
                    units.append(cl)
    units.sort()
    if PUA_START + len(units) - 1 > PUA_END:
        raise SystemExit(f"{code}: {len(units)} syllables do not fit in the private-use area")
    pua_of = {cl: PUA_START + i for i, cl in enumerate(units)}

    # 2. one new glyph per syllable, in both weights
    for face in faces.values():
        for cl, pua in pua_of.items():
            face.add_unit(pua, cl)

    # 3. rewrite the strings the app loads; make sure every other character can be drawn
    problems = set()

    def encode(value):
        def swap(m):
            return "".join(chr(pua_of[cl]) for cl in split_clusters(reg.hbfont, m.group(0)))
        out = INDIC.sub(swap, value)
        for ch in out:
            if PUA_START <= ord(ch) <= PUA_END or ch in "\n\t":
                continue
            if ord(ch) not in reg.cmap and ord(ch) not in (0x20,):
                problems.add(ch)
        return out

    encoded = {k: encode(v) for k, v in table.items()}
    name_enc = encode(getattr(src, "NAME", ""))
    if problems:
        shown = ", ".join(f"{c!r} U+{ord(c):04X}" for c in sorted(problems))
        raise SystemExit(f"{code}: characters missing from the font: {shown}")

    for weight, face in faces.items():
        face.save(os.path.join(FONTS, f"{out_stem}-{weight}.ttf"), out_stem)

    out = os.path.join(ENGINE, f"i18n_{code}.py")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write('# -*- coding: utf-8 -*-\n"""GENERATED by tools/build_i18n.py from i18n_src/%s.py - do not edit.\n' % code)
        fh.write('Indic letters are replaced by pre-shaped syllable glyphs in fonts/%s-*.ttf (private-use\n' % out_stem)
        fh.write('code points), because Kivy cannot shape Hindi/Bengali itself. Edit the source and re-run."""\n')
        fh.write(f"NAME = {name_enc!r}\n")
        fh.write("T = {\n")
        for k in sorted(encoded):
            fh.write(f"    {k!r}: {encoded[k]!r},\n")
        fh.write("}\n")
    print(f"{code}: {len(table)} strings, {len(units)} syllable glyphs -> {out_stem}-*.ttf, i18n_{code}.py")


if __name__ == "__main__":
    for code in LANGS:
        build_language(code)
