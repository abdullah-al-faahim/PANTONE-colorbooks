"""Minimal readers for Adobe Color Book (.acb) and Adobe Swatch Exchange (.ase) files.

Only what this repository needs: book title, color names and an approximate
sRGB preview value for every swatch.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Swatch:
    name: str
    model: str
    hex: str


@dataclass
class ColorBook:
    path: Path
    title: str
    format: str
    model: str
    swatches: list[Swatch] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.swatches)


# --------------------------------------------------------------------------- color maths

def _clamp(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def _to_hex(r: float, g: float, b: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(round(_clamp(c) * 255) for c in (r, g, b)))


def _srgb_gamma(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def lab_to_hex(L: float, a: float, b: float) -> str:
    """CIE L*a*b* (D50, as Adobe stores it) -> sRGB hex."""
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200

    def finv(t: float) -> float:
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787

    x, y, z = 0.96422 * finv(fx), 1.0 * finv(fy), 0.82521 * finv(fz)
    # XYZ(D50) -> linear sRGB, Bradford-adapted matrix
    r = 3.1338561 * x - 1.6168667 * y - 0.4906146 * z
    g = -0.9787684 * x + 1.9161415 * y + 0.0334540 * z
    bl = 0.0719453 * x - 0.2289914 * y + 1.4052427 * z
    return _to_hex(*(_srgb_gamma(_clamp(c)) for c in (r, g, bl)))


def cmyk_to_hex(c: float, m: float, y: float, k: float) -> str:
    """Naive CMYK (0..1) -> sRGB hex. Good enough for a preview."""
    return _to_hex((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))


# --------------------------------------------------------------------------- .acb

class _Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, n: int) -> bytes:
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def u16(self) -> int:
        return struct.unpack(">H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]

    def utf16(self, chars: int) -> str:
        return self.take(chars * 2).decode("utf-16-be").rstrip("\x00")


def _acb_string(r: _Reader) -> str:
    text = r.utf16(r.u32())
    # Localised strings look like "$$$/colorbook/PANTONE/title=PANTONE Solid Coated"
    return text.split("=", 1)[1] if text.startswith("$$$") and "=" in text else text


def read_acb(path: Path) -> ColorBook:
    r = _Reader(path.read_bytes())
    if r.take(4) != b"8BCB":
        raise ValueError(f"{path.name}: not an .acb file")
    r.u16()  # version
    r.u16()  # book id
    title = _acb_string(r)
    prefix = _acb_string(r)
    suffix = _acb_string(r)
    _acb_string(r)  # description
    count = r.u16()
    r.u16()  # page size
    r.u16()  # page selector offset
    space = r.u16()
    model = {0: "RGB", 2: "CMYK", 7: "Lab"}.get(space, f"#{space}")

    book = ColorBook(path, title.replace("^R", "®").replace("^C", "©"), "ACB", model)
    for _ in range(count):
        name = _acb_string(r)
        r.take(6)  # catalogue code
        if space == 0:
            red, green, blue = r.take(3)
            hx = _to_hex(red / 255, green / 255, blue / 255)
        elif space == 2:
            c, m, y, k = (1 - v / 255 for v in r.take(4))
            hx = cmyk_to_hex(c, m, y, k)
        elif space == 7:
            l, a, b = r.take(3)
            hx = lab_to_hex(l / 2.55, a - 128, b - 128)
        else:
            raise ValueError(f"{path.name}: unsupported color space {space}")
        if name.strip():  # empty names are page-padding placeholders
            book.swatches.append(Swatch(f"{prefix}{name}{suffix}".strip(), model, hx))
    return book


# --------------------------------------------------------------------------- .ase

def read_ase(path: Path) -> ColorBook:
    r = _Reader(path.read_bytes())
    if r.take(4) != b"ASEF":
        raise ValueError(f"{path.name}: not an .ase file")
    r.u16(), r.u16()  # version
    blocks = r.u32()
    models: set[str] = set()
    swatches: list[Swatch] = []
    for _ in range(blocks):
        kind, length = r.u16(), r.u32()
        end = r.pos + length
        if kind == 0x0001:
            name = r.utf16(r.u16())
            model = r.take(4).decode("ascii").strip()
            if model == "LAB":
                L, a, b = struct.unpack(">3f", r.take(12))
                hx = lab_to_hex(L * 100, a, b)
                model = "Lab"
            elif model == "RGB":
                hx = _to_hex(*struct.unpack(">3f", r.take(12)))
            elif model == "CMYK":
                hx = cmyk_to_hex(*struct.unpack(">4f", r.take(16)))
            else:  # Gray
                (g,) = struct.unpack(">f", r.take(4))
                hx = _to_hex(g, g, g)
            models.add(model)
            swatches.append(Swatch(name, model, hx))
        r.pos = end
    model = "/".join(sorted(models)) or "-"
    return ColorBook(path, path.stem, "ASE", model, swatches)


def read(path: Path) -> ColorBook:
    return read_acb(path) if path.suffix.lower() == ".acb" else read_ase(path)
