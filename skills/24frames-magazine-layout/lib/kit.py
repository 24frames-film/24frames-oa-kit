"""Shared library: paths, config, fonts, Pillow drawing (raster covers/cards + layout for textsvg), official-logo flattening. Paths are relative to the skill folder."""
import os, re, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG = json.load(open(f"{KIT}/kit.json", encoding="utf-8"))
def kp(rel): return rel if rel.startswith("/") else f"{KIT}/{rel}"
FONTS = {k: (kp(v) if isinstance(v, str) else v) for k, v in CFG["fonts"].items()}
_CJK_DIRS = ["/usr/share/fonts/opentype/noto", "/usr/share/fonts/noto-cjk", "/usr/share/fonts/google-noto-cjk",
             os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", f"{KIT}/fonts"]
for _k, _env in (("cjk_bold", "OA_CJK_BOLD"), ("cjk_regular", "OA_CJK_REGULAR")):
    if os.environ.get(_env): FONTS[_k] = os.environ[_env]
    elif not os.path.exists(FONTS[_k]):
        _hit = [f"{d}/{os.path.basename(FONTS[_k])}" for d in _CJK_DIRS if os.path.exists(f"{d}/{os.path.basename(FONTS[_k])}")]
        if _hit: FONTS[_k] = _hit[0]
def chrome():
    """Chrome for Playwright: env CHROME_PATH → kit.json verify.chrome → None (Playwright's bundled Chromium)."""
    p = os.environ.get("CHROME_PATH") or CFG["verify"]["chrome"]
    return p if p and os.path.exists(p) else None
SC = CFG["fonts"]["cjk_index_sc"]
CRIMSON = (211, 56, 28, 255); BLACK = (20, 20, 20, 255); WHITE = (255, 255, 255, 255)
def F(name_or_path, size, index=None):
    p = FONTS.get(name_or_path, name_or_path)
    if index is None and p.endswith(".ttc"): index = SC
    return ImageFont.truetype(p, size=size) if index is None else ImageFont.truetype(p, size=size, index=index)
def glow_char(base, xy, ch, font, color, radius=7, layers=6):
    x, y = xy; r, g, b, _ = color; glow = Image.new("RGBA", base.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for i in range(layers):
        a = 40 + i * 12
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]: gd.text((x + dx, y + dy), ch, font=font, fill=(r, g, b, min(a, 160)))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=radius))); ImageDraw.Draw(base).text((x, y), ch, font=font, fill=color)
def bracket_label(img, center_y, text, word_font, s, k=1.0, right_x=None, center_x=None, glow_r=7):
    """Word black + 「」 crimson (Noto CJK Bold, 40*k*s px) with glow; 「 top = cap top − 6ks, 」 bottom = baseline + 6ks, gaps 5ks."""
    d = ImageDraw.Draw(img); bf = F("cjk_bold", round(40 * k * s)); off, gap = 6 * k * s, 5 * k * s
    wb = d.textbbox((0, 0), text, font=word_font, anchor="ls"); cap = d.textbbox((0, 0), "H", font=word_font, anchor="ls")
    lb = d.textbbox((0, 0), "「", font=bf); rb = d.textbbox((0, 0), "」", font=bf); lw, rw = lb[2] - lb[0], rb[2] - rb[0]; ww = wb[2] - wb[0]
    total = lw + gap + ww + gap + rw; x0 = (right_x - total) if right_x is not None else (center_x - total / 2)
    base = center_y - (cap[1] + cap[3]) / 2; wx = x0 + lw + gap; ly = base + cap[1] - off; rx, ryb = wx + ww + gap, base + off
    glow_char(img, (round(x0 - lb[0]), round(ly - lb[1])), "「", bf, CRIMSON, radius=glow_r * s // 2 + 2)
    ImageDraw.Draw(img).text((round(wx - wb[0]), round(base)), text, font=word_font, fill=BLACK, anchor="ls")
    glow_char(img, (round(rx - rb[0]), round(ryb - rb[3])), "」", bf, CRIMSON, radius=glow_r * s // 2 + 2)
    return (x0, ly, rx + rw, ryb)
# Text SVGs: glyph outlines from the font files only (bin/textsvg.py + lib/textsvg_core.py). Never trace bitmaps of text.
# ── official logo → flattened plain paths (no <use>/<defs>/clipPath/transform) ──
def flatten_official_logo():
    import xml.etree.ElementTree as ET, pathops
    from svgpathtools import parse_path, Line, CubicBezier, QuadraticBezier
    NS = {"s": "http://www.w3.org/2000/svg"}; root = ET.parse(kp(CFG["logo"]["official_svg"])).getroot()
    glyph = {g.get("id"): g.find("s:path", NS).get("d") for g in root.iter("{http://www.w3.org/2000/svg}g") if g.get("id", "").startswith("glyph")}
    grp = [g for g in root.iter("{http://www.w3.org/2000/svg}g") if g.get("id") == "24frames-logo"][0]
    a, b, c, d, e, f = map(float, re.findall(r"[-\d.]+", grp.get("transform")))
    cr = root.find(".//s:clipPath/s:rect", NS); clip = [float(cr.get(k)) for k in ("x", "y", "width", "height")]
    bar = [float(grp.find("s:rect", NS).get(k)) for k in ("x", "y", "width", "height")]
    def add(P, ds, dx, dy):
        for sub in parse_path(ds).continuous_subpaths():
            z = sub[0].start; P.moveTo(z.real + dx, z.imag + dy)
            for s in sub:
                if isinstance(s, Line): P.lineTo(s.end.real + dx, s.end.imag + dy)
                elif isinstance(s, CubicBezier): P.cubicTo(s.control1.real + dx, s.control1.imag + dy, s.control2.real + dx, s.control2.imag + dy, s.end.real + dx, s.end.imag + dy)
                elif isinstance(s, QuadraticBezier): P.qCurveTo((s.control.real + dx, s.control.imag + dy), (s.end.real + dx, s.end.imag + dy))
            P.close()
    def rect(x, y, w, h):
        P = pathops.Path(); P.moveTo(x, y); P.lineTo(x + w, y); P.lineTo(x + w, y + h); P.lineTo(x, y + h); P.close(); return P
    L = pathops.Path()
    for u in grp.iter("{http://www.w3.org/2000/svg}use"):
        add(L, glyph[(u.get("href") or u.get("{http://www.w3.org/1999/xlink}href"))[1:]], float(u.get("x")), float(u.get("y")))
    L = pathops.op(L, rect(*clip), pathops.PathOp.INTERSECTION, fix_winding=True)
    logo = pathops.op(L, rect(*bar), pathops.PathOp.UNION, fix_winding=True)
    x0, y0, x1, y1 = logo.bounds
    canvas = [float(v) for v in root.get("viewBox").split()]
    info = {"svg_width": root.get("width"), "svg_height": root.get("height"), "viewBox": canvas, "group_scale": a, "group_translate": [e, f],
            "ink_box_canvas_px": [round(x0 * a + e, 3), round(y0 * a + f, 3), round(x1 * a + e, 3), round(y1 * a + f, 3)],
            "ink_w_canvas_px": round((x1 - x0) * a, 3), "ink_h_canvas_px": round((y1 - y0) * a, 3), "aspect_w_over_h": round((x1 - x0) / (y1 - y0), 5),
            "letters_visible_h_canvas_px": round((clip[1] + clip[3] - y0) * a, 3), "letters_to_bar_gap_canvas_px": round((bar[1] - (clip[1] + clip[3])) * a, 3),
            "bar_h_canvas_px": round(bar[3] * a, 3)}
    def d_of(width, ox=0.0, oy=0.0):
        k = width / (x1 - x0); out = []; fx = lambda p: f"{(p[0] - x0) * k + ox:.2f},{(p[1] - y0) * k + oy:.2f}"
        for verb, pts in logo:
            if verb == pathops.PathVerb.MOVE: out.append("M" + fx(pts[0]))
            elif verb == pathops.PathVerb.LINE: out.append("L" + fx(pts[0]))
            elif verb == pathops.PathVerb.CUBIC: out.append("C" + " ".join(fx(p) for p in pts))
            elif verb == pathops.PathVerb.QUAD: out.append("Q" + " ".join(fx(p) for p in pts))
            elif verb == pathops.PathVerb.CLOSE: out.append("Z")
        return "".join(out), (y1 - y0) * k
    return info, d_of
def logo_mask(width_px, colour=(255, 255, 255)):
    """Rasterise the flattened official logo at an exact ink width (Chrome, transparent background) → RGBA image."""
    from playwright.sync_api import sync_playwright
    _, d_of = flatten_official_logo(); d, h = d_of(width_px); H = int(np.ceil(h))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{H}" viewBox="0 0 {width_px} {H}"><path fill="rgb{colour}" d="{d}"/></svg>'
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome(), args=["--headless=new", "--no-sandbox"]); pg = b.new_page(viewport={"width": width_px, "height": H})
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("<svg ", "<svg style=display:block ")}</body></html>')
        png = pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": width_px, "height": H}); b.close()
    import io; return Image.open(io.BytesIO(png)).convert("RGBA"), h
def res(p, adir):
    """Resolve a data-local path: "@kit/…" → kit file, else relative to the article dir."""
    return kp(p[5:]) if p.startswith("@kit/") else os.path.join(adir, p)
