#!/usr/bin/env python3
"""ALL text SVGs of the kit = glyph outlines from the font files. Bitmap tracing of text is forbidden.
How: each asset runs its Pillow layout (fonts, px, gaps, centring loops) under
lib/textsvg_core.Recorder; every opaque text run is re-drawn from the font's glyph outlines (fontTools;
glyph ids from the font's cmap; pen positions = Pillow's), 2-decimal path data, original nonzero winding.
Neutral ink fill="currentColor", crimson 「」 fill="#D3381C"; the 「」 glow is not part of the SVG.
viewBox = the outline ink box (ink-tight): centred 1238-wide strips keep x 0–1238; masthead/footer keep the
official logo width 839 (logo = assets/logo_flat.json, a one-time bake, not text).
usage:
  python3 bin/textsvg.py strips [<out_dir>=assets]          # masthead, footer, read_more, follow_head, byline_label, follow_qr_labels
                                                           #   → <out_dir>/*.svg + textsvg.json (manifest) + strip_ink.json (build data)
  python3 bin/textsvg.py wordmarks <article_dir> [<out_dir>=<article_dir>/out/svg]   # ## NN 中文 | ENGLISH → wm_NN.svg + wordmarks.json
  python3 bin/textsvg.py check <svg>...                    # exit 1 if an SVG is not a textsvg output (manifest hash) or looks traced"""
import os, sys, json, math, re, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import kit, textsvg_core as T
from PIL import Image, ImageDraw
W = 1238; GREY = (62, 62, 62, 255); GEN = "bin/textsvg.py (font outlines)"
SVG_STYLE = 'width="100%" style="display:block;width:100%;height:auto;margin:0;padding:0;" role="img"'
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def ink_mask(im, thr=200): return im.convert("L").point(lambda v: 255 if v < thr else 0)
def solid(im, thr=200):
    b = ink_mask(im, thr).getbbox()
    return b if b else (0, 0, 0, 0)
# ── layouts (each returns the recorded opaque text runs + how the viewBox is fitted) ──
def qr_labels(lab_px=42, sub_px=42):
    """二维码标签 公众号/小红书/小助手 Noto Sans CJK SC Bold 42, centred under each 330-px code (codes at x 0/454/908 of 1238),
    label ink top 26 below the codes; CTA Noto Sans CJK SC Regular 42 centred, top = label top + label ink h + 72. #3E3E3E."""
    Q = 330; GAP = (W - 3 * Q) // 2
    lf = kit.F("cjk_bold", lab_px); sf = kit.F("cjk_regular", sub_px); tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lh = tmp.textbbox((0, 0), "公众号", font=lf); lh = lh[3] - lh[1]; y_lab = Q + 26; y_sub = y_lab + lh + 72
    sub = "进 24帧影迷群  ·  映后 / 沙龙见"; sb = tmp.textbbox((0, 0), sub, font=sf); H = y_sub + (sb[3] - sb[1]) + 2
    with T.Recorder() as R:
        img = Image.new("RGBA", (W, H), kit.WHITE); d = ImageDraw.Draw(img)
        for i, lab in enumerate(("公众号", "小红书", "小助手")):
            x = i * (Q + GAP); lb = d.textbbox((0, 0), lab, font=lf)
            d.text((x + Q // 2 - (lb[2] - lb[0]) // 2 - lb[0], y_lab - lb[1]), lab, font=lf, fill=GREY)
        d.text(((W - (sb[2] - sb[0])) // 2 - sb[0], y_sub - sb[1]), sub, font=sf, fill=GREY)
    return dict(name="follow_qr_labels", calls=R.solid(img), fit="x0-1238", origin=(0, Q), colour="#3E3E3E", codes_bottom=Q,
                spec={"labels": f"Noto Sans CJK SC Bold {lab_px}px", "cta": f"Noto Sans CJK SC Regular {sub_px}px", "colour": "#3E3E3E"})
def _latin_px(cap=42):
    d = ImageDraw.Draw(Image.new("RGB", (9, 9)))
    for px in range(54, 70):
        if -d.textbbox((0, 0), "H", font=kit.F("ma_bold", px), anchor="ls")[1] >= cap: return px
def section_label(name, word, cjk=False):
    """栏目标签 T: 「Read more」「Follow us」 Montserrat Alternates Bold 60 (cap 42 canvas px); 「24帧/文」 Noto CJK SC Bold 59;
    「」 Noto CJK SC Bold 2× (120/118), kit.bracket_label k=1, s=px/20; solid ink centred on 1238 (|L−R| ≤ 1)."""
    px = 59 if cjk else _latin_px(); s = px / 20; f = kit.F("cjk_bold", px) if cjk else kit.F("ma_bold", px); cx = W / 2
    for _ in range(6):
        with T.Recorder() as R:
            img = Image.new("RGBA", (W, 500), kit.WHITE); kit.bracket_label(img, 250, word, f, s, k=1.0, center_x=cx, glow_r=7)
        x0, y0, x1, y1 = solid(img); dl = ((W - x1) - x0) / 2
        if abs(2 * dl) <= 1: break
        cx += dl
    return dict(name=name, calls=R.solid(img), fit="x0-1238", colour="#141414",
                spec={"word": f"{'Noto Sans CJK SC Bold' if cjk else 'Montserrat Alternates Bold'} {px}px", "brackets": f"Noto Sans CJK SC Bold {round(40 * s)}px #D3381C"})
MH_ROW = {"words": [["Screen", 0, 303], ["Play", 372.5, 303], ["Portrait", 685, 303]], "font": "Montserrat Alternates Medium 40px (anchor ls)",
          "brackets": "kit.bracket_label(center_y=288.5, center_x=421.0, s=2, k=1) → Noto Sans CJK SC Bold 80px",
          "canvas": "masthead_v3@2x 841×395 (fitted 2026-11-04; Screen/Portrait/「」 pixel-exact, Play 1 px of 906)", "to_svg": "svg = canvas − (1, 61.45)"}
def masthead(active="Play"):
    """刊头: official logo (flattened, 839 wide, not text) + Screen / Play / Portrait row.
    Brackets mark the article's column (cover_label). Default Play is pixel-identical to the kit asset."""
    wf = kit.F("ma_medium", 40)
    labels = [w[0] for w in MH_ROW["words"]]
    if active not in labels:
        raise SystemExit(f"masthead active must be one of {labels}, got {active!r}")
    with T.Recorder() as R:
        img = Image.new("RGBA", (841, 395), kit.WHITE); d = ImageDraw.Draw(img)
        if active == "Play":
            for w, x, b in MH_ROW["words"]: d.text((x, b), w, font=wf, fill=kit.BLACK, anchor="ls")
            kit.bracket_label(img, 288.5, "Play", wf, 2, k=1.0, center_x=421.0)
        else:
            # Keep un-bracketed companions on the Play-masthead x; iterate the
            # bracketed word's center so the row's left ink matches Play (x≈2).
            pos = {w: x for w, x, _ in MH_ROW["words"]}
            for w, x, b in MH_ROW["words"]:
                if w != active: d.text((x, b), w, font=wf, fill=kit.BLACK, anchor="ls")
            def left_ink(cx):
                im = Image.new("RGBA", (841, 395), kit.WHITE)
                dd = ImageDraw.Draw(im)
                for w, x, b in MH_ROW["words"]:
                    if w != active: dd.text((x, b), w, font=wf, fill=kit.BLACK, anchor="ls")
                kit.bracket_label(im, 288.5, active, wf, 2, k=1.0, center_x=cx)
                a = ink_mask(im)
                xs = a.crop((0, 200, im.width, 360)).getbbox()
                return xs[0] if xs else 999
            # start from a mid estimate and seek left_ink == 2 (Play masthead)
            cx = 112.0; best, best_d = cx, 10**9
            for _ in range(24):
                lo = left_ink(cx); dlt = lo - 2
                if abs(dlt) < best_d: best, best_d = cx, abs(dlt)
                if dlt == 0: break
                cx += -0.5 if dlt > 0 else 0.5
            kit.bracket_label(img, 288.5, active, wf, 2, k=1.0, center_x=best)
    name = "masthead" if active == "Play" else f"masthead_{active.lower()}"
    spec = {**MH_ROW, "active": active}
    out = dict(name=name, calls=R.solid(img), fit="masthead", origin=(1, 61.45), colour="#141414", spec=spec)
    # Play keeps the historic aria so assets/masthead.svg stays byte-identical.
    if active != "Play":
        out["aria"] = "24FRAMES 「" + active + "」 " + " ".join(w for w in labels if w != active)
    return out
SPAN, G = 1354 * (347 - 30) / 347, 40      # wordmark solid-ink span (= 15px column at 347, @2x) and glow room while baking
def _wm_draw(Wb, num, chinese, english, S=2):
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    num_f = kit.F("bebas", 76 * S); nb = tmp.textbbox((0, 0), num, font=num_f)
    cn_f = kit.F("cjk_bold", 34 * S); cb = tmp.textbbox((0, 0), chinese, font=cn_f)
    top, gap, bottom = 44 * S, 18 * S, 44 * S; nh, ch = nb[3] - nb[1], cb[3] - cb[1]
    img = Image.new("RGBA", (Wb, top + nh + gap + ch + bottom), kit.WHITE); d = ImageDraw.Draw(img)
    d.text((G - nb[0], top - nb[1]), num, font=num_f, fill=kit.BLACK)
    kit.bracket_label(img, top + nh // 2, english, kit.F("ma_semibold", 20 * S), S, k=1.0, right_x=Wb - G, glow_r=6)
    ImageDraw.Draw(img).text((G - cb[0], top + nh + gap - cb[1]), chinese, font=cn_f, fill=kit.BLACK)
    return img
def wordmark(num, cn, en):
    """章节词标: number Bebas Neue 152 (top-left) · 「ENGLISH」 Montserrat Alternates SemiBold 40 + 「」 Noto CJK SC Bold 80 (k=1, s=2),
    right-aligned, centred on the number · Chinese title Noto Sans CJK SC Bold 68, 36 below the number. Solid ink spans 1236.9."""
    Wb = int(SPAN) + 2 * G
    for _ in range(6):
        with T.Recorder() as R: img = _wm_draw(Wb, num, cn, en)
        x0, y0, x1, y1 = solid(img); err = SPAN - (x1 - x0)
        if abs(err) < 0.5: break
        Wb += int(round(err))
    cbx = ImageDraw.Draw(img).textbbox((0, 0), cn, font=kit.F("cjk_bold", 68))
    if cbx[2] - cbx[0] > SPAN: raise SystemExit(f"chapter {num}: Chinese title wider than the column — shorten it")
    return dict(name=f"wm_{num}", calls=R.solid(img), fit="xy", colour="#141414", label=f"{num} {cn} {en}", text=[num, cn, en],
                spec={"number": "Bebas Neue 152px", "english": "Montserrat Alternates SemiBold 40px", "brackets": "Noto Sans CJK SC Bold 80px #D3381C",
                      "chinese": "Noto Sans CJK SC Bold 68px", "solid_ink_span": round(SPAN, 2)})
def chapters(md):
    return [(m.group(1), m.group(2).strip(), m.group(3).strip()) for m in re.finditer(r"^## (\d\d) (.+?)\s*\|\s*(.+)$", md, re.M)]
# ── emit ──
def emit(a, prec=2):
    ink, cr = T.layers(a["calls"]); b = T.bounds(ink, cr); fl = lambda v: math.floor(v * 100) / 100; ce = lambda v: math.ceil(v * 100) / 100
    if a["fit"] == "xy": x0, y0, x1, y1 = fl(b[0]), fl(b[1]), ce(b[2]), ce(b[3])
    elif a["fit"] == "x0-1238": x0, y0, x1, y1 = 0, fl(b[1]), W, ce(b[3])
    else:   # masthead: logo occupies 0–839 × 0–153.05 in svg coords; the row hangs below it
        ox, oy = a["origin"]; x0, y0, x1, y1 = ox, oy, ox + 839, oy + ce(b[3] - oy)
    Wv, Hv = round(x1 - x0, 2), round(y1 - y0, 2); paths = ""
    if a["fit"] == "masthead":
        _, d_of = kit.flatten_official_logo(); paths = f'<path fill="currentColor" d="{d_of(839)[0]}"/>'
        aria = a.get("aria") or "24FRAMES Screen Play Portrait"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wv:g} {Hv:g}" width="100%" preserveAspectRatio="xMidYMin meet" '
               f'style="display:block;width:100%;height:auto;margin:0;padding:0;" role="img" aria-label="{aria}">{paths}')
        svg += f'<path fill="currentColor" d="{T.d_of(ink, -x0, -y0, prec)}"></path><path fill="#D3381C" d="{T.d_of(cr, -x0, -y0, prec)}"></path></svg>'
    else:
        svg = T.svg(a.get("label", a["name"]), Wv, Hv, ink, cr, -x0, -y0, prec)
    info = {"generator": GEN, "method": "font-outline", "viewBox": [Wv, Hv], "size": [Wv, Hv], "solid_top": 0, "solid_bottom": 0,
            "css_per_px@347": round(317 / Wv, 5), "colour": a["colour"], "runs": [c["text"] for c in a["calls"]], "spec": a["spec"]}
    if "codes_bottom" in a: info["gap_from_codes_canvas_px"] = round(y0 - a["codes_bottom"], 2)
    return svg, info
def footer():
    _, d_of = kit.flatten_official_logo(); d, h = d_of(839)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 839 {h:.2f}" width="100%" preserveAspectRatio="xMidYMin meet" '
           f'style="display:block;width:100%;height:auto;margin:0;padding:0;" role="img" aria-label="24FRAMES"><path fill="currentColor" d="{d}"/></svg>')
    return svg, {"generator": "bin/textsvg.py (official logo, kit.flatten_official_logo — no text)", "method": "official-vector", "viewBox": [839, round(h, 2)],
                 "size": [839, round(h, 2)], "solid_top": 0, "solid_bottom": 0, "colour": "#141414"}
# ── traced-text detector (used by selfcheck) ──
def looks_traced(svg):
    """potrace output (old kit/bake_v13): fill-rule evenodd + only M/L/C commands + every number with exactly 1 decimal."""
    ds = re.findall(r'\sd="([^"]+)"', svg); nums = [n for d in ds for n in re.findall(r"-?\d+(?:\.\d+)?", d)]
    one_dec = sum(1 for n in nums if re.fullmatch(r"-?\d+\.\d", n)) / max(1, len(nums))
    reasons = []
    if 'fill-rule="evenodd"' in svg: reasons.append("fill-rule evenodd (potrace layer)")
    if nums and one_dec > 0.8: reasons.append(f"{one_dec:.0%} numbers with exactly 1 decimal (potrace)")
    return reasons
def manifest_ok(path, manifests):
    s = open(path, encoding="utf-8").read(); e = None
    for m in manifests:
        if os.path.exists(m): e = json.load(open(m, encoding="utf-8")).get(os.path.basename(path)) or e
    if not e: return [f"{os.path.basename(path)} not in a textsvg manifest"]
    out = [] if e.get("generator", "").startswith("bin/textsvg.py") else [f"generator = {e.get('generator')}"]
    if e.get("sha256") != sha(s): out.append("file differs from the textsvg manifest (edited or traced after generation)")
    return out + looks_traced(s)
if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "strips":
        out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else kit.kp("assets"); os.makedirs(out, exist_ok=True); man, strip = {}, {}
        for a in (masthead(), qr_labels(), section_label("read_more", "Read more"), section_label("follow_head", "Follow us"), section_label("byline_label", "24帧/文", cjk=True)):
            svg, info = emit(a); fn = f"{a['name']}.svg"
            open(f"{out}/{fn}", "w", encoding="utf-8").write(svg); man[fn] = {**info, "sha256": sha(svg)}; print(fn, info["viewBox"], len(svg), "B")
        svg, info = footer(); open(f"{out}/footer.svg", "w", encoding="utf-8").write(svg); man["footer.svg"] = {**info, "sha256": sha(svg)}
        json.dump(man, open(f"{out}/textsvg.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for fn, e in man.items():
            strip[fn] = {k: e[k] for k in ("size", "solid_top", "solid_bottom", "colour", "generator") if k in e}
            if "gap_from_codes_canvas_px" in e: strip[fn]["gap_from_codes_canvas_px"] = e["gap_from_codes_canvas_px"]
        json.dump(strip, open(f"{out}/strip_ink.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif mode == "masthead":
        # python3 bin/textsvg.py masthead Screen <out_dir>  → masthead_screen.svg (+ merge into wordmarks.json if present)
        active = sys.argv[2]; out = os.path.abspath(sys.argv[3]); os.makedirs(out, exist_ok=True)
        a = masthead(active=active); svg, info = emit(a); fn = f"{a['name']}.svg"
        open(f"{out}/{fn}", "w", encoding="utf-8").write(svg)
        entry = {**info, "sha256": sha(svg)}
        print(fn, info["viewBox"], len(svg), "B")
        logp = f"{out}/wordmarks.json"
        log = json.load(open(logp, encoding="utf-8")) if os.path.exists(logp) else {}
        log[fn] = entry
        json.dump(log, open(logp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif mode == "wordmarks":
        adir = os.path.abspath(sys.argv[2]); out = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else f"{adir}/out/svg"; os.makedirs(out, exist_ok=True); log = {}
        for num, cn, en in chapters(open(f"{adir}/article.md", encoding="utf-8").read()):
            a = wordmark(num, cn, en); svg, info = emit(a); fn = f"wm_{num}.svg"
            open(f"{out}/{fn}", "w", encoding="utf-8").write(svg); log[fn] = {**info, "text": a["text"], "sha256": sha(svg)}; print(fn, info["viewBox"], len(svg), "B")
        json.dump(log, open(f"{out}/wordmarks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif mode == "check":
        bad = 0
        for p in sys.argv[2:]:
            r = manifest_ok(p, [kit.kp("assets/textsvg.json"), os.path.join(os.path.dirname(p), "wordmarks.json")]); bad += bool(r); print(("FAIL " if r else "ok   ") + p, "; ".join(r))
        sys.exit(1 if bad else 0)
