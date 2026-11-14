"""True font-outline text → SVG paths. Layout runs the Pillow layout code with ImageDraw.text recorded
(Recorder), so pen positions / baselines match Pillow; each recorded run is then re-drawn from the
font's own glyph outlines (fontTools, unhinted), glyph ids from HarfBuzz (same shaping as Pillow+raqm).
Neutral ink → fill="currentColor"; crimson 「」 → fill="#D3381C"; glow layers (alpha < 255) are not drawn (as before)."""
import re, math
import numpy as np
from PIL import ImageDraw, ImageFont
from fontTools.ttLib import TTFont, TTCollection
from fontTools.pens.transformPen import TransformPen
import pathops, uharfbuzz as hb
_FONTS = {}
def _font(path, index):
    k = (path, index or 0)
    if k not in _FONTS:
        tt = TTCollection(path).fonts[index] if path.endswith(".ttc") else TTFont(path)
        blob = hb.Blob.from_file_path(path); face = hb.Face(blob, index or 0); f = hb.Font(face)
        _FONTS[k] = (tt, tt.getGlyphSet(), tt["head"].unitsPerEm, f, tt.getGlyphOrder())
    return _FONTS[k]
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
    """One recorded Pillow text call → pathops.Path in canvas px (y down)."""
    pf: ImageFont.FreeTypeFont = call["font"]; text = call["text"]; x, y = call["xy"]; anc = call["anchor"]
    tt, gs, upem, hf, order = _font(pf.path, getattr(pf, "index", 0)); size = pf.size; s = size / upem
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(hf, buf, {})
    gids = [i.codepoint for i in buf.glyph_infos]; cl = [i.cluster for i in buf.glyph_infos]
    assert len(gids) == len(text) and cl == list(range(len(text))), ("shaping is not 1:1", text)
    # Pillow pen positions (hinted advances + kerning, exactly what the old bake used)
    pen = [pf.getlength(text[:i + 1]) - pf.getlength(text[i]) for i in range(len(text))]
    hbx = np.cumsum([0] + [p.x_advance * s for p in buf.glyph_positions])[:-1]
    if stats is not None: stats.append(float(np.max(np.abs(np.array(pen) - hbx))) if len(text) > 1 else 0.0)
    d = ImageDraw.Draw(__import__("PIL.Image", fromlist=["Image"]).new("L", (4, 4)))
    asc = d.textbbox((0, 0), text, font=pf, anchor=anc[0] + "a")[1] - d.textbbox((0, 0), text, font=pf, anchor=anc[0] + "s")[1]
    base = y if anc[1] == "s" else (y + asc if anc[1] == "a" else None); assert base is not None, anc
    assert anc[0] == "l", anc
    P = pathops.Path()
    for gid, px in zip(gids, pen):
        g = gs[order[gid]]; tp = TransformPen(P.getPen(glyphSet=gs), (s, 0, 0, -s, x + px, base)); g.draw(tp)
    return P
def union(paths):
    if not paths: return None
    acc = pathops.Path()
    for p in paths: acc.addPath(p)
    return pathops.simplify(acc, fix_winding=True, keep_starting_points=False)
def d_of(P, dx=0.0, dy=0.0, prec=2):
    def n(v):
        s = f"{v:.{prec}f}".rstrip("0").rstrip("."); return "0" if s in ("-0", "") else s
    fx = lambda p: f"{n(p[0] + dx)},{n(p[1] + dy)}"; out = []
    for verb, pts in P:
        if verb == pathops.PathVerb.MOVE: out.append("M" + fx(pts[0]))
        elif verb == pathops.PathVerb.LINE: out.append("L" + fx(pts[0]))
        elif verb == pathops.PathVerb.QUAD: out.append("Q" + " ".join(fx(p) for p in pts))
        elif verb == pathops.PathVerb.CUBIC: out.append("C" + " ".join(fx(p) for p in pts))
        elif verb == pathops.PathVerb.CLOSE: out.append("Z")
        else: raise ValueError(verb)
    return re.sub(r" -", "-", "".join(out)).replace(",-", "-")
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
