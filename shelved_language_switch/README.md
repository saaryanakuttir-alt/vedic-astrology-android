# Shelved: Hindi / Bengali language switch

Removed from the app on 2026-09-19 at the owner's request: the owner wanted ALL text (including the
long classical readings) in the chosen language, which is not achievable reliably without a very large
translation run plus native-speaker proofreading; a half-translated interface was not wanted. Nothing
in this folder is shipped in the APK (see `source.exclude_dirs` in buildozer.spec).

What is here (same layout as android_app/, so `tools/build_i18n.py` still runs in place):

* `engine/i18n.py` - the offline `t()` translation layer (English text is the key).
* `i18n_src/hi.py`, `bn.py` - readable translations (titles, bottom bar, Home cards only).
* `tools/build_i18n.py` + `tools/fonts_src/` - pre-joins Hindi/Bengali letters with HarfBuzz and bakes each
  syllable into `fonts/IndicHi-*.ttf` / `IndicBn-*.ttf`, because Kivy's text engine (checked on desktop
  and on the OnePlus) cannot shape those scripts. Generated: `engine/i18n_hi.py`, `i18n_bn.py`.
* `ui/fonts.py` - points Kivy's default font at the language's font. `tests/test_i18n.py`.

To bring it back: copy the folders over android_app/, re-add the `LanguageBar` on Home and the
`set_language()` / `t()` calls (see git commits 0c77df6 "v1.5.1" and f8d64fd "v1.5"), and translate the rest.
Sizing measured: ~3,300 distinct classical sentences (~79,000 words) plus the text the engine composes.
