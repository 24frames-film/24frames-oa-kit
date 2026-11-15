"""Shared library: paths, config, fonts, Pillow drawing (raster covers/cards + layout for textsvg), baked official-logo path. Paths are relative to the skill folder."""
import os, re, json, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter
KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG = json.load(open(f"{KIT}/kit.json", encoding="utf-8"))
def kp(rel): return rel if rel.startswith("/") else f"{KIT}/{rel}"
FONTS = {k: (kp(v) if isinstance(v, str) else v) for k, v in CFG["fonts"].items()}
_CJK_DIRS = [os.path.expanduser("~/.cache/24frames-magazine-layout/fonts"),
             "/usr/share/fonts/opentype/noto", "/usr/share/fonts/noto-cjk", "/usr/share/fonts/google-noto-cjk",
             os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", f"{KIT}/fonts"]
_CJK_GLOB = {"cjk_bold": ["NotoSansSC*Bold*.ttf", "NotoSansSC*Bold*.otf", "NotoSansCJK*Bold*.ttc", "SourceHanSansSC*Bold*"],
             "cjk_regular": ["NotoSansSC*Regular*.ttf", "NotoSansSC*Regular*.otf", "NotoSansCJK*Regular*.ttc", "SourceHanSansSC*Regular*"]}
for _k, _env in (("cjk_bold", "OA_CJK_BOLD"), ("cjk_regular", "OA_CJK_REGULAR")):
    if os.environ.get(_env): FONTS[_k] = os.environ[_env]
    elif not os.path.exists(FONTS[_k]):
        _hit = [f"{d}/{os.path.basename(FONTS[_k])}" for d in _CJK_DIRS if os.path.exists(f"{d}/{os.path.basename(FONTS[_k])}")]
        if not _hit: _hit = [p for d in _CJK_DIRS for pat in _CJK_GLOB[_k] for p in sorted(glob.glob(f"{d}/{pat}"))]
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
    try:
        return ImageFont.truetype(p, size=size) if index is None else ImageFont.truetype(p, size=size, index=index)
    except OSError:
        raise SystemExit(
            f"CJK font not found: {p}\n"
            "Set OA_CJK_BOLD / OA_CJK_REGULAR to any Noto Sans CJK SC / Source Han Sans SC file "
            "(.ttf/.otf preferred; .ttc uses index 2), or put the files in fonts/ or "
            "~/.cache/24frames-magazine-layout/fonts/.\n"
            "Blocked network quick fetch:\n"
            "  npm pack @expo-google-fonts/noto-sans-sc --registry=https://registry.npmmirror.com\n"
            "  tar xzf expo-google-fonts-noto-sans-sc-*.tgz\n"
            "  cp package/700Bold/*.ttf package/400Regular/*.ttf fonts/")
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
# ── official logo → baked flat path (assets/logo_flat.json; no SVG parsing / boolean ops at build time) ──
def flatten_official_logo():
    """Return (info, d_of). d_of(width) scales the baked 839-wide path; re-bake only if the logo SVG changes."""
    j = json.load(open(kp("assets/logo_flat.json"), encoding="utf-8"))
    base, bw = j["d"], j["ink_w_px"]
    def fnum(v):
        s = f"{v:.2f}".rstrip("0").rstrip("."); return "0" if s in ("-0", "") else s
    def d_of(width, ox=0.0, oy=0.0):
        assert not ox and not oy, "baked logo path has no offset support"
        k = width / bw
        return re.sub(r"-?\d+(?:\.\d+)?", lambda m: fnum(float(m.group()) * k), base), j["h"] * k
    return {"baked": True, "ink_w_px": bw, "ink_h_px": j["h"]}, d_of

_LOGO_WHITE = None
def logo_mask(width_px, colour=(255, 255, 255)):
    """Official logo at an exact ink width from assets/logo_white_2400.png (no browser) → (RGBA image, height)."""
    global _LOGO_WHITE
    if _LOGO_WHITE is None: _LOGO_WHITE = Image.open(kp("assets/logo_white_2400.png")).convert("RGBA")
    h = round(_LOGO_WHITE.height * width_px / _LOGO_WHITE.width)
    im = _LOGO_WHITE.resize((width_px, h), Image.LANCZOS)
    if tuple(colour) != (255, 255, 255):
        alpha = im.getchannel("A"); im = Image.new("RGBA", im.size, tuple(colour) + (255,)); im.putalpha(alpha)
    return im, h
def res(p, adir):
    """Resolve a data-local path: "@kit/…" → kit file, else relative to the article dir."""
    return kp(p[5:]) if p.startswith("@kit/") else os.path.join(adir, p)
