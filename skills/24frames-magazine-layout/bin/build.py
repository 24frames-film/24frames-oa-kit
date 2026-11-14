#!/usr/bin/env python3
"""Build a 24帧 OA article from <article_dir>/article.md.
usage: python3 bin/build.py <article_dir>
→ <article_dir>/out/content.html (the WeChat body, local srcs, data-local attrs), out/preview.html (page wrapper),
  out/used.txt (local images in order), out/meta.json (title/digest/author/cover settings).
Needs out/svg/wm_NN.svg (bin/wordmarks.py) and out/readmore_card.jpg (bin/readmore.py) — `bin/make.py` runs all three.
Paths: article images are relative to <article_dir>; kit assets are written as "@kit/…" and resolved by kit.res()."""
import os, re, sys, json; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit
ACC = "#D3381C"
FONT = "PingFangSC-light,'PingFang SC','Hiragino Sans GB','Microsoft YaHei','Noto Sans CJK SC',sans-serif"
BODY = (f"margin:0;padding:0;font-family:{FONT};font-size:14px;font-weight:300;line-height:1.8;letter-spacing:1.5px;"
        f"color:#3E3E3E;text-align:justify;text-indent:0;box-sizing:border-box;overflow-wrap:break-word;word-break:break-word;")
CAPF = (f"font-family:{FONT};font-size:12px;font-weight:300;line-height:1.8;letter-spacing:1px;color:{ACC};"
        f"text-align:justify;box-sizing:border-box;overflow-wrap:break-word;word-break:break-word;")
SMALL = (f"margin:0;padding:0;font-family:{FONT};font-size:12px;font-weight:300;line-height:1.8;letter-spacing:1px;"
         f"color:#3E3E3E;text-align:justify;box-sizing:border-box;")
BR = f'<p style="{BODY}"><br></p>'
INK14, INK12 = (5.25, 7.19), (5.0, 5.59)           # live text ink inside its line box (14/1.8, 12/1.8)
GAP_ATTACHED, GAP_TIGHT, GAP_FLOW, GAP_HEADING, TOP_MASTHEAD = 16, 24, 48, 48, 24
CAP_MT = round(GAP_ATTACHED - INK12[0])             # image bottom → caption ink top = 16
PAD_BODY, PAD_SMALL, PAD_IMG = "padding:0 13.5px 0 15px;", "padding:0 14px 0 15px;", "padding:0 15px;"
MUSIC_HINT = '<span textstyle="" style="color: rgb(136, 136, 136);font-style: italic;text-decoration: none;">（请点击音乐继续阅读）</span>'
QR = (("@kit/assets/qr_oa.png", "0", "24帧公众号二维码"), ("@kit/assets/qr_xhs.png", "10.016%", "24帧小红书二维码"), ("@kit/assets/qr_helper.png", "10.016%", "24帧小助手二维码"))
def spacing(prev, nxt):
    if nxt == "wordmark" or prev == "wordmark": return GAP_HEADING
    if (prev, nxt) == ("hero", "dek"): return GAP_TIGHT
    if (prev, nxt) == ("rail-wrap", "rail-wrap"): return GAP_TIGHT
    if (prev, nxt) in (("readmore-head", "readmore-card"), ("follow-head", "follow-qr")): return GAP_HEADING
    if (prev, nxt) in (("byline-label", "byline-name"), ("byline-name", "byline-sig")): return GAP_ATTACHED
    return GAP_FLOW
def ink_off(role):
    if role in ("text", "rail-wrap", "byline-name"): return INK14
    if role in ("dek", "music", "credits", "byline-sig"): return INK12
    if role == "figure": return (0, INK12[1])
    if role == "figure-plain": return (0, 0)
    return (0, 0)                                   # ink-tight SVGs, photos, cards, QR row
def parse(md):
    fm, body = {}, md
    if md.startswith("---\n"):
        head, body = md[4:].split("\n---\n", 1)
        for l in head.splitlines():
            if ":" in l and not l.startswith("#"): k, v = l.split(":", 1); fm[k.strip()] = v.strip()
    return fm, [l.strip() for l in body.splitlines()]
def build(adir):
    md = open(f"{adir}/article.md", encoding="utf-8").read(); fm, lines = parse(md)
    for k in ("title", "author", "hero", "byline_name", "byline_sig", "readmore_url", "readmore_title"): assert fm.get(k), f"frontmatter: {k} missing"
    wmlog = json.load(open(f"{adir}/out/svg/wordmarks.json")); strip = json.load(open(kit.kp("assets/strip_ink.json")))
    used = []
    def u(p): used.append(p); return p
    def strong(t, color="#3E3E3E"):
        return "".join(f'<strong style="font-weight:600;color:{color};">{x}</strong>' if i % 2 else x for i, x in enumerate(t.split("**")))
    def img(p, alt=""):
        if p.endswith(".svg"):
            svg = open(kit.res(p, adir), encoding="utf-8").read().replace("<svg ", f'<svg data-local="{p}" ', 1)
            col = (strip.get(os.path.basename(p)) or wmlog.get(os.path.basename(p)))["colour"]
            return f'<section style="box-sizing:border-box;margin:0;padding:0;line-height:0;color:{col};">{svg}</section>'
        return (f'<img src="{u(p)}" width="100%" alt="{alt}" data-local="{p}" '
                f'style="width:100%;height:auto;display:block;vertical-align:top;margin:0 auto;padding:0;border:0;box-sizing:border-box;">')
    B = []   # (role, html with a single leading "margin:0;" placeholder in the block style)
    def add(role, h): B.append((role, h))
    def col(p, role, data_role=None, pad=PAD_IMG):
        add(role, f'<section data-role="{data_role or role}" style="box-sizing:border-box;width:100%;margin:0;{pad}line-height:0;">{img(p)}</section>')
    buf = []
    def flush():
        if buf: add("text", f'<section data-role="text" style="box-sizing:border-box;width:100%;margin:0;{PAD_BODY}">' + BR.join(f'<p style="{BODY}">{strong(p)}</p>' for p in buf) + '</section>'); buf.clear()
    def small(t, color, role):
        add(role, f'<section data-role="{role}" style="box-sizing:border-box;width:100%;margin:0;{PAD_SMALL}"><p style="{SMALL}color:{color};">{t}</p></section>')
    _lab = fm.get("cover_label", "Play")
    _mast = "@kit/assets/masthead.svg" if _lab == "Play" else f"out/svg/masthead_{_lab.lower()}.svg"
    col(_mast, "masthead", pad=f"padding:{TOP_MASTHEAD}px 15px 0;")
    col(fm["hero"], "hero"); credits = []
    for l in lines:
        if not l or l == "---" or l.startswith("# "): continue
        assert not l.startswith("【"), f"unresolved marker: {l[:30]}"
        if l.startswith("### "): flush(); small(l[4:], ACC, "dek"); continue
        m = re.match(r"## (\d\d) (.+?)\s*\|\s*(.+)$", l)
        if m:
            flush(); add("wordmark", f'<section data-role="wordmark" style="box-sizing:border-box;width:100%;margin:0;{PAD_IMG}line-height:0;">{img(f"out/svg/wm_{m.group(1)}.svg")}</section>'); continue
        m = re.match(r"!\[(.*)\]\((.+)\)$", l)
        if m:
            flush(); files = m.group(2).split(); caps = [c.strip() for c in m.group(1).split("//") if c.strip()]
            imgs = "".join(f'<section style="box-sizing:border-box;width:100%;margin:{"4px" if i else "0"} 0 0;padding:0;line-height:0;">{img(f)}</section>' for i, f in enumerate(files))
            cap_html = (f'<p data-role="caption" style="margin:{CAP_MT}px 0 0 0;padding:0;{CAPF}">{"<br>".join(caps)}</p>' if caps else "")
            role = "figure" if caps else "figure-plain"
            add(role, f'<section data-role="figure" data-kind="{"pair" if len(files) > 1 else "single"}" style="box-sizing:border-box;width:100%;margin:0;{PAD_IMG}">'
                f'{imgs}{cap_html}</section>'); continue
        if l == "[[music-card]]":
            for k in ("music_name", "music_singer", "music_albumurl", "music_duration", "music_listenid"): assert fm.get(k), f"[[music-card]] needs frontmatter {k} (copy it from the card inserted in the mp editor) — or delete the line"
            flush(); r, h = B[-1]; assert r == "text", "[[music-card]] must follow a paragraph"
            B[-1] = (r, h[:-len("</section>")] + f'<p style="{BODY}">{MUSIC_HINT}</p></section>')
            card = ('<mp-common-clmusic class="res_iframe clmusic_iframe js_uneditable custom_select_card" data-pluginname="insertaudio" type="1" '
                    f'music_name="{fm["music_name"]}" albumurl="{fm["music_albumurl"]}" singer="{fm["music_singer"]}" count="0" is_vip="0" '
                    f'duration="{fm["music_duration"]}" music_source="1" listenid="{fm["music_listenid"]}"></mp-common-clmusic>')
            add("music-card", f'<section data-role="music-card" style="box-sizing:border-box;width:100%;margin:0;{PAD_IMG}"><section nodeleaf="">{card}</section></section>'); continue
        if l.startswith("♪"): flush(); small(l, ACC + ";text-indent:-3px", "music"); continue
        if l.startswith(">> "):
            flush(); m = re.match(r"\*\*(.+?)\*\*(.*)", l[3:])
            add("rail-wrap", f'<section data-role="rail-wrap" style="box-sizing:border-box;width:100%;margin:0;{PAD_BODY}">'
                f'<section data-role="rail" style="box-sizing:border-box;width:85%;margin:0 0 0 15%;padding:0;text-align:left;">'
                f'<p style="{BODY}"><strong style="font-weight:600;color:{ACC};">{m.group(1)}</strong>{m.group(2)}</p></section></section>'); continue
        if l == "[[byline]]":
            flush(); ctr = "text-align:center;text-align-last:center;"
            col("@kit/assets/byline_label.svg", "byline-label")
            add("byline-name", f'<section data-role="byline-name" style="box-sizing:border-box;width:100%;margin:0;{PAD_BODY}"><p style="{BODY}font-weight:600;{ctr}">{fm["byline_name"]}</p></section>')
            add("byline-sig", f'<section data-role="byline-sig" style="box-sizing:border-box;width:100%;margin:0;{PAD_SMALL}"><p style="{SMALL}color:#999999;{ctr}">{fm["byline_sig"]}</p></section>'); continue
        if l.startswith("[credit] "): credits.append(l[9:]); continue
        buf.append(l)
    flush()
    add("credits", f'<section data-role="credits" style="box-sizing:border-box;width:100%;margin:0;{PAD_SMALL}">' + "".join(f'<p style="{SMALL}">{c}</p>' for c in credits) + '</section>')
    col("@kit/assets/footer.svg", "footer", "footer-card")
    col("@kit/assets/read_more.svg", "readmore-head", "footer-card")
    t = fm["readmore_title"]
    add("readmore-card", f'<section data-role="figure" data-kind="readmore-card" style="box-sizing:border-box;width:100%;margin:0;{PAD_IMG}line-height:0;">'
        f'<a href="{fm["readmore_url"]}" target="_blank" title="{t}" style="display:block;width:100%;margin:0;padding:0;border:0;text-decoration:none;line-height:0;">{img("out/readmore_card.jpg", t)}</a></section>')
    col("@kit/assets/follow_head.svg", "follow-head", "footer-card")
    # QR row: the ONLY flex / inline-block / % exception (WeChat long-press recognises one code per image)
    cells = "".join(f'<section style="box-sizing:border-box;display:inline-block;vertical-align:top;width:26.656%;flex:0 0 26.656%;margin:0 0 0 {ml};padding:0;line-height:0;">'
                    f'<img src="{u(p)}" width="100%" alt="{alt}" data-local="{p}" style="width:100%;height:auto;display:block;vertical-align:top;margin:0;padding:0;border:0;box-sizing:border-box;"></section>' for p, ml, alt in QR)
    qg = round(strip["follow_qr_labels.svg"]["gap_from_codes_canvas_px"] * 353 / 1238)
    add("follow-qr", f'<section data-role="footer-card" style="box-sizing:border-box;width:100%;margin:0;{PAD_IMG}line-height:0;">'
        f'<section data-role="qr-row" style="box-sizing:border-box;display:flex;flex-direction:row;align-items:flex-start;width:100%;margin:0;padding:0;line-height:0;font-size:0;">{cells}</section>'
        + img("@kit/assets/follow_qr_labels.svg").replace("margin:0;padding:0;", f"margin:{qg}px 0 0;padding:0;", 1) + "</section>")
    out, prev = [], None
    for role, h in B:
        mt = 0 if prev is None else max(0, round(spacing(prev, role) - ink_off(prev)[1] - ink_off(role)[0]))
        out.append(h.replace("margin:0;", f"margin:{mt}px 0 0;" if prev is not None else "margin:0;", 1)); prev = role
    WB = u("@kit/assets/whitebase.jpg")
    body = ('<section data-role="article" style="box-sizing:border-box;width:100%;margin:0;padding:0 0 40px;'
            f'background-image:url(&quot;{WB}&quot;);background-repeat:repeat-y;background-size:100% auto;background-position:0% 0%;color:#3E3E3E;">' + "".join(out) + '</section>')
    meta = dict(title=fm["title"], author=fm["author"], digest=fm.get("digest") or next(l[4:] for l in lines if l.startswith("### ")),
                cover_still=fm.get("cover_still"), cover_label=fm.get("cover_label", "Play"), roles=[r for r, _ in B])
    return body, used, meta
def page(body, title):
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title></head><body style="margin:0;padding:0;background:#ffffff;">{body}</body></html>')
if __name__ == "__main__":
    adir = os.path.abspath(sys.argv[1]); body, used, meta = build(adir); os.makedirs(f"{adir}/out", exist_ok=True)
    open(f"{adir}/out/content.html", "w", encoding="utf-8").write(body)
    # preview page: local files resolved to file paths so Chrome can render it
    pv = re.sub(r'(src="|url\(&quot;)([^"&]+)', lambda m: m.group(1) + "file://" + kit.res(m.group(2), adir), body)
    open(f"{adir}/out/preview.html", "w", encoding="utf-8").write(page(pv, meta["title"]))
    open(f"{adir}/out/used.txt", "w").write("\n".join(used) + "\n"); json.dump(meta, open(f"{adir}/out/meta.json", "w"), ensure_ascii=False, indent=1)
    print(f"out/content.html {len(body)} chars, {len(used)} images, {len(meta['roles'])} blocks")
