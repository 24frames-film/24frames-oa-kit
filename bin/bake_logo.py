#!/usr/bin/env python3
"""Bake a flat, single-path logo SVG into assets/logo_flat.json (ink width 839). Run only when the brand logo changes;
typesetting never parses SVG. The path must use M/L/C/Q/Z with absolute coordinates and fill its viewBox.
Add --png to also re-render assets/logo_white_2400.png (needs Playwright; only for rebranding).
usage: python3 bin/bake_logo.py [logo/24frames_logo_paths.svg] [--png]"""
import sys, os, re, json
import xml.etree.ElementTree as ET
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
src = args[0] if args else f"{K}/logo/24frames_logo_paths.svg"
root = ET.parse(src).getroot()
vb = [float(v) for v in root.get("viewBox", "").replace(",", " ").split()]
path = root.find(".//{http://www.w3.org/2000/svg}path")
if path is None or not path.get("d"): sys.exit(f"{src}: no <path d=...> found")
d = path.get("d").upper()
if re.search(r"[HVA]", d): sys.exit("logo path must use only M/L/C/Q/Z with absolute coordinates; flatten it first")
def n(v):
    s = f"{v:.2f}".rstrip("0").rstrip("."); return "0" if s in ("-0", "") else s
W, H = vb[2] - vb[0], vb[3] - vb[1]; k = 839.0 / W
toks = re.findall(r"[MLCQZ]|-?\d+(?:\.\d+)?", d); out = []; i = 0
while i < len(toks):
    if toks[i] in "MLCQZ": out.append(toks[i]); i += 1; continue
    j = i
    while j < len(toks) and toks[j] not in "MLCQZ": j += 1
    v = [float(x) for x in toks[i:j]]
    if len(v) % 2: sys.exit(f"odd coordinate count in {src}")
    out.append(" ".join(n((v[a] - vb[0]) * k) + "," + n((v[a + 1] - vb[1]) * k) for a in range(0, len(v), 2)))
    i = j
out_d = "".join(out); out_h = round(H * k, 4)
dst = f"{K}/assets/logo_flat.json"
json.dump({"generator": f"bin/bake_logo.py from {os.path.relpath(src, K)}", "d": out_d, "h": out_h, "ink_w_px": 839},
          open(dst, "w", encoding="utf-8"), ensure_ascii=False)
print(f"baked {os.path.relpath(src, K)} → assets/logo_flat.json  ({len(out_d)} B, {839}×{out_h})")

if "--png" in sys.argv[1:]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("--png needs Playwright (rebrand only): pip install playwright && python3 -m playwright install chromium")
    W = 2400; H = int(round(out_h * W / 839))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 839 {out_h}">'
           f'<path fill="rgb(255,255,255)" d="{out_d}"/></svg>')
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--headless=new", "--no-sandbox"]); pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("<svg ", "<svg style=display:block ")}</body></html>')
        png = pg.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": W, "height": H}); b.close()
    open(f"{K}/assets/logo_white_2400.png", "wb").write(png)
    print(f"rendered assets/logo_white_2400.png  ({W}×{H})")
