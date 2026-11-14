#!/usr/bin/env python3
"""24帧 OA cover. One still → horizontal 1800×766 (the upload; WeChat crops 1:1 from it via cover_info) + standalone square 1080×1080.
usage: python3 bin/cover.py <still.jpg> <out_dir> [LABEL=Play]
writes <out_dir>/cover_h.jpg (1800×766), cover_sq.jpg (1080×1080), cover_pair_preview.jpg (h at 900 + crop at 383), cover_info.json"""
import sys, os, json; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter
C = kit.CFG["cover"]
def compose(im, W, H, s, label):
    """s = scale vs the 1800×766 spec (1 for horizontal, 1080/766 for the square)."""
    im = im.convert("RGB"); r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS); x = (im.width - W) // 2; y = (im.height - H) // 2
    im = ImageEnhance.Brightness(im.crop((x, y, x + W, y + H))).enhance(C["brightness"]).convert("RGBA")
    lw = round(C["logo_ink_width_px"] * s); lm, _ = kit.logo_mask(lw)
    wf = kit.F(C["label_font"], round(C["label_px"] * s)); bf = kit.F(C["bracket_font"], round(C["bracket_px"] * s)); d = ImageDraw.Draw(im)
    cap = -d.textbbox((0, 0), "P", font=wf, anchor="ls")[1]; gap = round(C["logo_to_label_cap_gap_px"] * s)
    ly = (H - (lm.height + gap + cap)) // 2; lx = (W - lm.width) // 2; im.alpha_composite(lm, (lx, ly))
    base = ly + lm.height + gap + cap; top = base - cap
    ib = d.textbbox((0, 0), label, font=wf, anchor="ls"); iw = ib[2] - ib[0]
    lb = d.textbbox((0, 0), "「", font=bf); rb = d.textbbox((0, 0), "」", font=bf); g, ov = C["bracket_gap_px"] * s, C["bracket_overhang_px"] * s
    xs = W / 2 - ((lb[2] - lb[0]) + g + iw + g + (rb[2] - rb[0])) / 2
    def br(xi, ch, bb, al):
        yy = (top - ov - bb[1]) if al == "top" else (base + ov - bb[3]); xx = xi - bb[0]
        gi = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(gi).text((xx, yy), ch, font=bf, fill=(211, 56, 28, C["bracket_glow_alpha"]))
        im.alpha_composite(gi.filter(ImageFilter.GaussianBlur(C["bracket_glow_blur_px"] * s))); ImageDraw.Draw(im).text((xx, yy), ch, font=bf, fill=kit.CRIMSON)
    br(xs, "「", lb, "top"); xw = xs + (lb[2] - lb[0]) + g
    ImageDraw.Draw(im).text((xw - ib[0], base), label, font=wf, fill="white", anchor="ls"); br(xw + iw + g, "」", rb, "bottom")
    return im.convert("RGB"), {"logo": [lx, ly, lm.width, lm.height], "label_baseline": base}
if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]; label = sys.argv[3] if len(sys.argv) > 3 else C["label_default"]; os.makedirs(out, exist_ok=True)
    still = Image.open(src); W, H = C["size"]
    h, gh = compose(still, W, H, 1.0, label); h.save(f"{out}/cover_h.jpg", quality=92)
    # standalone square: crop the still to the same centre column the 1:1 crop shows, then compose at 1080
    sq, gs = compose(still, 1080, 1080, 1080 / 766, label) if still.width / still.height < 1.2 else (None, None)
    if sq is None:   # wide still: take the exact horizontal-cover centre column of the still, re-compose natively
        r = max(W / still.width, H / still.height); st = still.convert("RGB").resize((round(still.width * r), round(still.height * r)), Image.LANCZOS)
        x0 = (st.width - W) // 2 + C["square_crop_px"][0]; y0 = (st.height - H) // 2
        sq, gs = compose(st.crop((x0, y0, x0 + 766, y0 + 766)), 1080, 1080, 1080 / 766, label)
    sq.save(f"{out}/cover_sq.jpg", quality=92)
    x1, _, x2, _ = C["square_crop_px"]; crop = h.crop((x1, 0, x2, 766)).resize((383, 383), Image.LANCZOS)
    pv = Image.new("RGB", (900 + 24 + 383 + 24 + 383, 383), (255, 255, 255)); pv.paste(h.resize((900, 383), Image.LANCZOS), (0, 0)); pv.paste(crop, (924, 0))
    pv.paste(sq.resize((383, 383), Image.LANCZOS), (924 + 383 + 24, 0)); pv.save(f"{out}/cover_pair_preview.jpg", quality=90)
    sq.resize((383, 383), Image.LANCZOS).save(f"{out}/cover_square_preview.jpg", quality=90)
    json.dump({"horizontal": gh, "square": gs, "cover_info": C["cover_info"]}, open(f"{out}/cover_info.json", "w"), indent=1)
    print(json.dumps({"horizontal": gh, "square": gs}))
