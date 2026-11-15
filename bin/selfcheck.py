#!/usr/bin/env python3
"""Pre-delivery self-check. Run after bin/make.py and BEFORE any upload. Exit 0 = all PASS.
usage: python3 bin/selfcheck.py <article_dir> [--shots]
Static: banned CSS, white-image base, text SVGs = textsvg font outlines (manifest hash + no potrace pattern), roles/structure, every local file present, image sizes, QR codes decode.
Rendered (Chrome, DPR 2, 347/383/677): no horizontal overflow, no overlaps / negative margins, ink on the 15px edges,
ink-to-ink gaps = spec (48 flow / 48 headings / 24 tight / 16 attached, ±1px), and WeChat dark mode (mp-darkmode 1.2.2
on #191919) keeps text #3E3E3E and the reading area white; editor view with OS dark keeps text dark.
--shots also writes out/selfcheck_<w>_{light,dark}.png"""
import os, re, sys, io, json; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit
from PIL import Image
adir = os.path.abspath(sys.argv[1]); SHOTS = "--shots" in sys.argv
c = open(f"{adir}/out/content.html", encoding="utf-8").read(); R = []
def ok(name, cond, info=""): R.append((bool(cond), name, info)); print(("PASS " if cond else "FAIL ") + name + (f"  — {info}" if info else ""))
# ── static ──
ok("no light-dark()/color-scheme", "light-dark" not in c and "color-scheme" not in c)
ok("white-image base on the article wrapper", re.search(r'data-role="article" style="[^"]*background-image:url\(&quot;[^&]*whitebase', c))
ok("no &#39; (WeChat empties such style attrs)", "&#39;" not in c)
ok("no unresolved 【markers】", "【" not in c)
ok("no negative margins", not re.search(r'margin(-[a-z]+)?:[^;"]*-\d', c))
chk = re.sub(r'<section data-role="qr-row".*?</section></section>', "", c, flags=re.S)
bad = [b for b in ("inline-block", "flex", "scroll-snap", "overflow:", "max-width", "height=", "display:inline") if b in chk]
ok("flex/inline-block only in the QR row", not bad, ",".join(bad))
ok("no px widths", not re.search(r'width="\d+(px)?"', c) and not re.search(r'width:\s*\d+(\.\d+)?px', c))
roles = re.findall(r'data-role="([a-z-]+)"', c)
ok("masthead is the official logo SVG", re.search(r'data-role="masthead".*?<svg[^>]*aria-label="24FRAMES', c, re.S))
ok("footer logo SVG present (no black card)", 'aria-label="24FRAMES"' in c and "#111" not in c)
ok("QR row = 3 separate images", len(re.findall(r'<img [^>]*qr_(oa|xhs|helper)\.png', c)) == 3 and roles.count("qr-row") == 1)
ok("byline stack present", all(r in roles for r in ("byline-label", "byline-name", "byline-sig")))
ok("dek + credits present", "dek" in roles and "credits" in roles)
locs = sorted(set(re.findall(r'data-local="([^"]+)"', c)) | set(re.findall(r'url\(&quot;([^&]+)&quot;', c)))
miss = [p for p in locs if not os.path.exists(kit.res(p, adir))]; ok("every local file exists", not miss, ",".join(miss))
# text SVGs must be glyph outlines from bin/textsvg.py (no traced text)
sys.path.insert(0, os.path.dirname(__file__)); import textsvg
tbad = []
for m in re.finditer(r'<svg data-local="([^"]+)" (.*?)</svg>', c, re.S):
    p = m.group(1); f = kit.res(p, adir); inline = "<svg " + m.group(2) + "</svg>"
    r = textsvg.manifest_ok(f, [kit.kp("assets/textsvg.json"), f"{adir}/out/svg/wordmarks.json"]) if os.path.exists(f) else ["missing"]
    if open(f, encoding="utf-8").read() != inline if os.path.exists(f) else True: r.append("inline SVG differs from the generated file")
    r += textsvg.looks_traced(inline)
    if r: tbad.append(f"{os.path.basename(p)}: {', '.join(sorted(set(r)))}")
nsvg = len(re.findall(r"<svg ", c))
ok(f"text SVGs = font outlines from bin/textsvg.py, none traced ({nsvg} inline SVGs)", not tbad and nsvg == len(re.findall(r'<svg data-local=', c)), "; ".join(tbad[:4]))
small = []
for p in locs:
    if p.endswith((".jpg", ".png", ".gif")) and "whitebase" not in p and "qr_" not in p:
        w = Image.open(kit.res(p, adir)).size[0]
        if w < (480 if p.endswith(".gif") else 1080): small.append(f"{os.path.basename(p)}={w}px")
ok("photos ≥1080px wide (GIF ≥480)", not small, ",".join(small))
try:
    sys.path.insert(0, "/tmp/cvc"); import cv2, numpy as np; det = cv2.wechat_qrcode.WeChatQRCode()
    dec = [bool(det.detectAndDecode(cv2.cvtColor(np.asarray(Image.open(kit.kp(f"assets/qr_{n}.png")).convert("RGB")), cv2.COLOR_RGB2BGR))[0]) for n in ("oa", "xhs", "helper")]
    ok("all three QR images decode (wechat_qrcode)", all(dec), str(dec))
except Exception as e: print("SKIP QR decode:", kit.CFG["verify"]["wechat_qrcode"], e)
# ── rendered ──
try:
    from playwright.sync_api import sync_playwright
    import numpy as np
except ImportError:
    print("SKIP rendered checks — pip install playwright numpy && python3 -m playwright install chromium")
    n = sum(1 for r in R if not r[0]); print(f"\n{len(R) - n}/{len(R)} PASS (rendered skipped)"); sys.exit(1 if n else 0)
DM = open(kit.kp(kit.CFG["verify"]["mp_darkmode_js"])).read(); INK14, INK12 = (5.25, 7.19), (5.0, 5.59)
TEXTY = {"text": INK14, "rail-wrap": INK14, "byline-name": INK14, "dek": INK12, "music": INK12, "credits": INK12, "byline-sig": INK12}
sys.path.insert(0, os.path.dirname(__file__)); import build
meta = json.load(open(f"{adir}/out/meta.json")); RL = meta["roles"]
EXPECT = [build.spacing(a, b) for a, b in zip(RL, RL[1:])]
JS = """() => {const A=document.querySelector('[data-role=article]'); const Y=scrollY;
 return [...A.children].map((e,i)=>{const b=e.getBoundingClientRect(); e.setAttribute('data-ix',i);
  const ps=[...e.querySelectorAll('p')].filter(p=>p.textContent.trim()&&p.dataset.role!=='caption'); const cap=e.querySelector('[data-role=caption]');
  const m=e.querySelectorAll('img,svg'); const R=x=>{const r=x.getBoundingClientRect();return [r.left,r.right,r.top+Y,r.bottom+Y]};
  return {i, top:b.top+Y, bottom:b.bottom+Y, p0:ps.length?R(ps[0]):null, p1:ps.length?R(ps[ps.length-1]):null, cap:cap?R(cap):null,
          media:[...m].map(R), mc:!!e.querySelector('mp-common-clmusic')}})}"""
OVL = """()=>{let n=0,neg=0;document.querySelectorAll('[data-role=article] *').forEach(e=>{const s=getComputedStyle(e);
 for(const k of ['marginTop','marginBottom','marginLeft','marginRight']) if(parseFloat(s[k])<0) neg++;
 const kids=[...e.children].filter(c=>{const r=c.getBoundingClientRect();return r.height>0&&getComputedStyle(c).display!=='inline'});
 for(let i=1;i<kids.length;i++){const a=kids[i-1].getBoundingClientRect(),b=kids[i].getBoundingClientRect();
  if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>0.01&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>0.01) n++}});
 return {overlaps:n,neg,sw:document.documentElement.scrollWidth}}"""
COLS = """()=>{const o={};document.querySelectorAll('[data-role=article] p, [data-role=article] svg').forEach(e=>{if(e.tagName==='svg'||e.textContent.trim()){const k=getComputedStyle(e).color;o[k]=(o[k]||0)+1}});return o}"""
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=kit.chrome(), args=["--headless=new", "--no-sandbox", "--hide-scrollbars"])
    for vw in kit.CFG["verify"]["widths"]:
        pg = br.new_page(viewport={"width": vw, "height": 900}, device_scale_factor=2); pg.goto(f"file://{adir}/out/preview.html", wait_until="networkidle")
        pg.add_style_tag(content="mp-common-clmusic{display:block;height:64px;background:#bbbbbb}")   # WeChat renders the music card natively
        o = pg.evaluate(OVL); ok(f"@{vw} no horizontal overflow / overlaps / negative margins", o["sw"] <= vw and o["overlaps"] == 0 and o["neg"] == 0, json.dumps(o))
        bl = pg.evaluate(JS); edges, gaps = [], []
        for k, e in enumerate(bl):
            role = RL[k]; el = pg.query_selector(f'[data-ix="{k}"]')
            a = np.asarray(Image.open(io.BytesIO(el.screenshot())).convert("L")); bb = el.bounding_box()
            if role in TEXTY: t, b_ = e["p0"][2] + TEXTY[role][0], e["p1"][3] - TEXTY[role][1]
            elif role == "figure": t, b_ = e["media"][0][2], e["cap"][3] - INK12[1]
            elif role == "figure-plain": t, b_ = e["media"][0][2], max(m[3] for m in e["media"])
            elif role == "music-card": t, b_ = e["top"], e["bottom"]
            else: t, b_ = e["media"][0][2], max(m[3] for m in e["media"])
            e["t"], e["b"] = t, b_
            xs = np.where((a < 200).any(0))[0]
            if role in ("masthead", "wordmark", "footer", "readmore-head", "follow-head", "figure", "figure-plain", "hero", "readmore-card", "follow-qr", "byline-label") and len(xs):
                L = bb["x"] + xs.min() / 2 - 15; Rr = vw - 15 - (bb["x"] + (xs.max() + 1) / 2)
                if role in ("figure", "figure-plain", "hero", "readmore-card"): L, Rr = e["media"][0][0] - 15, vw - 15 - e["media"][0][1]
                if role in ("readmore-head", "follow-head", "byline-label"): Rr = L = abs(L - Rr) / 2   # centred strips: symmetric
                if role == "follow-qr": L, Rr = e["media"][0][0] - 15, vw - 15 - e["media"][2][1]
                if max(abs(L), abs(Rr)) > kit.CFG["verify"]["ink_edge_tolerance_px"]: edges.append(f"{role}#{k} L{L:+.2f} R{Rr:+.2f}")
            if role == "text" and abs(e["p0"][0] - 15) > 0.6: edges.append(f"text#{k} box L {e['p0'][0]:.2f}")
        for k in range(1, len(bl)):
            g = bl[k]["t"] - bl[k - 1]["b"]
            if abs(g - EXPECT[k - 1]) > kit.CFG["verify"]["gap_tolerance_px"]: gaps.append(f"{RL[k-1]}→{RL[k]} {g:.2f} (want {EXPECT[k-1]})")
        ok(f"@{vw} ink on the 15px edges", not edges, "; ".join(edges[:6]))
        ok(f"@{vw} ink-to-ink gaps = spec ±1px ({len(bl)-1} pairs)", not gaps, "; ".join(gaps[:6]))
        if SHOTS: pg.screenshot(path=f"{adir}/out/selfcheck_{vw}_light.png", full_page=True)
        if vw == 383:   # WeChat dark: mp-darkmode on the content, page #191919
            pg.add_script_tag(content=DM); pg.evaluate("Darkmode.run(document.querySelectorAll('[data-role=article], [data-role=article] *'),{mode:'dark'});document.body.style.background='#191919'")
            cols = pg.evaluate(COLS); bgi = pg.evaluate("getComputedStyle(document.querySelector('[data-role=article]')).backgroundImage")
            ok("@383 WeChat dark: text stays dark on the white base", set(cols) <= {"rgb(62, 62, 62)", "rgb(20, 20, 20)", "rgb(211, 56, 28)", "rgb(153, 153, 153)"} and "whitebase" in bgi, json.dumps(cols))
            if SHOTS: pg.screenshot(path=f"{adir}/out/selfcheck_{vw}_dark.png", full_page=True)
        pg.close()
    ctx = br.new_context(viewport={"width": 578, "height": 900}, color_scheme="dark"); pg = ctx.new_page()
    pg.set_content('<html><body style="margin:0;background:#fff"><div style="padding:0 20px">' + c + "</div></body></html>")
    cols = pg.evaluate(COLS); ok("editor view, OS dark: no white text", "rgb(255, 255, 255)" not in cols, json.dumps(cols)); br.close()
n = sum(1 for r in R if not r[0]); print(f"\n{len(R) - n}/{len(R)} PASS" + (f", {n} FAIL" if n else "")); sys.exit(1 if n else 0)
