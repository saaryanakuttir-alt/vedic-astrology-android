"""i18n_tool.py - prepares the app's own text for translation and merges the translations back.

    python tools/i18n_tool.py rewrite     one-time source change: f-strings become tr("template {0}", arg) calls, text
                                          literals used to build sentences become t("..."), display tables become tbl({...})
    python tools/i18n_tool.py extract     writes i18n_todo/keys.json and numbered batch files (id | English) to translate
    python tools/i18n_tool.py merge bn    reads the finished batch files (id | translation) into i18n_src/bn_strings.py

The rewrite keeps English output byte-for-byte identical (the tests prove it); it only lets the text be
swapped for a translation while the app runs. Run with the project venv (Python 3.12).
"""
import ast
import json
import os
import re
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(APP, "i18n_todo")

# modules whose composed text is translated in this step
ENGINE_MODULES = ["extras", "life_profile", "remedy_plan", "varshaphal", "shadbala", "more_dashas", "planet_effects", "transits"]
UI_MODULES = ["tabs_chart", "tabs_entry", "tabs_extra", "tabs_family", "tabs_help", "tabs_home", "tabs_insights", "tabs_reports", "tabs_tables"]
FILES = [f"engine/{m}.py" for m in ENGINE_MODULES] + [f"ui/{m}.py" for m in UI_MODULES] + ["main.py"]

# module-level display tables whose values are translated when read (wrapped in tbl())
TABLES = {
    "engine/extras.py": ["SHODASHVARGA", "_HOUSE_AREA", "_SIGNIFIES", "_EFFECTS", "_TONE_GIST", "_TONE_PHRASE", "_HOUSE_TEMPLATE",
                         "_PHASE_STORY", "_PHASE_PLAIN", "_ASPECT_PLAIN"],
    "engine/life_profile.py": ["RISING", "MOON", "CAREER", "LEISURE", "LEARNING", "NAKSHATRA", "PURPOSE", "MONEY", "SPEAKING"],
    "engine/remedy_plan.py": ["EVERYONE"],
    "engine/varshaphal.py": ["_MUNTHA_TEXT"],
    "engine/shadbala.py": ["_TONE_TEXT", "_STRENGTH_THEME"],
    "engine/more_dashas.py": ["_YOGINI_MEANING", "_KARAKA_ROLES", "_KARAKAMSA_TRAIT"],
    "engine/transits.py": ["_PLANET_THEME"],
}
DENY_CALL_ATTRS = {"startswith", "endswith", "split", "rsplit", "replace", "join", "strip", "lstrip", "rstrip", "get", "index", "count", "find",
                   "pop", "setdefault", "strftime", "fromisoformat", "bind", "fbind", "register", "info", "error", "warning", "debug",
                   "exception", "compile", "match", "search", "sub", "findall", "getattr", "select", "set", "add", "discard", "remove",
                   "goto", "save", "load", "dump", "loads", "dumps"}
DENY_CALL_NAMES = {"print", "getattr", "hasattr", "setattr", "isinstance", "open", "repr", "int", "float", "sorted", "set", "dict", "len",
                   "super", "type", "Logger", "check", "assert_"}
WORDY = re.compile(r"[A-Za-z]{3,}")


def _offsets(src_bytes):
    starts, pos = [0], 0
    for line in src_bytes.split(b"\n"):
        pos += len(line) + 1
        starts.append(pos)
    return starts


def _span(node, starts):
    return starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset


def _parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node
    return tree


def _ancestors(node):
    while getattr(node, "_parent", None) is not None:
        node = node._parent
        yield node


def _in_function(node):
    return any(isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef)) for a in _ancestors(node))


def _docstring_ids(tree):
    ids = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _call_is_denied(call):
    f = call.func
    if isinstance(f, ast.Attribute):
        if f.attr in DENY_CALL_ATTRS:
            return True
        base = f.value
        while isinstance(base, ast.Attribute):
            base = base.value
        return isinstance(base, ast.Name) and base.id in ("Logger", "re", "os", "json", "datetime", "traceback", "sys")
    return isinstance(f, ast.Name) and f.id in DENY_CALL_NAMES


def _template(node, src):
    """(template, [arg source strings]) for an f-string node, or None if it cannot be converted safely."""
    parts, args = [], []
    for v in node.values:
        if isinstance(v, ast.Constant):
            parts.append(v.value.replace("{", "{{").replace("}", "}}"))
        else:
            if v.format_spec is not None and any(not isinstance(x, ast.Constant) for x in v.format_spec.values):
                return None
            spec = ""
            if v.format_spec is not None:
                spec = ":" + "".join(x.value for x in v.format_spec.values)
            conv = {-1: "", 115: "!s", 114: "!r", 97: "!a"}[v.conversion]
            text = ast.get_source_segment(src, v.value)
            if text is None or "\n" in text and text.count("(") != text.count(")"):
                return None
            parts.append("{%d%s%s}" % (len(args), conv, spec))
            args.append(text.strip())
    return "".join(parts), args


def _emit_template_call(template, args, col):
    """tr("...", args) with a long template broken into adjacent string literals."""
    chunks, cur = [], ""
    for word in re.split(r"(?<= )", template):
        if len(cur) + len(word) > 96 and cur:
            chunks.append(cur)
            cur = ""
        cur += word
    chunks.append(cur)
    pad = " " * (col + 3)
    lit = ("\n" + pad).join(repr(c) for c in chunks)
    return "tr(" + lit + "".join(", " + a for a in args) + ")"


def collect(path, apply_wrap=False):
    """Return (edits, keys) for one file. edits: [(start, end, replacement)]; keys: [dict]."""
    full = os.path.join(APP, path)
    text = open(full, encoding="utf-8").read()
    src_bytes = text.encode("utf-8")
    tree = _parents(ast.parse(text))
    starts = _offsets(src_bytes)
    docs = _docstring_ids(tree)
    edits, keys, used = [], [], set()

    def seg(node):
        a, b = _span(node, starts)
        return src_bytes[a:b].decode("utf-8")

    # 1. f-strings -> tr(template, args)
    fstrings = [n for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) and not any(isinstance(a, ast.JoinedStr) for a in _ancestors(n))]
    for n in fstrings:
        if id(n) in docs or any(isinstance(a, ast.Call) and _call_is_denied(a) and n in a.args for a in _ancestors(n)):
            continue
        if any(isinstance(a, ast.Compare) for a in _ancestors(n)):
            continue
        conv = _template(n, text)
        if not conv:
            continue
        template, args = conv
        bare = re.sub(r"\{[^}]*\}", "", template)
        if not WORDY.search(bare):
            if not args or not re.match(r"^[\s\d:()\[\]\-,.;/%=]*$", bare):
                continue                 # only clear display punctuation ("{0} ({1}): {2}", "--- {0} ---") is converted
        a, b = _span(n, starts)
        col = n.col_offset
        edits.append((a, b, _emit_template_call(template, args, col)))
        used.add("tr")
        if WORDY.search(bare):
            keys.append({"kind": "template", "en": template, "args": args, "where": f"{path}:{n.lineno}"})

    # 2. text literals used to build sentences -> t("...")
    inside_f = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            for c in ast.walk(n):
                if isinstance(c, ast.Constant):
                    inside_f.add(id(c))
    module_strings = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and len(node.value.value) > 20:
            module_strings.update(t.id for t in node.targets if isinstance(t, ast.Name))
    for n in ast.walk(tree):
        # a module-level text constant handed straight to a list (parts.append(_ADVICE)) or added to a sentence
        if isinstance(n, ast.Name) and n.id in module_strings and _in_function(n):
            par = getattr(n, "_parent", None)
            if (isinstance(par, ast.Call) and n in par.args and isinstance(par.func, ast.Attribute) and par.func.attr in ("append", "insert")) or \
                    (isinstance(par, ast.BinOp) and isinstance(par.op, ast.Add)):
                a, b = _span(n, starts)
                edits.append((a, b, "tx(" + n.id + ")"))
                used.add("tx")
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)) or id(n) in docs:
            continue
        s = n.value
        if not WORDY.search(s):
            continue
        parent = getattr(n, "_parent", None)
        if id(n) in inside_f:
            # constants inside f-string expressions ({'a' if x else 'b'}) are looked up as pieces
            fs = next((a for a in _ancestors(n) if isinstance(a, ast.JoinedStr)), None)
            in_expr = fs is not None and any(isinstance(a, ast.FormattedValue) for a in _ancestors(n))
            if in_expr and (" " in s.strip() or len(s) > 12):
                keys.append({"kind": "text", "en": s, "where": f"{path}:{n.lineno}", "note": "piece slotted into a sentence"})
            continue
        if isinstance(parent, (ast.Dict,)) and n in parent.keys or isinstance(parent, ast.Subscript) or isinstance(parent, ast.Compare):
            continue
        if any(isinstance(a, (ast.Raise, ast.Assert)) for a in _ancestors(n)):
            continue
        if any(isinstance(a, ast.Call) and _call_is_denied(a) for a in _ancestors(n) if a is not tree):
            # a denied call may still wrap the text elsewhere; skip only when the constant is a direct argument
            if any(isinstance(a, ast.Call) and _call_is_denied(a) and (n in a.args or any(n is k.value for k in a.keywords)) for a in _ancestors(n)):
                continue
        multiword = " " in s.strip() and len(s.strip()) >= 8
        if not multiword and len(s) < 12:
            continue
        keys.append({"kind": "text", "en": s, "where": f"{path}:{n.lineno}"})
        # wrap only where the text is being assembled inside a function
        if not _in_function(n):
            continue
        wrap = False
        # only where text is clearly being assembled for display: operands of "+" and items appended to a list.
        # (returns, assignments, list items and conditional values are often program tokens - left alone)
        if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Add):
            wrap = True
        elif isinstance(parent, ast.Call) and n in parent.args and isinstance(parent.func, ast.Attribute) and parent.func.attr in ("append", "insert"):
            wrap = True
        elif isinstance(parent, ast.AugAssign) and parent.value is n:
            wrap = True
        elif isinstance(parent, ast.Dict) and n in parent.values:
            wrap = True
        elif (len(s) >= 50 or s.startswith(("--- ", "=== "))) and " " in s:
            wrap = True                  # a long sentence anywhere in a function (return, assignment, list item, conditional value)
        if wrap and multiword:
            a, b = _span(n, starts)
            edits.append((a, b, "tx(" + src_bytes[a:b].decode("utf-8") + ")"))
            used.add("tx")

    # 2b. tr("template {0}", arg, ...) calls that already exist (after the rewrite) -> template keys with their arguments
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "tr" and n.args and \
                isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            args = [ast.get_source_segment(text, a) or "" for a in n.args[1:]]
            keys.insert(0, {"kind": "template", "en": n.args[0].value, "args": args, "where": f"{path}:{n.lineno}"})

    # 3. display tables -> tbl({...}); their string values are keys too
    for name in TABLES.get(path, []):
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                for c in ast.walk(node.value):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str) and WORDY.search(c.value) and (" " in c.value or len(c.value) > 12 or c.value[:1].isupper()):
                        keys.append({"kind": "text", "en": c.value, "where": f"{path}:{c.lineno}", "note": f"table {name}"})
                a, b = _span(node.value, starts)
                edits.append((a, b, "tbl(" + src_bytes[a:b].decode("utf-8") + ")"))
                used.add("tbl")
    return text, src_bytes, edits, keys, used, tree


def _drop_nested(edits):
    edits = sorted(edits, key=lambda e: (e[0], -e[1]))
    out, last_end = [], -1
    for e in edits:
        if e[0] >= last_end:
            out.append(e)
            last_end = e[1]
    return out


def rewrite():
    total = 0
    for path in FILES:
        text, src_bytes, edits, _keys, used, tree = collect(path)
        if "from i18n import" in text:
            print(f"skip {path}: already rewritten")
            continue
        edits = _drop_nested(edits)
        for n in ast.walk(tree):
            if isinstance(n, ast.JoinedStr) and len(n.values) == 1 and isinstance(n.values[0], ast.FormattedValue):
                fv = n.values[0]
                spec = "".join(x.value for x in fv.format_spec.values) if fv.format_spec is not None and all(isinstance(x, ast.Constant) for x in fv.format_spec.values) else ""
                if "%" in spec and fv.conversion == -1:
                    a, b = _span(n, _offsets(src_bytes))
                    if not any(e[0] <= a and b <= e[1] for e in edits):
                        edits.append((a, b, "fmt_date(%s, %r)" % (ast.get_source_segment(text, fv.value), spec)))
                        used.add("fmt_date")
        edits = _drop_nested(edits)
        if not edits:
            continue
        out = src_bytes
        for a, b, rep in sorted(edits, key=lambda e: -e[0]):
            out = out[:a] + rep.encode("utf-8") + out[b:]
        text2 = out.decode("utf-8")
        names = sorted(n for n in ("fmt_date", "join_list", "tbl", "tr", "tx") if n in used)
        # insert the import after the last top-level import
        tree2 = ast.parse(text2)
        last = max((n.end_lineno for n in tree2.body if isinstance(n, (ast.Import, ast.ImportFrom))), default=0)
        lines = text2.split("\n")
        lines.insert(last, "from i18n import " + ", ".join(names) + "  # noqa: E402 - translation helpers (engine/i18n.py)")
        open(os.path.join(APP, path), "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        ast.parse("\n".join(lines))
        total += len(edits)
        print(f"{path}: {len(edits)} edits")
    print("total edits:", total)


def _vocab():
    out = []
    for name in ("vocab.txt", "vocab_astro.txt", "vocab_auto.txt"):
        path = os.path.join(TODO, name)
        if os.path.exists(path):
            out += [{"kind": "text", "en": line.rstrip("\n"), "where": name} for line in open(path, encoding="utf-8")
                    if line.strip() and not line.startswith("#")]
    return out


def extract():
    os.makedirs(TODO, exist_ok=True)
    seen, keys = {}, []
    for path in FILES:
        _text, _sb, _edits, ks, _used, _tree = collect(path)
        for k in ks:
            key = k["en"]
            if key in seen:
                continue
            k["id"] = len(keys) + 1
            seen[key] = k["id"]
            keys.append(k)
    for k in _vocab():
        if k["en"] not in seen:
            k["id"] = len(keys) + 1
            seen[k["en"]] = k["id"]
            keys.append(k)
    json.dump(keys, open(os.path.join(TODO, "keys.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("keys:", len(keys), "templates:", sum(1 for k in keys if k["kind"] == "template"))


def write_batches(size=90):
    keys = json.load(open(os.path.join(TODO, "keys.json"), encoding="utf-8"))
    for i in range(0, len(keys), size):
        chunk = keys[i:i + size]
        with open(os.path.join(TODO, f"batch_{i // size + 1:02d}.txt"), "w", encoding="utf-8") as fh:
            for k in chunk:
                note = ""
                if k["kind"] == "template":
                    note = "   ## " + ", ".join(f"{{{n}}}={a[:40]}" for n, a in enumerate(k["args"]))
                fh.write(str(k["id"]) + "\t" + k["en"].replace("\n", "\\n") + note + "\n")
    print("batches:", (len(keys) + size - 1) // size)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "rewrite":
        rewrite()
    elif cmd == "extract":
        extract()
        write_batches()
    else:
        print(__doc__)
