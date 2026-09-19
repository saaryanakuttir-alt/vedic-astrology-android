"""
pdf_writer.py - a tiny, dependency-free PDF writer (A4 pages, Helvetica text, lines, rectangles).

No third-party library on purpose: the app must build with what it already ships and stay
fully offline. Text uses the PDF's built-in Helvetica / Helvetica-Bold (WinAnsi encoding, so
Latin letters, digits, curly quotes and dashes work; anything else is replaced by "?").
Pure Python - no Kivy - so it is easy to test.
"""
import zlib

PAGE_W, PAGE_H = 595.28, 841.89

# Helvetica advance widths (1/1000 em) for the printable ASCII range 32..126
_ASCII_WIDTHS = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]
_CP1252_WIDTHS = {0x85: 1000, 0x91: 222, 0x92: 222, 0x93: 333, 0x94: 333, 0x95: 350, 0x96: 556, 0x97: 1000}


def to_bytes(text):
    return text.encode("cp1252", "replace")


def text_width(text, size, bold=False):
    total = 0
    for b in to_bytes(text):
        total += _ASCII_WIDTHS[b - 32] if 32 <= b <= 126 else _CP1252_WIDTHS.get(b, 556)
    return total * size / 1000.0 * (1.06 if bold else 1.0)


def wrap(text, size, max_width, bold=False):
    """Greedy word wrap; returns a list of lines."""
    lines = []
    for raw in (text or "").split("\n"):
        words, line = raw.split(), ""
        if not words:
            lines.append("")
            continue
        for word in words:
            trial = f"{line} {word}" if line else word
            if line and text_width(trial, size, bold) > max_width:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def _escape(text):
    out = bytearray()
    for b in to_bytes(text):
        if b in (0x28, 0x29, 0x5C):
            out += b"\\" + bytes([b])
        elif 32 <= b <= 126:
            out.append(b)
        else:
            out += b"\\%03o" % b
    return bytes(out)


class Pdf:
    def __init__(self, title="", author=""):
        self.title, self.author = title, author
        self.pages = []
        self._ops = None

    # ---- pages and drawing
    def new_page(self):
        self._ops = []
        self.pages.append(self._ops)

    def text(self, x, y, text, size=10, bold=False, color=(0, 0, 0)):
        r, g, b = color
        self._ops.append(b"BT /%s %.2f Tf %.3f %.3f %.3f rg %.2f %.2f Td (" % (b"F2" if bold else b"F1", size, r, g, b, x, y)
                         + _escape(text) + b") Tj ET")

    def line(self, x1, y1, x2, y2, width=0.6, color=(0, 0, 0)):
        r, g, b = color
        self._ops.append(b"q %.2f w %.3f %.3f %.3f RG %.2f %.2f m %.2f %.2f l S Q" % (width, r, g, b, x1, y1, x2, y2))

    def rect(self, x, y, w, h, width=0.6, color=(0, 0, 0), fill=None):
        r, g, b = color
        op = b"q %.2f w %.3f %.3f %.3f RG " % (width, r, g, b)
        if fill is not None:
            op += b"%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re B Q" % (fill + (x, y, w, h))
        else:
            op += b"%.2f %.2f %.2f %.2f re S Q" % (x, y, w, h)
        self._ops.append(op)

    def polygon(self, points, fill):
        """A filled polygon (no outline) through `points` [(x, y), ...]."""
        r, g, b = fill
        path = b" ".join(b"%.2f %.2f %s" % (x, y, b"m" if i == 0 else b"l") for i, (x, y) in enumerate(points))
        self._ops.append(b"q %.3f %.3f %.3f rg " % (r, g, b) + path + b" f Q")

    # ---- serialise
    def output(self):
        objs = []                                    # index i holds object number i+1

        def add(body):
            objs.append(body)
            return len(objs)

        catalog = add(b"")                            # 1 (filled in below)
        pages_root = add(b"")                         # 2
        f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        info = add(b"<< /Title (" + _escape(self.title) + b") /Author (" + _escape(self.author) + b") "
                   b"/Producer (Vedic Astrology app) >>")
        kids = []
        for ops in self.pages:
            data = zlib.compress(b"\n".join(ops))
            stream = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
            page = add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] /Contents %d 0 R "
                       b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> >>" % (pages_root, PAGE_W, PAGE_H, stream, f1, f2))
            kids.append(page)
        objs[pages_root - 1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids) + \
                               b"] /Count %d >>" % len(kids)
        objs[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_root

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objs) + 1, catalog, info, xref)
        return bytes(out)
