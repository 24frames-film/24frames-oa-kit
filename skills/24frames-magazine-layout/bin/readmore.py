#!/usr/bin/env python3
"""Read more card: 2.35:1 cover of the linked article → 1218 px wide card, bottom gradient (from 42% height, α up to 215),
title Noto Sans CJK SC Regular 45px white, inset 39px left, ink bottom 46px above the card bottom (= 13.0px type at 383).
usage: python3 bin/readmore.py <cover_235.jpg> "<linked article title>" <out.jpg>"""
import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit
from PIL import Image, ImageDraw
def card(src, title, out, px=45):
    s = Image.open(src).convert("RGB"); CW = 1218; CH = round(s.size[1] * CW / s.size[0])
    c = s.resize((CW, CH), Image.LANCZOS).convert("RGBA"); grad = Image.new("L", (1, CH), 0)
    for y in range(CH):
        t = max(0, (y - CH * 0.42) / (CH * 0.58)); grad.putpixel((0, y), int(215 * t ** 0.9))
    sh = Image.new("RGBA", (CW, CH), (0, 0, 0, 255)); sh.putalpha(grad.resize((CW, CH))); c.alpha_composite(sh)
    inset = round(CW * 0.032); bottom = round(457 * 0.1); f = kit.F("cjk_regular", px); d = ImageDraw.Draw(c); tb = d.textbbox((0, 0), title, font=f)
    if tb[2] - tb[0] > CW - 2 * inset: raise SystemExit("Read more title too long for one line at 45px")
    d.text((inset - tb[0], CH - bottom - tb[3]), title, font=f, fill=(255, 255, 255, 255)); c.convert("RGB").save(out, quality=92, optimize=True)
    return CW, CH
if __name__ == "__main__": print(card(sys.argv[1], sys.argv[2], sys.argv[3]))
