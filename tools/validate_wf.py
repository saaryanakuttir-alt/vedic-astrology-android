"""validate_wf.py - checks one translated batch against its English input.

    python tools/validate_wf.py 007            (checks i18n_todo/wf/in_007.txt against out_007.txt)
    python tools/validate_wf.py all            (checks every batch that has an output file)

Errors (must be fixed): a missing / duplicated / unknown id, a changed placeholder ({0}, {1:.0f}, %s ...), an empty
translation, Latin (English) words left in a translation, raw '\\n' count differing from the English.
Exit code 1 when any batch has errors.
"""
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(APP, "i18n_todo", "wf")
PLACEHOLDER = re.compile(r"\{[^}]*\}|%s|%d")
# Latin words that may stay: chart codes, abbreviations and Sanskrit-script-less technical tokens
ALLOWED = {"KP", "Rx", "MC", "AM", "PM", "D1", "D2", "D3", "D4", "D9", "D10", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60",
           "Om", "deg", "PDF", "FAQ", "AI", "OK", "US", "OWN", "TENDENCIES", "Sammya", "Das"}


def read(path, keep_notes=False):
    out = {}
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        ident, tab, rest = line.partition("\t")
        if not ident.strip().isdigit():
            raise ValueError(f"{os.path.basename(path)}:{n}: line does not start with a number and a tab")
        if not keep_notes:
            rest = re.sub(r"\s+## \{0\}=.*$", "", rest) if "## {0}=" in rest else rest
        if ident in out:
            raise ValueError(f"{os.path.basename(path)}:{n}: id {ident} appears twice")
        out[ident] = rest
    return out


def check(n):
    name = f"{int(n):03d}" if str(n).isdigit() else n
    src, dst = os.path.join(WF, f"in_{name}.txt"), os.path.join(WF, f"out_{name}.txt")
    errors = []
    try:
        english = read(src)
    except ValueError as exc:
        return [str(exc)]
    if not os.path.exists(dst):
        return [f"out_{name}.txt does not exist"]
    try:
        bengali = read(dst)
    except ValueError as exc:
        return [str(exc)]
    for ident in english:
        if ident not in bengali:
            errors.append(f"id {ident}: missing")
    for ident in bengali:
        if ident not in english:
            errors.append(f"id {ident}: not in the input")
    for ident, en in english.items():
        bn = bengali.get(ident)
        if bn is None:
            continue
        if not bn.strip():
            errors.append(f"id {ident}: empty translation")
            continue
        pe, pb = sorted(PLACEHOLDER.findall(en)), sorted(PLACEHOLDER.findall(bn))
        if pe != pb:
            errors.append(f"id {ident}: placeholders differ: English {pe} / Bengali {pb}")
        if en.count("\\n") != bn.count("\\n"):
            errors.append(f"id {ident}: line breaks (\\n) differ: English {en.count(chr(92) + 'n')} / Bengali {bn.count(chr(92) + 'n')}")
        stripped = PLACEHOLDER.sub(" ", bn).replace("\\n", " ")
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z']{2,}", stripped) if w not in ALLOWED]
        if words:
            errors.append(f"id {ident}: English words left in the translation: {words[:6]}")
        if not re.search(r"[ঀ-৿]", bn) and re.search(r"[A-Za-z]{3,}", en):
            errors.append(f"id {ident}: no Bengali letters at all")
    return errors


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = sorted(f[4:-4] for f in os.listdir(WF) if f.startswith("out_")) if arg == "all" else [arg]
    bad = 0
    for name in names:
        errs = check(name)
        if errs:
            bad += 1
            print(f"batch {name}: {len(errs)} problem(s)")
            for e in errs[:40]:
                print("   ", e)
        else:
            print(f"batch {name}: OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
