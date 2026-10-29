"""Generate the README artwork (banner, swatch galleries, download buttons) from the color books.

Usage:  python scripts/build_assets.py
Re-run after adding or replacing a library in color-books/.
"""

from __future__ import annotations

import colorsys
from pathlib import Path
from xml.sax.saxutils import escape

import colorbooks

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "color-books"
ASSETS = ROOT / "assets"

FONT = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Arial, sans-serif"
BG, CARD, LINE, TEXT, MUTED = "#0E1014", "#161920", "#262A33", "#F4F5F7", "#9AA3B2"

# Display order and copy for every library (file name -> label, suffix, blurb)
CATALOG = {
    "graphics": (
        "Graphics",
        [
            ("PANTONE Solid Coated-V4.acb", "Solid Coated", "C", "Core PMS spot colors on coated stock"),
            ("PANTONE Solid Uncoated-V4.acb", "Solid Uncoated", "U", "Core PMS spot colors on uncoated stock"),
            ("PANTONE Color Bridge Coated-V4.acb", "Color Bridge Coated", "CP", "Spot colors matched to CMYK process"),
            ("PANTONE Color Bridge Uncoated-V4.acb", "Color Bridge Uncoated", "UP", "Spot colors matched to CMYK process"),
            ("PANTONE CMYK Coated.acb", "CMYK Coated", "C", "Process-color builds for coated stock"),
            ("PANTONE CMYK Uncoated.acb", "CMYK Uncoated", "U", "Process-color builds for uncoated stock"),
            ("PANTONE Extended Gamut Coated.acb", "Extended Gamut Coated", "XGC", "7-color CMYK + OGV process"),
            ("PANTONE Metallics Solid Coated.acb", "Metallics Solid Coated", "C", "Metallic spot colors"),
            ("PANTONE Pastels & Neons Coated.acb", "Pastels & Neons Coated", "C", "Soft pastels and fluorescent neons"),
            ("PANTONE Pastels & Neons Uncoated.acb", "Pastels & Neons Uncoated", "U", "Soft pastels and fluorescent neons"),
            ("PANTONE SkinTone(TM) Guide.acb", "SkinTone™ Guide", "SP", "Real human skin tones"),
        ],
    ),
    "fashion-home-interiors": (
        "Fashion, Home + Interiors",
        [
            ("PANTONE(R) F+H cotton TCX.ase", "Cotton", "TCX", "FHI colors dyed on cotton"),
            ("PANTONE(R) FHI Paper TPG.ase", "Paper", "TPG", "FHI colors printed on paper"),
            ("PANTONE(R) FHI Polyester TSX.ase", "Polyester", "TSX", "FHI colors on polyester"),
            ("PANTONE(R) FHI Metallic Shimmers TPM.ase", "Metallic Shimmers", "TPM", "FHI metallic shimmer finishes"),
            ("PANTONE(R) F+H nylon brights TN.acb", "Nylon Brights", "TN", "Neon brights on nylon"),
        ],
    ),
}


def load() -> dict[str, list[tuple[colorbooks.ColorBook, str, str, str]]]:
    out = {}
    for folder, (_, entries) in CATALOG.items():
        out[folder] = [(colorbooks.read(BOOKS / folder / f), label, sfx, blurb) for f, label, sfx, blurb in entries]
    return out


def hue_sorted(hexes: list[str]) -> list[str]:
    def key(h: str):
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hue, light, sat = colorsys.rgb_to_hls(r, g, b)
        neutral = sat < 0.12 or light < 0.08 or light > 0.95
        # bucket by hue, light -> dark inside each bucket, neutrals last
        return (neutral, 0 if neutral else int((hue + 0.96) % 1 * 10), -light)
    return sorted(hexes, key=key)


def sample(book: colorbooks.ColorBook, n: int) -> list[str]:
    s = book.swatches
    if len(s) <= n:
        return [w.hex for w in s]
    return [s[round(i * (len(s) - 1) / (n - 1))].hex for i in range(n)]


def write(name: str, svg: str) -> None:
    path = ASSETS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg.strip() + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {path.relative_to(ROOT)}")


# --------------------------------------------------------------------------- banner

def banner(books, total: int, n_books: int) -> str:
    solid = books["graphics"][0][0]
    page = 7  # Solid Coated pages hold seven tints of one family
    pages = len(solid.swatches) // page
    picks = [round(i * (pages * 0.78) / 8) for i in range(9)]  # stay in the chromatic part of the book
    px, py = 1010, 392
    angles = [-62 + i * 10.5 for i in range(9)]

    strips = []
    for i, (pg, ang) in enumerate(zip(picks, angles)):
        tints = solid.swatches[pg * page:pg * page + 6]
        blocks = "".join(
            f'<rect x="{px - 42}" y="{py - 320 + j * 41.7:.1f}" width="84" height="42.2" fill="{t.hex}"/>'
            for j, t in enumerate(tints)
        )
        label = escape(tints[0].name.replace("PANTONE ", ""))
        strips.append(f"""
    <g transform="rotate({ang} {px} {py})" filter="url(#shadow)">
      <animateTransform attributeName="transform" type="rotate" from="-62 {px} {py}" to="{ang} {px} {py}"
        begin="{0.15 + i * 0.07:.2f}s" dur="1.1s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.16 1 0.3 1"/>
      <g clip-path="url(#strip)">
        <rect x="{px - 42}" y="{py - 320}" width="84" height="340" fill="#FFFFFF"/>
        {blocks}
      </g>
      <text x="{px}" y="{py - 46}" text-anchor="middle" font-size="11" font-weight="700" fill="#1B1D22">{label}</text>
    </g>""")

    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="440" viewBox="0 0 1280 440" font-family="{FONT}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#151821"/><stop offset="1" stop-color="{BG}"/>
    </linearGradient>
    <linearGradient id="rainbow" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#FFD100"/><stop offset=".25" stop-color="#FF6A13"/>
      <stop offset=".5" stop-color="#E10098"/><stop offset=".75" stop-color="#3D5CFF"/>
      <stop offset="1" stop-color="#00B2A9"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.79" cy="0.55" r="0.45">
      <stop offset="0" stop-color="#3D5CFF" stop-opacity=".22"/><stop offset="1" stop-color="#3D5CFF" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="strip"><rect x="{px - 42}" y="{py - 320}" width="84" height="340" rx="9"/></clipPath>
    <clipPath id="card"><rect width="1280" height="440" rx="24"/></clipPath>
    <filter id="shadow" x="-30%" y="-10%" width="160%" height="130%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity=".45"/>
    </filter>
  </defs>
  <g clip-path="url(#card)">
    <rect width="1280" height="440" fill="url(#bg)"/>
    <rect width="1280" height="440" fill="url(#glow)"/>
    {"".join(strips)}
    <circle cx="{px}" cy="{py}" r="9" fill="#C9CED8" stroke="#6B7280" stroke-width="2"/>
    <rect y="434" width="1280" height="6" fill="url(#rainbow)"/>
  </g>
  <text x="72" y="104" font-size="14" font-weight="600" letter-spacing="3.2" fill="{MUTED}">COLOR LIBRARIES · ADOBE ILLUSTRATOR 2024+</text>
  <text x="68" y="186" font-size="80" font-weight="800" letter-spacing="2" fill="{TEXT}">PANTONE<tspan font-size="30" dy="-38" font-weight="400">®</tspan></text>
  <text x="70" y="258" font-size="62" font-weight="300" fill="url(#rainbow)">Color Books</text>
  <text x="72" y="306" font-size="20" fill="#C9CED8">{n_books} libraries · {total:,} swatches · .acb &amp; .ase</text>
  <g font-size="14" font-weight="600">
    <rect x="72" y="334" width="104" height="34" rx="17" fill="{CARD}" stroke="{LINE}"/>
    <text x="124" y="356" text-anchor="middle" fill="{TEXT}">Graphics</text>
    <rect x="186" y="334" width="214" height="34" rx="17" fill="{CARD}" stroke="{LINE}"/>
    <text x="293" y="356" text-anchor="middle" fill="{TEXT}">Fashion, Home + Interiors</text>
    <rect x="410" y="334" width="150" height="34" rx="17" fill="url(#rainbow)"/>
    <text x="485" y="356" text-anchor="middle" fill="#111">One-click ZIP</text>
  </g>
</svg>"""


# --------------------------------------------------------------------------- galleries

def gallery(title: str, entries) -> str:
    row_h, top, w = 58, 78, 1000
    sx, sw, n = 330, 600, 60
    h = top + row_h * len(entries) + 24
    rows = []
    for i, (book, label, sfx, _) in enumerate(entries):
        y = top + i * row_h
        cells = hue_sorted(sample(book, n))
        cw = sw / len(cells)
        rects = "".join(
            f'<rect x="{sx + k * cw:.2f}" y="{y + 8}" width="{cw + 0.6:.2f}" height="30" fill="{c}"/>'
            for k, c in enumerate(cells)
        )
        rows.append(f"""
  <text x="40" y="{y + 22}" font-size="16" font-weight="600" fill="{TEXT}">{escape(label)}</text>
  <text x="40" y="{y + 41}" font-size="12.5" fill="{MUTED}">{book.count:,} swatches · {sfx} · .{book.format.lower()}</text>
  <g clip-path="url(#r{i})">{rects}</g>
  <clipPath id="r{i}"><rect x="{sx}" y="{y + 8}" width="{sw}" height="30" rx="6"/></clipPath>""")
        if i:
            rows.append(f'<line x1="40" x2="{w - 40}" y1="{y - 6}" y2="{y - 6}" stroke="{LINE}"/>')
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">
  <rect width="{w}" height="{h}" rx="18" fill="{CARD}"/>
  <rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{LINE}"/>
  <text x="40" y="48" font-size="13" font-weight="700" letter-spacing="2.5" fill="{MUTED}">{escape(title.upper())}</text>
  {"".join(rows)}
</svg>"""


# --------------------------------------------------------------------------- buttons

ARROW = "M0 -11 V7 M-7 0 L0 7 L7 0 M-9 12 H9"


def button(w: int, h: int, title: str, sub: str, strip: list[str], primary: bool) -> str:
    r = h / 2 - 8 if primary else h / 2 - 7
    cx = 16 + r
    tx = cx + r + 16
    ts, ss = (22, 14) if primary else (16, 12)
    cw = (w - 2) / len(strip)
    bar = "".join(f'<rect x="{1 + k * cw:.2f}" y="{h - 6}" width="{cw + 0.6:.2f}" height="6" fill="{c}"/>' for k, c in enumerate(strip))
    scale = 1.0 if primary else 0.8
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFD100"/><stop offset=".35" stop-color="#FF4F6D"/>
      <stop offset=".7" stop-color="#7A3CFF"/><stop offset="1" stop-color="#00A3E0"/>
    </linearGradient>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="14"/></clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="{CARD if primary else BG}"/>
    {bar}
  </g>
  <rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{LINE}"/>
  <circle cx="{cx}" cy="{h / 2 - 2}" r="{r}" fill="url(#g)">
    <animate attributeName="r" values="{r};{r + 1.5};{r}" dur="2.4s" repeatCount="indefinite"/>
  </circle>
  <path d="{ARROW}" transform="translate({cx} {h / 2 - 3}) scale({scale})" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="{tx}" y="{h / 2 - (4 if primary else 3)}" font-size="{ts}" font-weight="700" fill="{TEXT}">{escape(title)}</text>
  <text x="{tx}" y="{h / 2 + (16 if primary else 12)}" font-size="{ss}" fill="{MUTED}">{escape(sub)}</text>
</svg>"""


# --------------------------------------------------------------------------- main

def main() -> None:
    books = load()
    every = [e for entries in books.values() for e in entries]
    total = sum(b.count for b, *_ in every)

    print(f"{len(every)} libraries, {total:,} swatches")
    for folder, entries in books.items():
        for b, label, *_ in entries:
            print(f"  {folder:24} {label:26} {b.format} {b.model:4} {b.count:>6,}")

    spectrum = hue_sorted([c for b, *_ in every for c in sample(b, 12)])
    write("banner.svg", banner(books, total, len(every)))
    for folder, (title, _) in CATALOG.items():
        write(f"gallery-{folder}.svg", gallery(title, books[folder]))

    g, f = books["graphics"], books["fashion-home-interiors"]
    write("buttons/download-all.svg", button(
        470, 84, "Download All Color Books", f"ZIP · {len(every)} libraries · {total:,} swatches", spectrum, True))
    write("buttons/download-graphics.svg", button(
        300, 64, "Graphics Pack", f"{len(g)} libraries · {sum(b.count for b, *_ in g):,} swatches",
        hue_sorted([c for b, *_ in g for c in sample(b, 10)]), False))
    write("buttons/download-fhi.svg", button(
        300, 64, "Fashion, Home + Interiors", f"{len(f)} libraries · {sum(b.count for b, *_ in f):,} swatches",
        hue_sorted([c for b, *_ in f for c in sample(b, 20)]), False))


if __name__ == "__main__":
    main()
