#!/usr/bin/env python3
"""Verify the REAL WeChat preview page (not draft/get): WeChat iPhone UA, 383 wide, DPR 2, light + dark.
Forces lazy images / the lazy white-base background to load the way WeChat does, then checks: white base present,
text colours in light and dark (dark must keep #3E3E3E on white), masthead/footer logo ink on the content 15px edges,
three separate QR <img> that each decode (wechat_qrcode), no horizontal overflow. Saves out/preview_light_dark.png.
usage: python3 bin/preview_verify.py <article_dir> [url]   (url defaults to out/preview_url.txt from bin/draft.py get)"""
import os, sys, io, json; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
adir = os.path.abspath(sys.argv[1]); url = sys.argv[2] if len(sys.argv) > 2 else open(f"{adir}/out/preview_url.txt").read().strip()
V = kit.CFG["verify"]; R = []; shots = []
def ok(n, c, i=""): R.append(bool(c)); print(("PASS " if c else "FAIL ") + n + (f"  — {i}" if i else ""))
LOAD = """async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,50))}window.scrollTo(0,0);
 document.querySelectorAll('#js_content img[data-src]').forEach(i=>{i.src=i.dataset.src;i.classList.remove('wx_img_placeholder');i.style.background='transparent'});
 document.querySelectorAll('[data-lazy-bgimg]').forEach(e=>{const u=e.getAttribute('data-lazy-bgimg');e.style.setProperty('background-image','url("'+u+'")','important');e.classList.remove('wx_imgbc_placeholder')});
 await Promise.all([...document.querySelectorAll('#js_content img')].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r})));
 [...document.querySelectorAll('body *')].forEach(e=>{const s=getComputedStyle(e).position;if(s==='fixed'||s==='sticky')e.style.display='none'})}"""
INFO = """()=>{const c=document.querySelector('#js_content'),a=c.querySelector('[data-role=article]'),cb=c.getBoundingClientRect();
 const r=e=>{const q=e.getBoundingClientRect();return [q.left-cb.left,cb.right-q.right,q.top+scrollY,q.bottom+scrollY]};
 const cols={};c.querySelectorAll('p, svg').forEach(e=>{if(e.tagName==='svg'||e.textContent.trim()){const k=getComputedStyle(e).color;cols[k]=(cols[k]||0)+1}});
 const svgs=[...c.querySelectorAll('svg')];const ft=svgs.find(s=>s.getAttribute('aria-label')==='24FRAMES');
 return {bg:getComputedStyle(a).backgroundImage.slice(0,80), cols, mast:r(c.querySelector('[data-role=masthead] svg')), foot:ft?r(ft):null,
   qr:[...c.querySelectorAll('[data-role=qr-row] img')].map(r), sw:document.documentElement.scrollWidth}}"""
sys.path.insert(0, "/tmp/cvc")
try: import cv2; det = cv2.wechat_qrcode.WeChatQRCode()
except Exception: det = None; print("SKIP QR decode —", V["wechat_qrcode"])
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=kit.chrome(), args=["--headless=new", "--no-sandbox", "--hide-scrollbars"])
    for mode in ("light", "dark"):
        ctx = b.new_context(viewport={"width": 383, "height": 900}, device_scale_factor=2, user_agent=V["wechat_ua"], color_scheme=mode, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); pg.goto(url, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1500); pg.evaluate(LOAD); pg.wait_for_timeout(2500)
        if not pg.query_selector("#js_content [data-role=article]"): ok(f"{mode}: preview page has the article", False, "expired/changed url? run bin/draft.py get"); continue
        i = pg.evaluate(INFO)
        ok(f"{mode}: white-image base loaded", "url(" in i["bg"] and "data:" not in i["bg"], i["bg"])
        ok(f"{mode}: text colours dark (no white / grey conversion)", set(i["cols"]) <= {"rgb(62, 62, 62)", "rgb(20, 20, 20)", "rgb(211, 56, 28)", "rgb(153, 153, 153)", "rgb(136, 136, 136)"}, json.dumps(i["cols"]))
        for k in ("mast", "foot"):
            e = i[k]; ok(f"{mode}: {k} logo box on the 15px edges", e and abs(e[0] - 15) <= 1 and abs(e[1] - 15) <= 1, str([round(v, 2) for v in e]) if e else "missing")
        ok(f"{mode}: no horizontal overflow", i["sw"] <= 383, str(i["sw"]))
        ok(f"{mode}: QR row = 3 images", len(i["qr"]) == 3)
        if det:
            dec = []
            for el in pg.query_selector_all("#js_content [data-role=qr-row] img"):
                a = np.asarray(Image.open(io.BytesIO(el.screenshot())).convert("RGB")); dec.append(bool(det.detectAndDecode(cv2.cvtColor(a, cv2.COLOR_RGB2BGR))[0]))
            ok(f"{mode}: each QR decodes from the rendered page", dec and all(dec), str(dec))
        pg.screenshot(path=f"/tmp/oa_kit_pv_{mode}.png", full_page=True); shots.append(Image.open(f"/tmp/oa_kit_pv_{mode}.png").convert("RGB")); ctx.close()
    b.close()
if len(shots) == 2:
    h = max(s.height for s in shots); M = Image.new("RGB", (shots[0].width * 2 + 16, h), (128, 128, 128)); M.paste(shots[0], (0, 0)); M.paste(shots[1], (shots[0].width + 16, 0))
    M.save(f"{adir}/out/preview_light_dark.png"); print("saved out/preview_light_dark.png")
print(f"{sum(R)}/{len(R)} PASS"); sys.exit(0 if all(R) else 1)
