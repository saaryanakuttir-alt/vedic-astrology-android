"""make_wf_batches.py - cuts the remaining English text (i18n_todo/keys2.json and keys_kb.json) into small translation
batches for parallel translators.

    python tools/make_wf_batches.py [words_per_batch]      writes i18n_todo/wf/in_001.txt ... and wf/batches.json

Each line:  id<TAB>English text (newlines as the two characters \\n)  [## note about the placeholders]
Lines starting with # are context only. Sentences of one paragraph stay together in one batch.
"""
import json
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(APP, "i18n_todo")
WF = os.path.join(TODO, "wf")


def line_for(k):
    note = ""
    if k.get("kind") == "template" and k.get("args"):
        note = "   ## " + ", ".join("{%d}=%s" % (i, a[:40]) for i, a in enumerate(k["args"]))
    return "%d\t%s%s" % (k["id"], k["en"].replace("\n", "\\n"), note)


def main():
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    os.makedirs(WF, exist_ok=True)
    for name in os.listdir(WF):
        if name.startswith(("in_", "out_")):
            os.remove(os.path.join(WF, name))
    keys = []
    for name in ("keys2.json", "keys_kb.json"):
        keys += json.load(open(os.path.join(TODO, name), encoding="utf-8"))
    batches, cur, words, last_where = [], [], 0, None
    for k in keys:
        w = len(k["en"].split())
        source = k.get("where", "").split(":")[0]
        # start a new batch when the size is reached, but never in the middle of one source paragraph
        new_paragraph = k.get("where") != last_where
        if cur and words + w > size and new_paragraph:
            batches.append(cur)
            cur, words = [], 0
        cur.append(k)
        words += w
        last_where = k.get("where")
    if cur:
        batches.append(cur)
    index = []
    for n, batch in enumerate(batches, 1):
        path = os.path.join(WF, "in_%03d.txt" % n)
        with open(path, "w", encoding="utf-8") as fh:
            prev = None
            for k in batch:
                src = k.get("where", "").split(":")
                head = ":".join(src[:2])
                if head != prev:
                    fh.write("# %s\n" % head)
                    prev = head
                fh.write(line_for(k) + "\n")
        index.append({"n": n, "in": "in_%03d.txt" % n, "out": "out_%03d.txt" % n, "ids": len(batch),
                      "words": sum(len(k["en"].split()) for k in batch)})
    json.dump(index, open(os.path.join(WF, "batches.json"), "w", encoding="utf-8"), indent=1)
    print(f"{len(index)} batches, {sum(b['ids'] for b in index)} texts, {sum(b['words'] for b in index)} words")


if __name__ == "__main__":
    main()
