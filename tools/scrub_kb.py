"""scrub_kb.py - remove death / lifespan and children content from the Android
app's bundled knowledge base (engine/kb/*.json).

The Android app deliberately has NO lifespan, time-of-death or children
predictions. The dedicated engine sections were removed in rule_engine.py;
this tool cleans the same themes out of the classical interpretive text the
engine quotes, so they cannot resurface through a house or planet reading.

What it does to every string in the KB (idempotent - safe to re-run, e.g.
after re-copying the KB from chart_engine/kb):
  1. Strips "children" / "longevity" out of comma-separated label lists
     ("the house of children, intelligence, creativity" -> "the house of
     intelligence, creativity"), and drops "with a mild maraka sensitivity".
  2. Drops any remaining SENTENCE that still mentions those themes
     (fewer children, longevity-supporting, ...).
  3. Drops list items that are only such a theme (keywords: "children").
  4. Deletes the Saptamsha (D7, the children chart) KB file and entry.

Left alone on purpose: nakshatra*.json (mythology such as "Yama, god of
death", "fertility" as a nature theme) and vrat.json (a pregnancy SAFETY
note). Run:  python tools/scrub_kb.py [--dry-run]
"""
import glob
import json
import os
import re
import sys

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine", "kb")
SKIP_FILES = {"vrat.json", "nakshatra.json", "nakshatra_pada.json"}
DROP_FILES = {"divisional_D7_planet_in_sign.json"}

TERMS = re.compile(
    r"\b(children|child|childless\w*|progeny|offspring|longevity|maraka|lifespan|death|dies|die|died|dying|demise)\b",
    re.I,
)
_LIST_WORD = r"(?:children|longevity)"

# (compiled pattern, replacement) applied in order; see _strip_labels
_LABEL_RULES = [
    (re.compile(r"\s+with a mild maraka sensitivity", re.I), ""),
    (re.compile(r",\s+with a mild maraka sensitivity", re.I), ""),
    (re.compile(r"\b" + _LIST_WORD + r"\s+and\s+creativity\b", re.I), "creativity"),
    (re.compile(r"\bregarding children or\s+", re.I), "regarding "),
    (re.compile(r",?\s+and\s+" + _LIST_WORD + r"(?=[.,;)\s]|$)", re.I), ""),
]
_LEADING_ITEM = re.compile(r"\b(" + _LIST_WORD + r"),\s+(\w)", re.I)
_TRAILING_ITEM = re.compile(r",\s+" + _LIST_WORD + r"(?=,|\.|\)|$)", re.I)


def _strip_labels(s):
    for pat, rep in _LABEL_RULES:
        s = pat.sub(rep, s)

    def lead(m):
        was_cap = m.group(1)[0].isupper()
        nxt = m.group(2)
        return nxt.upper() if was_cap else nxt

    s = _LEADING_ITEM.sub(lead, s)
    s = _TRAILING_ITEM.sub("", s)
    return s


def _drop_sentences(s):
    if not TERMS.search(s):
        return s
    parts = re.split(r"(?<=[.!?])\s+", s)
    kept = [p for p in parts if not TERMS.search(p)]
    return " ".join(kept)


def scrub_string(s):
    return _drop_sentences(_strip_labels(s))


def scrub(obj, stats):
    if isinstance(obj, str):
        new = scrub_string(obj)
        if new != obj:
            stats["changed"] += 1
        return new
    if isinstance(obj, list):
        out = []
        for item in obj:
            if isinstance(item, str):
                new = scrub_string(item)
                if new != item:
                    stats["changed"] += 1
                if not new.strip():
                    stats["items_dropped"] += 1
                    continue
                out.append(new)
            else:
                out.append(scrub(item, stats))
        return out
    if isinstance(obj, dict):
        return {k: scrub(v, stats) for k, v in obj.items()}
    return obj


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def main(dry_run=False, src_dir=None):
    """Reads KB files from src_dir (default: KB_DIR itself) and makes KB_DIR
    contain their scrubbed versions. Passing a pristine copy as src_dir
    (e.g. exported from git) regenerates KB_DIR from scratch."""
    src_dir = src_dir or KB_DIR
    total = {"changed": 0, "items_dropped": 0}
    for path in sorted(glob.glob(os.path.join(src_dir, "*.json"))):
        name = os.path.basename(path)
        dst = os.path.join(KB_DIR, name)
        if name in DROP_FILES:
            if os.path.exists(dst):
                print(f"delete  {name}")
                if not dry_run:
                    os.remove(dst)
            continue
        raw = _read_bytes(path)
        if name in SKIP_FILES:
            out = raw
        else:
            data = json.loads(raw.decode("utf-8"))
            stats = {"changed": 0, "items_dropped": 0}
            if name == "divisional_charts.json":
                before = len(data.get("items", []))
                data["items"] = [i for i in data.get("items", []) if not str(i.get("id", "")).endswith("D7")]
                if len(data["items"]) != before:
                    print(f"        {name}: removed the D7 (Saptamsha) entry")
                    stats["items_dropped"] += before - len(data["items"])
            data = scrub(data, stats)
            if stats["changed"] or stats["items_dropped"]:
                print(f"scrub   {name}: {stats['changed']} strings changed, {stats['items_dropped']} list items dropped")
                out = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            else:
                out = raw
            for k in total:
                total[k] += stats[k]
        if not dry_run and (not os.path.exists(dst) or _read_bytes(dst) != out):
            with open(dst, "wb") as fh:
                fh.write(out)
    print("total  ", total, "(dry run - nothing written)" if dry_run else "")


if __name__ == "__main__":
    args = sys.argv[1:]
    src = args[args.index("--src") + 1] if "--src" in args else None
    main(dry_run="--dry-run" in args, src_dir=src)
