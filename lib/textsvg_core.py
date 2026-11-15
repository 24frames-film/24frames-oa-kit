"""True font-outline text → SVG paths, fontTools only (no HarfBuzz, no skia-pathops).
Layout runs the Pillow layout code with ImageDraw.text recorded (Recorder), so pen positions / baselines
match Pillow; each recorded run is re-drawn from the font's own glyph outlines (fontTools, unhinted),
glyph ids from the font's cmap (wordmark text is CJK + uppercase Latin, always 1:1), overlaps kept with the
font's original nonzero winding (SVG's default fill, so no boolean union is needed).
Neutral ink → fill="currentColor"; crimson 「」 → fill="#D3381C"; glow layers (alpha < 255) are not drawn."""
import re
from PIL import ImageDraw, ImageFont
from fontTools.ttLib import TTFont, TTCollection
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

_FONTS = {}
def _font(path, index):
    k = (path, index or 0)
    if k not in _FONTS:
        tt = TTCollection(path).fonts[index] if path.endswith(".ttc") else TTFont(path)
        _FONTS[k] = (tt.getGlyphSet(), tt["head"].unitsPerEm, tt.getBestCmap())
    return _FONTS[k]

class _Collect(BasePen):
    """BasePen that formats its segments like the old pathops output (2-decimal, x,y)."""
    def __init__(self, glyphSet, prec=2):
        super().__init__(glyphSet); self.parts = []; self.prec = prec
    def _fmt(self, p):
        def n(v):
            s = f"{v:.{self.prec}f}".rstrip("0").rstrip("."); return "0" if s in ("-0", "") else s
        return f"{n(p[0])},{n(p[1])}"
    def _moveTo(self, p): self.parts.append("M" + self._fmt(p))
    def _lineTo(self, p): self.parts.append("L" + self._fmt(p))
    def _curveToOne(self, p1, p2, p3): self.parts.append("C" + self._fmt(p1) + " " + self._fmt(p2) + " " + self._fmt(p3))
    def _qCurveToOne(self, p1, p2): self.parts.append("Q" + self._fmt(p1) + " " + self._fmt(p2))
    def _closePath(self): self.parts.append("Z")

class Outline:
    """Glyph placements in canvas px; d() renders them at any translation."""
    __slots__ = ("glyphs", "_b")
    def __init__(self, glyphs=()): self.glyphs = list(glyphs); self._b = None
    def add(self, other): self.glyphs += other.glyphs; self._b = None
    @property
    def bounds(self):
        if self._b is None:
            b = None
            for gs, name, s, x, base in self.glyphs:
                bp = BoundsPen(gs); gs[name].draw(TransformPen(bp, (s, 0, 0, -s, x, base)))
                q = bp.bounds
                if q: b = q if b is None else (min(b[0], q[0]), min(b[1], q[1]), max(b[2], q[2]), max(b[3], q[3]))
            if b is None: raise ValueError("outline has no ink")
            self._b = b
        return self._b
    def d(self, dx=0.0, dy=0.0, prec=2):
        out = []
        for gs, name, s, x, base in self.glyphs:
            c = _Collect(gs, prec); gs[name].draw(TransformPen(c, (s, 0, 0, -s, x + dx, base + dy)))
            out.append("".join(c.parts))
        return "".join(out)

class Recorder:
    """Context manager: records every ImageDraw.text call (still draws, so the bitmap is identical to the old bake)."""
    def __enter__(self):
        self.calls = []; self._orig = ImageDraw.ImageDraw.text; rec = self
        def text(this, xy, text, fill=None, font=None, anchor=None, *a, **kw):
            rec.calls.append(dict(xy=tuple(xy), text=text, fill=fill, font=font, anchor=anchor or "la", im=this.im))
            return rec._orig(this, xy, text, fill, font, anchor, *a, **kw)
        ImageDraw.ImageDraw.text = text; return self
    def __exit__(self, *e): ImageDraw.ImageDraw.text = self._orig
    def solid(self, im=None):
        """Only opaque draws (glow passes are alpha ≤160 on a separate layer)."""
        out = []
        for c in self.calls:
            f = c["fill"]; a = 255 if (f is None or len(f) == 3) else f[3]
            if a == 255 and (im is None or c["im"] is im.im): out.append(c)
        return out

def run_path(call, stats=None):
    """One recorded Pillow text call → Outline in canvas px (y down)."""
    pf: ImageFont.FreeTypeFont = call["font"]; text = call["text"]; x, y = call["xy"]; anc = call["anchor"]
    gs, upem, cmap = _font(pf.path, getattr(pf, "index", 0)); size = pf.size; s = size / upem
    glyphs = []
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            raise SystemExit(f"font {pf.path} has no glyph for {ch!r} in {text!r} — add it to the font or the text")
        glyphs.append(name)
    # Pillow pen positions (hinted advances + kerning, exactly what the bake used)
    pen = [pf.getlength(text[:i + 1]) - pf.getlength(text[i]) for i in range(len(text))]
    d = ImageDraw.Draw(__import__("PIL.Image", fromlist=["Image"]).new("L", (4, 4)))
    asc = d.textbbox((0, 0), text, font=pf, anchor=anc[0] + "a")[1] - d.textbbox((0, 0), text, font=pf, anchor=anc[0] + "s")[1]
    base = y if anc[1] == "s" else (y + asc if anc[1] == "a" else None); assert base is not None, anc
    assert anc[0] == "l", anc
    return Outline((gs, g, s, x + px, base) for g, px in zip(glyphs, pen))

def union(paths):
    if not paths: return None
    acc = Outline()
    for p in paths: acc.add(p)
    return acc

def d_of(P, dx=0.0, dy=0.0, prec=2): return P.d(dx, dy, prec)

def is_crimson(fill): return fill is not None and tuple(fill[:3]) == (211, 56, 28)

def layers(calls, stats=None):
    ink = [run_path(c, stats) for c in calls if not is_crimson(c["fill"])]
    cr = [run_path(c, stats) for c in calls if is_crimson(c["fill"])]
    return union(ink), union(cr)

def svg(name, W, H, ink, cr, dx, dy, prec=2, extra_paths=""):
    """dx, dy: translate canvas coords → viewBox coords (= −crop origin)."""
    parts = [extra_paths]
    if ink is not None: parts.append(f'<path fill="currentColor" d="{d_of(ink, dx, dy, prec)}"></path>')
    if cr is not None: parts.append(f'<path fill="#D3381C" d="{d_of(cr, dx, dy, prec)}"></path>')
    vb = f"0 0 {W:g} {H:g}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="100%" '
            f'style="display:block;width:100%;height:auto;margin:0;padding:0;" role="img" aria-label="{name}">' + "".join(parts) + "</svg>")

def bounds(*ps):
    b = [p.bounds for p in ps if p is not None]
    return (min(v[0] for v in b), min(v[1] for v in b), max(v[2] for v in b), max(v[3] for v in b))
