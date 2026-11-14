#!/usr/bin/env python3
"""WeChat draft tool for one article. NEVER publishes (freepublish / mass send are blocked in lib/wechat.py).
usage:
  python3 bin/draft.py <article_dir> dry-run            # map images (fake URLs), write out/content_cdn.html — no network
  python3 bin/draft.py <article_dir> upload             # upload body images (uploadimg; GIF → add_material), cache in out/img_map.json
  python3 bin/draft.py <article_dir> upload --material  # body images via material/add_material (type=image, 10MB, no 1MB recompress)
  python3 bin/draft.py <article_dir> add --yes-add      # ONE draft/add (refuses if out/wechat_state.json already has a draft)
  python3 bin/draft.py <article_dir> get                # draft/get → out/readback_<time>.html + out/preview_url.txt
  python3 bin/draft.py <article_dir> update <content.html> --yes-update   # draft/update index 0 of THIS article's draft only
Cover: out/cover/cover_h.jpg (bin/cover.py) → add_material; cover_info crop list from kit.json (2.35:1 full, 1:1 centre)."""
import os, re, sys, json, time; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit, wechat as w
adir = os.path.abspath(sys.argv[1]); cmd = sys.argv[2]; O = f"{adir}/out"
MAP, STATE = f"{O}/img_map.json", f"{O}/wechat_state.json"
meta = json.load(open(f"{O}/meta.json")); st = json.load(open(STATE)) if os.path.exists(STATE) else {}
def save(): json.dump(st, open(STATE, "w"), ensure_ascii=False, indent=1)
def images(c): return list(dict.fromkeys(re.findall(r'data-local="([^"]+\.(?:jpg|jpeg|png|gif))"', c) + re.findall(r'url\(&quot;([^&]+)&quot;', c)))
def upload(dry):
    c = open(f"{O}/content.html", encoding="utf-8").read(); m = json.load(open(MAP)) if os.path.exists(MAP) else {}
    for rel in images(c):
        p = kit.res(rel, adir); h = w.sha1(p)
        if rel in m and m[rel]["sha1"] == h: continue
        if dry: m[rel] = {"url": f"https://DRYRUN/{os.path.basename(p)}", "sha1": h, "dry": True}; continue
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif"}[p.rsplit(".", 1)[1].lower()]
        use_material = mime == "image/gif" or "--material" in sys.argv
        if use_material:
            if os.path.getsize(p) > 10 * 1024 * 1024: sys.exit(f"cannot upload {p}: over 10MB material limit")
            up, note = p, "add_material" if mime != "image/gif" else "add_material gif"
        else:
            up, note = w.prepare(p)
        files = {"media": (os.path.basename(up), open(up, "rb"), mime)}
        j = w.call("POST", "material/add_material", params={"type": "image"}, files=files) if use_material else w.call("POST", "media/uploadimg", files=files)
        m[rel] = {"url": j["url"].replace("http://", "https://"), "sha1": h, "media_id": j.get("media_id", ""), "note": note, "via": "add_material" if use_material else "uploadimg"}; print("[up]", rel, note)
        json.dump(m, open(MAP, "w"), indent=1)
    if not dry: json.dump(m, open(MAP, "w"), indent=1)
    def url(rel): return m[rel]["url"]
    c = re.sub(r'(<img[^>]*?\ssrc=")([^"]+)(")', lambda x: x.group(1) + url(x.group(2)) + x.group(3), c)
    c = re.sub(r'url\(&quot;([^&]+)&quot;\)', lambda x: f"url(&quot;{url(x.group(1))}&quot;)", c)
    c = re.sub(r'\sdata-local="[^"]*"', "", c)
    assert "&#39;" not in c and "@kit/" not in c and not re.search(r'src="(?!https://)', c)
    open(f"{O}/content_cdn.html" if not dry else f"{O}/content_dryrun.html", "w", encoding="utf-8").write(c)
    n = len(images(open(f"{O}/content.html", encoding="utf-8").read())); print(f"[{'dry-run' if dry else 'upload'}] {n} images mapped → {'content_dryrun.html' if dry else 'content_cdn.html'} ({len(c)} chars)")
    return c
def article(content, thumb):
    return dict(title=meta["title"], author=meta["author"], digest=meta["digest"][:120], content=content, content_source_url="",
                thumb_media_id=thumb, need_open_comment=1, only_fans_can_comment=0, cover_info=kit.CFG["cover"]["cover_info"])
if cmd == "dry-run":
    c = upload(True); a = article(c, "DRYRUN_THUMB"); a["content"] = f"<{len(c)} chars>"; print(json.dumps(a, ensure_ascii=False, indent=1)); sys.exit()
if cmd == "upload": upload(False); sys.exit()
if cmd == "add":
    if "--yes-add" not in sys.argv: sys.exit("refusing: draft/add needs --yes-add (and the user's explicit approval for this one draft)")
    if st.get("draft_media_id"): sys.exit(f"refusing: this article already has a draft ({st['draft_media_id']}); use update")
    c = upload(False); cov = f"{O}/cover/cover_h.jpg"; assert os.path.exists(cov), "run bin/cover.py first"
    j = w.call("POST", "material/add_material", params={"type": "image"}, files={"media": ("cover_h.jpg", open(cov, "rb"), "image/jpeg")})
    st["cover"] = {"media_id": j["media_id"], "sha1": w.sha1(cov)}
    j = w.jpost("draft/add", {"articles": [article(c, st["cover"]["media_id"])]})
    st["draft_media_id"] = j["media_id"]; st["created"] = time.strftime("%Y-%m-%d %H:%M:%S %z"); save(); print("[draft/add] media_id", j["media_id"]); cmd = "get"
if cmd == "get":
    a = w.jpost("draft/get", {"media_id": st["draft_media_id"]})["news_item"][0]; ts = time.strftime("%H%M%S")
    open(f"{O}/readback_{ts}.html", "w", encoding="utf-8").write(a["content"]); open(f"{O}/preview_url.txt", "w").write(a["url"].replace("http://", "https://"))
    print({k: (v if k != "content" else f"<{len(v)} chars>") for k, v in a.items() if k != "url"}, "\nread-back → out/readback_%s.html, preview url → out/preview_url.txt" % ts); sys.exit()
if cmd == "update":
    if "--yes-update" not in sys.argv: sys.exit("refusing: draft/update needs --yes-update")
    c = open(sys.argv[3], encoding="utf-8").read().replace("&#39;", "'"); assert "data-local" not in c and "@kit/" not in c
    a = w.jpost("draft/get", {"media_id": st["draft_media_id"]})["news_item"][0]
    open(f"{O}/before_update_{time.strftime('%H%M%S')}.html", "w", encoding="utf-8").write(a["content"])   # rollback copy
    keep = ("title", "digest", "content_source_url", "thumb_media_id", "need_open_comment", "only_fans_can_comment", "article_type", "cover_info", "author")
    art = {k: a[k] for k in keep if k in a}; art["content"] = c
    print(w.jpost("draft/update", {"media_id": st["draft_media_id"], "index": 0, "articles": art}))
    st.setdefault("updates", []).append(time.strftime("%Y-%m-%d %H:%M:%S %z")); save(); sys.exit()
sys.exit(__doc__)
