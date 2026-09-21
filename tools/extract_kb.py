"""extract_kb.py - lists every distinct English sentence of the classical knowledge base that the app can show,
in reading order (sentences of one paragraph stay next to each other so a translator sees the context).

    python tools/extract_kb.py        writes i18n_todo/keys_kb.json  (ids from 10001)

Which fields count is decided by tracing the running app (i18n_todo/kb_fields_used.json = the fields the code reads);
files the app only takes numbers or names from (gemstones, mantras, daan ...) are handled by bn_vocab_kb.txt instead.
Sentences are split exactly like engine/i18n.py splits them at run time, so a translation is found again on screen.
"""
import glob
import json
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(APP, "engine", "kb")
TODO = os.path.join(APP, "i18n_todo")
sys.path.insert(0, os.path.join(APP, "engine"))
import i18n  # noqa: E402

# text fields that can be shown (used when the trace saw none of a file's text fields)
TEXT_FIELDS = {"summary", "effects", "dignity", "dignity_note", "house_theme", "sign_theme", "title", "formation",
               "strength_modifiers_and_cautions", "name", "deity", "symbol", "method", "primary_use", "overview",
               "general_effects", "favorable_indications", "challenging_indications", "calculation_note", "division_scheme",
               "core_theme", "rahu_ketu_dignity_note"}
NOTES = {"dignity_note", "rahu_ketu_dignity_note", "formation", "strength_modifiers_and_cautions", "overview", "calculation_note"}
SKIP_FILES = {"colors_deities", "daan", "gemstones", "yantras", "rudraksha", "mantras", "vrat"}
WITH_NOTES = {"classical_yogas", "planet_in_house", "planet_in_sign", "nakshatra", "divisional_charts"}


def fields_for(stem, used):
    traced = set(used.get(stem, [])) & TEXT_FIELDS
    if not traced:
        return set(TEXT_FIELDS)
    return traced | (NOTES if stem in WITH_NOTES else set())


def collect(obj, fields, out, trail=""):
    if isinstance(obj, dict):
        label = obj.get("id") or obj.get("name") or trail
        for key, value in obj.items():
            if key in fields and isinstance(value, str):
                out.append((str(label), key, value))
            elif isinstance(value, (dict, list)):
                collect(value, fields, out, str(label))
    elif isinstance(obj, list):
        for value in obj:
            collect(value, fields, out, trail)


def main():
    used = json.load(open(os.path.join(TODO, "kb_fields_used.json"), encoding="utf-8"))
    known = {k["en"] for k in json.load(open(os.path.join(TODO, "keys.json"), encoding="utf-8"))}
    keys2 = os.path.join(TODO, "keys2.json")
    if os.path.exists(keys2):
        known |= {k["en"] for k in json.load(open(keys2, encoding="utf-8"))}
    sys.path.insert(0, os.path.join(APP, "i18n_src"))
    known |= set(__import__("bn").T)
    seen, keys = set(known), []
    for path in sorted(glob.glob(os.path.join(KB, "*.json"))):
        stem = os.path.basename(path)[:-5]
        if stem in SKIP_FILES:
            continue
        data = json.load(open(path, encoding="utf-8"))
        found = []
        collect(data.get("items", []), fields_for(stem, used), found)
        for label, field, text in found:
            for sentence in i18n._SENTENCE.split(text):
                sentence = sentence.strip()
                if len(sentence) < 3 or sentence in seen:
                    continue
                seen.add(sentence)
                keys.append({"id": 10000 + len(keys) + 1, "kind": "kb", "en": sentence, "where": f"{stem}:{label}:{field}", "args": []})
    json.dump(keys, open(os.path.join(TODO, "keys_kb.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    words = sum(len(k["en"].split()) for k in keys)
    print(f"keys_kb: {len(keys)} sentences, {words} words")


if __name__ == "__main__":
    main()
