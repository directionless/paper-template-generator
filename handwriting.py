#!/usr/bin/env python3
"""Generate handwriting practice paper as a PDF, including slant guides for cursive.

No third-party dependencies: the PDF is written directly.
Run `python3 handwriting.py --help` for options.
"""

import argparse
import math
import sys
import zlib

PT_PER = {"pt": 1.0, "mm": 72 / 25.4, "cm": 72 / 2.54, "in": 72.0}

PAGE_SIZES = {  # in points, portrait
    "letter": (612, 792),
    "legal": (612, 1008),
    "a4": (595.28, 841.89),
    "a5": (419.53, 595.28),
}

NAMED_COLORS = {
    "black": "#000000", "gray": "#888888", "grey": "#888888", "lightgray": "#cccccc",
    "red": "#d33a3a", "pink": "#f2a0b0", "blue": "#3a64c8", "lightblue": "#9db8e8",
    "green": "#3a9a5a", "lightgreen": "#a8d8b0", "orange": "#e08a2a", "purple": "#8a5ac8",
}

# Reasonable defaults. Each style is "WIDTH DASH COLOR" (any order).
DEFAULT_STYLES = {
    "ascender": "0.7 solid #000000",
    "midline": "0.6 dashed #7f9bd4",
    "baseline": "1.1 solid #000000",
    "descender": "0.5 dotted #9aaedb",
    "slant": "0.35 solid #b8c8ea",
}


def length(s):
    """Parse a length like '8mm', '0.5in', '12pt', '1cm'. Bare numbers are mm."""
    s = str(s).strip().lower()
    for unit, factor in PT_PER.items():
        if s.endswith(unit):
            return float(s[: -len(unit)]) * factor
    return float(s) * PT_PER["mm"]


def color(s):
    s = NAMED_COLORS.get(s.lower(), s)
    if not s.startswith("#") or len(s) not in (4, 7):
        raise ValueError(f"bad color {s!r} (use #rrggbb, #rgb, or a name like 'blue')")
    h = s[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


class Style:
    def __init__(self, spec):
        self.enabled = True
        self.width = 0.5
        self.dash = "solid"
        self.pattern = None  # custom dash pattern in pt
        self.rgb = (0, 0, 0)
        self.update(spec)

    def update(self, spec):
        for tok in _tokens(spec):
            t = tok.lower()
            if t in ("none", "off", "hide"):
                self.enabled = False
            elif t in ("on", "show"):
                self.enabled = True
            elif t in ("solid", "dashed", "dotted"):
                self.dash, self.pattern = t, None
            elif t.startswith("dash="):
                self.dash = "custom"
                self.pattern = [float(x) for x in t[5:].split("/")]
            elif t.startswith("#") or t in NAMED_COLORS:
                self.rgb = color(t)
            else:
                try:
                    self.width = length(t) if t[-1].isalpha() else float(t)  # bare width = pt
                except ValueError:
                    raise ValueError(f"don't understand {tok!r} in style {spec!r}") from None
        return self

    def pdf(self):
        """PDF operators that set this stroke style."""
        r, g, b = self.rgb
        ops = [f"{r:.3f} {g:.3f} {b:.3f} RG", f"{self.width:.3f} w"]
        if self.dash == "solid":
            ops += ["[] 0 d", "0 J"]
        elif self.dash == "dashed":
            on = max(3.0, self.width * 5)
            ops += [f"[{on:.2f} {on * 0.8:.2f}] 0 d", "0 J"]
        elif self.dash == "dotted":
            ops += [f"[0 {max(2.0, self.width * 3):.2f}] 0 d", "1 J"]  # round caps = dots
        else:
            ops += ["[" + " ".join(f"{x:.2f}" for x in self.pattern) + "] 0 d", "0 J"]
        return "\n".join(ops)


def _tokens(spec):
    # Split on whitespace; commas allowed as separators except inside dash=a/b.
    return [t for part in spec.split() for t in ([part] if part.startswith("dash=") else part.split(",")) if t]


def build_page(args, styles, page_w, page_h):
    m_l, m_r, m_t, m_b = args.margin_left, args.margin_right, args.margin_top, args.margin_bottom
    xh, asc, desc, gap = args.x_height, args.ascender, args.descender, args.row_gap
    row_h = asc + desc
    avail = page_h - m_t - m_b
    rows = args.rows or max(1, int((avail + gap) // (row_h + gap)))
    used = rows * row_h + (rows - 1) * gap
    top = page_h - m_t - max(0.0, (avail - used) / 2)  # center the block vertically
    x0, x1 = m_l, page_w - m_r

    out = []
    bands = []  # (y_bottom, y_top) of each row, for slant clipping
    for i in range(rows):
        y_asc = top - i * (row_h + gap)
        y_base = y_asc - asc
        y_desc = y_base - desc
        y_mid = y_base + xh
        bands.append((y_desc, y_asc))

        if args.xheight_fill:
            r, g, b = color(args.xheight_fill)
            out.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x0:.2f} {y_base:.2f} {x1 - x0:.2f} {xh:.2f} re f")

    # Slant lines go under the horizontal guides.
    st = styles["slant"]
    if st.enabled and args.slant_spacing > 0:
        tan = math.tan(math.radians(args.slant_angle))
        clip_bands = bands if args.slant_span == "row" else [(bands[-1][0], bands[0][1])]
        out.append("q " + st.pdf())
        for yb, yt in clip_bands:
            h = yt - yb
            dx = h / tan  # horizontal run of one slant line across the band
            out.append(f"q {x0:.2f} {yb:.2f} {x1 - x0:.2f} {h:.2f} re W n")
            # Anchor lines at the left margin on each band's bottom so rows line up.
            x = x0 - math.ceil(dx / args.slant_spacing) * args.slant_spacing
            while x <= x1:
                out.append(f"{x:.2f} {yb:.2f} m {x + dx:.2f} {yt:.2f} l S")
                x += args.slant_spacing
            out.append("Q")
        out.append("Q")

    for name in ("descender", "ascender", "midline", "baseline"):
        st = styles[name]
        if not st.enabled:
            continue
        out.append("q " + st.pdf())
        for y_desc, y_asc in bands:
            y_base = y_asc - asc
            y = {"ascender": y_asc, "midline": y_base + xh, "baseline": y_base, "descender": y_desc}[name]
            out.append(f"{x0:.2f} {y:.2f} m {x1:.2f} {y:.2f} l S")
        out.append("Q")

    if args.margin_line:
        st = Style(args.margin_line)
        out.append(f"q {st.pdf()} {x0:.2f} {bands[-1][0]:.2f} m {x0:.2f} {bands[0][1]:.2f} l S Q")

    return "\n".join(out).encode()


def write_pdf(path, pages, page_w, page_h):
    objs = []  # index i holds object number i+1

    def add(body):
        objs.append(body)
        return len(objs)

    catalog = add(None)
    pages_obj = add(None)
    kids = []
    for content in pages:
        data = zlib.compress(content)
        stream = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
        kids.append(add(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {page_w:.2f} {page_h:.2f}] "
            f"/Contents {stream} 0 R /Resources << >> >>".encode()
        ))
    objs[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()
    objs[pages_obj - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
    )

    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, body in enumerate(objs, 1):
        offsets.append(len(buf))
        buf += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(buf)
    buf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        buf += b"%010d 00000 n \n" % off
    buf += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)

    with open(path, "wb") as f:
        f.write(buf)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Generate handwriting practice paper (PDF) with optional cursive slant guides.",
        epilog="Lengths accept mm, cm, in, or pt suffixes (bare numbers are mm). "
        "Line styles are 'WIDTH DASH COLOR' in any order, e.g. '0.8 dashed #3366cc', "
        "'dotted red', 'dash=6/2', or 'none' to hide the line. Bare widths are in points.",
    )
    p.add_argument("-o", "--output", default="handwriting.pdf", help="output file (default: %(default)s)")
    p.add_argument("--paper", default="letter", choices=sorted(PAGE_SIZES), help="paper size (default: %(default)s)")
    p.add_argument("--landscape", action="store_true", help="landscape orientation")
    p.add_argument("--pages", type=int, default=1, help="number of pages (default: %(default)s)")

    g = p.add_argument_group("row geometry")
    g.add_argument("--x-height", type=length, default="8mm",
                   help="baseline to midline: the height of letters like a, c, o (default: 8mm)")
    g.add_argument("--ascender", type=length, default=None,
                   help="baseline to top line: the height of letters like l, h, k (default: 2 x x-height)")
    g.add_argument("--descender", type=length, default=None,
                   help="baseline to bottom line: the depth of letters like g, y, p (default: x-height)")
    g.add_argument("--row-gap", type=length, default="5mm",
                   help="blank space between one row's bottom line and the next row's top line (default: 5mm)")
    g.add_argument("--rows", type=int, default=0, help="rows per page (default: as many as fit)")

    g = p.add_argument_group("slant guides")
    g.add_argument("--slant-angle", type=float, default=55.0,
                   help="slant angle in degrees from horizontal; 90 is upright (default: 55)")
    g.add_argument("--slant-spacing", type=length, default=None,
                   help="horizontal distance between slant lines; 0 disables them (default: x-height)")
    g.add_argument("--slant-span", choices=("row", "page"), default="row",
                   help="draw slants inside each row only, or continuously down the page (default: row)")
    g.add_argument("--no-slant", action="store_true", help="turn off slant guides")

    g = p.add_argument_group("margins")
    g.add_argument("--margin", type=length, default="15mm", help="all margins (default: 15mm)")
    for side in ("top", "bottom", "left", "right"):
        g.add_argument(f"--margin-{side}", type=length, default=None, help=f"{side} margin (overrides --margin)")
    g.add_argument("--margin-line", metavar="STYLE", default=None,
                   help="draw a vertical line at the left margin with this style, e.g. '0.8 solid pink'")

    g = p.add_argument_group("line styles")
    for name, default in DEFAULT_STYLES.items():
        g.add_argument(f"--{name}-style", metavar="STYLE", default="",
                       help=f"style for the {name} line (default: '{default}')")
    g.add_argument("--xheight-fill", metavar="COLOR", default=None,
                   help="shade the band between baseline and midline, e.g. '#fff4cc'")
    g.add_argument("--color", default=None,
                   help="set one color for all guide lines (slant keeps its default unless styled)")

    args = p.parse_args(argv)
    if args.ascender is None:
        args.ascender = 2 * args.x_height
    if args.descender is None:
        args.descender = args.x_height
    if args.slant_spacing is None:
        args.slant_spacing = args.x_height
    for side in ("top", "bottom", "left", "right"):
        if getattr(args, f"margin_{side}") is None:
            setattr(args, f"margin_{side}", args.margin)
    if args.ascender < args.x_height:
        p.error("--ascender must be at least --x-height")

    try:
        styles = {}
        for name, default in DEFAULT_STYLES.items():
            st = Style(default)
            if args.color and name != "slant":
                st.update(args.color)
            styles[name] = st.update(getattr(args, f"{name}_style"))
        if args.margin_line:
            Style(args.margin_line)  # validate early
        if args.no_slant:
            styles["slant"].enabled = False
    except ValueError as e:
        p.error(str(e))

    w, h = PAGE_SIZES[args.paper]
    if args.landscape:
        w, h = h, w
    page = build_page(args, styles, w, h)
    write_pdf(args.output, [page] * args.pages, w, h)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    sys.exit(main())
